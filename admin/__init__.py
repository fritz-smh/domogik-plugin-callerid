# -*- coding: utf-8 -*-

### common imports
from flask import Blueprint, abort
from domogik.common.utils import get_packages_directory
from domogik.admin.application import render_template
from domogik.admin.views.clients import get_client_detail
from domogik_packages.plugin_callerid.bin.callerid import BLACKLIST_FILE, CONTACTS_FILE
from jinja2 import TemplateNotFound

### package specific imports
#import csv
import os
import traceback
from domogik.common.utils import get_data_files_directory_for_plugin
from flask_wtf import Form
from wtforms import TextAreaField
from flask import request, flash
try:
	from flask.ext.babel import gettext, ngettext
except ImportError:
	from flask_babel import gettext, ngettext
	pass



### package specific functions
def read_contacts():
    contacts_file = os.path.join(get_data_files_directory_for_plugin("callerid"), CONTACTS_FILE)
    contacts = ""  # name : phone number
    try:
        with open(contacts_file, 'rb') as fp_contacts:
            contacts = fp_contacts.read()
    except IOError:
        # we return an empty file
        return ""
    return contacts

def save_contacts(data):
    contacts_file = os.path.join(get_data_files_directory_for_plugin("callerid"), CONTACTS_FILE)
    try:
        with open(contacts_file, 'w') as fp_contacts:
            fp_contacts.write(data)
    except IOError:
        # notification
        flash(gettext(u"Error while saving the contacts file"), "error")
    flash(gettext(u"Contacts list updated. Please restart the plugin."), "success")

def read_blacklist():
    blacklist_file = os.path.join(get_data_files_directory_for_plugin("callerid"), BLACKLIST_FILE)
    blacklist = ""  # phone number : reason
    try:
        with open(blacklist_file, 'rb') as fp_blacklist:
            blacklist = fp_blacklist.read()
    except IOError:
        # we return an empty file
        return ""
    return blacklist

def save_blacklist(data):
    blacklist_file = os.path.join(get_data_files_directory_for_plugin("callerid"), BLACKLIST_FILE)
    try:
        with open(blacklist_file, 'w') as fp_blacklist:
            fp_blacklist.write(data)
    except IOError:
        # notification
        flash(gettext(u"Error while saving the blacklist file"), "error")
    flash(gettext(u"Blacklist updated. Please restart the plugin."), "success")


class ContactsForm(Form):
    contacts = TextAreaField("contacts")

class BlacklistForm(Form):
    blacklist = TextAreaField("blacklist")



### common tasks
package = "plugin_callerid"
template_dir = "{0}/{1}/admin/templates".format(get_packages_directory(), package)
static_dir = "{0}/{1}/admin/static".format(get_packages_directory(), package)

plugin_callerid_adm = Blueprint(package, __name__,
                        template_folder = template_dir,
                        static_folder = static_dir)



@plugin_callerid_adm.route('/<client_id>')
def index(client_id):
    detail = get_client_detail(client_id)
    try:
        return render_template('plugin_callerid.html',
            clientid = client_id,
            client_detail = detail,
            mactive="clients",
            active = 'advanced')

    except TemplateNotFound:
        abort(404)



@plugin_callerid_adm.route('/<client_id>/contacts', methods = ['GET', 'POST'])
def contacts(client_id):
    detail = get_client_detail(client_id)
    form = ContactsForm()
    if request.method == "POST":
        save_contacts(form.contacts.data)
    else:
        form.contacts.data = read_contacts()
    try:
        return render_template('plugin_callerid_contacts.html',
            clientid = client_id,
            client_detail = detail,
            mactive="clients",
            active = 'advanced',
            contacts = read_contacts(),
            form = form)

    except TemplateNotFound:
        abort(404)


@plugin_callerid_adm.route('/<client_id>/blacklist', methods = ['GET', 'POST'])
def blacklist(client_id):
    detail = get_client_detail(client_id)
    form = BlacklistForm()
    if request.method == "POST":
        save_blacklist(form.blacklist.data)
    else:
        form.blacklist.data = read_blacklist()
    try:
        return render_template('plugin_callerid_blacklist.html',
            clientid = client_id,
            client_detail = detail,
            mactive="clients",
            active = 'advanced',
            blacklist = read_blacklist(),
            form = form)

    except TemplateNotFound:
        abort(404)

