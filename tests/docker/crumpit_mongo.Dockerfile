from mongo:3.4

COPY mongobackup /mongobackup/
COPY mongo_restore.sh /docker-entrypoint-initdb.d/

EXPOSE 27017