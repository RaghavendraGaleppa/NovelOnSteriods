
import datetime
from typing import List, Optional


from nos.config import celery_app, logger, db
from nos.celery_tasks.tasks import translate_novel_metadata
from nos.schemas.scraping_schema import NovelData



def check_active_celery_workers():
    inspect = celery_app.control.inspect()
    active_queues = inspect.active_queues()
    if active_queues is None:
        logger.info("No active queues")
        return False
    

    logger.info(f"Active queues: {active_queues}")
    
    for host in active_queues:
        for queue in active_queues[host]:   
            if queue['name'] == "translations":
                return True
    
    return False


@celery_app.task
def dispatch_novel_metadata_translation():
    """ This is beat task that is supposed to run every 5 mins """

    if not check_active_celery_workers():
        logger.error("No active celery workers. Skipping dispatch")
        return
    
    query = {
        "all_data_parsed": False,
        "$or": [
            {"dispatched_at": {"$exists": False}},
            {"dispatched_at": {"$lt": datetime.datetime.now() - datetime.timedelta(hours=1)}}
        ]
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

    