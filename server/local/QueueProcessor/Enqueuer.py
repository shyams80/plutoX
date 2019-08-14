import pymongo
from redis import Redis
from rq import Queue
from datetime import datetime, date
from time import sleep
from bson.objectid import ObjectId

from Spawner import Spawn
from Config import Config
from Status import Status

class Enqueuer:
    def __init__(self):
        self.config = Config()
        self.metaQ = Queue('pluto', connection=Redis('windows', 6379, db=1), default_timeout=1*3600)
        self.status = Status()

        client = pymongo.MongoClient(f"mongodb+srv://explorer:{self.config.MongoPass}@cluster0-eyzcm.mongodb.net/test?retryWrites=true&w=majority")
        self.db = client.plutoQ

    def Cleanup(self):
        dmRet = self.db.q.delete_many({'$and': [ { '$or': [{'githubUser': 'shyams80'}, {'githubUser': 'stockviz'}] }, {'isProcessed': True} ]})
        print(f"delete {dmRet.deleted_count} from mongo queue")

    def Queue(self, meta):
        self.metaQ.enqueue(Spawn, meta, result_ttl=0)
        
    def Loop(self):
        request = self.db.q.find_one({ '$or': [{'$and': [{ 'isEnqueued': {'$exists': True} }, {'isEnqueued': False}]}, {'$and': [{ 'isEnqueued': {'$exists': False} }, {'isProcessed': False }] }] })
        if request == None:
            return
    
        qId = ObjectId(request['_id'])
        self.db.q.update_one({'_id': qId}, {'$set': {'isEnqueued': True, 'enqueuedOn': datetime.now()}})
        self.status.Update(qId, 'queued')
        
        meta = {
            "id": str(request['_id']),
            "githubUser": request['githubUser']
            }
        
        #Spawn(meta)
        self.Queue(meta)

enqueuer = Enqueuer()
#meta = {'id': '5d526abde7ccfb4adf63d359', 'githubUser': 'shyams80'}
#enqueuer.Queue(meta)
#enqueuer.Cleanup()

while True:
    try:
        enqueuer.Loop()
        #enqueuer.Cleanup()
        print(datetime.now())
    except Exception as exp:
        print(exp)

    sleep(1)


