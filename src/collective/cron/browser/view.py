#!/usr/bin/env python
# -*- coding: utf-8 -*-
__docformat__ = 'restructuredtext en'

from zope import schema
from zope.interface import implements, Interface
from zope.component import getUtility
from five import grok

from plone.app.layout.viewlets.interfaces import IPortalHeader
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.interfaces import IPloneSiteRoot
from Products.CMFCore.Expression import getExprContext  

from collective.cron import interfaces as i

#class cron_dashboard_link(grok.Viewlet):
#    grok.viewletmanager(IPortalHeader)
#    grok.context(IPloneSiteRoot)
#
class cron_dashboard(grok.View):
    grok.name('ccron_dashboard')
    grok.context(IPloneSiteRoot)
    grok.require('ccron.View')
    def getBackends(self):
        """get backends"""
        pc = getToolByName(self.context, 'portal_catalog')
        query = {
            'object_provides': i.IBackend.__identifier__
        }
        brains = pc.searchResults(**query)
        return brains

    def getBackendIcon(self, context):
        icon = None
        tt = getToolByName(self.context, 'portal_types')
        fti = tt.get(context.portal_type, None)
        if fti is not None:
            icone = fti.getIconExprObject()
            icon = icone(getExprContext(self.context))
        return icon

# vim:set et sts=4 ts=4 tw=80:
