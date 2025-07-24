from logging import Logger
from bson import ObjectId
from pymongo.database import Database
from nos.schemas.scraping_schema import NovelRawData
from nos.run_spider import run_spider
from typing import List
import logging
from urllib.parse import urlparse

# Set the logging level for noisy libraries to WARNING
logging.getLogger('scrapy').setLevel(logging.WARNING)
logging.getLogger('pymongo').setLevel(logging.WARNING)

# This will also hide the DeprecationWarnings from the console
logging.getLogger('py.warnings').setLevel(logging.ERROR)


def is_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except (ValueError, AttributeError):
        return False


class TestScrape1qxs:

    def test_data_type(self, scraped_data: List[NovelRawData]):
        assert all(isinstance(item.id, ObjectId) for item in scraped_data)
        assert isinstance(scraped_data, list)
        assert all(isinstance(item, NovelRawData) for item in scraped_data)
        assert len(scraped_data) == 5

    def test_novel_data_urls(self, scraped_data: List[NovelRawData]):
        for item in scraped_data:
            assert is_url(item.novel_url)
            assert is_url(item.chapter_list_url)
            assert is_url(item.image_url)

    def test_empty_strings(self, scraped_data: List[NovelRawData]):
        for item in scraped_data:
            assert item.title_raw.strip() != ""
            assert item.author_raw.strip() != ""
            assert item.description_raw.strip() != ""
            assert len(item.classification_raw) > 0
            assert len(item.tags_raw) > 0

    def test_novel_data_len(self, scraped_data: List[NovelRawData]):

        assert scraped_data is not None
        assert isinstance(scraped_data, list)
        assert len(scraped_data) == 5
        assert all(isinstance(item, NovelRawData) for item in scraped_data)

    def test_all_data_parsed_is_false(self, scraped_data: List[NovelRawData]):
        for item in scraped_data:
            assert item.all_data_parsed is False


    def assert_data_consistency(self, scraped_data: List[NovelRawData]):
        for item in scraped_data:
            assert item.novel_source_id in item.novel_url
            assert item.novel_source_id in item.chapter_list_url
            assert item.novel_source_id in item.image_url


