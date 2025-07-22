from logging import Logger
from pymongo.database import Database
from nos.schemas.scraping_schema import NovelRawData
from nos.run_spider import run_spider

import logging

# Set the logging level for noisy libraries to WARNING
logging.getLogger('scrapy').setLevel(logging.WARNING)
logging.getLogger('pymongo').setLevel(logging.WARNING)

# This will also hide the DeprecationWarnings from the console
logging.getLogger('py.warnings').setLevel(logging.ERROR)


def test_Scrape1qxs(db: Database, logger: Logger):

    # Import the db from nos.config and print db name and other info
    run_spider(max_pages=1, max_novels_per_page=5)
    # Load the data from the db
    data = NovelRawData.load(db=db, query={"source_name": "1qxs"}, many=True)
    assert data is not None
    assert isinstance(data, list)
    assert len(data) == 5
    assert all(isinstance(item, NovelRawData) for item in data)
