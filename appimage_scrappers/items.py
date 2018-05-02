# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy

class AppImageRelease(scrapy.Item):
    name = scrapy.Field()
    description = scrapy.Field()
    categories = scrapy.Field()
    authors = scrapy.Field()
    license = scrapy.Field()
    version = scrapy.Field()
    screenshots = scrapy.Field()
    downloadUrl = scrapy.Field()
    downloadSize = scrapy.Field()
