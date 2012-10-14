#!/usr/bin/env python
# -*- coding: utf-8 -*-
__docformat__ = 'restructuredtext en'

from zope.interface import (Interface,
                            Attribute,
                            implements,
                            implementedBy,
                            classProvides,
                            invariant,)
from zope import schema
from zope.schema import vocabulary
from collective.cron import MessageFactory as _
from collective.cron.utils import croniter
from zope.component.interfaces import IObjectEvent
from collective.cron.utils import asbool

from zope.interface import Invalid

try:
    import json
except: # pragma: no cover
    import simplejson as json


class InvalidObject(Exception): pass
class InvalidLog(InvalidObject): pass
class InvalidCron(InvalidObject): pass
class InvalidCrontab(InvalidObject): pass
class CronFormatError(Invalid): pass

class RegistryCrontabNotReady(Exception):pass
class AsyncQueueNotReady(Exception):pass



RESULTS_FOLDER = '--results--'
MANAGE_KEY = 'ccron.adapters.manager'

job_status = vocabulary.SimpleVocabulary([
    vocabulary.SimpleVocabulary.createTerm(0, '0', _(u'FAILURE')),
    vocabulary.SimpleVocabulary.createTerm(1, '1', _(u'OK')),
    vocabulary.SimpleVocabulary.createTerm(3, '3', _(u'NOTRUN')),
    vocabulary.SimpleVocabulary.createTerm(2, '2', _(u'WARN'))
])

def is_json_dict(value):
    if not value: return True
    try:
        v = json.loads(value)
        if not isinstance(v, dict):
            raise Exception()
    except:
        raise Invalid(
            'it is not a JSON dict'
        )
    return True


def cronFormatValidator(obj):
    data = obj
    if data is None:
        return True
    if data == '':
        return True
    try:
        croniter(data)
    except ValueError:
        raise CronFormatError('%s is invalid' % data)
    return True


class ConstrainedObject(object):
    def verify(self):
        errors = schema.getValidationErrors(
            [a for a in
             implementedBy(self.__class__)][0],
            self)
        if errors:
            raise schema.ValidationError(errors)


class ILayer(Interface):
    """Marker interface that defines a Zope 3 browser layer.
    """


class IAsyncManager(Interface):
    queue = Attribute(_('Jobs queue'))
    def get_job_infos(begin_after=None,
                      job=None,
                      context=None,
                      *args,
                      **kwargs):
        """Return the related jobs infos as a dict:
            {
            job:,
            context:,
            begin_after:,
            args:,
            kw:
                }
        """

class ICrontabManager(IAsyncManager):
    def is_job_to_be_removed(job):
        """Conditions:
            Job callable is runJob
            Belongs to our plone site
            related cron's uid is not in our crontab
        """
    def synchronize_crontab_with_queue():
        """Syncrhonize crontab with queue:

            - delete tasks which are not more in the crontab
            - add tasks created
            - Register other jobs if infos are changed
    """


class ICronManager(IAsyncManager):
    def register_or_remove(force=False):
        """Register or remove a job in the queue related to the backend
        activated status"""
    def register(begin_after=None, force=False):
        """Register a job in the queue

        @param datetime begin_after - Begin the job after date,
                                    - if None queue it directly
                                    - If the job begin_after is lower than a
                                      previously queued job, this is a NOOP
        @param boolean  force       force to queue the job even if there is
                                    always a job in the queue and that job is
                                    queued to be executed later that this one.
                                    """
    def remove_jobs(job_infos):
        """Remove a jobs in the queue related to the backend
        activated status"""


