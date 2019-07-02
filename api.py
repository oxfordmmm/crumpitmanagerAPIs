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

import config
from runsInfo import *
from clusterInfo import *

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

    cfg = config.Config()
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

setup_logging()
logger = logging.getLogger('api')
logger.debug("Logging initialized")
reload_cfg()

app = Flask(__name__)

@app.route('/',methods = ['GET'])
def api_root():
    rs = [1,'Welcome to crumpit Manager APIs']	
    return generateResponse(rs,200) 

@app.route('/runs',methods = ['GET'])
def getRuns():
    try:
        rs = [1, getRunsInfo().getRuns()]
    except Exception as e:
        logger.debug(str(e))
        rs = [-1, "could not connect to mongo db"]

    return generateResponse(rs,200) 

@app.route('/runs/graph',methods = ['GET'])
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

@app.route('/runs/liveStats',methods = ['GET'])
def getLiveStats():
    try:
        rs = [1, getRunsInfo().getLiveStats()]
    except Exception as e:
        logger.debug(str(e))
        rs = [-1, "Error Getting liveStats"]

    return generateResponse(rs,200)

@app.route('/backups',methods = ['GET'])
def getRunBackups():
    dbRuns = getRunsInfo().getRuns()
    rs = [1, clusterInfo().getBackupInfo(cfg.get('logDir'), dbRuns, cfg.get('clusterInfo')['remoteStorage'])]
    return generateResponse(rs,200) 

@app.route('/clusterInfo',methods = ['GET'])
def getClusterInfo():
    localInfo = clusterInfo().getLocalInfo(cfg.get('clusterInfo'))
    remoteInfo = clusterInfo().getRemoteInfo(cfg.get('clusterInfo')['remoteStorage'])
    combinedInfo = {'localInfo': localInfo, 'remoteInfo': remoteInfo}
    rs = [1, combinedInfo]
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
        
    app.run(host='0.0.0.0', port=port)
