# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class AppImageDownload(scrapy.Item):
    date = scrapy.Field()
    file_urls = scrapy.Field()
    files = scrapy.Field()
    cache = scrapy.Field()


class AppImageInfo(scrapy.Item):
    format = scrapy.Field()
    id = scrapy.Field()
    name = scrapy.Field()
    icon = scrapy.Field()
    abstract = scrapy.Field()
    description = scrapy.Field()
    license = scrapy.Field()
    categories = scrapy.Field()
    keywords = scrapy.Field()
    languages = scrapy.Field()
    developer = scrapy.Field()
    release = scrapy.Field()
    file = scrapy.Field()
    screenshots = scrapy.Field()
    mime_types = scrapy.Field()
    links = scrapy.Field()
