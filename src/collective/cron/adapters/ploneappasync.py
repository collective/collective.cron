#!/usr/bin/env python
# -*- coding: utf-8 -*-

__docformat__ = 'restructuredtext en'
import pytz
import datetime
import logging

from zope.interface import (implements,
                            alsoProvides,)

from zope.component import (
    adapts,
    getUtility,
    getMultiAdapter,
    getAdapters,
    getAdapter,
    adapter
)
import Zope2
from zope.event import notify
from zope.site.hooks import getSite, setSite
from AccessControl.SecurityManagement import getSecurityManager, setSecurityManager
from zope.annotation.interfaces import IAttributeAnnotatable, IAnnotations

from persistent.list import PersistentList
from persistent.dict import PersistentDict

import transaction

from zc.async import interfaces as zai
from Products.CMFPlone.interfaces.siteroot import IPloneSiteRoot

from plone.app.async.interfaces import IAsyncService
from plone.app.async.service import _executeAsUser
from plone.app.async.interfaces import IQueueReady

from collective.cron import interfaces as i
from collective.cron import events as e
from collective.cron import crontab
from collective.cron import utils


def queue_aware(func):
    def wrapper(self, *args, **kw):
        self.marker.mark_crontab_aware()
        return func(self, *args, **kw)
    return wrapper

