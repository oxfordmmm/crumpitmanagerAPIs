#! /usr/bin/python3

#RESTful API services for NanoporeManager
#
#Author: Jez Swann
#Date: April 2019
#Tutorial: http://blog.luisrei.com/articles/flaskrest.html
#Mongo JSON conversion adapted from https://gist.github.com/akhenakh/2954605

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

from runsInfo import *

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

setup_logging()
logger = logging.getLogger('api')
logger.debug("Logging initialized")

app = Flask(__name__)

@app.route('/',methods = ['GET'])
def api_root():
	rs = [1,'Welcome to Nanopore Manager APIs']	
	return generateResponse(rs,200) 

@app.route('/runs/',methods = ['GET'])
def getRuns():
	rs = [1, runsInfo().getRuns()]
	return generateResponse(rs,200) 

@app.route('/runs/getLiveStats',methods = ['GET'])
def getLiveStats():
	rs = [1, runsInfo().getLiveStats()]
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
    app.run(host='0.0.0.0', port=5607)
