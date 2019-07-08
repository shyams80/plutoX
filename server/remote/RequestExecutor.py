from notebook.utils import url_path_join
from notebook.base.handlers import IPythonHandler
import sys
import json
import os
import subprocess
import shlex
import gzip
import platform

from github import Github
from github import GithubException, UnknownObjectException
import pymongo
from datetime import datetime
import urllib.parse
import urllib.request
from bson.objectid import ObjectId
from bson.binary import Binary
from time import sleep

class RequestHandler(IPythonHandler):

    def post(self):
        statusMsg = {}
        statusMsg["finished"] = False;
        statusMsg["text"] = "starting..."
        statusMsg["ok"] = True;
        self.write(statusMsg)
        self.flush()

        try:
            curUser = self.get_current_user()
            userName = curUser['name']
        
            githubToken = os.environ['GITHUB_TOKEN']
            githubUserName = os.environ['GITHUB_USER']
            githubAcc = Github(githubToken)
            user = githubAcc.get_user()
            repos = [r.name for r in githubAcc.get_user().get_repos()]
            if not 'plutons' in repos:
                statusMsg["text"] = "creating repo..."
                self.write(statusMsg)
                self.flush()
                repo = user.create_repo("plutons", "notebooks created on pluto")
            else:
                repo = user.get_repo("plutons")
        
            jbody = json.loads(self.request.body.decode('utf-8'))
            #fullPath = os.path.join(os.getcwd(), jbody['notebook'])
            fullPath = jbody['notebook']

            existingFile = None
            tooBig = False
            try:
                existingFile = repo.get_contents(fullPath)
            except UnknownObjectException:
                pass
            except GithubException as exp:
                print(exp)
                if exp.data["errors"][0]['code'] == 'too_large':
                    tooBig = True
            except:
                pass

            cmdLine = f"jupyter nbconvert --ClearOutputPreprocessor.enabled=True --inplace {fullPath}"
            cpi = subprocess.run(shlex.split(cmdLine), env=os.environ, errors=True)
            with open(fullPath, mode='rb') as file:
                fileContent = file.read()
        
            if not tooBig:
                if existingFile == None:
                    repo.create_file(f"{fullPath}", "request", fileContent)
                else:
                    print(existingFile.sha)
                    repo.update_file(f"{fullPath}", "request", fileContent, existingFile.sha)
        
            mongoPass = urllib.parse.quote_plus(os.environ['MONGO_PASS'])
            client = pymongo.MongoClient(f"mongodb+srv://explorer:{mongoPass}@cluster0-eyzcm.mongodb.net/test?retryWrites=true&w=majority")
            db = client.plutoQ
        
            reqId = db.q.insert_one({ 'file': f"{fullPath}", 
                                  'createdOn': datetime.now(), 
                                  'isProcessed': False, 
                                  'notebook': Binary(gzip.compress(fileContent)), 
                                  'githubTok': githubToken,
                                  'githubUser': githubUserName,
				  'requestHost': platform.node()
                                })
            qId = ObjectId(reqId.inserted_id)

            statusMsg["text"] = "processing..."
            self.write(statusMsg)
            self.flush()

            while True:
                areWeThereYet = db.q.find_one({'_id': qId, 'isProcessed': True})
                if areWeThereYet != None:
                    break
                else:
                    sleep(1)
                    print('>', end='', flush=True)

            os.remove(fullPath)
            fileContent = areWeThereYet['notebook']
            with open(fullPath, 'wb') as file:
                file.write(gzip.decompress(fileContent))

            #don't delete the request, you may need it for preventing abuse
            #db.q.delete_one({'_id': qId})

            statusMsg["text"] = "done!"
            statusMsg["finished"] = True;
            self.finish(statusMsg)
        except Exception as exp:
            print(exp)
            statusMsg["text"] = str(exp)
            statusMsg["ok"] = False
            self.finish(statusMsg)


def _jupyter_server_extension_paths():
    return [{
        "module": "plutoX.server.remote.RequestExecutor"
    }]

def load_jupyter_server_extension(nb_server_app):
    """
    Called when the extension is loaded.

    Args:
        nb_server_app (NotebookWebApplication): handle to the Notebook webserver instance.
    """

    web_app = nb_server_app.web_app
    host_pattern = '.*$'
    route_pattern = url_path_join(web_app.settings['base_url'], '/plutoEx')
    web_app.add_handlers(host_pattern, [(route_pattern, RequestHandler)])

