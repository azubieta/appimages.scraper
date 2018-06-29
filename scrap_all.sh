#!/bin/bash 


for P in projects/*; do
    scrapy crawl generic.crawler -a project_file=$P
done