class Queue(object):
    implements(i.IQueue)
    adapts(IPloneSiteRoot)

    def __init__(self, portal):
        self.log = logging.getLogger('collective.cron.ploneappasync')
        self.portal = portal

    @property
    def marker(self):
        return getMultiAdapter(
            (self.portal, self.queue), i.ICrontabMarker)

    @property
    def job(self):
        return crontab.runJob

    @property
    def service(self):
        return getUtility(IAsyncService)

    @property
    def queue(self):
        try:
            queue = self.service.getQueues()['']
            return queue
        except Exception, ex:
            i.AsyncQueueNotReady('Queue is not ready')

    @property
    def jobs(self):
        return [a for a in self.queue]

    @queue_aware
    def register_job(self, job_infos):
        job = self.service.queueJobWithDelay(
            None,
            job_infos['begin_after'], # either None or UTC datetime
            job_infos['job'],
            job_infos['context'],
            *job_infos['args'],
            **job_infos['kwargs']
        )
        self.log.info('Registering this job : %s' % repr(job))
        return True

    def remove(self, job):
        return self.queue.remove(job)

    def remove_jobs(self, job_infos):
        if job_infos is None: # pragma: no cover
            job_infos = self.get_job_infos()
        job_infos = job_infos.copy()
        for job in self.queue:
            job_infos['begin_after'] = job.begin_after
            if self.compare_job(job, job_infos):
                self.log.info('Removing this job : %s' % repr(job))
                self.queue.remove(job)

    def compare_job(self, job, job_infos):
        if job_infos is None: # pragma: no cover
            job_infos = self.get_job_infos(job.begin_after)
        # args0 is the context physical path
        if job.callable == _executeAsUser:
            # job info can also be wrapped
            wrapped = False
            if job_infos['job'] == _executeAsUser:
                wrapped = True
            try:
                same_path = job_infos['context'].getPhysicalPath() == job.args[0]
            except Exception, ex: # pragma: no cover
                same_path = False
            try:
                same_job = job_infos['job'] == job.args[4]
                # if the job is wrapped, test in the args
                if not same_job and wrapped:
                    same_job = job_infos['args'][4] == job.args[4]
            except Exception, ex: # pragma: no cover
                same_job = False
            try:
                is_cron = crontab.runJob == job.args[4]
            except Exception, ex: # pragma: no cover
                is_cron = False
            same_cron = True
            if is_cron and job_infos['args']:
                try:
                    if wrapped:
                        cron = job_infos['args'][5]
                    else:
                        cron = job_infos['args'][0]
                    same_cron = cron.uid == job.args[5].uid
                except Exception, ex: # pragma: no cover
                    same_cron = False
            same_args = True
            if not is_cron:
                try:
                    same_args = job_infos['args'] == tuple(job.args[5:])
                except Exception, ex: # pragma: no cover
                    same_args = False
            same_kw = job_infos['kwargs'] == job.kwargs
            if job_infos['begin_after'] is not None:
                try:
                    same_ba = job_infos['begin_after'] == job.begin_after
                except Exception, ex:
                    # exception on datetime comparison, we are false !
                    same_ba = False
            else:
                same_ba = True
            if (same_cron and same_path and same_job
                and same_args and same_kw and same_ba):
                return True
        return False

    def get_job_status(self, job_infos=None):
        status = None
        j = self.get_job_present(job_infos)
        if j is not None:
            status = j.status
        return status

    def is_job_present(self, job_infos=None):
        present = False
        if self.get_job_in_queue(job_infos) is not None:
            present = True
        return present

    def is_job_running(self, job_infos=None):
        """Search on all agents if the job is running"""
        return (
            self.get_job_status(job_infos) ==
            zai.ACTIVE)

    def is_job_finished(self, job_infos=None):
        return (
            self.get_job_status(job_infos) ==
            zai.COMPLETED)

    def is_job_pending(self, job_infos=None):
        return (
            self.get_job_status(job_infos) ==
            zai.PENDING)

    def get_job_infos(self,
                      begin_after=None,
                      job=None,
                      context=None,
                      *args,
                      **kwargs):
        if not kwargs:
            kwargs = {}
        if not args:
            args = tuple()
        if job is None:
            job = crontab.runJob
        if context is None:
            context = self.portal
        job_infos = {
            'job': job,
            'context': context,
            'begin_after': begin_after,
            'args': args,
            'kwargs': kwargs}
        return job_infos

    def get_job_present(self, job_infos=None, only_in_queue=False, only_in_agents=False):
        job = None
        if (not only_in_agents) or only_in_queue:
            job = self.get_job_in_queue(job_infos)
        # if job is not in the queue, search in the agent
        if (not only_in_queue and job is None) or only_in_agents:
            job = self.get_job_in_agents(job_infos)
        return job

    def get_job_in_queue(self, job_infos=None):
        job = None
        if job_infos is None: # pragma: no cover
            job_infos = self.get_job_infos()
        job_infos = job_infos.copy()
        for j in self.queue:
            job_infos['begin_after'] = j.begin_after
            if self.compare_job(j, job_infos):
                job = j
                break
        return job

    def get_job_in_agent(self,
                         agent,
                         job_infos = None,
                         only_active = False,
                         only_completed = False,
                        ):
        job = None
        if job_infos is None: # pragma: no cover
            job_infos = self.get_job_infos()
        # first search in ._data for running job
        if (not only_completed) or only_active:
            for j in agent._data:
                if self.compare_job(j, job_infos):
                    job = j
                    break
        # first search in .completed for completed job
        # on the contrary of active jobs, we must
        # take care to get the last matching job in the queues
        if ((not only_active and job is None)
            or only_completed):
            for j in agent.completed:
                if self.compare_job(j, job_infos):
                    job = j
                    break
        return job

    def get_job_in_agents(self,
                          job_infos = None,
                          only_active = False,
                          only_completed = False,):
        job = None
        for dispatcher in self.queue.dispatchers.values():
            for agent in dispatcher.values():
                j = self.get_job_in_agent(
                    agent=agent,
                    job_infos=job_infos,
                    only_active=only_active,
                    only_completed=only_completed)
                if j is not None:
                    job = j
                    break
        return job

    def cleanup_before_job(self, job_infos, force=False):
        if job_infos is None: # pragma: no cover
            job_infos = self.get_job_infos()
        now = datetime.datetime.now(pytz.UTC)
        begin_after = job_infos['begin_after']
        j = self.get_job_in_queue(job_infos)
        #  - force is on, unconditionnaly removing pending job
        #  - if not force, we remove:
        #     - job that executes later then this cron
        #     - job that executes prior to now (zombies)
        #     - cron that have changed name
        remove = False
        if j is not None:
            is_cron, cron, ncron = False, None, None
            try:
                cron =  j.args[5]
                is_cron = isinstance(cron, crontab.Cron)
                ncron = job_infos['args'][0]
            except Exception, ex: # pragma: no cover
                is_cron = False
            if force and (j.status == zai.PENDING):
                remove = True
            if not remove and (isinstance(j.begin_after, datetime.datetime)
                               and isinstance(begin_after, datetime.datetime)):
                if ((j.begin_after > begin_after)
                    or ((j.begin_after < now) and (j.status == zai.PENDING))):
                    remove = True
            # reschedule if we have changed the name of a cron
            if not remove and is_cron:
                if not ncron.similar(cron):
                    remove = True
        if remove:
            self.remove_jobs(job_infos)

    def get_job_infos_from_job(self, j):
        ji = {
            'context': self.portal,
            'begin_after': j.begin_after,
            'job': j.callable,
            'args': j.args,
            'kwargs': j.kwargs,
        }
        if j.callable == _executeAsUser:
            try:
                ji['context'] = self.portal.restrictedTraverse(
                '/'.join(j.args[0]))
            except Exception, ex: # pragma: no cover
                pass
            #try:
            #    is_cron = j.args[4] == crontab.runJob
            #except Exception, ex:
            #    is_cron = False
            #if is_cron:
            #    ji['job'] = crontab.runJob
            #    try:
            #        ji['args'] = j.args[5:]
            #    except Exception, ex:
            #        ji['args'] = tuple()
        return ji

    def get_job_infos_from_queue(self):
        job_infos = []
        if self.queue:
            for j in self.queue:
                job_infos.append(
                    self.get_job_infos_from_job(j)
                )
        return job_infos


