from logging import Logger
from pymongo.database import Database



def test_Scrape1qxs(db: Database, logger: Logger):
    db.client.admin.command("ping")

    pass