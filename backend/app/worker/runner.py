import base64
import logging
from dataclasses import dataclass

import docker
import docker.errors

from app.core.config import settings

logger = logging.getLogger(__name__)

_MAX_LOG_BYTES = 10 * 1024 * 1024  # 10 MiB


@dataclass
class RunResult:
    exit_code: int
    stdout: str
    stderr: str
    container_id: str
    timed_out: bool = False


class DockerRunner:
    """Runs a script in an ephemeral, heavily-sandboxed Docker container.

    Security constraints (every container):
    - Non-root user 1000:1000
    - No network access (network_mode=none)
    - Read-only root filesystem + small noexec /tmp tmpfs
    - Memory capped at 256 MiB, CPU at 0.5 cores
    - All Linux capabilities dropped, no-new-privileges
    - Container destroyed immediately after execution
    """

    def __init__(self) -> None:
        self._client = docker.DockerClient(base_url=f"unix://{settings.DOCKER_SOCKET}")

    def run_task(
        self,
        task_id: str,
        script_content: str,
        script_type: str,
        parameters: dict | None = None,
    ) -> RunResult:
        container = None
        container_id = "unknown"
        try:
            logger.info("Starting container for task %s", task_id)
            container = self._client.containers.run(
                image=settings.EXECUTION_IMAGE,
                # SECURITY: script content passed base64-encoded to avoid shell
                # metacharacter injection at the env-var boundary
                environment={
                    "CIS_TASK_ID": task_id,
                    "SCRIPT_TYPE": script_type,
                    "SCRIPT_CONTENT": base64.b64encode(
                        script_content.encode("utf-8")
                    ).decode("ascii"),
                    **(
                        {f"CIS_PARAM_{self._sanitize_param_name(k)}": str(v) for k, v in parameters.items()}
                        if parameters else {}
                    ),
                },
                user="1000:1000",
                network_mode="none",
                read_only=True,
                mem_limit=settings.MAX_MEMORY,
                nano_cpus=int(settings.MAX_CPUS * 1_000_000_000),
                security_opt=["no-new-privileges:true"],
                cap_drop=["ALL"],
                tmpfs={"/tmp": "size=64m,noexec,nosuid"},
                auto_remove=False,
                detach=True,
                labels={"cis.task_id": task_id},
            )
            container_id = container.id

            try:
                result = container.wait(timeout=settings.TASK_TIMEOUT)
                exit_code: int = result.get("StatusCode", -1)
                timed_out = False
            except Exception:
                logger.warning("Task %s timed out, killing container", task_id)
                container.kill()
                exit_code = -1
                timed_out = True

            stdout, stderr = self._collect_logs(container)
            return RunResult(
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                container_id=container_id,
                timed_out=timed_out,
            )

        except docker.errors.ImageNotFound:
            return RunResult(
                exit_code=-1, stdout="",
                stderr=f"Execution image '{settings.EXECUTION_IMAGE}' not found",
                container_id=container_id,
            )
        except Exception as exc:
            logger.exception("Runner error for task %s: %s", task_id, exc)
            return RunResult(exit_code=-1, stdout="", stderr=str(exc), container_id=container_id)
        finally:
            self._cleanup(container)

    @staticmethod
    def _sanitize_param_name(key: str) -> str:
        """Convert a parameter key to a safe env-var name suffix."""
        return "".join(c if c.isalnum() or c == "_" else "_" for c in key.upper())

    @staticmethod
    def _collect_logs(container) -> tuple[str, str]:
        try:
            raw_out = container.logs(stdout=True, stderr=False)
            raw_err = container.logs(stdout=False, stderr=True)
            return (
                raw_out[:_MAX_LOG_BYTES].decode("utf-8", errors="replace"),
                raw_err[:_MAX_LOG_BYTES].decode("utf-8", errors="replace"),
            )
        except Exception as exc:
            return "", f"Log collection failed: {exc}"

    @staticmethod
    def _cleanup(container) -> None:
        if container is None:
            return
        try:
            container.remove(force=True)
        except docker.errors.NotFound:
            pass
        except Exception as exc:
            logger.warning("Container cleanup error: %s", exc)
