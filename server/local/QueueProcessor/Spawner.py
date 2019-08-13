import shlex
import pymongo
from github import Github
import gzip
import os
import nbformat
import subprocess
from datetime import datetime
import shutil

from ContainerManager import ContainerManager
from Config import Config
from bson.objectid import ObjectId

class Spawner:
    def __init__(self):
        self.config = Config()
        client = pymongo.MongoClient(f"mongodb+srv://explorer:{self.config.MongoPass}@cluster0-eyzcm.mongodb.net/test?retryWrites=true&w=majority")
        self.db = client.plutoQ
        self.cm = ContainerManager()
        
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
        
    def Execute(self, meta):
        print(meta)
        
        print('acquiring egg')
        egg = self.cm.GetProcessor(meta['githubUser'])
    
        request = self.db.q.find_one({'_id': ObjectId(meta['id'])})
        
        githubUserName = request['githubUser']
        print(f"processing for: {githubUserName}")
        
        githubAcc = Github(request['githubTok'])
        user = githubAcc.get_user()
        self.repo = user.get_repo("plutons")
        
        self.plutoPath = "~/notebook-temp/" + meta['id'] + "/"
        
        try:
            os.makedirs(self.plutoPath)
        except FileExistsError:
            pass
        
        fullPath = request['file']
        notebook = gzip.decompress(request['notebook'])
    
        self.nbFileName = self.plutoPath + fullPath[fullPath.rfind('/')+1:]
        print(f"processing notebook: {self.nbFileName}")
        with open(self.nbFileName, mode='wb') as file:
            file.write(notebook)
            
        self.insertRef()
        
        egg.files.recursive_put(self.plutoPath, f"/home/pluto/")
        
        #with open(self.nbFileName, "rb") as f:
        #    content = f.read()
            #egg.files.put(f"/home/pluto/{self.nbFileName}", content)
            
    
        print(f"executing in egg")
        ret = egg.execute(shlex.split(f"jupyter nbconvert --to notebook --execute /home/pluto/{self.nbFileName} --inplace --allow-errors"))
        print(ret.exit_code)
        
        egg.files.get(f"/home/pluto/{self.nbFileName}", self.nbFileName)
        
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
        try:
            fileContent = self.repo.get_contents(fullPath)
            self.repo.update_file(fullPath, "response", outFileContent, fileContent.sha)
        except Exception as exp:
            print(exp)
            if exp.data["errors"][0]['code'] == 'too_large':
                tooBig = True
    
        if tooBig:
            print("file is too big!")
            cmdLine = f"sudo -E -H -u pluto jupyter nbconvert --to markdown --execute {self.nbFileName} --allow-errors"
            cpi = subprocess.run(shlex.split(cmdLine), env=os.environ, errors=True)
            filePattern = self.nbFileName.replace(".ipynb", "")
    
            self.upsertGithub(filePattern + ".md", self.repo)
            for fname in os.listdir(filePattern + "_files"):
                self.upsertGithub(filePattern + "_files/" + fname, self.repo)
    
        shutil.rmtree(self.plutoPath)
    
        self.db.q.update_one({'_id': ObjectId(meta['id'])}, {'$set': {'isProcessed': True, 'processedOn': datetime.now(), 'notebook': gzip.compress(outFileContent)}})

def Spawn(meta):
    if meta == None:
        return
    
    print(meta)
    
    spawn = Spawner()
    spawn.Execute(meta)
    

meta = {'id': '5d526abde7ccfb4adf63d359', 'githubUser': 'shyams80'}
Spawn(meta)