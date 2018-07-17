#!/bin/bash 

LOCK_FILE="/tmp/lock_appimages.scraper.scrap_all.sh"

rm scrap_all_projects_failed
rm scrap_all_projects_succeed

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
            echo "${P}" >> scrap_all_projects_failed
        else
            echo "${P}" >> scrap_all_projects_succeed
        fi
    done
    rm ${LOCK_FILE}
fi
