
import datetime
from typing import List, Optional


from nos.config import celery_app, logger, db
from nos.celery_tasks.tasks import translate_novel_metadata
from nos.schemas.scraping_schema import NovelData


@celery_app.task
def dispatch_novel_metadata_translation():
    """ This is beat task that is supposed to run every 5 mins """
    
    query = {
        "dispatched_at": {
            "$or": [
                {"$exists": False},
                {"$lt": datetime.datetime.now() - datetime.timedelta(hours=1)}
            ]
        }
    }

    novels: Optional[List[NovelData]] = NovelData.load(db=db, query=query, many=True, limit=3) # type: ignore

    if novels is None:
        logger.info("No novels to dispatch")
        return
    
    logger.info(f"Dispatching {len(novels)} novels")

    for novel in novels:

        translate_novel_metadata.delay(str(novel.id))
        novel.dispatched_at = datetime.datetime.now()
        novel.update(db=db)
        logger.info(f"Dispatched novel {novel.id} for translation")

    