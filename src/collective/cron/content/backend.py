#!/usr/bin/env python
# -*- coding: utf-8 -*-
__docformat__ = 'restructuredtext en'

import datetime
import logging

from zope.annotation.interfaces import IAnnotations
from zope.event import notify
from zope import schema
from zope.interface import implements
from AccessControl.SecurityManagement import getSecurityManager, setSecurityManager
from zope.site.hooks import getSite, setSite
import transaction

from zope.lifecycleevent.interfaces import IObjectModifiedEvent, IObjectAddedEvent

from five import grok
from plone.app.async.interfaces import IQueueReady
from plone.dexterity.content import Container
from plone.directives import form, dexterity

from collective.cron.config import MANAGE_KEY, RESULTS_FOLDER
from collective.cron import events as e
from collective.cron import interfaces as i
from collective.cron import MessageFactory as _
from collective.cron.utils import croniter, to_utc, su_plone

from Products.CMFCore.utils import getToolByName

class CronFormatError(schema.ValidationError): pass
class Backend(Container):
    """Base MixIn for backends"""
    implements((i.IBackend, i.ICCRONContent))
    def results_folder(self):
      return i.ICCRONUtils(self).getFolder(RESULTS_FOLDER, 'Results')

    def getResults(self):
        folder = self.results_folder()
        pc = getToolByName(self, 'portal_catalog')
        query = {
            'portal_type' : 'JobResult',
            'path' : {'query': '/'.join(folder.getPhysicalPath())},
            'sort_on': 'getObjPositionInParent',
        }
        results = pc.searchResults(**query)
        return results

    def getLastResult(self):
        res = self.getResults()
        if len(res):
            return res[-1].getObject()

    def getLastRun(self):
        result = self.getLastResult()
        if result is not None:
            return result.date

    def getLastStatus(self):
        result = self.getLastResult()
        if result is not None:
            return result.status

    def getLastErrors(self):
        result = self.getLastResult()
        if result is not None:
            return result.errors
        return []
  
    def next(self):
        log = logging.getLogger('Backend.next')
        now = datetime.datetime.now() + datetime.timedelta(minutes=1)
        try:
            unextr = to_utc(croniter(self.periodicity, start_time=now).get_next())
        except:
            log.error('Failed to get next run time for %s' % self)
            unextr = None
        return unextr

@form.validator(field=i.IBackend['periodicity'])
def cronFormatValidator(data):
    if data is None:
        return
    if data == '':
        return
    try:
        croniter(data)
    except ValueError:
        raise CronFormatError(
            _(u"The cron is not valid.")
        )

@grok.subscribe(i.IBackend, i.IServerRestartEvent)
@grok.subscribe(i.IBackend, i.IBackendFinnishedJobEvent)
def registerAgainJob(backend, event=None):
    manageJobInQueue(backend, event)

@grok.subscribe(i.IBackend, IObjectAddedEvent)
@grok.subscribe(i.IBackend, IObjectModifiedEvent)
def manageJobInQueue(backend, event):
    # we maybe just activated the job
    # starting a loop to make the cron
    i.IBackendJobManager(backend).register_or_remove()

@grok.subscribe(IQueueReady)
def registerOnRestart(event):

    site = getSite()
    queue = event.object
    conn = queue._p_jar.root()
    dbs = queue._p_jar.db().databases
    log = logging.getLogger('ccron.registerOnRestart')
    infos = None
    current_user = None
    scontext = getSecurityManager()
    try:
        infos = IAnnotations(queue)
    except Exception, ex :
        log.error('Seem the queue was never feeded with backends jobs!')
    try:
        if infos:
            plones = infos.get(MANAGE_KEY, {}).get('plone', [])
            for content in plones:
                mountpoint, ppath = content
                try:
                    pconn = dbs[mountpoint].open()
                    root = pconn.root()['Application']
                    root = dbs[mountpoint].open().root()['Application']
                    plone = root.unrestrictedTraverse(ppath)
                    setSite(plone)
                    brains = plone.portal_catalog.searchResults(
                        object_provides=i.IBackend.__identifier__
                    )
                    try:
                        backends = [b.getObject() for b in brains]
                    except Exception, ex:
                        backends = [ root.unrestrictedTraverse(b.getPath())
                                    for b in brains]
                    for backend in backends:
                        creators = list(backend.creators[:])
                        user = su_plone(root, plone, creators)
                        creators.reverse()
                        try:
                            notify(e.ServerRestartEvent(backend))
                        except Exception, ex:
                            log.error('Ooops in reactivating job: %s'%ex)
                        transaction.commit()
                    setSecurityManager(scontext)
                finally:
                    pconn.close()
    except Exception, ex:
        log.error('Ooops in registerOnRestart // loop')
    setSite(site)
    transaction.commit()

class View(dexterity.DisplayForm):
    grok.context(i.IBackend)
    grok.require('ccron.View')

    def has_logs(self):
        c = self.context
        if RESULTS_FOLDER in c.objectIds():
            if len(c[RESULTS_FOLDER]) > 0:
                return True

    def next_runtime(self):
        b = self.context
        manager = i.IBackendJobManager(b)
        j = manager.get_job_present()
        d = None
        if j is not None:
            d = j._begin_after
        sstr = _('NOW')
        if d is not None:
           pv = b.restrictedTraverse('@@plone')
           sstr = pv.toLocalizedTime(d, long_format=True)
        return sstr

    def getTitle(self):
        return "%s (%s)" % (
            self.context.title,
            self.getTitleCompl()
        )

    def getTitleCompl(self):
        return i.IBackendTitleCompl(
            self.context).getTitleCompl()

class BackendActionsViewletManager(grok.ViewletManager):
    grok.context(i.IBackend)
    grok.name('ccron.backendactions')

class glinks(grok.Viewlet):
    grok.viewletmanager(BackendActionsViewletManager)
    grok.context(i.IBackend)

class BackendGetAdapter(grok.Adapter):
    grok.implements(i.IBackendTitleCompl)
    grok.context(i.IBackend)
    def getTitleCompl(self):
        return self.context.portal_type

# vim:set et sts=4 ts=4 tw=0:
