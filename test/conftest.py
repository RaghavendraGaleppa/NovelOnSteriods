import pytest
from uuid import uuid4
from logging import Logger
from pymongo.database import Database
from typing import Generator, Any

from src.main import db_config, get_db_client
from src.utils.logging_utils import get_logger



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
    
    yield db

    try:
        logger.debug(f"Dropping test db {db_name}")
        db.client.drop_database(db_name)
        logger.debug(f"Dropped test db {db_name}")
    finally:
        db.client.close()
        logger.debug(f"Closed db client")

    