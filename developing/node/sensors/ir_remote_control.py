#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
from node.libs import control
import Pyro4
from node.libs.pyro4bot_gpio import *


class IR_remote_control(control.Control):
    __REQUIRED = ["gpioservice","IR_receiver"]

    def __init__(self):
        self.GPIO=bot_GPIO(self.gpioservice,self.pyro4id)
        self.GPIO.setup(self.IR_receiver,IN,PUD_UP)
        #self.GPIO.setup(self.IR_receiver,PUD_UP)
        self.init_workers(self.worker)
        #print(self.GPIO.STATUS)

    def worker(self):
        while self.worker_run:
            k=self.getkey()
            if k:
                print(hex(k))
            time.sleep(self.frec)
            #print(self.line)

    def getkey(self):
    	if self.GPIO.input(self.IR_receiver) == 0:
    		count = 0
    		while self.GPIO.input(self.IR_receiver) == 0 and count < 200:  #9ms
    			count += 1
    			time.sleep(0.00006)

    		count = 0
    		while self.GPIO.input(self.IR_receiver) == 1 and count < 80:  #4.5ms
    			count += 1
    			time.sleep(0.00006)

    		idx = 0
    		cnt = 0
    		data = [0,0,0,0]
    		for i in range(0,32):
    			count = 0
    			while self.GPIO.input(self.IR_receiver) == 0 and count < 15:    #0.56ms
    				count += 1
    				time.sleep(0.00006)

    			count = 0
    			while self.GPIO.input(self.IR_receiver) == 1 and count < 40:   #0: 0.56mx
    				count += 1                               #1: 1.69ms
    				time.sleep(0.00006)

    			if count > 8:
    				data[idx] |= 1<<cnt
    			if cnt == 7:
    				cnt = 0
    				idx += 1
    			else:
    				cnt += 1
    		if data[0]+data[1] == 0xFF and data[2]+data[3] == 0xFF:  #check
    			return data[2]

    		if data[0] == 255 and data[1] == 255 and data[2] == 15 and data[3] == 255:
    			return "repeat"
