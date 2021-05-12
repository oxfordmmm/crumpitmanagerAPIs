#! /usr/bin/python3

#RESTful API services for crumpitManager
#
#Author: Jez Swann
#Date: May 2019
#Tutorial: http://blog.luisrei.com/articles/flaskrest.html
#Mongo JSON conversion adapted from https://gist.github.com/akhenakh/2954605

import base64
import pathlib

import logging
from flask import Flask, url_for, request
try:
    import simplejson as json
except ImportError:
    try:
        import json
    except ImportError:
        raise ImportError
import datetime
from bson.objectid import ObjectId
from werkzeug import Response
from ete3 import NCBITaxa

import app.config
from app.liveRuns.runsInfo import *
from app.clusterInfo import *
from app.metadata.metaDataConnection import *
from app.nanoporeSeqOptions import *

class MongoJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        elif isinstance(obj, ObjectId):
            return str(obj)
        return json.JSONEncoder.default(self, obj)

def jsonify(*args, **kwargs):
    """ jsonify with support for MongoDB ObjectId
    """
    return Response(json.dumps(dict(*args, **kwargs), cls=MongoJsonEncoder), mimetype='application/json')

def setup_logging():
    logger = logging.getLogger("api")
    logger.setLevel(logging.DEBUG)
    c_handler = logging.StreamHandler()
    f_handler = logging.FileHandler("api.log")
    c_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    f_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(f_handler)
    logger.addHandler(c_handler)

def reload_cfg():
    global configFile
    global cfg
    configFile = pathlib.Path("configs/config.yaml")

    cfg = app.config.Config()
    cfg.load(str(configFile))

def getRunsInfo():
    try:
        mongoDBcfg = cfg.get('mongoDB')
    except Exception as e:
        return runsInfo()
    try:
        mongoDBcfg['port']
    except Exception as e:
        return runsInfo(mongoDBcfg['ip'])
    
    return runsInfo(mongoDBcfg['ip'], mongoDBcfg['port'])

def getRunInfo(run):
    try:
        mongoDBcfg = cfg.get('mongoDB')
    except Exception as e:
        return runInfo(run)
    try:
        mongoDBcfg['port']
    except Exception as e:
        return runInfo(run, mongoDBcfg['ip'])
    
    return runInfo(run, mongoDBcfg['ip'], mongoDBcfg['port'])

def getMetadata():
    try:
        sqlDBcfg = cfg.get('sqlDB')
        try:
            sqlDBcfg['ip']
            try:
                sqlDBcfg['port']
                try:
                    sqlDBcfg['database']
                    return metaDataConnection(ip=sqlDBcfg['ip'], port=sqlDBcfg['port'], database=sqlDBcfg['database'])
                except Exception as e:
                    return metaDataConnection(ip=sqlDBcfg['ip'], port=sqlDBcfg['port'])
            except Exception as e:
                try:
                    sqlDBcfg['database']
                    return metaDataConnection(ip=sqlDBcfg['ip'], database=sqlDBcfg['database'])
                except Exception as e:
                    return metaDataConnection(ip=sqlDBcfg['ip'])
        except:
            try:
                sqlDBcfg['port']
                try:
                    sqlDBcfg['database']
                    return metaDataConnection(port=sqlDBcfg['port'], database=sqlDBcfg['database'])
                except Exception as e:
                    return metaDataConnection(port=sqlDBcfg['port'])
            except Exception as e:
                try:
                    sqlDBcfg['database']
                    return metaDataConnection(database=sqlDBcfg['database'])
                except Exception as e:
                    logging.exception('Config file does not contain valid sql info, using defaults')

    except Exception as e:
        logging.exception('Could not find sql config info, using defaults')

    return metaDataConnection()

def getNanoporeOptions():
    try:
        nanoporeOptionscfg = cfg.get('nanoporeOptions')
    except Exception as e:
        return None
    try:
        nanoporeOptionscfg['barcodeFile']
    except Exception as e:    
        return nanoporeSeqOptions(nanoporeOptionscfg['basecallerFile'])
    
    return nanoporeSeqOptions(nanoporeOptionscfg['basecallerFile'], nanoporeOptionscfg['barcodeFile'])

