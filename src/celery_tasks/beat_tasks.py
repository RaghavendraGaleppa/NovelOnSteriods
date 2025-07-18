from src.main import celery_app


@celery_app.task
def translate_and_update_tags():
    print("Hello")
    pass