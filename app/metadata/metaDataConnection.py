#!/usr/bin/env python3
import mysql.connector
import logging
import uuid
from dateutil.parser import parse
import bson.int64

from app.nanoporeSeqOptions import *

class metaDataConnection:
    def __init__(self, ip='localhost', port=3306, user='crumpit', password='CrumpitUserP455!', database='NanoporeMeta', use_pure=True):
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
            self.conn = mysql.connector.connect(user=self.user, database=self.database, host=self.ip, port=self.port, password=self.password, connection_timeout=10, use_pure=True)
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

    def __getCurrentMapIDs(self):
        if not self.activeConnection:
            self.resetSqlConnection()

        try:
            query = ("SELECT DISTINCT TaxID FROM `Mapped Species` Order By TaxID;")
            self.cursor.execute(query)

            taxIDs = []
            for row in self.cursor:
                taxIDs.append(int(row['TaxID']))
            
            return taxIDs
        
        except mysql.connector.Error as err:
            logging.exception("Could not access DB: {}".format(err))
            return []

    def __createInsertQuery(self, values:dict, fkID:str=None, fkColumn:str=None):
        columnsText = "(ID"
        valuesText = "VALUES (%(ID)s"
        valuesData = { 'ID':uuid.uuid4().bytes }

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
            elif isinstance(value, bson.int64.Int64):
                valuesData[column] = str(value)
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
                elif column == 'run_date':
                    run[column] = parse(post[column])
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

    def __insertIntoMappedSpecies(self, post:dict, runID:bytes):
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

    def __insertIntoBarcodes(self, post:dict, runID:bytes):
        if 'barcodes' not in post:
            logging.debug('no barcode information was provided for run {}'.format(post["sample_name"]))
        else:
            if not post['barcodes'] == None:
                for barcode in post['barcodes']:
                    (queryText, valuesData) = self.__createInsertQuery(values=barcode, fkID=runID, fkColumn='RunID')
                    query = ("INSERT INTO Barcode " + queryText)

                    if not self.activeConnection:
                        self.resetSqlConnection()

                    self.cursor.execute(query, valuesData)
                    if self.cursor.rowcount < 1:
                        raise mysql.connector.errors.Error("No rows inserted")

    def __insertIntoFKTable(self, table:str, idVal:str, idColumn:str, post:dict, fkID:bytes, fkColumn:str):
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

    def getRun(self, name:str):
        if not self.activeConnection:
            self.resetSqlConnection()

        try:
            query = ("SELECT * FROM Run WHERE sample_name = %s")
            self.cursor.execute(query, (name,))

            for row in self.cursor:
                return row

        except mysql.connector.Error as err:
            logging.exception("Could not access runs DB: {}".format(err))
            return -1

    def getRuns(self):
        if not self.activeConnection:
            self.resetSqlConnection()

        try:
            query = ("SELECT sample_name, basecalling, porechop, map, flow, kit FROM Run")
            self.cursor.execute(query)

            runs = {}
            for row in self.cursor:
                runs[row['sample_name']] = row
            return runs

        except mysql.connector.Error as err:
            logging.exception("Could not access runs DB: {}".format(err))
            return -1

    def getPreRunFields(self):
        porechop = {'normal': 'Default porechop', 
        'strict': 'Strict porechop', 
        'guppy': 'Default guppy', 
        'guppy_strict': 'Strict guppy', 
        'off': 'No demultiplexing is required or demultiplexing will occur on the GridION.'}

        currentTaxIDs = self.__getCurrentMapIDs()
        taxIDs = [485, 813, 1045]
        for taxID in taxIDs:
            if taxID not in currentTaxIDs:
                currentTaxIDs.append(taxID)

        currentTaxIDs.sort()
        return { 'porechop': porechop, 'taxIDs': currentTaxIDs }

    def getPreRunInfo(self, name:str = None):
        if not self.activeConnection:
            self.resetSqlConnection()

        try:
            if name != None:
                query = ("SELECT Run.ID_text AS RunID, sample_name, run_date, basecalling, porechop, flow, seq_kit, bar_kit, wash_number, watch_hours, map AS mapping, TaxID FROM Run LEFT JOIN `Mapped Species` ON `Mapped Species`.RunID = Run.ID WHERE sample_name = %s;")
                self.cursor.execute(query, (name,))
            else:
                query = ("SELECT Run.ID_text AS RunID, sample_name, run_date, basecalling, porechop, flow, seq_kit, bar_kit, wash_number, watch_hours, map AS mapping, TaxID FROM Run LEFT JOIN `Mapped Species` ON `Mapped Species`.RunID = Run.ID;")
                self.cursor.execute(query)

            info = {}
            
            for row in self.cursor:
                if row['sample_name'] in info:
                    info[row['sample_name']]['mapping'] += ' ' + row['TaxID']
                else:
                    info[row['sample_name']] = {'sample_name':row['sample_name'], 'RunID':row['RunID'], 'run_date':row['run_date'], 'basecalling':row['basecalling'], 'porechop':row['porechop'], 'flow':row['flow'], 'seq_kit':row['seq_kit'], 'bar_kit':row['bar_kit'], 'wash_number':row['wash_number'], 'watch_hours':row['watch_hours'] }
                    if row['TaxID'] == None:
                        if row['mapping'] == '0':
                            info[row['sample_name']]['mapping'] = 'off'
                        else:
                            info[row['sample_name']]['mapping'] = 'on'
                    else:
                        info[row['sample_name']]['mapping'] = row['TaxID']
            
            for (sample_name, run) in info.items():
                if (not run['mapping'] == 'off') and (not run['mapping'] == 'on'):
                    mappingSort = run['mapping'].split(' ')
                    mappingSortInt = []
                    for taxID in mappingSort:
                        mappingSortInt.append(int(taxID))
                    mappingSortInt.sort()
                    run['mapping'] = ' '.join(str(taxID) for taxID in mappingSortInt)
                
                query = ("SELECT barcode, `Barcode`.ID_text AS sampleID, name, total_bases, total_reads, unclassified_bases, unclassified_reads FROM Run JOIN `Barcode` ON `Barcode`.RunID = Run.ID WHERE Run.ID_text = %s ORDER BY length(barcode), barcode;")
                self.cursor.execute(query, (info[sample_name]['RunID'],))

                barcodes = []
                for row in self.cursor:
                    barcodes.append({"barcode":row['barcode'], "sampleID":row['sampleID'], "name":row['name'], "total_bases":row['total_bases'], "total_reads":row['total_reads'], "unclassified_bases":row['unclassified_bases'], "unclassified_reads":row['unclassified_reads']})
                
                if name != None:
                    query = ("SELECT b.ID_text as BarcodeID, TaxID as taxID, k.name AS kingdom_name, cs.bases, cs.sequenceReads as sequence_reads, cs.filtered  \
                        FROM NanoporeMeta.`Classified Species` AS cs \
                        JOIN NanoporeMeta.Kingdom as k ON cs.KingdomID = k.ID \
                        JOIN NanoporeMeta.Barcode as b ON k.BarcodeID = b.ID \
                        JOIN NanoporeMeta.Run as r ON b.RunID = r.ID \
                        WHERE r.ID_text = %s and filtered = 1 \
                        ORDER BY cs.bases DESC;")
                    self.cursor.execute(query, (info[sample_name]['RunID'],))

                    for row in self.cursor:
                        for barcode in barcodes:
                            if row['BarcodeID'] == barcode['sampleID']:
                                if 'mapped_species' in barcode:
                                    barcode['mapped_species'].append({"taxID": row['taxID'], "kingdom_name": row['kingdom_name'], "bases": row['bases'], "sequence_reads":row['sequence_reads'], "filtered":row['filtered']})
                                else:
                                    barcode['mapped_species'] = [{"taxID": row['taxID'], "kingdom_name": row['kingdom_name'], "bases": row['bases'], "sequence_reads":row['sequence_reads'], "filtered":row['filtered']}]

                run['barcodes'] = barcodes
            
            return info

        except mysql.connector.Error as err:
            logging.exception("Could not access runs DB: {}".format(err))
            return -1

    def getBarcodeInfo(self, guid:str = None):
        if not self.activeConnection:
            self.resetSqlConnection()

        try:
            if guid != None:
                query = ("SELECT `Barcode`.ID_text AS 'sampleID', name as 'barcode_name', sample_name as 'run_name', barcode, total_bases, total_reads, unclassified_bases, unclassified_reads FROM Run JOIN `Barcode` ON `Barcode`.RunID = Run.ID WHERE `Barcode`.ID_text = %s;")
                self.cursor.execute(query, (guid,))
            else:
                logging.exception("Need to request a specific sample GUID")
                return -1

            resultDict = {}
            for row in self.cursor:
                resultDict = row
                break

            query = ("SELECT b.ID_text as BarcodeID, TaxID as taxID, k.name AS kingdom_name, cs.bases, cs.sequenceReads as sequence_reads, cs.filtered  \
                FROM `Classified Species` AS cs \
                JOIN `Kingdom` AS k  ON cs.KingdomID = k.ID \
                JOIN `Barcode` AS b ON k.BarcodeID = b.ID \
                WHERE b.ID_text = %s \
                ORDER BY cs.bases DESC;")
            self.cursor.execute(query, (guid,))

            mapped_species = []
            for row in self.cursor:
                mapped_species.append({"taxID": row['taxID'], "kingdom_name": row['kingdom_name'], "bases": row['bases'], "sequence_reads":row['sequence_reads'], "filtered":row['filtered']})
            resultDict['mapped_species'] = mapped_species
            return resultDict

        except mysql.connector.Error as err:
            logging.exception("Could not access runs DB: {}".format(err))
            return -1

    def addRun(self, post: dict):
        logging.info("Inserting Run {}".format(post['sample_name']))
        try:
            if self.getRun(post['sample_name']):
                logging.exception("Run {} already exists".format(post['sample_name']))
                return (-1, "Run {} already exists".format(post["sample_name"]))
            
            if 'barcodes' not in post or post['barcodes'] == None:
                logging.debug('No Samples were provided for run {}'.format(post["sample_name"]))
                return (-1, "No Samples were provided for run {}".format(post["sample_name"]))
            else:
                for barcode in post['barcodes']:
                    if 'name' not in barcode or barcode['name'] == None:
                        logging.debug('An empty sample was provided for run {}. Please report this error'.format(post["sample_name"]))
                        return (-1, "An empty sample was provided for run {}. Please report this error".format(post["sample_name"]))

                    if 'sampleID' in barcode:
                        del barcode['sampleID']

            runID = self.__insertIntoRun(post=post)
            self.__insertIntoMappedSpecies(post=post, runID=runID)
            self.__insertIntoBarcodes(post=post, runID=runID)
            self.conn.commit()
        except Exception as e:
            logging.exception("Exception {}".format(e))
            logging.exception("Run {}".format(post['sample_name']))
            logging.exception(post)
            return (-1, str(e))
        return (1, "Inserted Run {}".format(post["sample_name"]))