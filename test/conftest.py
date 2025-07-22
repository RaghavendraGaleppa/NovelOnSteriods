import pytest
from uuid import uuid4
from logging import Logger
from pymongo.database import Database
from pytest import MonkeyPatch
from typing import Generator, Any, List

from nos.config import db_config, get_db_client
from nos.utils.logging_utils import get_logger
from nos.schemas.scraping_schema import NovelRawData
from nos.run_spider import run_spider



@pytest.fixture(scope="session")
def logger() -> Logger:
    return get_logger("test-suite")
        

@pytest.fixture(scope="session")
def db(logger: Logger) -> Generator[Database, Any, Any]:
    db_name=f"test-db-{uuid4()}"
    logger.debug(f"Settin up test db {db_name}")
    db = get_db_client(
        host=db_config.host,
        port=db_config.port,
        username=db_config.username,
        pwd=db_config.pwd,
        db_name=db_name,
        db_auth_source=db_config.db_auth_source
    )
    logger.debug(f"Test DB name: {db.name}")
    logger.debug(f"Test DB client: {db.client}")
    logger.debug(f"Test DB server info: {db.client.server_info()}")
    
    yield db

    try:
        logger.debug(f"Dropping test db {db_name}")
        db.client.drop_database(db_name)
        logger.debug(f"Dropped test db {db_name}")
    finally:
        db.client.close()
        logger.debug(f"Closed db client")


@pytest.fixture(scope="function", autouse=True)
def patch_db_everywhere(db: Database, monkeypatch: MonkeyPatch):
    monkeypatch.setattr("nos.config.db", db)



@pytest.fixture(scope="class")
def scraped_data(db: Database) -> List[NovelRawData]:
    """ Delete any existing data """
    data = NovelRawData.load(db=db, query={"source_name": "1qxs"}, many=True)
    if data is not None:
        for item in data:
            item.delete(db=db) # type: ignore
    
    # Run the spider
    run_spider(max_pages=1, max_novels_per_page=5)

    # Load the data again
    data = NovelRawData.load(db=db, query={"source_name": "1qxs"}, many=True)
    return data # type: ignore
