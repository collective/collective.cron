#!/usr/bin/env python
# -*- coding: utf-8 -*-
__docformat__ = 'restructuredtext en'
import logging
import datetime
import pytz

from zope.annotation.interfaces import IAttributeAnnotatable, IAnnotations
from zope.component import getUtility
from zope.event import notify
from zope import interface
from zope.site.hooks import getSite

from persistent.list import PersistentList
from persistent.dict import PersistentDict

from five import grok
from zc.async import interfaces as zai
from plone.app.async.interfaces import IAsyncService
from plone.app.async.service import _executeAsUser
from Products.statusmessages.interfaces import IStatusMessage

from collective.cron import interfaces as i
from collective.cron import events as e
from collective.cron.config import MANAGE_KEY
from collective.cron import MessageFactory as _

def runJob(backend, *args, **kwargs):
    logger = logging.getLogger('backend/runJob')
    logger.debug('Run job: %s' % backend.title)
    bpath = backend.getPhysicalPath()
    status = 'NOTRUN'
    errors = []
    try:
        if backend.activated:
            errors = i.IJobRunner(backend).run()
            status = 'OK'
            # if we have had errors without exceptions, those
            # are just warnings
            if len(errors):
                status = 'WARN'
    except Exception, ex:
        errors.append('%s' % ex)
        status = 'FAILED'
    i.ICACRONUtils(backend).log(status=status, errors=errors)
    notify(e.BackendFinnishedJobEvent(backend, status))
    return status, bpath

class BackendJobManager(grok.Adapter):
    grok.provides(i.IBackendJobManager)
    grok.context(i.IBackend)

    def __init__(self, *args, **kwargs):
        grok.Adapter.__init__(self, *args, **kwargs)
        self.log = logging.getLogger('BackendJobManager')

    @property
    def async(self):
        return getUtility(IAsyncService)

    @property
    def queue(self):
        return self.async.getQueues()['']

    def get_job_infos(self, begin_after=None):
        job_infos = {'job': runJob,
                     'context':self.context,
                     'args': (),
                     'begin_after': begin_after,
                     'kwargs': {}}
        return job_infos

    def register_job(self, begin_after=None, force=False):
        backend = self.context
        now = datetime.datetime.now(pytz.UTC)
        # if job is not already scheduled
        logger = logging.getLogger('backend/register_job')
        logger.debug('Register job: %s' % backend.title)
        #schedule_time = datetime.datetime.now(pytz.UTC) + datetime.timedelta(seconds=10)# test values: execute each 10 seconds
        job_infos = self.get_job_infos(begin_after)
        if (begin_after is not None) or force:
            j = self.get_job_present()
            if j is not None:
                remove = False
                if force and (j.status == zai.PENDING):
                    remove = True
                # either renew the job if the schedule time is prior to the previous scheduled one
                # or renew jobs that are pending and not executed so just zombies
                elif isinstance(j.begin_after, datetime.datetime):
                    if ((j.begin_after >= begin_after)
                        or ((j.begin_after < now) and (j.status == zai.PENDING))):
                        remove = True
                else:
                    remove = True
                if remove:
                    self.remove_jobs(job_infos)
        if ((not self.is_job_present())
            and ((begin_after is not None) or force)
            and backend.activated):
            msg = 'Registring a new job: %s' % repr(job_infos)
            if begin_after:
                msg += ' | schedule time: %s' % begin_after
            self.log.debug(msg)
            self.mark_queue_plonesite_aware()
            # queue the job
            job = self.async.queueJob(
                job_infos['job'],
                job_infos['context'],
                *job_infos['args'],
                **job_infos['kwargs']
            )
            # or scheduled at a specific time
            # we need to reschedule it more precisely
            # after p.a.async wrapped it
            if begin_after:
                queue = job.queue
                queue.remove(job)
                job.begin_after = begin_after
                queue.put(job)
        job = self.get_job_present(job_infos)
        return job

    def compare_job(self, job, job_infos):
        if job_infos is None:
            job_infos = self.get_job_infos(job.begin_after)
        #args0 is the context physical path
        if job.callable == _executeAsUser:
            same_path = job_infos['context'].getPhysicalPath() == job.args[0]
            same_job = job_infos['job'] == job.args[4]
            same_args = job_infos['args'] == tuple(job.args[5:])
            same_kw = job_infos['kwargs'] == job.kwargs
            same_ba = job_infos['begin_after'] == job.begin_after
            if same_path and same_job and same_args and same_kw and same_ba:
                return True
        return False

    def get_job_present(self, job_infos=None):
        job = None
        if job_infos is None:
            job_infos = self.get_job_infos()
        for j in self.queue:
            job_infos['begin_after'] = j.begin_after
            if self.compare_job(j, job_infos):
                job = j
                break
        return job

    def is_job_present(self, job_infos=None):
        present = False
        if self.get_job_present(job_infos) is not None:
            present = True
        return present

    def is_job_running(self, job_infos=None):
        present = False
        j = self.get_job_present(job_infos)
        if j is not None:
            if j.status == zai.ACTIVE:
                present = True
        return present

    def remove_jobs(self, job_infos=None):
        if job_infos is None:
            job_infos = self.get_job_infos()
        for job in self.queue:
            job_infos['begin_after'] = job.begin_after
            if self.compare_job(job, job_infos):
                self.log.info('Removing this job : %s' % repr(job))
                self.queue.remove(job)

    def register_or_remove(self, force=False):
        backend = self.context
        ret = None
        if backend.activated:
            # we maybe just actovated the job
            # starting a loop to make the cron
            ret = i.IBackendJobManager(
                backend
            ).register_job(
                begin_after=backend.next(),
                force=force)
        else:
            # we have deactivated the job or cancel the schedulation
            # remove the job from the queue !
            ret = i.IBackendJobManager(
                backend).remove_jobs()
        return ret

    def mark_queue_plonesite_aware(self):
        """Mark the plone site in the queue annotations to register jobs on restarts."""
        site = getSite()
        queue = self.async.getQueues()['']
        interface.alsoProvides(queue, IAttributeAnnotatable)
        infos = IAnnotations(queue)
        if not MANAGE_KEY in infos:
            infos[MANAGE_KEY] = PersistentDict()
        if not 'plone' in infos[MANAGE_KEY]:
            infos[MANAGE_KEY]['plone'] = PersistentList()
        db = site._p_jar.db().database_name
        ppath = "/".join(site.getPhysicalPath())
        if not (db, ppath) in infos[MANAGE_KEY]['plone']:
            infos[MANAGE_KEY]['plone'].append((db, ppath))