def getSpeciesFromTaxID(taxID):
    ncbi = NCBITaxa()
    taxid2name = ncbi.get_taxid_translator([taxID])
    if len(taxid2name) > 0:
        return taxid2name[int(taxID)]
    else:
        return str(taxID)

def getSpeciesFromTaxIDs(taxIDs):
    filteredIDs = []
    for taxid in taxIDs:
        try:
            filteredIDs.append(int(taxid))
        except ValueError:
            logging.info('Filtered out an invalid TaxID {}'.format(taxid))

    ncbi = NCBITaxa()
    taxid2name = ncbi.get_taxid_translator(filteredIDs)
    return taxid2name

setup_logging()
logger = logging.getLogger('api')
logger.debug("Logging initialized")
reload_cfg()

app = Flask(__name__)

@app.route('/',methods = ['GET'])
def api_root():
    rs = [1,'Welcome to crumpit Manager APIs']	
    return generateResponse(rs,200) 

@app.route('/liveRuns',methods = ['GET'])
def getRuns():
    try:
        rs = [1, getRunsInfo().getRuns()]
    except Exception as e:
        logger.debug(str(e))
        rs = [-1, "could not connect to mongo db"]

    return generateResponse(rs,200) 

@app.route('/liveRuns/graph',methods = ['GET'])
def getRunsGraph():
    runsInfo = None
    try:
        runsInfo = getRunsInfo()
    except Exception as e:
        logger.debug(str(e))
        rs = [-1, "could not connect to mongo db"]
        return generateResponse(rs, 200)

    try:
        filename = runsInfo.getRunsGraph()
        if isinstance(filename, str):
            runGraph = open(filename, 'rb')
            image_read = runGraph.read()
            image_64_encode = base64.encodestring(image_read)
            image_64_string = image_64_encode.decode('utf-8')
            imageDict = {
                "image" : image_64_string
            }
            rs = [1, imageDict]
            return generateResponse(rs, 200)
        else:
            rs = [0, "Could not create Image"]
            return generateResponse(rs, 500)
    except Exception as e:
        logger.debug(str(e))
        rs = [0, "Could not create Image"]
        return generateResponse(rs, 500)

@app.route('/liveRuns/graph/<runId>',methods = ['GET'])
def getLiveRunGraph(runId):
    runsInfo = None
    try:
        runsInfo = getRunsInfo().getRuns()
    except Exception as e:
        logger.debug(str(e))
        rs = [-1, "could not connect to mongo db"]
        return generateResponse(rs, 200)

    if runId in runsInfo:
        filenames = getRunInfo(runsInfo[runId]).getRunGraphs()
        imageDict = {}
        for graph, filename in filenames.items():
            try:
                if filename and isinstance(filename, str):
                    runGraph = open(filename, 'rb')
                    image_read = runGraph.read()
                    image_64_encode = base64.encodestring(image_read)
                    image_64_string = image_64_encode.decode('utf-8')
                    imageDict[graph] = image_64_string
                else:
                    logger.debug("Could not create Image for run {}, graph {}".format(runId, graph))
                    imageDict[graph] = None
            except Exception as e:
                logger.debug(str(e))
                logger.debug("Could not create Image for run {}, graph {}".format(runId, graph))
                imageDict[graph] = None
        rs = [1, imageDict]
        return generateResponse(rs, 200)
    else:
        logger.debug("Not a valid Run")
        rs = [0, "Not a valid Run"]
        return generateResponse(rs, 500)

@app.route('/liveRuns/liveStats',methods = ['GET'])
def getLiveStats():
    try:
        rs = [1, getRunsInfo().getLiveStats()]
    except Exception as e:
        logger.debug(str(e))
        rs = [-1, "Error Getting liveStats"]

    return generateResponse(rs,200)

@app.route('/metadata/runs',methods = ['GET'])
def getMetadataRuns():
    try:
        rs = [1, getMetadata().getPreRunInfo()]
    except Exception as e:
        logger.debug(str(e))
        rs = [-1, "could not connect to SQL db"]

    return generateResponse(rs,200) 

