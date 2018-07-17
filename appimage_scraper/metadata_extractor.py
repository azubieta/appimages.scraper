#!/usr/bin/env python3

import os
import stat
import urllib3
import logging
import subprocess

# Write data to file
filename = "/tmp/AppImage_Metadata_Extractor.linuxdeploy.AppImage"
file_url = 'https://github.com/azubieta/appimage-metadata-extractor/releases/download/continuous' \
           '/AppImage_Metadata_Extractor.linuxdeploy.AppImage'

logger = logging.getLogger(__name__)


def extract_appimage_metadata(path, target_dir):
    logger.info("Extracting AppImage metadata in: %s" % target_dir)
    if not os.path.exists(filename):
        download_metadata_extractor_binary()

    process = subprocess.Popen([filename, "-t", target_dir, path])
    process.communicate()

    if process.returncode == 0:
        return "AppImageInfo.json", "AppImageIcon"
    else:
        output = process.stderr.read() if process.stderr \
            else "Return code: " + str(process.returncode)
        raise RuntimeError('Unable to extract AppImage metadata. Error output: ' + output)


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