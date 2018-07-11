# -*- coding: utf-8 -*-
import functools
import hashlib
import os
import os.path
import time
import logging
import requests
from six.moves.urllib.parse import urlparse
import json

try:
    from cStringIO import StringIO as BytesIO
except ImportError:
    from io import BytesIO

from twisted.internet import defer

from scrapy.pipelines.media import MediaPipeline
from scrapy.settings import Settings
from scrapy.exceptions import NotConfigured, IgnoreRequest
from scrapy.http import Request
from scrapy.utils.misc import md5sum
from scrapy.utils.log import failure_to_exc_info
from scrapy.utils.python import to_bytes
from scrapy.utils.request import referer_str

from appimage_scraper.appimageinfo_cache import AppImageInfoCache
from appimage_scraper.metadata_extractor import extract_metadata
from appimage_scraper.items import AppImageDownload, AppImageInfo
from scrapy.pipelines.files import FileException, FSFilesStore, GCSFilesStore, S3FilesStore

logger = logging.getLogger(__name__)


class AppImageFilePipeline(MediaPipeline):
    MEDIA_NAME = "file"
    EXPIRES = 90
    STORE_SCHEMES = {
        '': FSFilesStore,
        'file': FSFilesStore,
        's3': S3FilesStore,
        'gs': GCSFilesStore,
    }
    DEFAULT_FILES_URLS_FIELD = 'file_urls'
    DEFAULT_FILES_RESULT_FIELD = 'files'

    def __init__(self, store_uri, download_func=None, settings=None):
        if not store_uri:
            raise NotConfigured

        if isinstance(settings, dict) or settings is None:
            settings = Settings(settings)

        cls_name = "FilesPipeline"
        self.store = self._get_store(store_uri)
        resolve = functools.partial(self._key_for_pipe,
                                    base_class_name=cls_name,
                                    settings=settings)
        self.expires = settings.getint(
            resolve('FILES_EXPIRES'), self.EXPIRES
        )
        if not hasattr(self, "FILES_URLS_FIELD"):
            self.FILES_URLS_FIELD = self.DEFAULT_FILES_URLS_FIELD
        if not hasattr(self, "FILES_RESULT_FIELD"):
            self.FILES_RESULT_FIELD = self.DEFAULT_FILES_RESULT_FIELD
        self.files_urls_field = settings.get(
            resolve('FILES_URLS_FIELD'), self.FILES_URLS_FIELD
        )
        self.files_result_field = settings.get(
            resolve('FILES_RESULT_FIELD'), self.FILES_RESULT_FIELD
        )

        # AppImage Info cache
        self.cache = AppImageInfoCache()

        super(AppImageFilePipeline, self).__init__(download_func=download_func, settings=settings)

    @classmethod
    def from_settings(cls, settings):
        s3store = cls.STORE_SCHEMES['s3']
        s3store.AWS_ACCESS_KEY_ID = settings['AWS_ACCESS_KEY_ID']
        s3store.AWS_SECRET_ACCESS_KEY = settings['AWS_SECRET_ACCESS_KEY']
        s3store.POLICY = settings['FILES_STORE_S3_ACL']

        gcs_store = cls.STORE_SCHEMES['gs']
        gcs_store.GCS_PROJECT_ID = settings['GCS_PROJECT_ID']

        store_uri = settings['FILES_STORE']
        return cls(store_uri, settings=settings)

    def _get_store(self, uri):
        if os.path.isabs(uri):  # to support win32 paths like: C:\\some\dir
            scheme = 'file'
        else:
            scheme = urlparse(uri).scheme
        store_cls = self.STORE_SCHEMES[scheme]
        return store_cls(uri)

    def media_to_download(self, request, info):
        def _onsuccess(result):
            if not result:
                return  # returning None force download

            last_modified = result.get('last_modified', None)
            if not last_modified:
                return  # returning None force download

            age_seconds = time.time() - last_modified
            age_days = age_seconds / 60 / 60 / 24
            if age_days > self.expires:
                return  # returning None force download

            referer = referer_str(request)
            logger.debug(
                'File (uptodate): Downloaded %(medianame)s from %(request)s '
                'referred in <%(referer)s>',
                {'medianame': self.MEDIA_NAME, 'request': request,
                 'referer': referer},
                extra={'spider': info.spider}
            )
            self.inc_stats(info.spider, 'uptodate')

            checksum = result.get('checksum', None)
            return {'url': request.url, 'path': path, 'checksum': checksum}

        path = self.file_path(request, info=info)
        dfd = defer.maybeDeferred(self.store.stat_file, path, info)
        dfd.addCallbacks(_onsuccess, lambda _: None)
        dfd.addErrback(
            lambda f:
            logger.error(self.__class__.__name__ + '.store.stat_file',
                         exc_info=failure_to_exc_info(f),
                         extra={'spider': info.spider})
        )
        return dfd

    def media_failed(self, failure, request, info):
        if not isinstance(failure.value, IgnoreRequest):
            referer = referer_str(request)
            logger.warning(
                'File (unknown-error): Error downloading %(medianame)s from '
                '%(request)s referred in <%(referer)s>: %(exception)s',
                {'medianame': self.MEDIA_NAME, 'request': request,
                 'referer': referer, 'exception': failure.value},
                extra={'spider': info.spider}
            )

        raise FileException

    def media_downloaded(self, response, request, info):
        referer = referer_str(request)

        if response.status != 200:
            cache = self.cache.get_item_cache_path(request.url)
            if cache:
                return {'url': request.url, 'path': None, 'checksum': None}

            logger.warning(
                'File (code: %(status)s): Error downloading file from '
                '%(request)s referred in <%(referer)s>',
                {'status': response.status,
                 'request': request, 'referer': referer},
                extra={'spider': info.spider}
            )
            raise FileException('download-error')

        if not response.body:
            logger.warning(
                'File (empty-content): Empty file from %(request)s referred '
                'in <%(referer)s>: no-content',
                {'request': request, 'referer': referer},
                extra={'spider': info.spider}
            )
            raise FileException('empty-content')

        status = 'cached' if 'cached' in response.flags else 'downloaded'
        logger.debug(
            'File (%(status)s): Downloaded file from %(request)s referred in '
            '<%(referer)s>',
            {'status': status, 'request': request, 'referer': referer},
            extra={'spider': info.spider}
        )
        self.inc_stats(info.spider, status)

        try:
            path = self.file_path(request, response=response, info=info)
            checksum = self.file_downloaded(response, request, info)
        except FileException as exc:
            logger.warning(
                'File (error): Error processing file from %(request)s '
                'referred in <%(referer)s>: %(errormsg)s',
                {'request': request, 'referer': referer, 'errormsg': str(exc)},
                extra={'spider': info.spider}, exc_info=True
            )
            raise
        except Exception as exc:
            logger.error(
                'File (unknown-error): Error processing file from %(request)s '
                'referred in <%(referer)s>',
                {'request': request, 'referer': referer},
                exc_info=True, extra={'spider': info.spider}
            )
            raise FileException(str(exc))

        return {'url': request.url, 'path': path, 'checksum': checksum}

    def inc_stats(self, spider, status):
        spider.crawler.stats.inc_value('file_count', spider=spider)
        spider.crawler.stats.inc_value('file_status_count/%s' % status, spider=spider)


    def get_media_requests(self, item, info):
        if item and 'cache' in item \
                and item['cache'] and 'release' in item['cache'] \
                and item['cache']['release'] and 'date' in item['cache']['release']:
            mediaRequests = []
            for x in item.get(self.files_urls_field, []):
                request = Request(x,
                                  headers={"If-Modified-Since": item['cache']['release']['date']})
                mediaRequests.append(request)
            return mediaRequests
        else:
            return [Request(x) for x in item.get(self.files_urls_field, [])]

    def file_downloaded(self, response, request, info):
        path = self.file_path(request, response=response, info=info)
        buf = BytesIO(response.body)
        checksum = md5sum(buf)
        buf.seek(0)
        self.store.persist_file(path, buf, info)
        return checksum

    def item_completed(self, results, item, info):
        if isinstance(item, dict) or self.files_result_field in item.fields:
            item[self.files_result_field] = [x for ok, x in results if ok]
        return item

    def file_path(self, request, response=None, info=None):
        ## start of deprecation warning block (can be removed in the future)
        def _warn():
            from scrapy.exceptions import ScrapyDeprecationWarning
            import warnings
            warnings.warn('FilesPipeline.file_key(url) method is deprecated, please use '
                          'file_path(request, response=None, info=None) instead',
                          category=ScrapyDeprecationWarning, stacklevel=1)

        # check if called from file_key with url as first argument
        if not isinstance(request, Request):
            _warn()
            url = request
        else:
            url = request.url

        # detect if file_key() method has been overridden
        if not hasattr(self.file_key, '_base'):
            _warn()
            return self.file_key(url)
        ## end of deprecation warning block

        media_guid = hashlib.sha1(to_bytes(url)).hexdigest()  # change to request.url after deprecation
        media_ext = os.path.splitext(url)[1]  # change to request.url after deprecation
        return 'full/%s%s' % (media_guid, media_ext)

    # deprecated
    def file_key(self, url):
        return self.file_path(url)
    file_key._base = True


