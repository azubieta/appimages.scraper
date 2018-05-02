import scrapy
import json


class AppImageReleasesSpider(scrapy.Spider):
    name = "appimage.github.io"
    githubRequestCount = 0

    def start_requests(self):
        urls = ['https://appimage.github.io/feed.json']
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
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
        self.log('Parsing adhoc: %s' % response.body)
