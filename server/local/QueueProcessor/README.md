# Processing user requests

1. [Enqueuer](Enqueuer.py) picks up the request from the mongodb queue and puts it on an internal redis based queue: [python-rq](https://python-rq.org/)
1. Free workers are assigned a [Spawner](Spawner.py) that uses [ContainerManager](ContainerManager.py) to whip up an [lxd container](https://linuxcontainers.org/lxd/introduction/)

## What are goose eggs?

- **goose** is the master image from which containers (**eggs**) are created for each user. It has all the python and R libraries required to run a pluto notebook.
- If a user hasn't logged in for a while, as part of a cleanup routine, her **egg** is deleted to free up space.
- Any new release to the library, etc. only needs to go to the **goose**. The changes then propagate to the user containers.

*goose* is what lays the golden *eggs*