# class AppImageFilePipeline(FilesPipeline):
#     def get_media_requests(self, item, info):
#         if item and 'cache' in item \
#                 and item['cache'] and 'release' in item['cache'] \
#                 and item['cache']['release'] and 'date' in item['cache']['release']:
#             mediaRequests = []
#             for x in item.get(self.files_urls_field, []):
#                 request = Request(x,
#                                   headers={"If-Modified-Since": item['cache']['release']['date']})
#                 mediaRequests.append(request)
#             return mediaRequests
#         else:
#             return [Request(x) for x in item.get(self.files_urls_field, [])]


class ReadFileMetadataPipeline(object):

    def __init__(self):
        super(ReadFileMetadataPipeline, self).__init__()
        self.cache = AppImageInfoCache()

    def process_item(self, item, spider):
        if isinstance(item, AppImageInfo):
            return item

        if isinstance(item, AppImageDownload) \
                and 'files' in item and len(item['files']) > 0\
                and item['files'][0]['path']:
            url = item['file_urls'][0]
            file_path = item['files'][0]['path']

            settings = spider.settings
            file_store = settings.get("FILES_STORE")
            cache_dir_path = self.cache.get_item_cache_path(url)
            if not os.path.exists(cache_dir_path):
                os.mkdir(cache_dir_path)

            extract_metadata(file_store + "/" + file_path, cache_dir_path)

            metadata = {}
            try:
                metadata = self.read_cache_file(cache_dir_path)
            except IOError as err:
                pass

            self.set_file_url(metadata, url)
            self.set_release_date(metadata, item)
            self.save_cahe_file(cache_dir_path, metadata)

            if not settings['KEEP_FULL_FILES']:
                os.remove(file_store + "/" + file_path)

            newItem = AppImageInfo()
            newItem.update(metadata)
            return newItem
        else:
            url = item['file_urls'][0]
            cache = self.cache.get(url)
            if cache:
                newItem = AppImageInfo()
                newItem.update(cache)
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
