#!/usr/bin/env python
# -*- coding: utf-8 -*-
__docformat__ = 'restructuredtext en'
import datetime
from five import grok
from collective.cron import interfaces as i

class CACRONUtils(grok.Adapter):
    grok.provides(i.ICCRONUtils)
    grok.context(i.ICCRONContent)

    def log(self, date=None, status=u'OK', errors=None):
        if not date: date = datetime.datetime.now()
        if not errors: errors = []
        r = self.context.results_folder()
        rid = date.strftime('%d%m%Y%H%M%S') + '-%s' % status
        rid = r.invokeFactory('JobResult', rid)
        result = r[rid]
        result.date = date
        result.status = status
        result.errors = errors

    def getFolder(self, id, title='Folder', context=None):
        if context is None:
            context = self.context
        if not id in context.objectIds():
            id = context.invokeFactory('Folder', id, title=title)
        return context[id]
   
# vim:set et sts=4 ts=4 tw=80:
