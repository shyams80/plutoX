import sys
import nbformat
import subprocess
import os
import shlex
import gzip
from github import Github
import pymongo
from datetime import datetime
import urllib.parse
from bson.objectid import ObjectId

class ProcessorLxd:
    def __init__(self, mongoPassTxt):
        self.plutoPath = "/home/pluto/"
        self.mongoPass = urllib.parse.quote_plus(mongoPassTxt)
        client = pymongo.MongoClient(f"mongodb+srv://explorer:{self.mongoPass}@cluster0-eyzcm.mongodb.net/test?retryWrites=true&w=majority")
        self.db = client.plutoQ

    def getOutputLength(self):
        nbDoc = nbformat.read(self.nbFileName, as_version=4)
        textLength = 0
        for nbCell in nbDoc['cells']:
            if nbCell['cell_type'] != 'code':
                continue
    
            for nbOut in nbCell['outputs']:
                if nbOut['output_type'] != 'stream' or 'name' not in nbOut or nbOut['name'] != 'stdout':
                    continue
    
                textLength = textLength + len(nbOut['text'])
    
        return textLength

    def insertRef(self):
        nbDoc = nbformat.read(self.nbFileName, as_version=4)
        nbCells = nbDoc['cells']
        markdownCells = [x for x in nbCells if x['cell_type'] == 'markdown']
        
        hasRef = False
        for mdc in markdownCells:
            print (mdc['source'])
            if 'pluto.studio' in mdc['source']:
                hasRef = True
                break
    
        if not hasRef:
            outObj = nbformat.NotebookNode(cell_type='markdown', metadata={}, source=["This notebook was created using [pluto](http://pluto.studio). Learn more [here](https://github.com/shyams80/pluto)"])
            nbCells.append(outObj)
            nbformat.write(nbDoc, self.nbFileName, version=4)

    def upsertGithub(self, fullPath):
        with open(fullPath, mode='rb') as file:
            outFileContent = file.read()
    
        try:
            fileContent = self.repo.get_contents(fullPath)
            self.repo.update_file(fullPath, "response", outFileContent, fileContent.sha)
        except Exception as exp:
            if exp.status == 404:
                try:
                    self.repo.create_file(fullPath, "response", outFileContent)
                except Exception as exp:
                    print("Error creating file: " + fullPath)
                    print(exp)
                    
    def Process(self, requestId):
        request = self.db.q.find_one({'_id': ObjectId(requestId)})

        subprocess.run(shlex.split("ufw allow out to any port 443"), env=os.environ, errors=True)
        subprocess.run(shlex.split("ufw deny out to any port 27017"), env=os.environ, errors=True)
    
        githubAcc = Github(request['githubTok'])
        user = githubAcc.get_user()
        self.repo = user.get_repo("plutons")
    
        githubUserName = request['githubUser']
        print(f"processing for: {githubUserName}")
    
        qId = ObjectId(request['_id'])
        fullPath = request['file']
        notebook = gzip.decompress(request['notebook'])
    
        self.nbFileName = self.plutoPath + fullPath[fullPath.rfind('/')+1:]
        print(self.nbFileName)
        with open(self.nbFileName, mode='wb') as file:
            file.write(notebook)
    
        subprocess.run(shlex.split(f"chmod 666 {self.nbFileName}"), env=os.environ, errors=True)
    
        self.insertRef()
    
        subprocess.run(shlex.split("ufw deny out to any port 443"), env=os.environ, errors=True)
        cmdLine = f"sudo -E -H -u pluto jupyter nbconvert --to notebook --execute {self.nbFileName} --inplace --allow-errors"
        cpi = subprocess.run(shlex.split(cmdLine), env=os.environ, errors=True)
    
        textLength = self.getOutputLength()
        print(f"total output length: {textLength}")
    
        if githubUserName != 'shyams80' and textLength > 10000:
            cmdLine = f"jupyter nbconvert --ClearOutputPreprocessor.enabled=True --inplace {self.nbFileName}"
            subprocess.run(shlex.split(cmdLine), env=os.environ, errors=True)
            nbDoc = nbformat.read(self.nbFileName, as_version=4)
    
            for nbCell in nbDoc['cells']:
                if nbCell['cell_type'] != 'code' and nbCell['source'] != None:
                    continue
    
                nbCell['execution_count'] = 1
                outObj = nbformat.NotebookNode(output_type='stream', name='stderr', text=['total output string length exceeded 10000 characters. please stay within the limit.'])
                nbCell['outputs'].append(outObj)
                break
    
            nbformat.write(nbDoc, self.nbFileName, version=4)
    
        with open(self.nbFileName, mode='rb') as file:
            outFileContent = file.read()
    
        tooBig = False
        subprocess.run(shlex.split("ufw allow out to any port 443"), env=os.environ, errors=True)
        try:
            fileContent = self.repo.get_contents(fullPath)
            self.repo.update_file(fullPath, "response", outFileContent, fileContent.sha)
        except Exception as exp:
            print(exp)
            if exp.data["errors"][0]['code'] == 'too_large':
                tooBig = True
        subprocess.run(shlex.split("ufw deny out to any port 443"), env=os.environ, errors=True)
    
        if tooBig:
            cmdLine = f"sudo -E -H -u pluto jupyter nbconvert --to markdown --execute {self.nbFileName} --allow-errors"
            cpi = subprocess.run(shlex.split(cmdLine), env=os.environ, errors=True)
            filePattern = self.nbFileName.replace(".ipynb", "")
    
            subprocess.run(shlex.split("ufw allow out to any port 443"), env=os.environ, errors=True)
            self.upsertGithub(filePattern + ".md", self.repo)
            for fname in os.listdir(filePattern + "_files"):
                self.upsertGithub(filePattern + "_files/" + fname, self.repo)
    
            subprocess.run(shlex.split("ufw deny out to any port 443"), env=os.environ, errors=True)
    
        #os.remove(self.nbFileName)
    
        subprocess.run(shlex.split("ufw allow out to any port 27017"), env=os.environ, errors=True)
        self.db.q.update_one({'_id': qId}, {'$set': {'isProcessed': True, 'processedOn': datetime.now(), 'notebook': gzip.compress(outFileContent)}})


#argv[1]: _id
#argv[2]: mongodb password
if len(sys.argv) < 3:
    print("Nothing to do!")
    exit()

processor = ProcessorLxd(sys.argv[2])
processor.Process(sys.argv[1])