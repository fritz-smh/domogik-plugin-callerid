#!/usr/bin/python
# -*- coding: utf-8 -*-

from domogik.xpl.common.plugin import XplPlugin
from domogik.tests.common.plugintestcase import PluginTestCase
from domogik.tests.common.testplugin import TestPlugin
from domogik.tests.common.testdevice import TestDevice
from domogik.tests.common.testsensor import TestSensor
from domogik.common.utils import get_sanitized_hostname
from datetime import datetime
import unittest
import sys
import os
import traceback

class CallerIdTestCase(PluginTestCase):

    def test_0100_inbound_call(self):
        """ check if all the xpl messages for an inbound call is sent
            Example : 
            Sample messages : 
 
            xpl-trig : schema:cid.basic, data:{'calltype': 'inbound', 'phone' : '0102030405'}

        """
        global devices

        address = "/dev/ttyFAKE"
        device_id = devices[address]
        interval = 30

        print(u"Device address = {0}".format(address))
        print(u"Device id = {0}".format(device_id))
        print(u"Check that a message about inbound call is sent.")
        
        self.assertTrue(self.wait_for_xpl(xpltype = "xpl-trig",
                                          xplschema = "cid.basic",
                                          xplsource = "domogik-{0}.{1}".format(self.name, get_sanitized_hostname()),
                                          data = {"calltype" : "inbound", 
                                                  "phone" : "0102030405"},
                                          timeout = interval))
        print(u"Check that the value of the xPL message has been inserted in database")
        sensor = TestSensor(device_id, "callerid")
        self.assertTrue(sensor.get_last_value()[1] == self.xpl_data.data['phone'])





if __name__ == "__main__":

    test_folder = os.path.dirname(os.path.realpath(__file__))

    ### global variables
    # the key will be the device address
    devices = { "/dev/ttyFAKE" : 0
              }

    ### configuration

    # set up the xpl features
    xpl_plugin = XplPlugin(name = 'test', 
                           daemonize = False, 
                           parser = None, 
                           nohub = True,
                           test  = True)

    # set up the plugin name
    name = "callerid"

    # set up the configuration of the plugin
    # configuration is done in test_0010_configure_the_plugin with the cfg content
    # notice that the old configuration is deleted before
    cfg = { 'configured' : True}
    # specific configuration for test mdode (handled by the manager for plugin startup)
    cfg['test_mode'] = True 
    cfg['test_option'] = "{0}/data.json".format(test_folder)
   

    ### start tests

    # load the test devices class
    td = TestDevice()

    # delete existing devices for this plugin on this host
    client_id = "{0}-{1}.{2}".format("plugin", name, get_sanitized_hostname())
    try:
        td.del_devices_by_client(client_id)
    except: 
        print(u"Error while deleting all the test device for the client id '{0}' : {1}".format(client_id, traceback.format_exc()))
        sys.exit(1)

    # create a test device
    try:
        params = td.get_params(client_id, "callerid.callerid")
   
        for dev in devices:
            # fill in the params
            params["device_type"] = "callerid.callerid"
            params["name"] = "test_device_callerid_{0}".format(dev)
            params["reference"] = "reference"
            params["description"] = "description"
            # global params
            for the_param in params['global']:
                if the_param['key'] == "device":
                    the_param['value'] = dev
            # xpl params
            pass # there are no xpl params for this plugin
            # create
            device_id = td.create_device(params)['id']
            devices[dev] = device_id

    except:
        print(u"Error while creating the test devices : {0}".format(traceback.format_exc()))
        sys.exit(1)

    
    ### prepare and run the test suite
    suite = unittest.TestSuite()
    # check domogik is running, configure the plugin
    suite.addTest(CallerIdTestCase("test_0001_domogik_is_running", xpl_plugin, name, cfg))
    suite.addTest(CallerIdTestCase("test_0010_configure_the_plugin", xpl_plugin, name, cfg))
    
    # start the plugin
    suite.addTest(CallerIdTestCase("test_0050_start_the_plugin", xpl_plugin, name, cfg))

    # do the specific plugin tests
    suite.addTest(CallerIdTestCase("test_0100_inbound_call", xpl_plugin, name, cfg))

    # do some tests comon to all the plugins
    #suite.addTest(CallerIdTestCase("test_9900_hbeat", xpl_plugin, name, cfg))
    suite.addTest(CallerIdTestCase("test_9990_stop_the_plugin", xpl_plugin, name, cfg))
    
    # quit
    res = unittest.TextTestRunner().run(suite)
    if res.wasSuccessful() == True:
        rc = 0   # tests are ok so the shell return code is 0
    else:
        rc = 1   # tests are ok so the shell return code is != 0
    xpl_plugin.force_leave(return_code = rc)


