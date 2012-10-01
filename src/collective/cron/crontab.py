#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import pytz
import time
import uuid
__docformat__ = 'restructuredtext en'
from zope.schema.fieldproperty import FieldProperty
from zope.interface import (Interface,
                            Attribute,
                            implements,
                            implementedBy,
                            classProvides,
                            invariant,)

from zope import schema
from ordereddict import OrderedDict
from pprint import pformat
import datetime
try:
    import json
except: # pragma: no cover
    import simplejson as json
from zope.component import adapts, getUtility, getAdapters, getMultiAdapter, queryMultiAdapter
from zope.event import notify
from collective.cron.utils import croniter, to_utc
from z3c.form.object import registerFactoryAdapter

from collective.cron import MessageFactory as _
from collective.cron import events as e
from collective.cron.interfaces import (
    ConstrainedObject,
    ICrontab,
    ILog,
    InvalidObject,
    ICrontabRegistryManager,
    InvalidCrontab,
    InvalidCron,
    IJobRunner,
    InvalidLog,
    ICCRONUtils,
    ICron,
    job_status,
    IRegistryCrontab,
    IJobRunner,
    ICronManager,
)
from collective.cron.utils import asbool
from Products.CMFPlone.interfaces.siteroot import IPloneSiteRoot

class NoSuchCron(Exception):pass

datefmt = '%Y-%m-%d %H:%M:%S'

def find_term(voc, value):
    ret = None
    ret = voc.by_value.get(value)
    if ret is None:
        ret = voc.by_token.get(value)
    if ret is None:
        try:
            ret = [a for a in voc if a.title == value][0]
        except IndexError, ex: # pragma: no cover
            pass
    return ret


class Runner(object):
    implements(IJobRunner)
    adapts(IPloneSiteRoot, ICron)

    def __init__(self, context, cron):
        self.context = context
        self.cron = cron

    def run(self): # pragma: no cover
        raise NotImplementedError('implement me!')

def runJob(context, cron):
    logger = logging.getLogger('backend/runJob')
    status = find_term(job_status, 'NOTRUN').value
    bpath = context.getPhysicalPath()
    messages = []
    try:
        notify(e.StartedCronJobEvent(context, cron))
        logger.debug('Run job: %s/%s' % (cron.name, cron.uid))
        if cron.activated and cron.crontab.activated:
            adapter = queryMultiAdapter(
                (context, cron), IJobRunner, name=cron.name)
            if adapter is not None:
                ret = adapter.run()
                if ret is not None:
                    if not isinstance(ret, list):
                        ret = [ret]
                    messages.extend(ret)
                status = find_term(job_status, 'OK').value
                # if we have had messages without exceptions, those
                # are just warnings or pieces of information
                if len(messages):
                    status = find_term(job_status, 'WARN').value
        notify(e.FinishedCronJobEvent(context, cron))
    except Exception, ex:
        messages.append('%s' % ex)
        status = find_term(job_status, 'FAILURE').value
    cron.log(status=status, messages=messages)
    # fire the crontabmodified event which in turn will reregister the job
    cron.save()
    # if the job is not regitered throught the event, try to Re-register it
    manager = getMultiAdapter((context, cron), ICronManager)
    if not manager.queue.is_job_present(): # pragma: no cover
        manager.register_or_remove()
    return status, messages, cron.uid, bpath


