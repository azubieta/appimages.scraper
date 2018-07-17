# -*- coding: utf-8 -*-
import os
import json
import shutil
import logging
import requests
import hashlib

from tqdm import tqdm
from scrapy.exceptions import DropItem
from appimage_scraper.appimageinfo_cache import AppImageInfoCache
from appimage_scraper.metadata_extractor import extract_appimage_metadata
from appimage_scraper.items import AppImageDownload, AppImageInfo

logger = logging.getLogger(__name__)


class DownloadAppImageFilePipeline(object):
    def __init__(self):
        self.cache = AppImageInfoCache()

    def process_item(self, item, spider):
        store_uri = spider.settings['FILES_STORE']
        if not os.path.exists(store_uri):
            os.mkdir(store_uri)

        if 'remote_url' in item and item['remote_url']:
            item['file_path'] = self.get_file_path(item, store_uri)
            try:
                self.try_download_file(item['remote_url'], item['file_path'])
            except Exception:
                if not spider.settings['KEEP_FULL_FILES']:
                    os.remove(item['file_path'])
                item['file_path'] = None

            return item
        else:
            raise DropItem()

    @staticmethod
    def get_file_path(item, store_uri):
        sha1 = hashlib.sha1()
        sha1.update(item['remote_url'].encode('utf-8'))
        fileName = sha1.hexdigest() + '.AppImage'
        file_path = store_uri + "/" + fileName
        return file_path

    def try_download_file(self, remote_url, local_filename):
        cache = self.cache.get(remote_url)

        if_modified_since = None
        if cache and 'release' in cache and cache['release'] and 'date' in cache['release']:
            if_modified_since = cache['release']['date']

        logger.debug("Get If Modified Since: " + str(if_modified_since))
        with requests.get(remote_url, stream=True, allow_redirects=True,
                          headers={"If-Modified-Since": if_modified_since}) as r:
            logger.debug("Downloading: " + remote_url + ' to ' + local_filename)
            with open(local_filename, 'wb') as f:
                for chunk in tqdm(r.iter_content(chunk_size=1024), ncols=60, ascii=True):
                    if chunk:
                        f.write(chunk)
            if r.status_code != 200:
                raise RuntimeError(r.text)


class ReadFileMetadataPipeline(object):

    def __init__(self):
        self.cache = AppImageInfoCache()

    def process_item(self, item, spider):
        if isinstance(item, AppImageDownload) and item['remote_url']:
            if item['file_path']:
                url = item['remote_url']
                file_path = item['file_path']

                cache_dir_path = self.cache.get_item_cache_path(url)
                if not os.path.exists(cache_dir_path):
                    os.mkdir(cache_dir_path)

                old_metadata = self.cache.get(url)
                try:
                    extract_appimage_metadata(file_path, cache_dir_path)
                except RuntimeError as err:
                    if spider.sentry:
                        spider.sentry.captureException(tags={'url': url})
                    raise DropItem(err)
                finally:
                    if not spider.settings['KEEP_APPIMAGE_FILES'] and os.path.exists(file_path):
                        os.remove(file_path)
                try:
                    metadata = self.cache.get(url)
                    metadata['file']['url'] = url
                    metadata['release'] = {'date': item['date']}

                    if old_metadata \
                            and old_metadata['file']['sha512checksum'] == metadata['file']['sha512checksum']:
                        logger.info('The AppImage file has not changed. Keeping old one!')
                        metadata = old_metadata

                    self.cache.set(url, metadata)

                    newItem = AppImageInfo()
                    newItem.update(metadata)
                    return newItem
                except Exception as err:
                    shutil.rmtree(cache_dir_path)
                    logger.error(err)
                    raise DropItem("Unable to load AppImageInfo")
            else:
                logger.info("Using data in cache for: " + item['remote_url'])
                cache = self.cache.get(item['remote_url'])
                if cache:
                    newItem = AppImageInfo()
                    newItem.update(cache)
                    return newItem
                else:
                    raise DropItem("ERROR: Unable to read file cache")
        else:
            raise DropItem("ERROR: Missing item url.")

    def get_sha1(self, url):
        sha1 = hashlib.sha1()
        sha1.update(url.encode('utf-8'))
        digest = sha1.hexdigest()
        return digest


class ApplyProjectPresets(object):
    def process_item(self, item, spider):
        if item and spider.project and 'presets' in spider.project:
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
