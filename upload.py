#!/usr/bin/env python3

import os
import sys
import requests
import json

API_URL="http://localhost:3000/api/"

def login(username, password):
    response = requests.post(url=API_URL+"Users/login", 
                  headers={"Content-Type": "application/json", "Accept": "application/json"}, 
                  data="{\"username\" : \""+username+"\", \"password\": \""+ password+"\"}")
    
    r = response.json();
    if 'id' in r:
        return r['id']
    else:
        return ''

def logout(auth):
    response = requests.post(url=API_URL+"Users/logout?access_token="+auth, 
                  headers={"Content-Type": "application/json", "Accept": "application/json"}, )
    
    print("Logout succeed: " + str(response.ok))

def upload(path, auth):
    info = None
    with open(path, 'r') as f:
        info = json.loads(f.read())
    
    if info:
        response = requests.post(url=API_URL+"applications/uploadAppInfo?access_token="+auth, 
                                 headers={"Content-Type": "application/json", "Accept": "application/json"}, 
                                 json={"AppImageInfo": info})
        
        print (response.json())
        
if __name__ == '__main__':
    if len(sys.argv) != 4:
        print('Usage: ./upload_results.py https://apiurl.com/api/ username password')
        exit(1)
    
    API_URL = sys.argv[1]
    auth = login(sys.argv[2], sys.argv[3])
    print(auth)
    
    items = os.listdir('cache')
    for item in items:
        upload('cache/'+item+'/AppImageInfo.json', auth)
    
    logout(auth)
