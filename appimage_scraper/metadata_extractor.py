#!/usr/bin/env python3

import urllib3
import os
import stat
import subprocess

# Write data to file
filename = "/tmp/AppImage_Metadata_Extractor-x86_64.AppImage"
file_url = 'https://github.com/azubieta/appimage-metadata-extractor/releases/download/continuous' \
           '/AppImage_Metadata_Extractor-x86_64.AppImage '


def extract_metadata(path, target_dir):
    if not os.path.exists(filename):
        download_metadata_extractor_binary()

    process = subprocess.Popen([filename, "-t", target_dir, path])
    process.communicate()

    return "AppImageInfo.json", "AppImageIcon.png"


def download_metadata_extractor_binary():
    http = urllib3.PoolManager()
    r = http.request("GET", file_url, preload_content=False)
    with open(filename, "wb") as out:
        while True:
            data = r.read()
            if not data:
                break
            out.write(data)
    r.release_conn()
    os.chmod(filename, stat.S_IEXEC | stat.S_IREAD)