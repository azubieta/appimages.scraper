import scrapy
import json
import re


from scrapy.linkextractors import LinkExtractor

from appimage_scraper.items import AppImageFileMetadata


class GenericCrawler(scrapy.Spider):
    name = "generic.crawler"
    githubRequestCount = 0
    appImageLinkExtractor = LinkExtractor(allow='.*\.AppImage$')

    def __init__(self, name=None, **kwargs):
        super(GenericCrawler, self).__init__(name, **kwargs)
        print("Using project spec: " + self.project_file)
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
            item = AppImageFileMetadata(file_urls=[url])

            if 'apps' in self.project:
                for appId in self.project['apps']:
                    app = self.project['apps'][appId]
                    if re.match(app['match'], url):
                        if 'presets' in app:
                            item.update(app['presets'])
                        yield item
            else:
                if 'presets' in self.project:
                    item.update(self.project['presets'])
                yield item

    def parse2(self, response):
        results = json.loads(response.body)
        for item in results['items']:
            if item['screenshots']:
                item['screenshots'] = self.expand_screenshots_urls(item)

            if item['authors']:
                item['authors'] = self.format_authors(item)

            if item['links']:
                githubUrl = self.get_github_project_url(item)
                if githubUrl:
                    request = scrapy.Request(url=githubUrl, callback=self.parese_github_releases)
                    request.meta['item'] = item
                    yield request
                else:
                    for link in item['links']:
                        if link['type'] == 'Download':
                            request = scrapy.Request(url=link['url'], callback=self.parse_adhoc_release)
                            request.meta['item'] = item
                            yield request
                            pass
            else:
                self.logger.warning("Unable to get links of %s" % item['name'])

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