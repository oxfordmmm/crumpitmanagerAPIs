#!/usr/bin/env python3
import mysql.connector
import logging
import uuid

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

    def getTableColumns(self, table):
        if not self.activeConnection:
            self.resetSqlConnection()

        try:
            query = ("SELECT DISTINCT COLUMN_NAME, IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s")
            self.cursor.execute(query, (self.database, table))

            columns = {}
            for row in self.cursor:
                columns[row['COLUMN_NAME']] = row['IS_NULLABLE']
            
            return columns
        
        except mysql.connector.Error as err:
            logging.exception("Could not access DB: {}".format(err))
            return []

    def __createInsertQuery(self, values:dict, fkID:str=None, fkColumn:str=None):
        columnsText = "(ID"
        valuesText = "VALUES (%(ID)s"
        valuesData = { 'ID':str(uuid.uuid4()) }

        if fkID:
            columnsText += ", {}".format(fkColumn)
            valuesText += ", %(fkID)s"
            valuesData['fkID'] = fkID
        
        for (column, value) in values.items():
            columnsText += ", " + column
            valuesText += ", %(" + column + ")s"

            if isinstance(value, list) and len(value) == 0:
                valuesData[column] = "NULL"
            elif isinstance(value, list):
                valuesData[column] = value[0]
            elif isinstance(value, str) and (value.lower() == "false" or value.lower() == 'n'):
                valuesData[column] = 0
            elif isinstance(value, str) and (value.lower() == "true" or value.lower() == 'y'):
                valuesData[column] = 1
            else:
                valuesData[column] = value
        
        columnsText += ") "
        valuesText += ")"
        return (columnsText + valuesText, valuesData)

    def __getMapInfo(self, post:dict):
        mapping = None
        splitMap = None
        if 'map' not in post: 
            logging.debug('mapping is switched off for run {}'.format(post['sample_name']))
            mapping = False
        else:
            if isinstance(post['map'], str):
                if (str(post['map']).lower() == 'off'):
                    logging.debug('mapping is switched off for run {}'.format(post['sample_name']))
                    mapping = False
                elif str(post['map']).lower() == 'on':
                    logging.debug('mapping is switched on for run {} with no specific TaxIDs'.format(post['sample_name']))
                    mapping = True
                else:
                    mapping = True
                    splitMap = str(post['map']).split(' ')
            else:
                if (str(post['map'][0]).lower() == 'off'):
                    logging.debug('mapping is switched off for run {}'.format(post['sample_name']))
                    mapping = False
                elif str(post['map'][0]).lower() == 'on':
                    logging.debug('mapping is switched on for run {} with no specific TaxIDs'.format(post['sample_name']))
                    mapping = True
                else:
                    mapping = True
                    splitMap = str(post['map'][0]).split(' ')
        return (mapping, splitMap)

    def __insertIntoRun(self, post: dict):
        columns = self.getTableColumns('Run')
        run = {}

        for (column, nullable) in columns.items():
            if column in post:
                if column == 'map':
                    (mapping, splitMap) = self.__getMapInfo(post)
                    if mapping != None:
                        run[column] = mapping
                else:
                    run[column] = post[column]
            elif not nullable:
                raise Exception('Field {} not found and is required.'.format(column))
            else:
                logging.debug('Field {} not found but is not required'.format(column))

        (queryText, valuesData) = self.__createInsertQuery(values=run)
        query = ("INSERT INTO Run " + queryText)

        if not self.activeConnection:
            self.resetSqlConnection()

        self.cursor.execute(query, valuesData)
        if self.cursor.rowcount < 1:
            raise mysql.connector.errors.Error("No rows inserted")
        else:
            return valuesData['ID']

    def __insertIntoMappedSpecies(self, post:dict, runID:str):
        (mapping, splitMap) = self.__getMapInfo(post)
        
        if splitMap:
            mapList = []
            for species in splitMap:
                mapList.append({'taxID':int(species)})
            
            for entry in mapList:
                (queryText, valuesData) = self.__createInsertQuery(values=entry, fkID=runID, fkColumn='RunID')
                query = ("INSERT INTO `Mapped Species` " + queryText)

                if not self.activeConnection:
                    self.resetSqlConnection()

                self.cursor.execute(query, valuesData)
                if self.cursor.rowcount < 1:
                    raise mysql.connector.errors.Error("No rows inserted")

    def __insertIntoFKTable(self, table:str, idVal:str, idColumn:str, post:dict, fkID:str, fkColumn:str):
        columns = self.getTableColumns(table)

        valuesDict = { idColumn:idVal }
        for (column, nullable) in columns.items():
            if column in post:
                valuesDict[column] = post[column]
            elif not nullable:
                raise Exception('Field {} not found and is required.'.format(column))
        
        (queryText, valuesData) = self.__createInsertQuery(values=valuesDict, fkID=fkID, fkColumn=fkColumn)
        query = ("INSERT INTO `{}` ".format(table) + queryText)

        if not self.activeConnection:
            self.resetSqlConnection()

        self.cursor.execute(query, valuesData)
        if self.cursor.rowcount < 1:
            raise mysql.connector.errors.Error("No rows inserted")
        else:
            return valuesData['ID']

    def getRuns(self):
        if not self.activeConnection:
            self.resetSqlConnection()

        try:
            query = ("SELECT sample_name, porechop, map, flow, kit FROM Run")
            self.cursor.execute(query)

            runs = {}
            for row in self.cursor:
                runs[row['sample_name']] = row
            return runs

        except mysql.connector.Error as err:
            logging.exception("Could not access runs DB: {}".format(err))
            return -1

    def getPreRunFields(self):
        porechop = ['normal', 'strict', 'guppy']
        taxIds = [485, 813, 1045]
        flowcells = ['FLO-MIN106', 'FLO-MIN107']
        sequenceKits = ['SQK-LSK108', 'SQK-LSK109', 'SQK-RBK004', 'SQK-RPB004']
        barcodeKits = ['EXP-NBD104', 'SQK-RBK004', 'SQK-RPB004']
        return { 'porechop': porechop, 'taxIDs': taxIds, 'flowcells': flowcells, 'sequenceKits': sequenceKits, 'barcodeKits': barcodeKits }

    def getPreRunInfo(self):
        if not self.activeConnection:
            self.resetSqlConnection()

        try:
            query = ("SELECT sample_name, porechop, map AS mapping, TaxID FROM Run LEFT JOIN `Mapped Species` ON `Mapped Species`.RunID = Run.ID;")
            self.cursor.execute(query)

            info = {}
            for row in self.cursor:
                if row['sample_name'] in info:
                    info[row['sample_name']]['mapping'] += ' ' + row['TaxID']
                else:
                    info[row['sample_name']] = {'sample_name':row['sample_name'], 'porechop':row['porechop']}
                    if row['TaxID'] == None:
                        if row['mapping'] == '0':
                            info[row['sample_name']]['mapping'] = 'off'
                        else:
                            info[row['sample_name']]['mapping'] = 'on'
                    else:
                        info[row['sample_name']]['mapping'] = row['TaxID']
            
            for run in info.values():
                if (not run['mapping'] == 'off') and (not run['mapping'] == 'on'):
                    mappingSort = run['mapping'].split(' ')
                    mappingSortInt = []
                    for taxID in mappingSort:
                        mappingSortInt.append(int(taxID))
                    mappingSortInt.sort()
                    run['mapping'] = ' '.join(str(taxID) for taxID in mappingSortInt)
            
            return info

        except mysql.connector.Error as err:
            logging.exception("Could not access runs DB: {}".format(err))
            return -1

    def addRun(self, post: dict):
        logging.info("Inserting Run {}".format(post['sample_name']))
        try:
            runID = self.__insertIntoRun(post=post)
            self.__insertIntoMappedSpecies(post=post, runID=runID)
            self.conn.commit()
        except Exception as e:
            logging.exception("Exception {}".format(e))
            logging.exception("Sample {}".format(post['sample_name']))
            logging.exception(post)
            return str(e)
        return "Inserted Run {}".format(post["sample_name"])