# -*- coding: utf-8 -*-

import os
import json
import requests
import logging

from scrapy.http import Request
from scrapy.pipelines.files import FilesPipeline
from scrapy.utils.project import get_project_settings

from appimage_scraper.metadata_extractor import extract_metadata
from appimage_scraper.items import AppImageInfo, AppImageDownload
from appimage_scraper.appimageinfo_cache import AppImageInfoCache


class AppImageFilePipeline(FilesPipeline):
    def get_media_requests(self, item, info):
        return [Request(x) for x in item.get(self.files_urls_field, [])]


class ReadFileMetadataPipeline(object):

    def __init__(self):
        super(ReadFileMetadataPipeline, self).__init__()
        self.cache = AppImageInfoCache()

    def process_item(self, item, spider):
        if isinstance(item, AppImageInfo):
            return item

        if isinstance(item, AppImageDownload) and 'files' in item and len(item['files']) > 0:
            url = item['file_urls'][0]
            file_path = item['files'][0]['path']

            settings = get_project_settings()
            file_store = settings.get("FILES_STORE")
            cache_dir_path = self.cache.get_item_cache_path(url)
            if not os.path.exists(cache_dir_path):
                os.mkdir(cache_dir_path )

            extract_metadata(file_store + "/" + file_path, cache_dir_path)

            app_info = self.read_cache_file(cache_dir_path)
            self.set_file_url(app_info, url)
            self.set_release_date(app_info, item)
            self.save_cahe_file(cache_dir_path, app_info)

            newItem = AppImageInfo()
            newItem.update(app_info)

            if not settings['KEEP_FULL_FILES']:
                os.remove(file_store + "/" + file_path)

            return newItem

    @staticmethod
    def set_file_url(app_info, url):
        if 'file' not in app_info:
            app_info['file'] = {}
        app_info['file']['url'] = url

    @staticmethod
    def set_release_date(app_info, item):
        if 'release' not in app_info:
            app_info['release'] = {}
        app_info['release']['date'] = item['date']

    @staticmethod
    def save_cahe_file(cache_dir_path, app_info):
        with open(cache_dir_path + '/AppImageInfo.json', 'w') as f:
            f.write(json.dumps(app_info))

    @staticmethod
    def read_cache_file(cache_dir_path):
        app_info_path = cache_dir_path + "/AppImageInfo.json"
        with open(app_info_path, "r") as f:
            return json.loads(f.read())


class ApplyProjectPresets(object):

    def process_item(self, item, spider):
        if 'presets' in spider.project:
            item.update(spider.project['presets'])
        return item


class PublishPipeline(object):

    def process_item(self, item, spider):
        api_url = 'http://localhost:3000/api/applications'
        if 'NX_APPS_API_URL' in os.environ:
            api = os.environ['NX_APPS_API_URL']

        r = requests.post(api_url, json=item)
        if r.status_code != 200:
            logging.warning(r.reason)

        return item
