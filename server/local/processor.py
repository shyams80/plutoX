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

    qId = ObjectId(request['_id'])
    fullPath = request['file']
    notebook = gzip.decompress(request['notebook'])

    fileContent = repo.get_contents(fullPath)

    tempFileName = fullPath[fullPath.rfind('/')+1:]
    with open(tempFileName, mode='wb') as file:
        file.write(notebook)

    subprocess.run(shlex.split("ufw deny out to any port 443"), env=os.environ, errors=True)
    cmdLine = f"jupyter nbconvert --to notebook --execute {tempFileName} --inplace --allow-errors"
    cpi = subprocess.run(shlex.split(cmdLine), env=os.environ, errors=True)

    textLength = getOutputLength(tempFileName)
    print(f"total output length: {textLength}")

    if textLength > 10000:
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

    subprocess.run(shlex.split("ufw allow out to any port 443"), env=os.environ, errors=True)
    repo.update_file(fullPath, "response", outFileContent, fileContent.sha)
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