@app.route('/metadata/run',methods = ['GET'])
def getMetadataRunFields():
    try:
        returnDict = getMetadata().getPreRunFields()
        returnDict.update({'flowcells': getNanoporeOptions().getFlowcells()})
        taxIDs = returnDict['taxIDs']
        taxIDs.sort()
        taxIDDict = dict()
        for taxID in taxIDs:
            taxIDDict[taxID] = getSpeciesFromTaxID(taxID)
        returnDict['taxIDs'] = taxIDDict

        returnDict['customRefs'] = []
        customRefPath = cfg.get('clusterInfo')['customRefsLocation']
        if customRefPath:
            try:
                fasta_ext = ['.fasta', '.fa', 'fas', 'fna']
                compress_ext = ['.gz', '.gzip', '.gunzip']

                returnDict['customRefs'] = []
                for filepath in [f for f in os.listdir(customRefPath) if os.path.isfile(os.path.join(customRefPath, f))]:
                    filename, ext = os.path.splitext(filepath)
                    if ext in fasta_ext:
                        returnDict['customRefs'].append(filepath)
                    elif ext in compress_ext and os.path.splitext(filename)[1] in fasta_ext:
                        returnDict['customRefs'].append(filepath)

            except os.error:
                logging.error("Error scanning custom reference directory")
        rs = [1, returnDict]
    except Exception as e:
        logger.debug(str(e))
        rs = [-1, "could not connect to SQL db"]

    return generateResponse(rs,200) 

@app.route('/metadata/run/seqKits/<flowcell>',methods = ['GET'])
def getSeqKits(flowcell):
    try:
        seqKits = getNanoporeOptions().getSequencingKitsForFlowcell(flowcell)
        rs = [1, seqKits]
    except Exception as e:
        logger.debug(str(e))
        rs = [-1, "flowcell not valid"]
    return generateResponse(rs,200)

@app.route('/metadata/run/barcoding/<flowcell>/<seqKit>',methods = ['GET'])
def getBarcoding(flowcell, seqKit):
    try:
        barcoding = getNanoporeOptions().getBarcodesForSeqkit(flowcell, seqKit)
        rs = [1, barcoding]
    except Exception as e:
        logger.debug(str(e))
        rs = [-1, "Sequencing kit not valid"]
    return generateResponse(rs,200) 

@app.route('/metadata/run',methods = ['POST'])
def addRun():
    if 'json' in request.headers['Content-Type']:
        try:
            data = request.json
            try:
                print("Params:" + str(data.items()))
            except:
                return generateResponse([0 ,"Invalid parameter"])

            (result, message) = getMetadata().addRun(data)
            rs = [result, message]
        except Exception as e:
            logger.debug(str(e))
            rs = [-1, "could not connect to SQL db"]

    else:
        return generateResponse([0,"Unsupported Media Type"])

    return generateResponse(rs,200) 

@app.route('/metadata/run/<runName>',methods = ['GET'])
def getMetadataRun(runName):
    try:
        rs = [1, getMetadata().getPreRunInfo(runName)]
    except Exception as e:
        logger.debug(str(e))
        rs = [-1, "could not connect to SQL db"]

    return generateResponse(rs,200)

@app.route('/metadata/sample/<guid>',methods = ['GET'])
def getMetadataBarcode(guid):
    try:
        rs = [1, getMetadata().getBarcodeInfo(guid)]
    except Exception as e:
        logger.debug(str(e))
        rs = [-1, "could not connect to SQL db"]

    return generateResponse(rs,200)  

@app.route('/metadata/graph/<runName>',methods = ['GET'])
def getMetaRunGraph(runName):
    if runName in getMetadata().getPreRunInfo().keys():
        file_name = "images/{}-depth.png".format(runName)
        if not os.path.isfile(file_name):
            logger.debug("No graph available for run {}".format(runName))
            rs = [0, "No graph available for run {}".format(runName)]
            return generateResponse(rs, 200)

        try:
            if isinstance(file_name, str):
                runGraph = open(file_name, 'rb')
                image_read = runGraph.read()
                image_64_encode = base64.encodestring(image_read)
                image_64_string = image_64_encode.decode('utf-8')
                imageDict = {
                    "image" : image_64_string
                }
                rs = [1, imageDict]
                return generateResponse(rs, 200)
            else:
                logger.debug("Could not create Image for run {} graph depth".format(runName))
                rs = [0, "Could not create Image for run {}, graph depth"]
                return generateResponse(rs, 200)
        except Exception as e:
            logger.debug(str(e))
            logger.debug("Could not create Image for run {}, graph depth".format(runName))
            rs = [0, "Could not create Image for run {}, graph depth"]
            return generateResponse(rs, 200)
    else:
        logger.debug("Not a valid Run")
        rs = [0, "Not a valid Run"]
        return generateResponse(rs, 500)