class run_job(grok.View):
    grok.context(i.IBackend)
    def render(self):
        messages = IStatusMessage(self.request)
        try:
            a = i.IBackendJobManager(self.context)
            job = a.register_job(force=True)
            messages.addStatusMessage(_( u"Job queued", ), type="info")
        except Exception, ex:
            messages.addStatusMessage(
                _(u"Job failed to be queued: ${ex}", mapping={"ex":ex}),
                type="error"
            )
        return self.response.redirect(
            self.context.absolute_url()
        )

class activate_job(grok.View):
    grok.context(i.IBackend)
    def render(self):
        messages = IStatusMessage(self.request)
        try:
            a = i.IBackendJobManager(self.context)
            self.context.activated = True
            job = a.register_or_remove()
            messages.addStatusMessage(_( u"Job activated", ), type="info")
        except Exception, ex:
            messages.addStatusMessage(
                _(u"Job failed to be deactivated: ${ex}", mapping={"ex":ex}),
                type="error"
            )
        return self.response.redirect(
            self.context.absolute_url()
        )

class deactivate_job(grok.View):
    grok.context(i.IBackend)
    def render(self):
        messages = IStatusMessage(self.request)
        try:
            a = i.IBackendJobManager(self.context)
            job = a.remove_jobs()
            self.context.activated = False
            messages.addStatusMessage(_( u"Job deactivated", ), type="info")
        except Exception, ex:
            messages.addStatusMessage(
                _(u"Job failed to be deactivated: ${ex}", mapping={"ex":ex}),
                type="error"
            )
        return self.response.redirect(
            self.context.absolute_url()
        )

# vim:set et sts=4 ts=4 tw=80:
