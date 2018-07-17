# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.org/en/latest/topics/items.html

from scrapy import Item, Field


class AppImageDownload(Item):
    date = Field()
    remote_url = Field()
    file_path = Field()


class AppImageInfo(Item):
    format = Field()
    id = Field()
    name = Field()
    icon = Field()
    abstract = Field()
    description = Field()
    license = Field()
    categories = Field()
    keywords = Field()
    languages = Field()
    developer = Field()
    release = Field()
    file = Field()
    screenshots = Field()
    mime_types = Field()
    links = Field()
