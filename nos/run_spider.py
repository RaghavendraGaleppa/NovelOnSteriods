from typing import Optional
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from nos.scraping.scrape_novel import Scrape1qxs



def run_spider(max_pages: int = 100, max_novels_per_page: int = 20) -> None:
    settings = get_project_settings()
    process = CrawlerProcess(settings)
    process.crawl(Scrape1qxs, max_pages=max_pages, max_novels_per_page=max_novels_per_page)
    process.start()
