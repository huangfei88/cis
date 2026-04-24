from __future__ import annotations

import base64
import hashlib
import io
import logging
import os
import socket
from dataclasses import dataclass, field

import paramiko

logger = logging.getLogger(__name__)


@dataclass
class SSHRunResult:
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    timed_out: bool = False


class FingerprintMismatchError(Exception):
    pass


class _VerifyPolicy(paramiko.MissingHostKeyPolicy):
    """
    Custom host-key policy.

    - If stored_fingerprint is None: first connect, record the fingerprint.
    - Otherwise: verify fingerprint matches; raise FingerprintMismatchError on mismatch.
    """

    def __init__(self, stored_fingerprint: str | None) -> None:
        self.stored_fingerprint = stored_fingerprint
        self.observed_fingerprint: str | None = None

    def missing_host_key(self, client: paramiko.SSHClient, hostname: str, key: paramiko.PKey) -> None:
        fp = "SHA256:" + base64.b64encode(hashlib.sha256(key.asbytes()).digest()).decode()
        self.observed_fingerprint = fp
        if self.stored_fingerprint is None:
            # First connection – trust and record
            logger.info("SSH: recording new fingerprint %s for %s", fp, hostname)
            return
        if fp != self.stored_fingerprint:
            raise FingerprintMismatchError(
                f"Host key fingerprint mismatch for {hostname}: "
                f"expected {self.stored_fingerprint!r}, got {fp!r}"
            )


class SSHRunner:
    def run_task(
        self,
        *,
        host: str,
        port: int,
        ssh_username: str,
        secret: str,
        cred_type: str,
        script_content: str,
        script_type: str,
        stored_fingerprint: str | None,
        timeout: int = 300,
    ) -> tuple[SSHRunResult, str | None]:
        """
        Execute a script on a remote host via SSH.

        Returns:
            (SSHRunResult, new_fingerprint | None)
            new_fingerprint is set only when this was the first connection
            (stored_fingerprint was None).
        """
        policy = _VerifyPolicy(stored_fingerprint)
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(policy)

        pkey: paramiko.PKey | None = None
        try:
            if cred_type == "private_key":
                pkey = paramiko.RSAKey.from_private_key(io.StringIO(secret))

            connect_kwargs: dict = {
                "hostname": host,
                "port": port,
                "username": ssh_username,
                "timeout": 30,
                "banner_timeout": 30,
                "auth_timeout": 30,
            }
            if pkey is not None:
                connect_kwargs["pkey"] = pkey
            else:
                connect_kwargs["password"] = secret

            client.connect(**connect_kwargs)
        finally:
            # SECURITY: best-effort memory clearing; Python does not guarantee
            # immediate GC or memory zeroing, but this limits the window.
            secret = ""

        new_fingerprint: str | None = None
        if stored_fingerprint is None and policy.observed_fingerprint is not None:
            new_fingerprint = policy.observed_fingerprint

        result = SSHRunResult()
        try:
            remote_path = f"/tmp/cis_{os.urandom(8).hex()}.sh"
            sftp = client.open_sftp()
            try:
                with sftp.file(remote_path, "w") as fh:
                    fh.write(script_content)
                sftp.chmod(remote_path, 0o700)
            finally:
                sftp.close()

            chan = client.get_transport().open_session()
            chan.settimeout(timeout)
            try:
                chan.exec_command(f"bash {remote_path}")
                stdout_data = b""
                stderr_data = b""
                while True:
                    try:
                        chunk = chan.recv(4096)
                        if chunk:
                            stdout_data += chunk
                        else:
                            break
                    except socket.timeout:
                        result.timed_out = True
                        break

                while chan.recv_stderr_ready():
                    stderr_data += chan.recv_stderr(4096)

                result.exit_code = chan.recv_exit_status() if not result.timed_out else 124
                result.stdout = stdout_data.decode("utf-8", errors="replace")
                result.stderr = stderr_data.decode("utf-8", errors="replace")
            finally:
                try:
                    chan.exec_command(f"rm -f {remote_path}")
                except Exception:
                    pass
                chan.close()
        finally:
            client.close()
            if pkey is not None:
                del pkey

        return result, new_fingerprint
