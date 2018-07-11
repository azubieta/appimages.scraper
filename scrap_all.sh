#!/bin/bash 

LOCK_FILE="/tmp/lock_appimages.scraper.scrap_all.sh"
if [ -f ${LOCK_FILE} ]
then
    echo "It seems that scrap_all.sh is already running. Or the previous run didn't ended quite well."
    echo "To continue please remove: ${LOCK_FILE}"
    exit 1
else
    touch ${LOCK_FILE}
    for P in projects/*
    do
        scrapy crawl generic.crawler -a project_file=${P}

        if [ %? ]
        then
            echo "Something went wrong with the scrapper."
            rm ${LOCK_FILE}
            exit 1;
        fi
    done
    rm ${LOCK_FILE}
fi
