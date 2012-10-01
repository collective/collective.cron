#!/usr/bin/env python
# -*- coding: utf-8 -*-
__docformat__ = 'restructuredtext en'
import datetime


from zope.interface import implements
from zope.component import adapts
from collective.cron import interfaces as i
from Products.CMFPlone.interfaces.siteroot import IPloneSiteRoot
from collective.cron import crontab

class CCRONUtils(object):
    adapts(IPloneSiteRoot, i.ICron)
    implements(i.ICCRONUtils)

    def __init__(self, context, cron):
        self.context = context
        self.cron = cron



    def getFolder(self, id, title='Folder', context=None):
        if context is None:
            context = self.context
        if not id in context.objectIds():
            id = context.invokeFactory('Folder', id, title=title)
            context[id].processForm()
        return context[id]


# vim:set et sts=4 ts=4 tw=80:
