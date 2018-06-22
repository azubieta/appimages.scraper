# appimages.scraper
Search for AppImage releases over the web.

### Dependencies
* Python 3.6
* Scrapy


### Run
* Normal run:`scrapy crawl generic.crawler -a project_file=./projects/AppImageKit.json`
* Output results to json:
`scrapy crawl appimage.github.io -o result.json -t json`


### Input 
The scraper should be feed with a `project_file` which will be a json formatted file like the following:

```
{
  "id" : "org.appimagekit",
  "urls" : ["https://github.com/AppImage/AppImageKit/releases"]
}
```

**Missing fields?**

Sometimes authors doesnt provide good metadata about their project so we could help them by means of preset values. 
Take a look in the following example at the `presets` field and to the `decription` field inside. It will be use
as a fallback value in case that the author forgets to fill that field.

```
{
  "id" : "org.appimagekit",
  "urls" : ["https://github.com/AppImage/AppImageKit/releases"]
  "presets": {
        "id" : "org.appimage.appimaged",
        "description" : {"null": "Daemon to monitor AppImage files in the user home dir."}
  }
}
```

**Multiple applications release in a single page ?** 

No problem use the match field. It expects to be a python regex 
that will be use to match the right AppImage download links for the app you are scraping.

```
{
  "id" : "org.appimagekit",
  "urls" : ["https://github.com/AppImage/AppImageKit/releases"],
  "match" : ".*\/appimagetool.*",
  "presets": {
        "id" : "org.appimage.appimaged",
        "description" : {"null": "Daemon to monitor AppImage files in the user home dir."}
  }
}
```

