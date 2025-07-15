import scrapy
from typing import List


class Scrape1qxs(scrapy.Spider):
    name = "scrape_1qxs"
    start_urls = [
        "https://www.1qxs.com/all/0_4_0_0_0_1.html" # The first page of the novel list
    ]
    custom_settings = {
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'DOWNLOAD_DELAY': 2 # Adds a 2-second delay between requests
    }

    def parse(self, response):
        # List out all the novel links
        novel_links = response.css("div.name.line_1 a::attr(href)").getall()
        for novel_link in novel_links:
            yield response.follow(novel_link, callback=self.parse_novel)

    def parse_novel(self, response):
        novel_url: str = response.url
        title_raw: str = response.css('div.name h1::text').get()
        author_raw: str = response.css('div.name span::text').get()
        description_raw: str = response.css('div.description::text').get()
        classification_raw: str = response.css('div.lable a::text').getall()
        tags_raw: List[str] = response.css("span.tags a::text").getall()
        image_url: str = response.css('div.image img::attr(data-original)').get()
        novel_source_id = novel_url.split(".html")[0].split("/")[-1]
        chapter_list_url = "https://www.1qxs.com/list/" + novel_source_id + ".html"

        novel_data = {
            # Make exact fiesl in this dict
            "novel_url": novel_url,
            "title_raw": title_raw,
            "author_raw": author_raw,
            "description_raw": description_raw,
            "classification_raw": classification_raw,
            "tags_raw": tags_raw,
            "image_url": image_url,
            "novel_source_id": novel_source_id,
            "chapter_list_url": chapter_list_url,
            "source_name": "1qxs"
        }


        # The data need to stroed in the db
        