class Log(ConstrainedObject):
    implements(ILog)
    date = FieldProperty(ILog["date"])
    status = FieldProperty(ILog["status"])
    messages = FieldProperty(ILog["messages"])
    def __eq__(self, other):
        ret = False
        try:
            if self is other:
                ret = True
            elif ((self.date == other.date)
                and (self.status == other.status)
                and (self.messages == other.messages)
               ):
                ret = True
        except Exception, e:
            ret = False
        return ret

    def __init__(self,
             date=None,
             status=None,
             messages=None):
        self.date = date
        self.status = status
        if messages is None: # pragma: no cover
            messages = []
        if messages is not None and not isinstance(messages, list): # pragma: no cover
            messages = [messages]
        for i in range(len(messages)):
            message = messages[i]
            if not isinstance(message, unicode):
                messages[i] = unicode(message)
        self.messages = messages

    def __repr__(self):
        srepr = u'log: %s' % (self.sdate)
        status = self.sstatus
        if status:
            srepr += u'/%s' % status
        if len(self.messages):
            srepr += '+'
        return srepr.strip()

    @property
    def sstatus(self):
        status = job_status.by_value.get(self.status, '')
        if status:
            status = status.title
        return status

    @property
    def sdate(self):
        ret = self.date
        if isinstance(ret, datetime.datetime):
            ret = ret.strftime(datefmt)
        if not ret: ret = ''
        return ret

    def dump(self):
        dt = ''
        if self.date:
            dt = self.date.strftime(datefmt)
        data = {
            'date': dt,
            'status': self.status,
            'messages': self.messages,
        }
        return data

    @classmethod
    def load(cls, item):
        """See interface."""
        if isinstance(item, Log): return item
        if not isinstance(item, dict): return
        try:
            dt = datetime.datetime.strptime(
                item.get('date', None),
                datefmt
            )
        except: # pragma: no cover
            # skip malformed date records
            return
        status = item.get('status', None)
        messages = item.get('messages', [])
        if not isinstance(messages, list):
            messages = [messages]
        messages = [unicode(a)
                    for a in messages]
        return cls(date=dt,
                status=status,
                messages=messages)
registerFactoryAdapter(ILog, Log)

