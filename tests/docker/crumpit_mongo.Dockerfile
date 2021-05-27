from mongo:3.4

COPY mongobackup/gridRuns /mongobackup/
COPY mongo_restore.sh /docker-entrypoint-initdb.d/

EXPOSE 27017