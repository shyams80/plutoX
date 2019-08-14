import configparser
import urllib.parse
import os

class Config(configparser.ConfigParser):
    def __init__(self):
        super().__init__()
        self.read('config.ini')
        
        self.MongoPassStr = os.environ['MONGO_PASS']
        self.MongoPass = urllib.parse.quote_plus(self.MongoPassStr)