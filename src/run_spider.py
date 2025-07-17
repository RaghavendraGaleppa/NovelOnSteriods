from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from src.scraping.scrape_novel import Scrape1qxs




def run_my_spider():
    settings = get_project_settings()
    scraped_items = []
    class ItemCollectorPipeline:

        def __init__(self):
            self.items = scraped_items

        def process_item(self, item, spider):
            self.items.append(item)
            return item

    settings.set('ITEM_PIPELINES', {
        ItemCollectorPipeline: 300
    })
    process = CrawlerProcess(settings)
    process.crawl(Scrape1qxs)
    process.start()
    return scraped_items
