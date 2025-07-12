import scrapy
from typing import List


class Scrape1qxs(scrapy.Spider):
    name = "scrape_1qxs"
    start_urls = [
        "https://www.1qxs.com/all/0_4_0_0_0_1.html" # The first page of the novel list
    ]

    def __init__(self, *args, **kwargs):
        self.db = kwargs['db']
        self.items_container = kwargs.pop('items_container')
        super(Scrape1qxs, self).__init__(*args, **kwargs)
    

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
        novel_list_url = "https://www.1qxs.com/list/" + novel_source_id + ".html"

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
            "novel_list_url": novel_list_url,
            "source_name": "1qxs"
        }
        
        # Go to the list link and make sure to pass the variables
        yield response.follow(novel_list_url, callback=self.parse_novel_list, meta={"novel_data": novel_data})

    def parse_novel_list(self, response):
        novel_data = response.meta["novel_data"]
        chapter_list = response.css("div.list ul li")
        n_chapters_raw = len(chapter_list)

        novel_data["n_chapters_raw"] = n_chapters_raw

        # Find data that needs to be translated
        novel_data_to_translate = {
            "title_raw": novel_data["title_raw"],
            "author_raw": novel_data["author_raw"],
            "description_raw": novel_data["description_raw"],
            "classification_raw": novel_data["classification_raw"],
            "tags_raw": novel_data["tags_raw"]
        }

        # Translate the data
        yield novel_data



        
        
