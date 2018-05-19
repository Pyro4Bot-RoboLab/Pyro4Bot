#!/usr/bin/env python
# ____________developed by cristian vazque____________________
# _________collaboration with cristian vazquez____________

import time
from node.libs import control
import pprint

class AlphaMirrorBase(control.Control):

    def __init__(self):

        self.init_workers(self.worker)

    def worker(self):
        print("ALPHA-MIRROR WORKING")
        pprint.pprint(self.__dict__)
        print(self.deps["master.basemotion"].__docstring__())
        while self.worker_run:
            time.sleep(self.frec)