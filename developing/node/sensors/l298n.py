#!/usr/bin/env python
# -*- coding: utf-8 -*-
#____________developed by paco andres____________________
# All datas defined in json configuration are atributes in your code object
import time
from node.libs import control
import Pyro4
from node.libs.pyro4bot_gpio import *


@Pyro4.expose
class l298n(control.Control):
    __REQUIRED = ["IN1", "IN2", "IN3", "IN4", "ENA", "ENB", "gpioservice"]

    def __init__(self):
        self.GPIO=bot_GPIO(self.gpioservice,self.pyro4id)
        self.GPIO.setup([self.IN1,self.IN2,self.IN3,self.IN4,self.ENA,self.ENB],OUT)
        self.motor_a = self.GPIO.PWM(self.ENA,100)
        self.motor_b = self.GPIO.PWM(self.ENB,100)
        self.stop()
        self.forward(80,80)
        time.sleep(2)
        self.stop()

    def forward(self, DCA=100, DCB=100):
        self.motor_a.ChangeDutyCycle(DCA)
        self.motor_b.ChangeDutyCycle(DCB)
        self.GPIO.output(self.IN1, HIGH)
        self.GPIO.output(self.IN2, LOW)
        self.GPIO.output(self.IN3, LOW)
        self.GPIO.output(self.IN4, HIGH)

    def stop(self):
        self.motor_a.ChangeDutyCycle(0)
        self.motor_b.ChangeDutyCycle(0)
        self.GPIO.output(self.IN1, LOW)
        self.GPIO.output(self.IN2, LOW)
        self.GPIO.output(self.IN3, LOW)
        self.GPIO.output(self.IN4, LOW)

    def backward(self, DCA=100, DCB=100):
        self.motor_a.ChangeDutyCycle(DCA)
        self.motor_b.ChangeDutyCycle(DCB)
        self.GPIO.output(self.IN1, LOW)
        self.GPIO.output(self.IN2, HIGH)
        self.GPIO.output(self.IN3, HIGH)
        self.GPIO.output(self.IN4, LOW)

    def setvel(self, DCA, DCB):
        self.motor_a.ChangeDutyCycle(DCA)
        self.motor_b.ChangeDutyCycle(DCB)
        self.GPIO.output(self.IN1, HIGH)
        self.GPIO.output(self.IN2, LOW)
        self.GPIO.output(self.IN3, HIGH)
        self.GPIO.output(self.IN4, LOW)

    def left(self, DC=100):
        self.setvel(0, DC)

    def right(self, DC=100):
        self.setvel(DC, 0)


if __name__ == "__main__":
    pass
