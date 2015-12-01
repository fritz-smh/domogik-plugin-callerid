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
            self.log.info(u"No contact file to open : {0}".format(contacts_file))


        ### Then, try to load known phone numbers from a vcf file
        vcf_file = os.path.join(self.get_data_files_directory(), "test.vcf")
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
                        vcf_fn = ""
                        vcf_num = []
                    elif line.startswith(FN):
                        vcf_fn = quopri.decodestring(line.split(":")[1].strip())
                    elif line.startswith(TEL):
                        num = line.split(":")[1].strip()
                        for ind in INDICATORS:
                            if num.startswith(ind):
                                num = num.replace(ind, INDICATORS[ind])
                        vcf_num.append(num)
                    elif line.startswith(END_VCARD):
                        for num in vcf_num:
                            self.contacts[num] = unicode(vcf_fn, "utf-8")
        except IOError:
            self.log.info(u"No VCF file to open : {0}".format(vcf_file))
        except:
            self.log.info(u"Error while reading VCF file : {0}".format(traceback.format_exc()))

        self.log.info(u"Contacts loaded :")
        for a_contact in self.contacts:
            self.log.info(u"- {0} : {1}".format(a_contact, self.contacts[a_contact]))

        ### Finally, load blacklisted numbers
        blacklist_file = os.path.join(self.get_data_files_directory(), BLACKLIST_FILE)
        self.blacklist = {}  # phone number : reason
        try:
            with open(blacklist_file, 'rb') as fp_blacklist:
                data = csv.reader(fp_blacklist, delimiter = ';')
                for a_blacklist in data:
                    self.blacklist[a_blacklist[1]] = a_blacklist[0]
        except IOError:
            self.log.info(u"No blacklist file to open : {0}".format(blacklist_file))

        self.log.info(u"Blacklist loaded :")
        for a_blacklist in self.blacklist:
            self.log.info(u"- {0} : {1}".format(a_blacklist, self.blacklist[a_blacklist]))

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
                                            self.contacts, 
                                            self.blacklist, 
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

    def send_xpl(self, calltype, number, name = None):
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
        if name != None:
            msg.add_data({"cln" : name})
        self.log.debug(u"Send xpl message...")
        self.log.debug(msg)
        self.myxpl.send(msg)


if __name__ == "__main__":
    p = CallerIdManager()