@app.route('/metadata/depthStats/run/<runID>',methods = ['GET'])
def getMetadataDepthStatsByRun(runID):
    try:
        rs = [1, getMetadata().getDepthStats(run_id=runID)]
    except Exception as e:
        logger.debug(str(e))
        rs = [-1, "could not connect to SQL db"]

    return generateResponse(rs,200)

@app.route('/metadata/depthStats/sample/<guid>',methods = ['GET'])
def getMetadataDepthStatsBySample(guid):
    try:
        rs = [1, getMetadata().getDepthStats(barcode_id=guid)]
    except Exception as e:
        logger.debug(str(e))
        rs = [-1, "could not connect to SQL db"]

    return generateResponse(rs,200)

@app.route('/taxid',methods = ['POST'])
def getTaxConversions():
    if 'json' in request.headers['Content-Type']:
        try:
            data = request.json
            try:
                print("Params:" + str(data.items()))
            except:
                return generateResponse([0 ,"Invalid parameter"])

            rs = [1, getSpeciesFromTaxIDs(data['taxIDs'])]
        except Exception as e:
            logger.debug(str(e))
            rs = [-1, "could not get species"]

    else:
        return generateResponse([0,"Unsupported Media Type"])

    return generateResponse(rs,200) 

@app.route('/taxid/<taxid>',methods = ['GET'])
def getTaxConversion(taxid):
    try:
        taxStr = getSpeciesFromTaxID(taxid)
        rs = [1, taxStr]
    except Exception as e:
        logger.debug(str(e))
        rs = [-1, "could not convert ID"]

    return generateResponse(rs,200) 

@app.route('/backups',methods = ['GET'])
def getRunBackups():
    dbRuns = getRunsInfo().getRuns()
    rs = [1, clusterInfo().getBackupInfo(cfg.get('logDir'), dbRuns, cfg.get('clusterInfo')['remoteStorage'])]
    return generateResponse(rs,200)

@app.route('/runDiskInfo',methods = ['GET'])
def getRunDiskInfo():
    dbRuns = getRunsInfo().getRuns()
    rs = [1, clusterInfo().getRunDiskInfo(cfg.get('diskDir'), dbRuns, cfg.get('clusterInfo')['remoteStorage'])]
    return generateResponse(rs,200)

@app.route('/clusterInfo',methods = ['GET'])
def getClusterInfo():
    localInfo = clusterInfo().getLocalInfo(cfg.get('clusterInfo'))
    remoteInfo = clusterInfo().getRemoteInfo(cfg.get('clusterInfo')['remoteStorage'])
    combinedInfo = {'localInfo': localInfo, 'remoteInfo': remoteInfo}
    rs = [1, combinedInfo]
    return generateResponse(rs,200)

@app.route('/customRefs',methods = ['GET'])
def getCustomRefs():
    customRefPath = cfg.get('clusterInfo')['customRefsLocation']
    if customRefPath:
        try:
            return generateResponse([1, [f for f in os.listdir(customRefPath) if os.path.isfile(os.path.join(customRefPath, f))]], 200)
        except os.error:
            return generateResponse([-1,"Error scanning custom reference directory"])
    else:
        return generateResponse([-1,"No path for custom reference directory"])
    return generateResponse(rs,200)

#input: result is an array
#result[0] = 0 for OK -- else for error 
#result[1] = data or error message
#Status code list = http://www.flaskapi.org/api-guide/status-codes/
def generateResponse(result, statusCode = None):
    if statusCode is None:
        if result[0] == 0:
            statusCode = 200
        else:
            statusCode = 500

    rs = {}
    rs["status"] = result[0]	
    rs["data"] = result[1]
    resp = jsonify(rs)
    resp.status_code = statusCode		
    return resp

if __name__ == '__main__':
    port = 5607
    try:
        port = cfg.get('flask')['port']
        logger.debug("Using flask port %d", port)
    except Exception as e: 
        logger.debug("Using default flask port 5607")
    
    print("setting up NCBI Taxa DB")
    ncbi = NCBITaxa()
    print("Running api")
    app.run(host='0.0.0.0', port=port)
