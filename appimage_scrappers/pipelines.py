# -*- coding: utf-8 -*-

import logging
import requests
import os


class FillMissingMetadataPipeline(object):
    def gessArch(self, url):
        arch = 'unknown'
        if 'x86' in url:
            arch = 'x86'

        if 'x86_64' in url:
            arch = 'x86_64'

        if 'i386' in url:
            arch = 'i386'

        if 'i386' in url:
            arch = 'i386'

        return arch

    def process_item(self, item, spider):
        if not 'version' in item:
            item['version'] = 'latest'
            
        if not 'codeName' in item:
            item['codeName'] = item['name'].lower()

        if not 'arch' in item:
            item['arch'] = self.gessArch(item['downloadUrl'])

        item['id'] = "%s-%s_%s" % (item['codeName'], item['version'].lower(), item['arch'])
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
