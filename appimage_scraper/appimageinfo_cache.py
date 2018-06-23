from scrapy.utils.project import get_project_settings
import hashlib
import json
import os
import shutil


class AppImageInfoCache:
    def __init__(self):
        settings = get_project_settings()
        self.cache_dir = settings.get("PROJECTS_CACHE")
        print("Using cache at: " + self.cache_dir)

    def get(self, url):
        app_info_cache = None
        item_cache_path = self.get_item_cache_path(url)
        if os.path.exists(item_cache_path + "AppImageInfo.json"):
            with open(item_cache_path + "AppImageInfo.json") as f:
                app_info_cache = json.loads(f.read())

        return app_info_cache

    def get_item_cache_path(self, url):
        sha1 = hashlib.sha1()
        sha1.update(url)
        digest = sha1.hexdigest()
        item_cache_path = self.cache_dir + "/" + digest + "/"

        return item_cache_path
