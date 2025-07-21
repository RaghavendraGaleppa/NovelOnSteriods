from typing import Optional
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from nos.scraping.scrape_novel import Scrape1qxs

class ItemCollectorPipeline:

    def __init__(self):
        self.items = []

    def process_item(self, item, spider):
        self.items.append(item)
        return item



def get_pipeline_results(max_pages: int = 100, settings: Optional[dict] = None):
    if settings is None:
        settings = {}
    pipeline = ItemCollectorPipeline()
    settings['ITEM_PIPELINES'] = {
        pipeline: 1
    }
    process = CrawlerProcess(settings)
    process.crawl(Scrape1qxs, max_pages=max_pages)
    process.start()
    results = pipeline.items
    return results
