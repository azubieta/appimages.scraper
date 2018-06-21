# -*- coding: utf-8 -*-

import logging
import requests
import os
import uuid
import json
import shutil
from scrapy.utils.project import get_project_settings

from appimage_scraper.metadata_extractor import extract_metadata

class ReadFileMetadataPipeline(object):
    def process_item(self, item, spider):
        settings = get_project_settings()
        file_store = settings.get("FILES_STORE")

        if 'files' in item:
            tmpDirPath = "/tmp/appimage-scrapper-" + str(uuid.uuid4())  # type: str
            os.mkdir(tmpDirPath)
            file = item['files'][0]

            (appInfoPath, appIconPath) = extract_metadata(file_store+"/"+file['path'], tmpDirPath)
            with open(appInfoPath, "r") as f:
                appInfo = json.loads(f.read())
                item.update(appInfo)

            shutil.rmtree(tmpDirPath)

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
