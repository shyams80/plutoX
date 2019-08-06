import nbformat
import subprocess
import os
import shlex
import gzip
from github import Github
import pymongo
from datetime import datetime
import urllib.parse
import urllib.request
from bson.objectid import ObjectId
from time import sleep

print("starting processor....")

plutoPath = "/home/pluto/"
mongoPass = urllib.parse.quote_plus(os.environ['MONGO_PASS'])
client = pymongo.MongoClient(f"mongodb+srv://explorer:{mongoPass}@cluster0-eyzcm.mongodb.net/test?retryWrites=true&w=majority")
db = client.plutoQ

def getOutputLength(nbFileName):
    nbDoc = nbformat.read(nbFileName, as_version=4)
    textLength = 0
    for nbCell in nbDoc['cells']:
        if nbCell['cell_type'] != 'code':
            continue

        for nbOut in nbCell['outputs']:
            if nbOut['output_type'] != 'stream' or 'name' not in nbOut or nbOut['name'] != 'stdout':
                continue

            textLength = textLength + len(nbOut['text'])

    return textLength

def insertRef(nbFileName):
    nbDoc = nbformat.read(nbFileName, as_version=4)
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
        nbformat.write(nbDoc, nbFileName, version=4)

def upsertGithub(fullPath, repo):
    with open(fullPath, mode='rb') as file:
        outFileContent = file.read()

    try:
        fileContent = repo.get_contents(fullPath)
        repo.update_file(fullPath, "response", outFileContent, fileContent.sha)
    except Exception as exp:
        if exp.status == 404:
            try:
                repo.create_file(fullPath, "response", outFileContent)
            except Exception as exp:
                print("Error creating file: " + fullPath)
                print(exp)


def loop():
    request = db.q.find_one({'isProcessed': False})
    if request == None:
        return

    subprocess.run(shlex.split("ufw allow out to any port 443"), env=os.environ, errors=True)
    subprocess.run(shlex.split("ufw deny out to any port 27017"), env=os.environ, errors=True)
    print(request['_id'])
    githubAcc = Github(request['githubTok'])
    user = githubAcc.get_user()
    repo = user.get_repo("plutons")

    githubUserName = request['githubUser']
    print(f"processing for: {githubUserName}")

    qId = ObjectId(request['_id'])
    fullPath = request['file']
    notebook = gzip.decompress(request['notebook'])

    tempFileName = plutoPath + fullPath[fullPath.rfind('/')+1:]
    print(tempFileName)
    with open(tempFileName, mode='wb') as file:
        file.write(notebook)

    subprocess.run(shlex.split(f"chmod 666 {tempFileName}"), env=os.environ, errors=True)

    insertRef(tempFileName)

    subprocess.run(shlex.split("ufw deny out to any port 443"), env=os.environ, errors=True)
    cmdLine = f"sudo -E -H -u pluto jupyter nbconvert --to notebook --execute {tempFileName} --inplace --allow-errors"
    cpi = subprocess.run(shlex.split(cmdLine), env=os.environ, errors=True)

    textLength = getOutputLength(tempFileName)
    print(f"total output length: {textLength}")

    if githubUserName != 'shyams80' and textLength > 10000:
        cmdLine = f"jupyter nbconvert --ClearOutputPreprocessor.enabled=True --inplace {tempFileName}"
        cpi = subprocess.run(shlex.split(cmdLine), env=os.environ, errors=True)
        nbDoc = nbformat.read(tempFileName, as_version=4)

        for nbCell in nbDoc['cells']:
            if nbCell['cell_type'] != 'code' and nbCell['source'] != None:
                continue

            nbCell['execution_count'] = 1
            outObj = nbformat.NotebookNode(output_type='stream', name='stderr', text=['total output string length exceeded 10000 characters. please stay within the limit.'])
            nbCell['outputs'].append(outObj)
            break

        nbformat.write(nbDoc, tempFileName, version=4)

    with open(tempFileName, mode='rb') as file:
        outFileContent = file.read()

    tooBig = False
    subprocess.run(shlex.split("ufw allow out to any port 443"), env=os.environ, errors=True)
    try:
        fileContent = repo.get_contents(fullPath)
        repo.update_file(fullPath, "response", outFileContent, fileContent.sha)
    except Exception as exp:
        print(exp)
        if exp.data["errors"][0]['code'] == 'too_large':
            tooBig = True
    subprocess.run(shlex.split("ufw deny out to any port 443"), env=os.environ, errors=True)

    if tooBig:
        cmdLine = f"sudo -E -H -u pluto jupyter nbconvert --to markdown --execute {tempFileName} --allow-errors"
        cpi = subprocess.run(shlex.split(cmdLine), env=os.environ, errors=True)
        filePattern = tempFileName.replace(".ipynb", "")

        subprocess.run(shlex.split("ufw allow out to any port 443"), env=os.environ, errors=True)
        upsertGithub(filePattern + ".md", repo)
        for fname in os.listdir(filePattern + "_files"):
            upsertGithub(filePattern + "_files/" + fname, repo)

        subprocess.run(shlex.split("ufw deny out to any port 443"), env=os.environ, errors=True)

    os.remove(tempFileName)

    subprocess.run(shlex.split("ufw allow out to any port 27017"), env=os.environ, errors=True)
    db.q.update_one({'_id': qId}, {'$set': {'isProcessed': True, 'processedOn': datetime.now(), 'notebook': gzip.compress(outFileContent)}})

while True:
    try:
        loop()
        print(datetime.now())
    except Exception as exp:
        print(exp)

    sleep(1)
