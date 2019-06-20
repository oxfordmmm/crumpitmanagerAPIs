import pandas as pd
from pymongo import MongoClient
import datetime

client = MongoClient('163.1.213.195', 27017)
db = client['gridRuns']
collection = db.gridRuns
hce=collection.find()
log={}
for h in hce: log[h['run_name']]=h

df=pd.DataFrame(log)
df=df.transpose()
df=df.sort_values(by=['starttime'],ascending=False)
timeframe=datetime.datetime.now()-datetime.timedelta(days=3)
f=df[df['Finishtime'] < timeframe]
timeframe=datetime.datetime(2019,3,31)
f=f[f['Finishtime'] > timeframe]
locs=f['cwd']
for l in locs:
    print(l)

