from __future__ import annotations

import io
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.credential import Credential
from app.models.script import Script
from app.models.server import Server
from app.models.task import Task, TaskStatus
from app.worker.celery_app import celery_app
from app.worker.runner import DockerRunner
from app.worker.ssh_runner import FingerprintMismatchError, SSHRunner

logger = logging.getLogger(__name__)

_sync_url = (
    settings.DATABASE_URL
    .replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    .replace("postgresql://", "postgresql+psycopg2://")
)
_engine = create_engine(_sync_url, pool_pre_ping=True, pool_size=5)
_Session = sessionmaker(bind=_engine, expire_on_commit=False)


def _upload_log_to_minio(object_key: str, content: str) -> None:
    """Upload task log to MinIO; swallows errors to avoid failing the task."""
    try:
        from minio import Minio  # type: ignore
        client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        data = content.encode("utf-8")
        client.put_object(
            settings.MINIO_BUCKET,
            object_key,
            io.BytesIO(data),
            length=len(data),
            content_type="text/plain",
        )
    except Exception as exc:
        logger.warning("MinIO upload failed for %s: %s", object_key, exc)


@celery_app.task(bind=True, name="execute_script_task", max_retries=0)
def execute_script_task(self, task_id: str) -> dict:
    logger.info("Worker picked up task %s", task_id)
    with _Session() as db:
        task: Task | None = db.get(Task, uuid.UUID(task_id))
        if task is None:
            logger.error("Task %s not found", task_id)
            return {"error": "Task not found"}

        script: Script | None = db.get(Script, task.script_id)
        if script is None:
            _fail_task(db, task, "Script not found")
            return {"error": "Script not found"}

        task.status = TaskStatus.running
        task.started_at = datetime.now(timezone.utc)
        db.commit()

        try:
            if task.server_id is not None:
                result_dict = _run_via_ssh(db, task, script)
            else:
                result_dict = _run_via_docker(task, script)
        except FingerprintMismatchError as exc:
            logger.error("Fingerprint mismatch for task %s: %s", task_id, exc)
            _fail_task(db, task, str(exc))
            return {"error": str(exc)}
        except Exception as exc:
            logger.exception("Runner raised for task %s", task_id)
            _fail_task(db, task, str(exc))
            return {"error": str(exc)}

        task.stdout = result_dict["stdout"]
        task.stderr = result_dict["stderr"]
        task.exit_code = result_dict["exit_code"]
        task.container_id = result_dict.get("container_id")
        task.finished_at = datetime.now(timezone.utc)
        timed_out = result_dict.get("timed_out", False)
        task.status = (
            TaskStatus.timeout
            if (timed_out or result_dict["exit_code"] == 124)
            else TaskStatus.success
            if result_dict["exit_code"] == 0
            else TaskStatus.failed
        )

        # Upload combined log to MinIO
        log_key = f"task-logs/{task_id}.txt"
        combined_log = f"=== STDOUT ===\n{task.stdout}\n\n=== STDERR ===\n{task.stderr}"
        _upload_log_to_minio(log_key, combined_log)
        task.log_object_key = log_key

        db.commit()

    logger.info("Task %s finished: %s (exit=%s)", task_id, task.status, task.exit_code)
    return {"task_id": task_id, "status": task.status.value}


def _run_via_docker(task: Task, script: Script) -> dict:
    result = DockerRunner().run_task(
        task_id=str(task.id),
        script_content=script.content,
        script_type=script.script_type.value,
        parameters=task.parameters,
    )
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
        "container_id": result.container_id,
        "timed_out": result.timed_out,
    }


def _run_via_ssh(db, task: Task, script: Script) -> dict:
    from app.services.credential_service import CredentialService

    server: Server | None = db.get(Server, task.server_id)
    if server is None:
        raise RuntimeError(f"Server {task.server_id} not found")

    secret: str | None = None
    ssh_username: str = "root"
    cred_type: str = "password"

    if task.credential_id is not None:
        credential: Credential | None = db.get(Credential, task.credential_id)
        if credential is None:
            raise RuntimeError(f"Credential {task.credential_id} not found")
        secret = CredentialService.decrypt(credential.secret_enc)
        ssh_username = credential.username
        cred_type = credential.cred_type

    if secret is None:
        raise RuntimeError("No credential supplied for SSH task")

    timeout = task.timeout_seconds or settings.TASK_TIMEOUT

    run_result, new_fingerprint = SSHRunner().run_task(
        host=server.host,
        port=server.port,
        ssh_username=ssh_username,
        secret=secret,
        cred_type=cred_type,
        script_content=script.content,
        script_type=script.script_type.value,
        stored_fingerprint=server.fingerprint,
        timeout=timeout,
    )
    secret = ""  # clear from memory

    if new_fingerprint:
        server.fingerprint = new_fingerprint
        db.commit()

    return {
        "stdout": run_result.stdout,
        "stderr": run_result.stderr,
        "exit_code": run_result.exit_code,
        "container_id": None,
        "timed_out": run_result.timed_out,
    }


def _fail_task(db, task: Task, msg: str) -> None:
    task.status = TaskStatus.failed
    task.stderr = msg
    task.finished_at = datetime.now(timezone.utc)
    db.commit()
