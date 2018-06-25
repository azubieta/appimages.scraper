import scrapy
import json
import re
import datetime

from scrapy.linkextractors import LinkExtractor

from appimage_scraper.items import AppImageDownload, AppImageInfo
from appimage_scraper.appimageinfo_cache import AppImageInfoCache


class GenericCrawler(scrapy.Spider):
    name = "generic.crawler"
    githubRequestCount = 0
    appImageLinkExtractor = LinkExtractor(allow='.*\.AppImage$')

    def __init__(self, name=None, **kwargs):
        super(GenericCrawler, self).__init__(name, **kwargs)
        print("Using project spec: " + self.project_file)
        self.cache = AppImageInfoCache()

        with open(self.project_file, "r") as f:
            self.project = json.loads(f.read())

    def start_requests(self):
        if self.project:
            for url in self.project["urls"]:
                yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        links = self.appImageLinkExtractor.extract_links(response)
        for link in links:
            url = link.url

            if self.is_url_valid(url):
                app_info_cache = self.cache.get(url)
                yield AppImageDownload(file_urls=[url], cache=app_info_cache,
                                       date=self.get_last_modified_date(response))

    def is_url_valid(self, url):
        valid_url = True
        if 'match' in self.project:
            valid_url = True if re.match(self.project['match'], url) else False
        return valid_url

    @staticmethod
    def get_last_modified_date(response):
        if "Date" in response.headers:
            return response.headers["Date"]
        else:
            return datetime.datetime.utcnow().strftime("%a %b %d %H:%M:%S UTC %Y")

    def get_github_project_url(self, item):
        githubUrl = ''
        for link in item['links']:
            if link['type'] == 'GitHub':
                githubUrl = 'https://api.github.com/repos/' + link['url'] + '/releases'
        return githubUrl

    def format_authors(self, item):
        new_authors = []
        for autor in item['authors']:
            new_authors.append(autor['name'])
        return new_authors

    def expand_screenshots_urls(self, item):
        new_screenshots = []
        for screenshot in item['screenshots']:
            if screenshot.startswith('http'):
                new_screenshots.append(screenshot)
            else:
                new_screenshots.append('https://appimage.github.io/database/' + screenshot)
        return new_screenshots

    def parese_github_releases(self, response):
        item = response.meta['item']
        results = json.loads(response.body)
        for release in results:
            self.log('Parsing github release: %s' % release['tag_name'])
            if 'assets' in release:
                for asset in release['assets']:
                    if asset['name'].endswith('.AppImage'):
                        release_item = {'name': item['name'], 'description': item['description'],
                                        'categories': item['categories'], 'authors': item['authors'],
                                        'license': item['license'], 'version': release['tag_name'],
                                        'screenshots': item['screenshots'], 'icon': item['icons'],
                                        'downloadUrl': asset['browser_download_url'], 'downloadSize': asset['size']}

                        yield release_item

    def parse_adhoc_release(self, response):
        item = response.meta['item']
        if response.url.startswith('https://download.opensuse.org'):
            yield self.parse_opensuse_release(item, response)
        else:
            item['downloadUrl'] = response.selector.xpath('//a/text()').re_first(r'http.*AppImage')
            item['downloadSize'] = '0'
            yield item

    def parse_opensuse_release(self, item, response):
        size_text = response.selector.xpath('//li/span[text()=\'Size:\']/../text()').extract()
        item['downloadSize'] = size_text[0].split('(')[1].split(' ')[0]  # Get only the size in bytes
        item['downloadUrl'] = response.selector.xpath('//a/text()').re_first(r'http.*AppImage')
        yield item
