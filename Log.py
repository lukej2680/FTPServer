# Log.py
# This is the LogFile class for logginf purposes in the server
# Contains methods opening the logfile and appending the logfile
# Dependencies;

import datetime


class LogFile():

    def __init__(self, name):
        self.name = name

    def openLog(self):
        f = open(self.name, 'w')
        f.close()

    def appendLog(self, line):
        f = open(self.name, 'a')
        f.write(datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S"))
        f.write(' ' + line + '\n')
        f.close()
