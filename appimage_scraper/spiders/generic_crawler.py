import scrapy
import json
import re
import datetime
import logging

from scrapy.linkextractors import LinkExtractor

from appimage_scraper.items import AppImageDownload, AppImageInfo
from appimage_scraper.appimageinfo_cache import AppImageInfoCache

from raven import Client

logger = logging.getLogger(__name__)


class GenericCrawler(scrapy.Spider):
    name = "generic.crawler"
    githubRequestCount = 0
    appImageLinkExtractor = LinkExtractor(allow='.*\.AppImage$')

    def __init__(self, name=None, **kwargs):
        super(GenericCrawler, self).__init__(name, **kwargs)
        self.sentry = None
        logger.debug("Using project spec: " + self.project_file)
        self.cache = AppImageInfoCache()

        with open(self.project_file, "r") as f:
            self.project = json.loads(f.read())

    def start_requests(self):
        if self.settings['SENTRY_PROJECT_URL']:
            self.sentry = Client(self.settings['SENTRY_PROJECT_URL'])
        else:
            logger.warning("NO SENTRY_ACCESS_KEY provided! Error reporting disabled!")

        if self.project:
            for url in self.project["urls"]:
                github_repo_id_search = re.search('github.com\/([\w\.\-]+\/[\w\.\-]+)[\/$]?', url)
                if github_repo_id_search:
                    github_repo_id = github_repo_id_search.group(1)
                    yield scrapy.Request(url='https://github.com/' + github_repo_id + '/releases', callback=self.parse)
                else:
                    if url.endswith('.AppImage'):
                        yield scrapy.Request(method='HEAD', url=url, callback=self.handle_appimage_file_head_response)

                        # Check the parent url for more AppImage download links
                        base_url = "/".join(url.split("/")[0:-1])
                        yield scrapy.Request(url=base_url, callback=self.parse)
                    else:
                        yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        links = self.appImageLinkExtractor.extract_links(response)
        for link in links:
            url = link.url

            if self.is_url_valid(url):
                yield AppImageDownload(remote_url=url, date=self.get_last_modified_date(response))

    def handle_appimage_file_head_response(self, response):
        yield AppImageDownload(remote_url=response.url, date=self.get_last_modified_date(response))

    def is_url_valid(self, url):
        valid_url = True
        if 'match' in self.project:
            valid_url = True if re.match(self.project['match'], url) else False
        return valid_url

    @staticmethod
    def get_last_modified_date(response):
        if response and "Date" in response.headers:
            return response.headers["Date"]
        else:
            return datetime.datetime.utcnow().strftime("%a %b %d %H:%M:%S UTC %Y")
