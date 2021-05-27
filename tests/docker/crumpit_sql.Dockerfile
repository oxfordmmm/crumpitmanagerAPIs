from mysql:5.7

ENV MYSQL_ROOT_PASSWORD rootP455
ENV MYSQL_DATABASE NanoporeMeta

COPY crumpit_init.sql /docker-entrypoint-initdb.d/crumpit_a.sql
COPY crumpit_backup.sql /docker-entrypoint-initdb.d/crumpit_b.sql

EXPOSE 3306
