#!/usr/bin/env python3

import os
import sys
import requests
import json
import optparse

API_URL = "http://localhost:3000/api/"


def login(username, password):
    response = requests.post(url=API_URL + "publishers/login",
                             headers={"Content-Type": "application/json", "Accept": "application/json"},
                             data="{\"username\" : \"" + username + "\", \"password\": \"" + password + "\"}")

    r = response.json()
    if 'id' in r:
        return r['id']
    else:
        return ''


def logout(auth):
    response = requests.post(url=API_URL + "publishers/logout?access_token=" + auth,
                             headers={"Content-Type": "application/json", "Accept": "application/json"}, )

    print("Logout succeed: " + str(response.ok))


def read(path):
    info = None
    with open(path, 'r') as f:
        info = json.loads(f.read())

    return info


def upload(info, auth):
    response = requests.post(url=API_URL + "applications/uploadAppInfo?access_token=" + auth,
                             headers={"Content-Type": "application/json", "Accept": "application/json"},
                             json={"AppImageInfo": info})

    if response.status_code != 200:
        print('WARNING: Upload failed\n' + response.text)


if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option("-l", "--url", dest="url",
                      help="NX Software Center Server api url.", metavar="URL")

    parser.add_option("-u", "--user", dest="user",
                      help="User name.", metavar="user")

    parser.add_option("-p", "--password", dest="password",
                      help="Password.", metavar="password")

    parser.add_option("-i", "--icons-prefix", dest="prefix",
                      help="Prefix to be appended to the icon path.", metavar="prefix")

    parser.add_option("-q", "--quiet",
                      action="store_false", dest="verbose", default=True,
                      help="don't print status messages to stdout")

    (options, args) = parser.parse_args()

    if not options.url or not options.user or not options.password:
        parser.print_help()
        exit(1)

    API_URL = options.url
    auth = login(options.user, options.password)
    print(auth)

    items = os.listdir('cache')
    for item in items:
        item_dir = 'cache/' + item + '/'
        files = os.listdir(item_dir)
        if 'AppImageInfo.json' in files:
            item = read(item_dir + 'AppImageInfo.json')
            if item:
                if options.prefix and 'AppImageIcon' in files:
                    item['icon'] = options.prefix + item_dir + 'AppImageIcon'
            if 'id' in item:
                print("Uploading " + item['id'] + " from: " + item_dir)
                upload(item, auth)
            else:
                print('WARNING: Malformed AppImageInfo at: ' + item_dir)
    logout(auth)
