#!/usr/bin/env python
# -*- coding: utf-8 -*-
__docformat__ = 'restructuredtext en'

from zope.interface import Interface, Attribute
from zope import schema
from plone.directives import form
from collective.cron import MessageFactory as _
from zope.component.interfaces import IObjectEvent

class IBackendFinnishedJobEvent(IObjectEvent):pass
class IServerRestartEvent(IObjectEvent):pass

RESULTS_FOLDER = '--results--'

class IResult(form.Schema):
    date   = schema.Datetime(title=_(u"The result date"), required=False,)
    status = schema.TextLine(title=_(u"Status"), default=u'')
    errors = schema.List(title=_(u"errors"),
                         default = [],
                         required=False,
                         value_type=schema.TextLine(title=_(u'error'))
                        )

class IBackend(form.Schema):
    """Backend is a container containing job informations"""
    activated = schema.Bool(title=_(u"Activated"), default=True)
    periodicity = schema.TextLine(title=_(u"How to repeat the job (CRON format)"), required=False)
    def results_folder():
        """Get the results folder"""
    def getLastResult():
        """Last result object"""
    def getLastRun():
        """Last run time"""
    def getLastStatus():
        """Last run time"""
    def getLastErrors():
        """Last run errors"""
    def getResults():
        """Get the execution results."""
    def getDatas():
        """Get the job stored datas as a dict"""
    def next():
        """Get next job execution time"""

class IBackendJobManager(Interface):
    async = Attribute(_('Async Service'))
    queue = Attribute(_('Jobs queue'))
    def register_job(begin_after=None, force=False):
        """Register a job in the queue

        @param datetime begin_after - Begin the job after date,
                                    - if None queue it directly
                                    - If the job begin_after is lower than a
                                      previously queued job, this is a NOOP
        @param boolean  force       force to queue the job even if there is
                                    always a job in the queue and that job is
                                    queued to be executed later that this one.
                                    """
    def remove_jobs(job_infos=None):
        """Remove jobs from a particular backend from the queue"""
    def compare_job(job, job_infos=None):
        """Compare a job with the related job_infos"""
    def get_job_present(job_infos=None):
        """Get the next related job is the queue"""
    def is_job_present(job_infos=None):
        """Return True
        if the job infos relate to a job in the queue"""
    def is_job_running(job_infos=None):
        """Return True
        if the job infos relate to a job which is running"""
    def get_job_infos():
        """Return the related jobs infos :
            (job, context, begin_after, args, kw)
        """
    def register_or_remove():
        """Register or remove a job in the queue related to the backend
        activated status"""
    def mark_queue_plonesite_aware():
        """Mark in annotations of the the queue some
        informations to make the queue aware of the current
        plonesite to restart jobs on zope2 restart"""

class IJobRunner(Interface):
    """Mixin for job runners"""
    def run(self):
        """run the job."""

class ICCRONUtils(Interface):
    """Backend log manager"""
    def log(date=None, status=u'OK', errors=None):
        """log a result on a results folder stocked on the context"""
    def getFolder(id, title, context=None):
        """Get and create if not present the folder "id/Title"
        in the related context"""

class IBackendTitleCompl(Interface):
    def getTitleCompl():
        """get the title complement."""

class ICCRONContent(Interface):
    """Marker interface for gmb content types"""


# vim:set et sts=4 ts=4 tw=80:
