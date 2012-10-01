#!/usr/bin/env python
# -*- coding: utf-8 -*-
__docformat__ = 'restructuredtext en'
import logging
from ordereddict import OrderedDict

from Products.CMFPlone.interfaces.siteroot import IPloneSiteRoot
from zope.interface import implements, implementsOnly
from zope.event import notify
from zope.component import (
    adapts,
    adapter,
    getAdapters,
    getMultiAdapter,
    getAdapter,
)
from collective.cron import interfaces as i
from collective.cron import utils
from collective.cron import crontab as mcrontab

import lxml

CRONTAB = '<?xml version="1.0" encoding="UTF-8"?>\n<crons>%s\n</crons>'
CRON = '\n  <cron uid="%(uid)s" name="%(name)s" activated="%(activated)s" periodicity="%(periodicity)s">'
CRONEND = '\n  </cron>'
ENVIRON = '\n    <environ><![CDATA[\n%s\n]]>\n    </environ>'

# vim:set et sts=4 ts=4 tw=80:
class CronsExportImporter(object):
    implements(i.IExportImporter)
    adapts(IPloneSiteRoot, i.ICrontab)
    def __init__(self, context, crontab):
        self.context = context
        self.crontab = crontab

    def do_import(self, xmlstring):
        crt = self.crontab
        changed = False
        crons = []
        for xcron in lxml.etree.fromstring(xmlstring).xpath('//crons/cron'):
            attrs = dict(xcron.items())
            delete = utils.asbool(attrs.get('remove', None))
            data = {}
            uid = data['uid'] = unicode(attrs['uid'])
            # first try delete
            if delete:
                if data['uid'] in crt.crons:
                    del crt.crons[uid]
                    changed= True
                continue # pragma: no cover
            for k in ['periodicity', 'activated', 'name']:
                if k in attrs:
                    val = attrs[k]
                    if isinstance(val, basestring):
                        val  = unicode(val)
                    if k in ['activated']:
                        val = utils.asbool(val)
                    data[k] = val
            envs = xcron.xpath('environ')
            environ = None
            if len(envs) > 0:
                env = envs[0]
                senv = env.text.strip()
                if senv:
                    data['environ'] = mcrontab.json.loads(senv)
            # Add cron if not in the crontab
            if not uid in crt.crons:
                cron = mcrontab.Cron.load(data, crontab=crt)
                changed = True
                continue
            # if we got there, we are in edit mode
            # try to find the cron to edit
            cron = crt.crons.get(uid, None)
            if not cron: # pragma: no cover
                continue
            for k in data:
                if getattr(cron, k) != data[k]:
                    setattr(cron, k, data[k])
                    changed = True
        if changed:
            crt.save()

    def do_export(self):
        crt = self.crontab
        xml = ''
        for scron in crt.crons:
            cron = crt.crons[scron]
            cxml = CRON % cron.dump()
            if cron.environ:
                cxml += ENVIRON % mcrontab.json.dumps(cron.environ)
            cxml += CRONEND
            xml += cxml
        fxml = (CRONTAB % xml).strip()
        return fxml.encode('utf-8')
