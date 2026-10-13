import logging
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select
from sqlalchemy.engine import make_url

from radar.core.process_lock import ProcessLock
from radar.database.models import Source
from radar.scheduler.service import MonitorService

logger = logging.getLogger(__name__)


def as_utc(value):
    return (
        value.replace(tzinfo=timezone.utc)
        if value.tzinfo is None
        else value.astimezone(timezone.utc)
    )


class MonitorRuntime:
    def __init__(self, sessions, settings):
        database = make_url(settings.database_url).database
        if not database or database == ":memory:":
            raise ValueError("El programador requiere una base de datos persistente")
        self.lock = ProcessLock(Path(str(Path(database).resolve()) + ".monitor.lock"))
        self.service = MonitorService(sessions, settings)
        self.sessions = sessions
        self.scheduler = BackgroundScheduler(timezone="UTC")
        self.sync_lock = RLock()

    def start(self):
        self.lock.acquire()
        try:
            self.service.recover()
            self.scheduler.start(paused=True)
            self.refresh()
            self.scheduler.add_job(
                self.refresh, "interval", seconds=5, id="refresh", max_instances=1, coalesce=True
            )
            self.scheduler.resume()
        except Exception:
            self.stop()
            raise

    def refresh(self):
        with self.sync_lock:
            with self.sessions() as session:
                sources = session.scalars(select(Source).where(Source.enabled.is_(True))).all()
                wanted = {f"source-{source.id}" for source in sources}
                for job in self.scheduler.get_jobs():
                    if job.id.startswith("source-") and job.id not in wanted:
                        self.scheduler.remove_job(job.id)
                for source in sources:
                    job_id = f"source-{source.id}"
                    desired = (
                        as_utc(source.next_run_at)
                        if source.next_run_at
                        else datetime.now(timezone.utc)
                    )
                    job = self.scheduler.get_job(job_id)
                    if job is None:
                        self.scheduler.add_job(
                            self.run_source,
                            "interval",
                            minutes=source.interval_minutes,
                            args=[source.id],
                            id=job_id,
                            next_run_time=desired,
                            max_instances=1,
                            coalesce=True,
                            misfire_grace_time=None,
                        )
                    else:
                        seconds = source.interval_minutes * 60
                        if job.trigger.interval.total_seconds() != seconds:
                            self.scheduler.reschedule_job(
                                job_id, trigger="interval", seconds=seconds
                            )
                        # El resultado ajusta el siguiente pulso; no cambiar un job activo.
                        if source.running_token is None and source.next_run_at is not None:
                            if job.next_run_time != desired:
                                self.scheduler.modify_job(job_id, next_run_time=desired)

    def run_source(self, source_id):
        try:
            return self.service.run_source(source_id)
        except Exception:
            logger.error("monitor_runtime_error source_id=%s", source_id)
            return "failed"

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
        self.lock.release()
