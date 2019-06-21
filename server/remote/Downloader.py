from notebook.utils import url_path_join
from notebook.base.handlers import IPythonHandler
import sys
import json
import os

from github import Github
import urllib.request

class DownloadHandler(IPythonHandler):
    def post(self):
        curUser = self.get_current_user()
        userName = curUser['name']
        
        githubToken = os.environ['GITHUB_TOKEN']
        githubAcc = Github(githubToken)
        user = githubAcc.get_user()
        repo = user.get_repo("plutons")

        jbody = json.loads(self.request.body.decode('utf-8'))
        #fullPath = os.path.join(os.getcwd(), jbody['notebook'])
        fullPath = jbody['notebook']

        fileContent = repo.get_contents(f"{fullPath}")
        os.remove(fullPath)
        urllib.request.urlretrieve(fileContent.download_url, fullPath)

        self.finish({'resp': 'success'})

def _jupyter_server_extension_paths():
    return [{
        "module": "plutoX.server.remote.Downloader"
    }]

def load_jupyter_server_extension(nb_server_app):
    """
    Called when the extension is loaded.

    Args:
        nb_server_app (NotebookWebApplication): handle to the Notebook webserver instance.
    """

    web_app = nb_server_app.web_app
    host_pattern = '.*$'
    route_pattern = url_path_join(web_app.settings['base_url'], '/plutoDl')
    web_app.add_handlers(host_pattern, [(route_pattern, DownloadHandler)])

