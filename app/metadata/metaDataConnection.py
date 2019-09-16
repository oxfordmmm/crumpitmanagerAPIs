#!/usr/bin/env python3
import mysql.connector
import logging

class metaDataConnection:
    def __init__(self, ip='localhost', port=3306, user='crumpit', password='CrumpitUserP455!', database='NanoporeMeta'):
        self.ip = ip
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.activeConnection = 0

        fileStream = logging.FileHandler('metaDataConnection.log')
        fileStream.setLevel(logging.DEBUG)
        consoleStream = logging.StreamHandler()
        consoleStream.setLevel(logging.ERROR)
        logging.basicConfig(level=logging.DEBUG,
            format="%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s",
            handlers=[
                fileStream,
                consoleStream]
            )

        self.resetSqlConnection()

    def resetSqlConnection(self):
        self.activeConnection = 0
        try:
            self.conn = mysql.connector.connect(user=self.user, database=self.database, host=self.ip, port=self.port, password=self.password, connection_timeout=10)
            self.cursor = self.conn.cursor(dictionary=True)
            self.activeConnection = 1
        except mysql.connector.Error as err:
            logging.exception("Something went wrong connecting to the SQL DB: {}".format(err))
        return self.activeConnection

    def __del__(self):
        try:
            self.cursor.close()
            self.conn.close()
        except Exception as e:
            print(e)

    def getRuns(self):
        if not self.activeConnection:
            self.resetSqlConnection()

        try:
            query = ("SELECT sample_name, porechop, map FROM Run")
            self.cursor.execute(query)

            runs = {}
            for row in self.cursor:
                runs[row['sample_name']] = row
            return runs

        except mysql.connector.Error as err:
            logging.exception("Could not access runs DB: {}".format(err))
            return -1