class IQueue(Interface):

    job = Attribute('Job wrapper responsible of '
                    'running, logging and reregistering jobs')
    jobs = Attribute('jobs in queue')
    queue = Attribute('queue of jobs')
    service = Attribute('service to queue jobs')
    def setUp(self):
        """setUp this queue"""
    def get_job_infos(begin_after=None,
                      job=None,
                      context=None,
                      *args,
                      **kwargs):
        """Return the related jobs infos :
            (job, context, begin_after, args, kw)
        """
    def register_job(job_infos=None):
        """Register a job matching job_infos in the queue
        Return True if job is submitted"""
    def cleanup_before_job(job_infos=None):
        """Cleanup any stale job:
            - if we force, we remove the job no mather what
            - if the job.begin_after job_infos
            - if the job.begin_after is previous to now
        """
    def remove_jobs(job_infos=None):
        """Remove jobs matching job_infos from the queue"""
    def is_job_present(job_infos=None):
        """Return True
        if the job infos relate to a job in the queue"""
    def is_job_running(job_infos=None):
        """Return True
        if the job infos relate to a job which is running"""
    def is_job_finished(job_infos=None):
        """Return True
        if the job infos relate to a job which is finished"""
    def is_job_pending(job_infos=None):
        """Return True
        if the job infos relate to a job which is finished"""


class ICrontabMarker(Interface):
    def unmark_crontab_aware(self):
        """Unmark an annoation on the
        async queue marking all plonesites
        using zc.async"""
    def mark_crontab_aware():
        """Mark an annoation on the
        async queue marking all plonesites
        using zc.async"""
    annotations = Attribute(_('Annnotations dict'))
    marked = Attribute(_('True is the zope instance is marker for this plone site'))
    key = Attribute(_('Annnotations key (site/zodbmounpoint_name)'))


class ICCRONUtils(Interface):
    """Backend log manager"""
    def log(date=None, status=u'OK', messages=None):
        """log a result on a results folder stocked on the context"""


class IJsonRegistryAware(Interface):
    def load(mapping=None):
        """(classmethod) load this object from the mapping settings
        mapping is either:

            - an instance of the object, it returns the instance untouched (NOOP)
            - a dict repr of the object
            - a json encodable representation
              of the previous dict

        """

    def dump():
        """Serialise this object in a mapping usable by klass.load"""


class ILog(IJsonRegistryAware):
    date   = schema.Datetime(title=_(u"The log date"), required=True,)
    status = schema.Choice(
        title=_(u"Status (OK|ERROR|WARN)"),
        default=None,
        vocabulary=job_status
    )
    messages = schema.List(
        title=_(u"errors"),
        required=False,
        value_type=schema.Text(title=_(u'Text message'))
    )
    sdate    = Attribute(_("date as a string"))
    sstatus  = Attribute(_("status title"))

    def load(data):
        """Load a log from a mapping
        {
            "date": string datetime %Y-%m-%d %H:%M:%S',
            "status": integer (status),
            "messages": string or list of string
        }
        """


class ICron(IJsonRegistryAware):
    crontab = schema.Object(Interface, title=_(u"Related Crontab"), required=True) # type will be set later
    uid = schema.TextLine(title=_(u"Unique task identifier"), required=True)
    name = schema.TextLine(title=_(u"Name of the task"), required=True)
    user = schema.TextLine(
        title=_(u"UserID the task will run as"),
        required=False, default=None,)
    activated = schema.Bool(title=_(u"Activated"), required=False,default=True)
    logs_limit = schema.Int(title=_(u"The logs limit (max: 25) "), default=3, max=25, required=True,)
    periodicity = schema.TextLine(
        title=_(u"How to repeat the job (CRON format)"),
        constraint = cronFormatValidator, required=True)
    logs = schema.List(
        title=_(u'Logs'),
        required = False,
        value_type=schema.Object(ILog, title=_(u'log'))
    )
    environ = schema.Dict(title=_(
        u"Configuration data to store with the task. "
        "For example a json encoded string."), required=False)
    next = Attribute(_(u"Get next job execution time"))
    snext = Attribute(_(u"Get next job execution time as a string representation"))
    last = Attribute(_("Last log logs"))
    last_date     = Attribute(_("Last log.date in logs"))
    slast_date     = Attribute(_("Alias to slast"))
    slast  = Attribute(_("Last log.date in logs as a string"))
    last_status   = Attribute(_("Last log.status in logs"))
    last_messages = Attribute(_("Last log.messages in logs"))

    def load(data):
        """Load a cron from a mapping:
            {
            "uid": UID of thje cron,
            "name": name of thje cron,
            "periodicity": periodicity of the cron
            "activated": activation status,
            "logs": list of logs data to load see Log.load or log instances
            "environ": configuration setting,
            }

        """

