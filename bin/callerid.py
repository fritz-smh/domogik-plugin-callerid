#!/usr/bin/python
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

Get incoming calls

Implements
==========

Caller id feature

@author: Fritz SMH <fritz.smh@gmail.com>
@copyright: (C) 2007-2015 Domogik project
@license: GPL(v3)
@organization: Domogik
"""

from domogik.xpl.common.xplmessage import XplMessage
from domogik.xpl.common.xplconnector import Listener
from domogik.xpl.common.plugin import XplPlugin
from domogik_packages.plugin_callerid.lib.callerid import CallerIdModem, CallerIdModemException
import time
import threading
import traceback


class CallerIdManager(XplPlugin):

    def __init__(self):
        """ Init 
        """
        XplPlugin.__init__(self, name='callerid')

        # check if the plugin is configured. If not, this will stop the plugin and log an error
        #if not self.check_configured():
        #    return

        ### get the devices list
        # for this plugin, if no devices are created we won't be able to use devices.
        # but.... if we stop the plugin right now, we won't be able to detect existing device and send events about them
        # so we don't stop the plugin if no devices are created
        self.devices = self.get_device_list(quit_if_no_device = True)

        ### get all config keys
        # n/a

        ### For each device
        threads = {}
        for a_device in self.devices:
            try:
                address = self.get_parameter(a_device, "device")
                cid_command = self.get_parameter(a_device, "cid_command")
                self.log.info(u"Launch thread to listen on device : {0} which address is '{1}' and cid command is '{2}'".format(a_device["name"], address, cid_command))
                thr_name = "dev_{0}".format(a_device['id'])
                threads[thr_name] = threading.Thread(None, 
                                           CallerIdModem,
                                           thr_name,
                                           (self.log,
                                            address, 
                                            cid_command, 
                                            self.send_xpl,
                                            self.get_stop(),
                                            self.options.test_option),
                                           {})
                threads[thr_name].start()
                self.register_thread(threads[thr_name])
            except:
                self.log.error(u"{0}".format(traceback.format_exc()))

        # notify ready
        self.ready()

    def send_xpl(self, calltype, number):
        """ Send data on xPL network
            @param calltype : inbound/outbound
            @param number : phone number
        """
        msg = XplMessage()
        msg.set_type("xpl-trig")
        msg.set_schema("cid.basic")
        msg.add_data({"calltype" : calltype})
        msg.add_data({"phone" : number})
        self.log.debug(u"Send xpl message...")
        self.log.debug(msg)
        self.myxpl.send(msg)


if __name__ == "__main__":
    p = CallerIdManager()