class Cron(ConstrainedObject):
    implements(ICron)
    uid = FieldProperty(ICron['uid'])
    name = FieldProperty(ICron['name'])
    activated = FieldProperty(ICron['activated'])
    periodicity = FieldProperty(ICron['periodicity'])
    logs = FieldProperty(ICron['logs'])
    environ = FieldProperty(ICron['environ'])

    def __eq__(self, other):
        return self._eq__mixin(other)

    def similar(self, other):
        return self._eq__mixin(other, from_crontab=True)

    def _eq__mixin(self, other, from_crontab = False):
        """We assume that a cron is the same of another if they
        share all the same infos but :

            - the logs

        """
        ret = False
        try:
            if from_crontab:
                same_crontab = True
            else:
                same_crontab = self.crontab is other.crontab
                if not same_crontab: # pragma: no cover
                    same_crontab = self.crontab == other.crontab
            if self is other:
                ret = True
            elif ((same_crontab)
                and (self.uid == other.uid)
                and (self.name == other.name)
                and (self.activated == other.activated)
                and (self.environ == other.environ)
               ):
                ret = True
        except Exception, e:
            ret = False
        return ret

    def __init__(self,
                 uid=None,
                 name=None,
                 user=None,
                 activated=None,
                 periodicity=None,
                 logs=None,
                 environ=None,
                 crontab=None,):
        if not uid:
            uid = self.get_uid()
        self.uid = unicode(uid)
        self._crontab = None
        self.crontab = crontab
        self.name = name
        self.user = user
        self.periodicity = periodicity
        self.activated = asbool(activated)
        if logs is not None and isinstance(logs, list):
            logs = [Log.load(l) for l in logs]
        self.logs = logs
        # 2 pass validation for environ 
        if not environ:
            environ = {}
        self.environ = environ
        if isinstance(self.environ, basestring): # pragma: no cover 
            environ = json.loads(self.environ) 
        if self.logs is None:
            self.logs = []

    def _get_crontab(self):
        return self._crontab
    def _set_crontab(self, value):
        self._crontab = value
        if self._crontab is not None:
            self._crontab.crons[self.uid] = self
        return self._crontab
    crontab = property(_get_crontab, _set_crontab)

    def __repr__(self):
        activated = (False==bool(self.activated)) and 'OFF' or 'ON'
        if bool(self.environ):
            env = ' %s' % pformat(self.environ)
        else:
            env = ''
        if self.logs:
            logs = ' (%s logs)' % len(self.logs)
        else:
            logs = ''
        nextr = ''
        if self.activated:
            nextr = ':%s' % self.snext
        srepr = ('cron: %(name)s/%(uid)s [%(a)s%(n)s]%(logs)s%(environ)s' % dict(
            uid=self.uid,
            name=self.name,
            a=activated,
            logs = logs,
            environ = env,
            n=nextr,
        )).strip()
        if isinstance(srepr, unicode):
            srepr = srepr.encode('utf-8')
        return srepr

    def log(self, date=None, status=None, messages=None):
        if status is None: status = u'OK'
        if not date: date = datetime.datetime.now()
        if not messages: messages = []
        r = Log(date, status, messages)
        self.logs.append(r)
        return r

    def get_uid(self):
        """As the uuid1 relies on local hour wait a little to avoid
        collisions"""
        time.sleep(0.01)
        return unicode(uuid.uuid1().hex)

    def change_uid(self):
        self.uid = self.get_uid()

    @property
    def snext(self):
        ret = ''
        if self.activated:
            val = self.next
            if not val: # pragma: no cover
                ret = 'NO NEXT TIME'
            else:
                ret = val.strftime(datefmt)
        return ret

    @property
    def next(self):
        log = logging.getLogger('Backend.next')
        now = datetime.datetime.now() + datetime.timedelta(minutes=1)
        now = datetime.datetime.now()
        try:
            unextr = to_utc(croniter(self.periodicity, start_time=now).get_next())
        except Exception, e: # pragma: no cover
            unextr = None
        return unextr

    @property
    def last(self):
        l = None
        if self.logs:
            l = self.logs[-1]
        return l

    @property
    def last_messages(self):
        ret, l = None, self.last
        if l:
            ret = l.messages
        if not ret: ret = []
        return ret

    @property
    def last_date(self):
        ret, l = None, self.last
        if l:
            ret = l.date
        return ret

    @property
    def slast_date(self): # pragma: no cover
        return self.slast

    @property
    def slast(self):
        ret, l = '', self.last
        if l:
            ret = l.sdate
        return ret

    @property
    def last_status(self):
        ret, l = None, self.last
        if l:
            ret = l.status
        return ret

    def dump(self):
        data = {
            'uid': self.uid,
            'name': self.name,
            'user': self.user,
            'activated': self.activated,
            'periodicity': self.periodicity,
            'logs': [l.dump() for l in self.logs],
            'environ': self.environ,
        }
        return data

    def save(self):
        if self.crontab is not None:
            self.crontab.save_cron(self)

    @classmethod
    def load(cls, data, crontab=None):
        """See interface."""
        if isinstance(data, Cron): return data
        uid = data.get('uid', None)
        name = unicode(data['name'])
        periodicity = data.get('periodicity', None)
        user = data.get('user', None)
        if periodicity: periodicity=unicode(periodicity)
        activated = data.get('activated', False)
        environ = data.get('environ', {})
        logs = []
        if not isinstance(data.get('logs', None), list):
            data['logs'] = []
        for item in data['logs']:
            try:
                if isinstance(item, Log):
                    l = item
                else:
                    l = Log.load(item)
            except schema.ValidationError: # pragma: no cover
                l = None
            if l:
                logs.append(l)
        cron = cls(crontab=crontab,
                   uid=uid,
                   name=name,
                   user=user,
                   activated=activated,
                   periodicity=periodicity,
                   logs=logs,
                   environ=environ,)
        return cron

registerFactoryAdapter(ICron, Cron)

