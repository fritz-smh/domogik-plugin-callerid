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

from domogik.butler.brain import get_sensor_value_and_date
from domogik.common.utils import ucode
import datetime
import traceback
import locale

def get_last_calls(cfg_i18n, args, log):
    """ Function for the brain part
    """

    # i18n
    LOCALE = "{0}".format(cfg_i18n['LOCALE'])
    ERROR_NO_HISTORY = cfg_i18n['ERROR_NO_HISTORY']
    ERROR_LOCALE = cfg_i18n['ERROR_LOCALE']
    DISPLAY_FORMAT = cfg_i18n['DISPLAY_FORMAT']
    TXT_LAST_CALL_IS = cfg_i18n['TXT_LAST_CALL_IS']
    TXT_BLACKLISTED = cfg_i18n['TXT_BLACKLISTED']

    device_name = ' '.join(args)
    if device_name == "None":
        device_name = None

    num, date1 = get_sensor_value_and_date(log, LOCALE, "DT_String", device_name, "callerid")
    name, date2 = get_sensor_value_and_date(log, LOCALE, "DT_String", device_name, "name")
    blacklisted, date3 = get_sensor_value_and_date(log, LOCALE, "DT_Bool", device_name, "blacklisted")

    # no history
    if num == None:
        return ERROR_NO_HISTORY

    # date1 != date2 means that the last name is not related to the last number
    if name == None or date2 == None or abs(date1 - date2) > 2:
        who = num
    else:
        who = name
    print(blacklisted)
    if date3 != None and abs(date1 - date3) <= 2 and blacklisted == "1":
        txt_blacklisted = TXT_BLACKLISTED
    else:
        txt_blacklisted = ""

    time = datetime.datetime.fromtimestamp(date1)
    try:
        locale.setlocale(locale.LC_ALL, LOCALE)
    except:
        return ERROR_LOCALE
    time = ucode(time.strftime(DISPLAY_FORMAT))

    return u"{0} {1}".format(TXT_LAST_CALL_IS.format(time, who), txt_blacklisted)



