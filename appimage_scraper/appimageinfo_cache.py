import os
import json
import hashlib
import logging

from scrapy.utils.project import get_project_settings

logger = logging.getLogger(__name__)


class AppImageInfoCache:
    def __init__(self):
        settings = get_project_settings()
        self.cache_dir = settings.get("PROJECTS_CACHE")
        logger.debug("Using cache at: " + self.cache_dir)

    def get(self, url):
        app_info_cache = None
        item_cache_path = self.get_item_cache_path(url)
        logger.debug("Loading cache from: " + item_cache_path)
        if os.path.exists(item_cache_path + "AppImageInfo.json"):
            with open(item_cache_path + "AppImageInfo.json") as f:
                app_info_cache = json.loads(f.read())

        return app_info_cache

    def set(self, url, app_info):
        item_cache_path = self.get_item_cache_path(url)
        with open(item_cache_path + 'AppImageInfo.json', 'w') as f:
            f.write(json.dumps(app_info, indent=4, sort_keys=True, default=str))

    def get_item_cache_path(self, url):
        sha1 = hashlib.sha1()
        sha1.update(url.encode('utf-8'))
        digest = sha1.hexdigest()
        item_cache_path = self.cache_dir + "/" + digest + "/"

        return item_cache_path
