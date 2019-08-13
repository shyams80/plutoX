import pylxd
import socket
import Config

class ContainerManager:
    def __init__(self):
        self.config = Config.Config()
        self.client = pylxd.Client(endpoint=self.config['DEFAULT']['LXD_URL'], cert=(self.config['DEFAULT']['LXD_CERT'], self.config['DEFAULT']['LXD_KEY']), verify=False)
        #client.authenticate('ferrari')
        
        
    def DeleteProcessor(self, githubUserName):
        try:
            cntnr = self.client.containers.get(githubUserName)
            if cntnr.state().status_code != 102:
                cntnr.stop(wait=True)
            cntnr.delete()
        except pylxd.exceptions.NotFound:
            pass
        
    def GetProcessor(self, githubUserName):
        egg = None
        try:
            egg = self.client.containers.get(githubUserName)
            if egg.state().status_code == 102:
                egg.start(wait=True)
        except pylxd.exceptions.NotFound:
            images = self.client.images.all()
            templates  = [t for t in images if len(t.aliases) > 0 and t.aliases[0]['name'] == 'goose']
            #if no template is found, create one from goose
            if len(templates) == 0:
                goose = self.client.containers.get('goose')
                if goose.state().status_code != 102:
                    goose.stop()
                template = goose.publish(public = True, wait = True)
                template.add_alias('goose', 'lays golden eggs')
                goose.start()
            else:
                template = templates[0]
    
            dna = {
                "ephemeral": False,
                "name": githubUserName,
                "source": {
                    "type": "image",
                    "certificate": "",
                    "fingerprint": template.fingerprint
                    }
                }
            
            egg = self.client.containers.create(dna, wait=True)
            egg.start(wait=True)

        #update the hosts file
        hosts = "127.0.0.1 localhost\n"
        for server in self.config['DEFAULT']['SERVERS'].split(','):
            lup = socket.gethostbyname(server)
            hosts = hosts + f"{lup} {server}\n"
            
        egg.files.put("/etc/hosts", hosts)
        
        #copy the processor
        with open("../ProcessorLxd.py", "r") as f:
            content = f.read()
            egg.files.put("/home/pluto/ProcessorLxd.py", content)
        
        return egg


#cm = ContainerManager()
#cm.GetProcessor("shyams80")
#cm.DeleteProcessor("shyams80")