def annotable(func):
    def wrapper(self, *a, **kw):
        if not IAttributeAnnotatable.providedBy(self.queue):
            alsoProvides(
                self.queue,
                IAttributeAnnotatable)
        return func(self, *a, **kw)
    return wrapper


class CrontabMarker(object):
    implements(i.ICrontabMarker)
    adapts(IPloneSiteRoot, zai.IQueue)
    def __init__(self, portal, queue):
        self.portal = portal
        self.queue = queue
        self.ppath = "/".join(portal.getPhysicalPath())

    @property
    @annotable
    def annotations(self):
        return i.IAnnotedQueue(self.queue).annotations

    @property
    @annotable
    def marked(self):
        infos = self.annotations
        return self.key in infos['plone']

    @property
    def key(self):
        return self.ppath

    @annotable
    def unmark_crontab_aware(self):
        infos = self.annotations
        if self.marked:
            idx = infos['plone'].index(self.key)
            infos['plone'].pop(idx)

    @annotable
    def mark_crontab_aware(self):
        """Mark the plone site in the queue annotations
        to register jobs on restarts."""
        infos = self.annotations
        if not self.marked:
            infos['plone'].append(self.key)


class AnnotedQueue(object):
    implements(i.IAnnotedQueue)
    adapts(zai.IQueue)

    def __init__(self, queue):
        self.queue = queue

    @property
    @annotable
    def annotations(self):
        infos = IAnnotations(self.queue)
        if not i.MANAGE_KEY in infos:
            infos[i.MANAGE_KEY] = PersistentDict()
        if not 'plone' in infos[i.MANAGE_KEY]:
            infos[i.MANAGE_KEY]['plone'] = PersistentList()
        return infos[i.MANAGE_KEY]

# from plone.app.async.interfaces import IAsyncDatabase
# from plone.app.async.service import AsyncService
# @adapter(i.ICrontabInstallationEvent)
# def register_on_install(event):
#     # see plone.app.async.service.AsyncService.getQueues
#     site = event.object
#     log = logging.getLogger(
#         'collective.cron.async.registerOnInstall')
#     itransaction = Zope2.zpublisher_transactions_manager
#     service = AsyncService()
#     db = service._db = getUtility(IAsyncDatabase)
#     asyncfs = db.databases.get(db.database_name)
#     try:
#         service._conn = asyncfs.open()
#         queue = service.getQueues()['']
#         s = getMultiAdapter((site, queue), i.ICrontabMarker)
#         s.mark_crontab_aware()
#         itransaction.commit()
#     finally:
#         asyncfs.close()
#     setSite(site)

@adapter(IQueueReady)
def register_on_restart(event):
    emsg = 'Ooops in registerOnRestart // loop (%s)'
    site = getSite()
    queue = event.object
    iqueue = i.IAnnotedQueue(queue)
    log = logging.getLogger(
        'collective.cron.async.registerOnRestart')
    scontext = getSecurityManager()
    root = Zope2.app()
    try:
        assert len(iqueue.annotations['plone']) > 0
    except Exception, ex : # pragma: no cover
        log.warning('Seem the queue was never feeded with jobs!')
    plones = iqueue.annotations['plone']
    try:
        try:
            for ppath in plones:
                try:
                    transaction.commit()
                    restore_plone(root, ppath)
                finally:
                    setSecurityManager(scontext)
            transaction.commit()
        except Exception, ex: # pragma: no cover
            transaction.abort()
            log.error(
                 emsg % (ex))
    finally:
        root._p_jar.close()
    setSite(site)
    transaction.commit()

def restore_plone(root, ppath):
    log = logging.getLogger(
        'collective.cron.async.restore_crons_for_plonesite')
    ex_msg = '%s: Ooops in reactivating: %s'
    try:
        plone = root.unrestrictedTraverse(ppath)
        setSite(plone)
        crt = crontab.Crontab.load()
        notify(e.ServerRestartEvent(plone, crt))
        log.info('%s: tasks re-activated' % (ppath))
    except Exception, ex: # pragma: no cover
        log.error(ex_msg % (ppath, ex))

# vim:set et sts=4 ts=4 tw=80 :
