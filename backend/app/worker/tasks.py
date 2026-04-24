import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.script import Script
from app.models.task import Task, TaskStatus
from app.worker.celery_app import celery_app
from app.worker.runner import DockerRunner

logger = logging.getLogger(__name__)

# Workers use the synchronous psycopg2 driver (Celery is not async-native)
_sync_url = (
    settings.DATABASE_URL
    .replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    .replace("postgresql://", "postgresql+psycopg2://")
)
_engine = create_engine(_sync_url, pool_pre_ping=True, pool_size=5)
_Session = sessionmaker(bind=_engine, expire_on_commit=False)


@celery_app.task(bind=True, name="execute_script_task", max_retries=0)
def execute_script_task(self, task_id: str) -> dict:
    """Fetch task from DB, run sandboxed container, write results back."""
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
            result = DockerRunner().run_task(
                task_id=task_id,
                script_content=script.content,
                script_type=script.script_type.value,
                parameters=task.parameters,
            )
        except Exception as exc:
            logger.exception("Runner raised for task %s", task_id)
            _fail_task(db, task, str(exc))
            return {"error": str(exc)}

        task.stdout = result.stdout
        task.stderr = result.stderr
        task.exit_code = result.exit_code
        task.container_id = result.container_id
        task.finished_at = datetime.now(timezone.utc)
        # exit code 124 = soft timeout: the `timeout` command inside the
        # container sent SIGTERM and the process did not exit in time.
        # result.timed_out = hard timeout: Docker's container.wait() expired
        # and container.kill() (SIGKILL) was sent.  Both map to TaskStatus.timeout.
        task.status = (
            TaskStatus.timeout if (result.timed_out or result.exit_code == 124)
            else TaskStatus.success if result.exit_code == 0
            else TaskStatus.failed
        )
        db.commit()

    logger.info("Task %s finished: %s (exit=%s)", task_id, task.status, result.exit_code)
    return {"task_id": task_id, "status": task.status.value}


def _fail_task(db, task: Task, msg: str) -> None:
    task.status = TaskStatus.failed
    task.stderr = msg
    task.finished_at = datetime.now(timezone.utc)
    db.commit()
