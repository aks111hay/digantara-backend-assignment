from worker import celery_app
from service.pass_detector import run_pass_detection
from db.base import SessionLocal
from logger import get_logger

logger = get_logger()

@celery_app.task(name="tasks.propagate_all_satellites")
def propagate_task(satellite_limit=None, clear_existing=True):
    """
    Celery task to run the heavy propagation process.
    """
    logger.info(f"Starting Celery task: propagate_all_satellites (limit={satellite_limit})")
    
    db = SessionLocal()
    try:
        result = run_pass_detection(
            db=db,
            satellite_limit=satellite_limit,
            clear_existing=clear_existing
        )
        return result
    except Exception as e:
        logger.error(f"Celery task failed: {e}")
        raise e
    finally:
        db.close()
