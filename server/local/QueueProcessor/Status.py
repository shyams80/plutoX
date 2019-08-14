import pymongo
from datetime import datetime
from Config import Config
from bson.objectid import ObjectId

class Status:
    def __init__(self):
        self.config = Config()
        client = pymongo.MongoClient(f"mongodb+srv://explorer:{self.config.MongoPass}@cluster0-eyzcm.mongodb.net/test?retryWrites=true&w=majority")
        self.db = client.plutoQ
        
    def Update(self, requestId, description, level = "procStat"):
        self.db.q.update_one({'_id': ObjectId(requestId)}, {'$set': {level: description, level + 'On': datetime.now()}})
        