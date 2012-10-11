# -*- coding: utf-8 -*-

import os, sys
import logging
import Zope2
from zope.site.hooks import getSite, setSite

from zope.component import getUtility, getMultiAdapter

try:
    from Products.CMFPlone.migrations import migration_util
except:
    #plone4
    from plone.app.upgrade import utils as migration_util

from AccessControl.SecurityManagement import getSecurityManager, setSecurityManager
from Products.CMFCore.utils import getToolByName
from Products.ATContentTypes.interface.image import IATImage
from Products.ATContentTypes.content.image import ATImage
import transaction


from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import _createObjectByType
from collective.cron import interfaces as i

PROFILE =  'collective.cron:default'
PROFILEID = 'profile-%s' % PROFILE

def log(message): # pragma: no cover
    logger = logging.getLogger('collective.cron.upgrades')
    logger.warn(message)

def recook_resources(context): # pragma: no cover
    """
    """
    site = getToolByName(context, 'portal_url').getPortalObject()
    jsregistry = getToolByName(site, 'portal_javascripts')
    cssregistry = getToolByName(site, 'portal_css')
    jsregistry.cookResources()
    cssregistry.cookResources()
    log('Recooked css/js')

def import_js(context): # pragma: no cover
    """
    """
    site = getToolByName(context, 'portal_url').getPortalObject()
    portal_setup = getToolByName(context, 'portal_setup')
    portal_setup.runImportStepFromProfile(PROFILEID, 'jsregistry', run_dependencies=False)
    log('Imported js')

def import_css(context): # pragma: no cover
    """
    """
    site = getToolByName(context, 'portal_url').getPortalObject()
    portal_setup = getToolByName(context, 'portal_setup')
    portal_setup.runImportStepFromProfile(PROFILEID, 'cssregistry', run_dependencies=False)
    log('Imported css')

def upgrade_profile(context, profile_id, steps=None): # pragma: no cover
    """
    >>> upgrade_profile(context, 'foo:default')
    """
    portal_setup = getToolByName(context.aq_parent, 'portal_setup')
    gsteps = portal_setup.listUpgrades(profile_id)
    class fakeresponse(object):
        def redirect(self, *a, **kw): pass
    class fakerequest(object):
        RESPONSE = fakeresponse()
        def __init__(self):
            self.form = {}
            self.get = self.form.get
    fr = fakerequest()
    if steps is None:
        steps = []
        for col in gsteps:
            if not isinstance(col, list):
                col = [col]
            for ustep in col:
                steps.append(ustep['id'])
        fr.form.update({
            'profile_id': profile_id,
            'upgrades': steps,
        })
    portal_setup.manage_doUpgrades(fr)

def upgrade_1000(context): # pragma: no cover
    """
    """
    site = getToolByName(context, 'portal_url').getPortalObject()
    portal_setup = site.portal_setup

    # install Products.PloneSurvey and dependencies
    #migration_util.loadMigrationProfile(site,
    #                                    'profile-Products.PloneSurvey:default')
    #portal_setup.runImportStepFromProfile('profile-collective.cron:default', 'jsregistry', run_dependencies=False)
    #portal_setup.runImportStepFromProfile('profile-collective.cron:default', 'cssregistry', run_dependencies=False)
    #portal_setup.runImportStepFromProfile('profile-collective.cron:default', 'portlets', run_dependencies=False)
    #portal_setup.runImportStepFromProfile('profile-collective.cron:default', 'propertiestool', run_dependencies=False)
    log('v1000 applied')

def upgrade_2001(context): # pragma: no cover
    """
    """
    site = getToolByName(context, 'portal_url').getPortalObject()
    portal_setup = site.portal_setup
    log = logging.getLogger(
        'collective.cron.upgrade.2001')
    try:
        from plone.app.async.interfaces import IAsyncDatabase
        from plone.app.async.service import AsyncService
    except:
        return
    service = AsyncService()
    db = service._db = getUtility(IAsyncDatabase)
    asyncfs = db.databases.get(db.database_name)
    itransaction = Zope2.zpublisher_transactions_manager
    # see plone.app.async.service.AsyncService.getQueues
    try:
        service._conn = asyncfs.open()
        service._conn.onCloseCallback(service.__init__)
        queues = service.getQueues()
        queue = queues['']
        s = getMultiAdapter((site, queue), i.ICrontabMarker)
        for idx, item in enumerate(s.annotations['plone'][:]):
            if isinstance(item, tuple):
                s.annotations['plone'][idx] = item[1]
        itransaction.commit()
    finally:
        asyncfs.close()
    setSite(site)
    log.info('upgrade runned')

