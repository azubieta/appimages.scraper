# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class AppImageFileMetadata(scrapy.Item):
    id = scrapy.Field()
    name = scrapy.Field()
    abstract = scrapy.Field()
    description = scrapy.Field()
    categories = scrapy.Field()
    developer = scrapy.Field()
    license = scrapy.Field()
    version = scrapy.Field()
    screenshots = scrapy.Field()
    downloadUrl = scrapy.Field()
    downloadSize = scrapy.Field()
    url_date = scrapy.Field()
    file_date = scrapy.Field()
    file_urls = scrapy.Field()
    files = scrapy.Field()
    sha512checksum = scrapy.Field()
    links = scrapy.Field()
    architecture = scrapy.Field()
    keywords = scrapy.Field()
    mimetype = scrapy.Field()
    size = scrapy.Field()
    type = scrapy.Field()
