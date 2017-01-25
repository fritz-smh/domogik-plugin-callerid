# -*- coding: utf-8 -*- 

""" This file is part of B{Domogik} project (U{http://www.domogik.org}).

License
=======

B{Domogik} is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

B{Domogik} is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Domogik. If not, see U{http://www.gnu.org/licenses}.

Plugin purpose
==============

Detect inbound calls

Implements
==========


@author: Fritz SMH <fritz.smh@gmail.com>
@copyright: (C) 2007-2015 Domogik project
@license: GPL(v3)
@organization: Domogik
"""


import serial as serial
import domogik.tests.common.testserial as testserial
import re
import traceback
import time



CID_COMMAND = "AT#CID=1"
NUM_START_LINE = "NMBR"
NUM_PATTERN = "NMBR *= *"


class CallerIdModemException(Exception):
    """
    OneWire exception
    """

    def __init__(self, value):
        Exception.__init__(self)
        self.value = value

    def __str__(self):
        return repr(self.value)



class CallerIdModem:
    """ Look for incoming calls with a modem
    """

    def __init__(self, log, device, cid_command, contacts, blacklist, callback, stop, stop2, fake_device = None):
        """ Create handler
        @param device : The full path or number of the device where 
                             modem is connected
        @param cid_command : AT caller id command
        @param contacts : dict of known numbers (number => reason)
        @param blacklist : dict of blacklisted numbers (number => reason)
        @param callback : method to call each time all data are collected
        @param stop : global Domogik stop event
        @param stop2 : stop event to reload the blacklist
        @param fake_device : fake device. If None, this will not be used. Else, the fake serial device library will be used
        """
        self._log = log
        self._cb = callback 
        self._stop = stop 
        self._stop2 = stop2

        # fake or real device
        self.fake_device = fake_device
        self.device = device

        self.contacts = contacts
        self.blacklist = blacklist

        self.open(cid_command)
        self.listen()


    def open(self, cid_command = CID_COMMAND):
        """ open Modem device
        """
        used_device = None
        self._log.info("Opening modem device")
        try:
            #self._ser = serial.Serial(device, 19200, 
            #                          timeout=1)
            if self.fake_device != None:
                self._log.info(u"Try to open fake Modem : {0}".format(self.fake_device))
                self._ser = testserial.Serial(self.fake_device, baudrate = 19200, timeout = 1)
                used_device = self.fake_device
            else:
                self._log.info(u"Try to open Modem : {0}".format(self.device))
                self._ser = serial.Serial(self.device, baudrate = 19200, timeout = 1)
                used_device = self.device
            if used_device == None:
                error = u"The device is not configured (current value == None)."
                self._log.error(error)
                raise CallerIdModemException(error)

            self._log.info("Modem opened")
            # Configure caller id mode
            self._log.info("Set modem to caller id mode : {0}".format(cid_command))
            self._ser.write("{0}\r\n".format(cid_command))
        except:
            error = u"Error while opening modem device : {0} : {1}".format(used_device, str(traceback.format_exc()))
            self._log.error(error)
            raise CallerIdModemException(error)

    def close(self):
        """ close Modem device
        """
        self._log.info("Close modem device")
        try:
            self._ser.close()
        except:
            error = "Error while closing modem device"
            raise CallerIdModemException(error)

    def listen(self):
        """ listen modem for incoming calls
        """
        self._log.info("Start listening modem")
        while not self._stop.isSet() and not self._stop2.isSet():
            num, name, blacklisted = self.read()
            if num != None:
                self._cb("inbound", num, name, blacklisted)



    def read(self):
        """ read one line on modem
        """
        resp = self._ser.readline()
        if NUM_START_LINE in resp:
            name = u""
            blacklisted = False
            # we get the third string's item (separator : blank)
            num = re.sub(NUM_PATTERN, "", resp).strip()
            self._log.debug("Incoming call from {0}".format(num))
            if num in self.contacts:
                name = self.contacts[num]
            if num in self.blacklist:
                self._log.info("BLACKLISTED incoming call from {0}".format(num))
                blacklisted = True
                reason = self.blacklist[num]
                self._ser.write("ATA\r\n")
                time.sleep(4)
                self._ser.write("ATH\r\n")
                self._log.info("Incoming call '{0}' rejected".format(num))
            return num, name, blacklisted
        else:
            return None, None, None


    
