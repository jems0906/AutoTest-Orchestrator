from __future__ import annotations

from datetime import UTC, datetime

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from .database import SessionLocal
from .execution import execute_test_run
from .models import ExecutionQueue


class RegressionScheduler:
    def __init__(self, timezone: str = "UTC") -> None:
        self.scheduler = BackgroundScheduler(timezone=timezone)
        self.started = False

    def start(self) -> None:
        if self.started:
            return
        # Nightly queueing + execution at 02:00 UTC.
        self.scheduler.add_job(self.queue_nightly_run, "cron", hour=2, minute=0, id="nightly-regression")
        self.scheduler.start()
        self.started = True

    def stop(self) -> None:
        if self.started:
            self.scheduler.shutdown(wait=False)
            self.started = False

    def queue_nightly_run(self) -> None:
        db: Session = SessionLocal()
        try:
            queue_item = ExecutionQueue(
                run_label=f"nightly-{datetime.now(UTC).strftime('%Y%m%d')}",
                status="queued",
                scheduled_for=datetime.now(UTC),
            )
            db.add(queue_item)
            db.commit()

            queue_item.status = "running"
            db.commit()

            execute_test_run(db, run_type="nightly", triggered_by="scheduler", only_risky=False)
            queue_item.status = "completed"
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
