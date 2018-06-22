# -*- coding: utf-8 -*-

import logging
import requests
import os
import uuid
import json
import shutil
from scrapy.utils.project import get_project_settings

from appimage_scraper.metadata_extractor import extract_metadata
from appimage_scraper.items import AppImageFileMetadata

class ReadFileMetadataPipeline(object):
    def process_item(self, item, spider):
        settings = get_project_settings()
        file_store = settings.get("FILES_STORE")

        if 'files' in item and len(item['files']) > 0:
            tmpDirPath = "/tmp/appimage-scrapper-" + str(uuid.uuid4())  # type: str
            os.mkdir(tmpDirPath)
            file_path = item['files'][0]['path']

            (app_info_path, app_icon_path) = extract_metadata(file_store+"/"+file_path, tmpDirPath)
            metadata = AppImageFileMetadata()

            with open(app_info_path, "r") as f:
                app_info = json.loads(f.read())
                metadata.update(app_info)

            if 'presets' in spider.project:
                metadata.update(spider.project['presets'])

            shutil.rmtree(tmpDirPath)

            return metadata



class PublishPipeline(object):
    def process_item(self, item, spider):
        api_url = 'http://localhost:3000/api/applications'
        if 'NX_APPS_API_URL' in os.environ:
            api = os.environ['NX_APPS_API_URL']

        r = requests.post(api_url, json=item)
        if r.status_code != 200:
            logging.warning(r.reason)

        return item
