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
from collective.cron import events as e
from collective.cron.crontab import runJob
from zope.site.hooks import getSite

class AsyncManager(object):
    implements(i.IAsyncManager)
    def __init__(self, context):
        self.context = context
        self.queue = getAdapter(self.context, i.IQueue)
        self.queue.setUp()

class CronManager(AsyncManager):
    implementsOnly(i.ICronManager)
    adapts(IPloneSiteRoot, i.ICron)

    def __init__(self, context, cron):
        AsyncManager.__init__(self, context)
        self.portal = context
        self.cron = cron
        self.log = logging.getLogger(
            'collective.cron.CronManager')

    def get_job_infos(self,
                      begin_after=None,
                      job=None,
                      context=None,
                      *args,
                      **kwargs):
        try:
            cron_first_in_args = self.cron == args[0]
        except:
            cron_first_in_args = False
        if job is None:
            job = self.queue.job
        if ((not cron_first_in_args)
            and (job == self.queue.job)):
            args = (self.cron,) + args
        return self.queue.get_job_infos(
            begin_after,
            job,
            context,
            *args,
            **kwargs)

    def register_job(self, begin_after=None, force=False):
        ret = False
        cron = self.cron
        if begin_after is None and not force:
            begin_after = self.cron.next
        job_infos = self.get_job_infos(begin_after)
        self.queue.cleanup_before_job(job_infos, force=force)
        if ((not self.queue.is_job_present(job_infos))
            and ((begin_after is not None) or force)
            and cron.activated
            and cron.crontab.activated):
            msg = 'Registering a new job: %s' % repr(cron)
            if begin_after:
                msg += ' | schedule time: %s' % begin_after
            self.log.warn(msg)
            ret = self.queue.register_job(job_infos)
        return ret

    def remove_jobs(self, job_infos=None):
        if job_infos is None:
            job_infos = self.get_job_infos()
        self.queue.remove_jobs(job_infos)

    def register_or_remove(self, force=False):
        activated, ret =  None, None
        if self.cron.activated and self.cron.crontab.activated:
            # we maybe just actovated the job
            # starting a loop to make the cron
            activated = True
            ret = self.register_job(force=force)
        else:
            # we have deactivated the job or cancel the schedulation
            # remove the job from the queue !
            activated = False
            ret = self.remove_jobs()
        return activated, ret


class CrontabManager(AsyncManager):
    implementsOnly(i.ICrontabManager)
    adapts(IPloneSiteRoot, i.ICrontab)

    def __init__(self, context, crontab):
        AsyncManager.__init__(self, context)
        self.portal = context
        self.crontab = crontab
        self.log = logging.getLogger(
            'collective.cron.CrontabManager')

    def is_job_to_be_removed(self, item):
        ret = False
        try:
            same_path = item['context'] == self.context
            try:
                is_cron =  item['args'][4] == runJob
            except: # pragma: no cover
                is_cron = False
            try:
                valid_uid = item['args'][5].uid in self.crontab.crons
            except Exception, ex: # pragma: no cover
                valid_uid = False
            if is_cron and same_path and not valid_uid:
                ret = True
        except Exception, ex: # pragma: no cover
            ret = False
        return ret

    def synchronize_crontab_with_queue(self):
        deleted, jobs = [], []
        # mayby cleanup unrelated jobs
        for job in self.queue.get_job_infos_from_queue():
            if self.is_job_to_be_removed(job):
                job['begin_after'] = None
                self.queue.remove_jobs(job)
                deleted.append(job)
        # register all the crontab jobs
        for scron in self.crontab.crons:
            cron = self.crontab.crons[scron]
            cronadapters = getAdapters(
                (self.context, cron), i.ICronManager)
            for cronaname, crona in cronadapters:
                activated, _ = crona.register_or_remove()
                jobs.append(
                    {'activated':activated, 'cron':cron})
        return {"jobs":jobs, "deleted": deleted,}


@adapter(i.IModifiedCrontabEvent)
def do_syncronize_on_mod(event):
    plone = getSite()
    evt = e.CrontabSynchronisationEvent(plone, event.object)
    notify(evt)


@adapter(i.ICrontabSynchronisationEvent)
def do_synchronize(event):
    plone, crt = event.object, event.crontab
    activated = []
    for cronaname, crona in getAdapters(
        (plone, crt), i.ICrontabManager):
        ret = crona.synchronize_crontab_with_queue()
        activated.append(ret)
    return activated


@adapter(i.IServerRestartEvent)
def server_restart(event):
    log = logging.getLogger('collective.cron.server_restart')
    ppath = '/'.join(event.object.getPhysicalPath())
    jobs = OrderedDict()
    event = e.CrontabSynchronisationEvent(
        event.object, event.crontab)
    activateds = do_synchronize(event)
    for activated in activateds:
        for item in activated['jobs']:
            jobs[item['cron'].uid] = item
    for sitem in jobs:
        item = jobs[sitem]
        if item['activated']:
            log.info('%s: Re activated %s' % (ppath, item['cron']))

#class run_job(grok.View):
#    grok.context(i.IBackend)
#    def render(self):
#        messages = IStatusMessage(self.request)
#        try:
#            a = i.IBackendJobManager(self.context)
#            job = a.register_job(force=True)
#            messages.addStatusMessage(_( u"Job queued", ), type="info")
#        except Exception, ex:
#            messages.addStatusMessage(
#                _(u"Job failed to be queued: ${ex}", mapping={"ex":ex}),
#                type="error"
#            )
#        return self.response.redirect(
#            self.context.absolute_url()
#        )
#class View(dexterity.DisplayForm):
#
#    def next_runtime(self):
#        b = self.context
#        manager = i.IBackendJobManager(b)
#        j = manager.get_job_present()
#        d = None
#        if j is not None:
#            d = j._begin_after
#        sstr = _('NOW')
#        if d is not None:
#           pv = b.restrictedTraverse('@@plone')
#           sstr = pv.toLocalizedTime(d, long_format=True)
#        return sstr

# vim:set et sts=4 ts=4 tw=80:
