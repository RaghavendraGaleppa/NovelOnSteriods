from logging import Logger
from pytest import MonkeyPatch
from pymongo.database import Database
from nos.schemas.scraping_schema import NovelRawData
from nos.run_spider import get_pipeline_results



def test_Scrape1qxs(db: Database, logger: Logger, monkeypatch: MonkeyPatch):

    monkeypatch.setattr("src.config.db", db)

    results = get_pipeline_results(max_pages=10)

    assert len(results) == 20
    assert all(isinstance(result, NovelRawData) for result in results)

    # Load the data from the db
    data = NovelRawData.load(db=db, query={"source_name": "1qxs"}, many=True)
    assert data is not None
    assert isinstance(data, list)
    assert len(data) == 20
    assert all(isinstance(item, NovelRawData) for item in data)