class Crontab(ConstrainedObject):
    """basically to load and save the crontab programmmatically, you ll have to do::

        >>> crontab = Crontab.load()
        ...  # by default load what is stored in registry
        ...  # Then play with the crontab.crons
        >>> crontab.save() # goes back to registry
    """
    implements(ICrontab)
    @property
    def manager(self):
        """Must be a property to allow the cronjob to persist without databases cross references"""
        return ICrontabRegistryManager(self)

    crons = FieldProperty(ICrontab['crons'])
    activated = FieldProperty(ICrontab['activated'])
    _read_only = FieldProperty(ICrontab['read_only'])

    def _get_read_only(self):
        return self._read_only
    def _set_read_only(self, value):
        self._read_only = value
        self.manager.read_only = value
    read_only = property(_get_read_only, _set_read_only)

    def __eq__(self, other):
        """We assume that a cron is the same of another if they
        share all the same infos but the logs"""
        ret = False
        try:
            if self is other:
                ret = True
            else:
                scrons = [self.crons[o] for o in self.crons]
                ocrons = [other.crons[o] for o in other.crons]
                same_crons = False
                if len(scrons) == len(ocrons):
                    for i, c in enumerate(scrons):
                        if not c._eq__mixin(
                            ocrons[i],
                            from_crontab=True): # pragma: no cover
                            same_crons = False
                            break
                        else:
                            same_crons = True
                if ((same_crons)
                    and (self.activated == other.activated)
                   ) :
                    ret = True
        except Exception, e:
            ret = False
        return ret

    def __init__(self, crons=None, activated=True, read_only=False):
        self.read_only = read_only
        self.activated = activated
        if crons is None:
            crons = OrderedDict()
        self.crons = crons

    def add_cron(self, cron):
        tries = 60
        while tries:
            tries -= 1
            if cron.uid in self.crons:
                cron.change_uid()
            if not cron.uid in self.crons:
                break
        cron.crontab = self
        self.crons[cron.uid] = cron

    def by_name(self, name):
        """See interface."""
        return self.by(name=name)

    def by_uid(self, uid):
        """See interface."""
        try:
            return self.by(uid=uid)[0]
        except IndexError, e:
            raise NoSuchCron('No such cron with uid %s' % uid)

    def by(self,
           uid=None,
           name=None,
           activated=None,
           periodicity=None):
        """See interface."""
        crons = []
        filters = {
            'uid': uid,
            'name': name,
            'activated': activated,
            'periodicity': periodicity,
        }
        for f in filters.keys():
            if filters[f] is None:
                del filters[f]
        for i in self.crons:
            ci = self.crons[i]
            matched = False
            for f in filters:
                val = getattr(ci, f, None)
                if (val is not None
                    and val==filters[f]):
                    matched = True
                else:
                    matched = False
                    break
            if matched:
                crons.append(ci)
        return crons

    def save(self):
        self.manager.save()
        notify(e.ModifiedCrontabEvent(self))

    def save_cron(self, cron):
        self.manager.save_cron(cron)
        notify(e.ModifiedCrontabEvent(self))

    def dump(self):
        data = [self.crons[uid].dump()
                for uid in self.crons]
        return data

    @classmethod
    def load(cls,
             sdata=None,
             activated = True,
             read_only = False,):
        """See interface."""
        crt = cls()
        crt.read_only = read_only
        activated = activated
        if isinstance(sdata, Crontab): return sdata
        if sdata is None:
            c_settings = crt.manager
            if not c_settings.crontab:
                crontab = []
            else:
                crontab = c_settings.crontab
            sdata = crontab
            activated = c_settings.activated
        if isinstance(sdata, basestring):
            try:
                sdata = json.loads(sdata)
                if not isinstance(sdata, (dict, list)): # pragma: no cover
                    raise ValueError()
            except ValueError, e:
                raise InvalidCrontab()
        crons = OrderedDict()
        if isinstance(sdata, dict):
            nsdata = []
            for k in sdata:
                nsdata.append(sdata[k])
            sdata = nsdata
        if not isinstance(sdata, list): # pragma: no cover
            raise ValueError('%s is not s list' % sdata)

        for scron in sdata:
            if isinstance(scron, basestring):
                try:
                    # maformed string must be skipped
                    scron = json.loads(scron)
                except:
                    continue
            if isinstance(scron, dict):
                try:
                    scron = Cron.load(scron)
                except schema.ValidationError: # pragma: no cover
                    scron = None
            if isinstance(scron, Cron):
                crons[scron.uid] = scron
                scron.crontab = crt
        crt.read_only = read_only
        crt.crons = crons
        crt.activated = activated
        return crt

registerFactoryAdapter(ICrontab, Crontab)


# vim:set et sts=4 ts=4 tw=80:
