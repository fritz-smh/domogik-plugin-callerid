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

Librairy for the caller id brain part

Implements
==========

@author: Fritz <fritz.smh@gmail.com>
@copyright: (C) 2007-2015 Domogik project
@license: GPL(v3)
@organization: Domogik
"""

from domogik.butler.brain import get_sensor_value_and_date, get_sensor_last_values_since
from domogik.common.utils import ucode, get_midnight_timestamp
import datetime
import traceback
import locale

def get_last_calls(cfg_i18n, args, log, devices):
    """ Function for the brain part
    """

    # i18n
    LOCALE = "{0}".format(cfg_i18n['LOCALE'])
    SEPARATOR = cfg_i18n['SEPARATOR']
    NO_HISTORY = cfg_i18n['NO_HISTORY']
    ERROR_LOCALE = cfg_i18n['ERROR_LOCALE']
    DISPLAY_FORMAT = cfg_i18n['DISPLAY_FORMAT']
    DISPLAY_FORMAT_FOR_HISTORY = cfg_i18n['DISPLAY_FORMAT_FOR_HISTORY']
    TXT_LAST_CALL_IS = cfg_i18n['TXT_LAST_CALL_IS']
    TXT_BLACKLISTED = cfg_i18n['TXT_BLACKLISTED']
    TXT_TODAY_CALLS_ARE = cfg_i18n['TXT_TODAY_CALLS_ARE']
    TXT_TODAY_CALLS_A_CALL = cfg_i18n['TXT_TODAY_CALLS_A_CALL']

    tab_args = ' '.join(args).split(SEPARATOR)
    device_name = tab_args[0]
    if device_name == "None":
        device_name = None

    if len(tab_args) > 1:
        period = tab_args[1]
    else:
        period = None

    # get the last call
    if period == None:
        num, date1 = get_sensor_value_and_date(log, devices, LOCALE, "DT_String", device_name, "callerid")
        name, date2 = get_sensor_value_and_date(log, devices, LOCALE, "DT_String", device_name, "name")
        blacklisted, date3 = get_sensor_value_and_date(log, devices, LOCALE, "DT_Bool", device_name, "blacklisted")
    
        # no history
        if num == None:
            return NO_HISTORY
    
        # date1 != date2 means that the last name is not related to the last number
        if name == "" or name == None or date2 == None or abs(date1 - date2) > 2:
            who = num
        else:
            who = name
        if date3 != None and abs(date1 - date3) <= 2 and blacklisted == "1":
            txt_blacklisted = TXT_BLACKLISTED
        else:
            txt_blacklisted = ""
    
        time = datetime.datetime.fromtimestamp(date1)
        try:
            locale.setlocale(locale.LC_ALL, LOCALE)
        except:
            return ERROR_LOCALE
        #time = ucode(time.strftime(DISPLAY_FORMAT.encode('utf-8')).decode('utf-8'))
        time = time.strftime(DISPLAY_FORMAT.encode('utf-8')).decode('utf-8')
        return u"{0} {1}".format(TXT_LAST_CALL_IS.format(who, time), txt_blacklisted)

    # get the calls of a period
    else:
        if period == "today":
            since = get_midnight_timestamp()
            data_num = get_sensor_last_values_since(log, devices, LOCALE, "DT_String", device_name, "callerid", since = since)
            data_name = get_sensor_last_values_since(log, devices, LOCALE, "DT_String", device_name, "name", since = since)
            idx = 0
            txt = u"{0}".format(TXT_TODAY_CALLS_ARE)
            for elt in data_num:
                num = elt['value_str']
                date = elt['timestamp']

                # search for corresponding name, if any...
                who = num
                for elt2 in data_name:
                    if elt2['timestamp'] == date:
                        who = elt2['value_str']
                        break

                time = datetime.datetime.fromtimestamp(date)
                try:
                    locale.setlocale(locale.LC_ALL, LOCALE)
                except:
                    return ERROR_LOCALE
                time = ucode(time.strftime(DISPLAY_FORMAT_FOR_HISTORY.encode('utf-8')).decode('utf-8'))
                txt += TXT_TODAY_CALLS_A_CALL.format(who, time)
                idx += 1
            if idx == 0:
                return NO_HISTORY
            return u"{0}".format(txt)

        else:
            # TODO
            return "TODO"

