#!/usr/bin/env python
# -*- coding: utf-8 -*-

__docformat__ = 'restructuredtext en'
import datetime
import os
import sys
import logging
import pytz
import time
import shutil

from AccessControl.SecurityManagement import newSecurityManager
from zope.testbrowser import browser

from croniter import croniter as baseT

D = os.path.dirname
J = os.path.join

FF2_USERAGENT =  'Mozilla/5.0 (Windows; U; Windows NT 5.1; fr; rv:1.8.1.14) Gecko/20080404 Firefox/2.0.0.14'
FF3_USERAGENT =  'Mozilla/5.0 (X11; U; Linux x86_64; fr; rv:1.9.2.15) Gecko/20110308 Fedora/3.6.15-1.fc14 Firefox/3.6.15'

class croniter(baseT):
    def get_next(self, ret_type=None):
        if ret_type is None:
            ret_type = datetime.datetime
        return self._get_next(ret_type, is_prev=False)

class NoSuchUserError(Exception):pass

def splitstrip(value):
    return [a.strip()
            for a in value.split()
            if a.strip()]

def which(program, environ=None, key = 'PATH', split = ':'): # pragma: no cover
    if not environ:
        environ = os.environ
    PATH=environ.get(key, '').split(split)
    for entry in PATH:
        fp = os.path.abspath(os.path.join(entry, program))
        if os.path.exists(fp):
            return fp
        if (sys.platform.startswith('win') or sys.platform.startswith('cyg'))  and os.path.exists(fp+'.exe'):
            return fp+'.exe'
    raise IOError('Program not fond: %s in %s ' % (program, PATH))

class Browser(browser.Browser): # pragma: no cover
    def __init__(self, url=None, mech_browser=None):
        browser.Browser.__init__(self, url, mech_browser)
        self.mech_browser.set_handle_robots(False)
        self.mech_browser.addheaders = [('User-agent' , FF3_USERAGENT)]
        if url is not None:
            self.open(url)

def get_tree(h): # pragma: no cover
    """h can be either a zc.testbrowser.Browser or a string."""
    from lxml.html import document_fromstring
    if isinstance(h, file):
        h = h.read()
    if not isinstance(h, basestring):
        h = h.contents
    return document_fromstring(h)

test_environment = {
    'CONTENT_TYPE': 'multipart/form-data; boundary=12345',
    'REQUEST_METHOD': 'POST',
    'SERVER_NAME': 'localhost',
    'SERVER_PORT': '80',
}

upload_request = """
--12345
Content-Disposition: form-data; name="file"; filename="%s"
Content-Type: application/octet-stream
Content-Length: %d

%s

"""
def set_file_content(atfile, data, filename=None): # pragma: no cover
    mutator = atfile.getField('file').getMutator(atfile)
    mutator(data)


def to_tz(d, tz):
    """
    convert to a timestamp from any datetime naive or not
    to the destination timezone """
    ud = d
    # try to convert naive datetime to UTC
    if ud.tzinfo is None:
        ts = time.mktime(ud.timetuple())
        ud = datetime.datetime.utcfromtimestamp(
            ts).replace(tzinfo=pytz.UTC)
    # if this is a non naive datetime just convert to the destination tz
    if ud.tzinfo is not None:
        ud = ud.astimezone(tz)
    return ud

def to_utc(d):
    return to_tz(d, pytz.UTC)

def to_local(d): # pragma: no cover
    """
    convert to a timestamp, then reconvert to a naive local datetime"""
    ud = None
    if d.tzinfo is None:
        ud = d
    if ud is not None:
        ts = time.mktime(d.timetuple())
        ud = datetime.datetime.fromtimestamp(
            ts).replace(tzinfo=None)
    return ud

def su_plone(app, plone, userids=None):
    """Try to get an user in plone, then in zope.
    From there, login as him"""
    log = logging.getLogger('su_zope')
    if not userids: userids = []
    user = None
    for u in userids:
        try:
            user = plone.acl_users.getUser(u)
            break
        except: # pragma: no cover
            log.info('No user matching %s in %s' % (
                user, '/'.join(plone.getPhysicalPath()))
            )
    if user is None:
        for u in userids:
            try:
                user = app.acl_users.getUser(u)
                break
            except: # pragma: no cover
                log.info('No user matching %s in /' % (
                    user, '/'.join(plone.getPhysicalPath()))
                )
    if user is not None:
        newSecurityManager(None, user)
    else:
        raise NoSuchUserError(
            'There are no user matching: %s' % userids
        )
    return user

def remove_path(path): # pragma: no cover
    """Remove a path."""
    if os.path.exists(path):
        if os.path.islink(path):
            os.unlink(path)
        elif os.path.isfile(path):
            os.unlink(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
    else:
        print
        print "'%s' was asked to be deleted but does not exists." % path
        print

def asbool(value):
    if isinstance(value, basestring):
        value = value.lower()
        for t in 'on', 'yes', 'true', '1':
            if t in value:
                return True
        for t in 'off', 'no', 'false', '0':
            if t in value:
                return False
        if value in ['t', 'y']:
            return True
        if value in ['n', 'f']:
            return False
    if value == -1:
        return False
    return bool(value)

# vim:set et sts=4 ts=4 tw=80:
