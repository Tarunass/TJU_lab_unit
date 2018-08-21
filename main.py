#!/usr/bin/python

import TJUControl
import logging

logging.config.fileConfig("/home/arunas/Documents/TJU/logging_config.ini")

tju_control = TJUControl.TJUControl()
tju_control.start()
try:
    while 1:
        pass
except:
    tju_control.stop()
