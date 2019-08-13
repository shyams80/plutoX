import shlex
from ContainerManager import ContainerManager
from Config import Config

def Spawn(meta):
    if meta == None:
        return
    
    print(meta)
    
    config = Config()
    cm = ContainerManager()
    egg = cm.GetProcessor(meta['githubUser'])
    ret = egg.execute(shlex.split(f"python3 /home/pluto/ProcessorLxd.py {meta['id']} {config.MongoPassStr}"))
    print(ret.exit_code)

#meta = {'id': '5d526abde7ccfb4adf63d359', 'githubUser': 'shyams80'}
#Spawn(meta)