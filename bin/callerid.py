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
from domogik.xpl.common.plugin import XplPlugin
from domogik_packages.plugin_callerid.lib.callerid import CallerIdModem, CallerIdModemException
from domogikmq.message import MQMessage
import time
import threading
import thread
import traceback
import os
import csv
import quopri
import re
from urllib2 import urlopen
try:
    # python3
    from urllib.request import urlopen
except ImportError:
    # python2
    from urllib import urlopen



CONTACTS_FILE = "contacts.csv"
BLACKLIST_FILE = "blacklist.csv"


URL_REGEXP = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

# TODO : complete
INDICATORS = { 
               "+33" : "0",   # france
             }


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
        url_vcf_file = self.get_config('vcf_url')
        vcf_cell_label = self.get_config('vcf_cell_label')
        vcf_home_label = self.get_config('vcf_home_label')
        vcf_work_label = self.get_config('vcf_work_label')

        ### First, try to load known phone numbers from a csv file
        contacts_file = os.path.join(self.get_data_files_directory(), CONTACTS_FILE)
        self.contacts = {}  # phone number : name
        try:
            with open(contacts_file, 'rb') as fp_contacts:
                data = csv.reader(fp_contacts, delimiter = ';')
                for a_contact in data:
                    num = a_contact[1]
                    for ind in INDICATORS:
                        if num.startswith(ind):
                            num = num.replace(ind, INDICATORS[ind])
                    self.contacts[num] = a_contact[0]
        except IOError:
            self.log.error(u"No contact file to open : {0}".format(contacts_file))


        ### Then, try to load known phone numbers from a vcf file
        vcf_file = os.path.join(self.get_data_files_directory(), "downloaded.vcf")
        if URL_REGEXP.search(url_vcf_file):
            self.log.info("Valid url file configured for the VCF file : start downloading '{0}' as '{1}'".format(url_vcf_file, vcf_file))
            try:
                fp = urlopen(url_vcf_file)
                with open(vcf_file, 'wb') as download:
                    download.write(fp.read())
            except:
                self.log.error(u"Error while downloading VCF file : '{0}'. Error is : {1}".format(url_vcf_file, traceback.format_exc()))
        else:
            self.log.info("No url defined (or not valid url) for the VCF file.")
        try:
            BEGIN_VCARD = "BEGIN:VCARD"
            FN = "FN"
            TEL = "TEL;"
            END_VCARD = "END:VCARD"
            with open(vcf_file, 'r') as vcf:
                for line in vcf:
                    if line.startswith(BEGIN_VCARD):
                        vcf_fn = None
                        vcf_num = []   # list of dicts : [{"num" : ...,
                                       #                   "num_type" : ...}, {...}]
                    elif line.startswith(FN):
                        vcf_fn = quopri.decodestring(line.split(":")[1].strip())
                    elif line.startswith(TEL):
                        tel = line.split(":")[0].strip()
                        num = line.split(":")[1].strip()
                        buffer = tel.split(";")
                        if len(buffer) > 1:
                             num_type = u"{0}".format(buffer[1])
                        else:
                             num_type = u""
                        for ind in INDICATORS:
                            if num.startswith(ind):
                                num = num.replace(ind, INDICATORS[ind])
                        vcf_num.append({"num" : num, "num_type" : num_type})
                    elif line.startswith(END_VCARD):
                        # if more than 1 number for a contact, add the num type
                        if len(vcf_num) > 1:
                            for num in vcf_num:
                                print("x{0}x".format(num['num_type']))
                                if num['num_type'] == 'CELL':
                                    num_type = vcf_cell_label
                                elif num['num_type'] == 'HOME':
                                    num_type = vcf_home_label
                                elif num['num_type'] == 'WORK':
                                    num_type = vcf_work_label
                                else:
                                    num_type = num['num_type']
                                self.contacts[num['num']] = u"{0} - {1}".format(unicode(vcf_fn, "utf-8"), num_type)
                        # else, just take the name
                        else:
                            for num in vcf_num:   # dummy for : just 1 loop
                                self.contacts[num['num']] = u"{0}".format(unicode(vcf_fn, "utf-8"))
        except IOError:
            self.log.error(u"No VCF file to open : {0}".format(vcf_file))
        except:
            self.log.error(u"Error while reading VCF file : {0}".format(traceback.format_exc()))

        self.log.info(u"Contacts loaded :")
        for a_contact in self.contacts:
            self.log.info(u"- {0} : {1}".format(a_contact, self.contacts[a_contact]))

        ### Finally, load blacklisted numbers
        self.load_blacklist()

        ### For each device
        self.open_modems()

        # notify ready
        self.ready()

    def open_modems(self):
        self.log.info("(Re)starting the threads...")
        # restart all threads that listen to the modems
        if not hasattr(self, "stop_to_reload"):
            self.stop_to_reload = threading.Event()
        else:
            self.stop_to_reload.set()
        self.threads = {}
        time.sleep(5)
        self.stop_to_reload.clear()
        self.threads = {}
        for a_device in self.devices:
            try:
                address = self.get_parameter(a_device, "device")
                cid_command = self.get_parameter(a_device, "cid_command")
                self.log.info(u"Launch thread to listen on device : {0} which address is '{1}' and cid command is '{2}'".format(a_device["name"], address, cid_command))
                thr_name = "dev_{0}".format(a_device['id'])
                self.threads[thr_name] = threading.Thread(None, 
                                           CallerIdModem,
                                           thr_name,
                                           (self.log,
                                            address, 
                                            cid_command, 
                                            self.contacts, 
                                            self.blacklist, 
                                            self.send_xpl,
                                            self.get_stop(),
                                            self.stop_to_reload,
                                            self.options.test_option),
                                           {})
                self.threads[thr_name].start()
                self.register_thread(self.threads[thr_name])
            except:
                self.log.error(u"{0}".format(traceback.format_exc()))


    def load_blacklist(self):
        """ Load the blacklist file
        """
        self.blacklist_file = os.path.join(self.get_data_files_directory(), BLACKLIST_FILE)
        self.blacklist = {}  # phone number : reason
        try:
            with open(self.blacklist_file, 'rb') as fp_blacklist:
                data = csv.reader(fp_blacklist, delimiter = ';')
                for a_blacklist in data:
                    if len(a_blacklist) > 1:
                        self.blacklist[a_blacklist[1]] = a_blacklist[0]
                    else:
                        self.log.warning("Blacklist file : invalid line : {0}".format(a_blacklist))
        except IOError:
            self.log.info(u"No blacklist file to open : {0}".format(self.blacklist_file))

        self.log.info(u"Blacklist loaded :")
        for a_blacklist in self.blacklist:
            self.log.info(u"- {0} : {1}".format(a_blacklist, self.blacklist[a_blacklist]))


    def on_mdp_request(self, msg):
        """ Called when a MQ req/rep message is received
        """
        XplPlugin.on_mdp_request(self, msg)
        if msg.get_action() == "client.cmd":
            print(msg)
            reason = None
            status = True
            data = msg.get_data()
            if 'blacklist' in data:
                bl = data['blacklist']
            else:
                reason = u"Invalid command : no blacklist key in message"
                status = False

            if status == True:
                try:
                    with open(self.blacklist_file, 'ab') as fp_blacklist:
                        fp_blacklist.write("\n{0};{1}".format("manual blacklisting", bl))
                except:
                    reason = u"Error while completing blacklist file : {0}. Error is : {1}".format(self.blacklist_file, traceback.format_exc())
                    self.log.error(reason)
                    status = False
                self.load_blacklist()


            self.log.info("Reply to command")
            reply_msg = MQMessage()
            reply_msg.set_action('client.cmd.result')
            reply_msg.add_data('status', status)
            reply_msg.add_data('reason', reason)
            self.reply(reply_msg.get())

            if status == True:
                thread.start_new_thread(self.open_modems, ())



    def send_xpl(self, calltype, number, name = None, blacklisted = False):
        """ Send data on xPL network
            @param calltype : inbound/outbound
            @param number : phone number
            @param name : caller name
        """
        msg = XplMessage()
        msg.set_type("xpl-trig")
        msg.set_schema("cid.basic")
        msg.add_data({"calltype" : calltype})
        msg.add_data({"phone" : number})
        if name != None and name != "":
            msg.add_data({"cln" : name})
        if blacklisted == True:
            msg.add_data({"blacklisted" : "yes"})
        elif blacklisted == False:
            msg.add_data({"blacklisted" : "no"})
        self.log.debug(u"Send xpl message...")
        self.log.debug(msg)
        self.myxpl.send(msg)


if __name__ == "__main__":
    p = CallerIdManager()
