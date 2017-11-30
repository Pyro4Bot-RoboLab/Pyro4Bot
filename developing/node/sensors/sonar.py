#!/usr/bin/env python
# -*- coding: utf-8 -*-
# lock().acquire()
#____________developed by paco andres____________________
# All datas defined in json configuration are atributes in you code object
import time
from node.libs import control
import Pyro4


@Pyro4.expose
class sonar (control.Control):
    @control.load_config
    def __init__(self, data, **kwargs):
        self.send_subscripcion(self.arduino, "US")

        # this line is the last line in constructor method
        super(sonar, self).__init__(self.worker)

    def worker(self):
        while self.worker_run:
            time.sleep(self.frec)

    def worker1(self):
        while self.worker_run:
            time.sleep(self.frec)

    def get__us(self):
        return self.US


if __name__ == "__main__":
    pass