class ICrontab(IJsonRegistryAware):
    read_only = schema.Bool(title=_('readonly mode'), default=False)
    activated = schema.Bool(
        title=_('Global crontab activation switch'),
        default=True
    )
    crons = schema.Dict(
        title=_(u'Crons (access based on task uuid)'),
        value_type=schema.Object(ICron, title=_(u'cron'))
    )
    def save():
        """ save the crontab back to the registry"""

    def by_name(name):
        """Return all tasks registered with that name"""

    def by(uid=None,
           name=None,
           activated=None,
           periodicity=None):
        """Return all tasks registered
        matching the filters"""

    def load(data=None):
        """ We accept for sdata either:

        - if sdata isNothing, we will fallback to the strings recorded in the registry
        - If you try to register two cron with same uid, only one will survive
        - A list of either:

            - json encoded cron strings mappings
            - python dictionnary representation this cron
            - cron instances

        the JSON/List looks like
        [
            CRON STRUCTURE MAPPING, See Cron.load
            CRON STRUCTURE MAPPING2
        ]

        """


# constraint crontab to be a crontrab
ICron['crontab'].schema = ICrontab
class IRegistryCrontab(Interface):
    """Plone.app.registry backend for the crontab persistence"""
    activated = schema.Bool(
        title=_('Global crontab activation switch'),
        default=True
    )
    crontab = schema.List(
        title=_(u'Crons'),
        value_type=schema.Text(title=_(u'JSON repr of a cron')),
    )


class ICrontabRegistryManager(Interface):
    read_only = ICrontab['read_only']
    crontab = IRegistryCrontab['crontab']
    activated = IRegistryCrontab['activated']
    def save_cron(cron):
        """Save only this cron"""
    def save():
        """Save the full crontab"""

class IExportImporter(Interface):
    context = Attribute(_('plonesite'))
    crontab = Attribute(_('crontab'))
    def do_export():
        """Exports cron to Generic setup XML (return stringio)"""
    def dp_import(xmlfile):
        """Import cron from Generic setup XML"""


class IJobRunner(Interface):
    """Mixin for job runners"""
    def run(self):
        """run the job."""

class IAnnotedQueue(Interface):
    queue = Attribute(_('Async queue'))
    annotations = Attribute(_('annotations'))

class IStartedCronJobEvent(IObjectEvent):
    object = Attribute(_('plonesite'))
    cron = Attribute(_('cron'))

class IFinishedCronJobEvent(IObjectEvent):
    object = Attribute(_('plonesite'))
    cron = Attribute(_('cron'))
    log = Attribute(_('Run log'))

class IModifiedCrontabEvent(IObjectEvent):
    crontab = Attribute(_('crontab'))

class IModifiedCrontabEvent(IObjectEvent):
    object = Attribute(_('crontab'))
    cron = Attribute(_('cron'))

class IServerRestartEvent(IObjectEvent):
    object = Attribute(_('plonesite'))
    crontab = Attribute(_('crontab'))

class ICrontabSynchronisationEvent(IObjectEvent):
    object = Attribute(_('crontab'))

class ICrontabCronSynchronisationEvent(IObjectEvent):
    object = Attribute(_('crontab'))
    cron = Attribute(_('cron'))

# vim:set et sts=4 ts=4 tw=80:
