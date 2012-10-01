#!/usr/bin/env python
# -*- coding: utf-8 -*-
__docformat__ = 'restructuredtext en'
import logging
from zope.schema.fieldproperty import FieldProperty
from zope.interface import (implements,)
from zope.component import adapts, getUtility, adapter, getAdapters
from zope.site.hooks import getSite
from zope.event import notify
from plone.registry.interfaces import (
    IRecordAddedEvent,
    IRecordModifiedEvent,
    IRecordRemovedEvent,
)
from plone.registry.interfaces import IRegistry
from collective.cron.interfaces import (
    ICrontab,
    ICrontabRegistryManager,
    IRegistryCrontab,
    RegistryCrontabNotReady,
)
from collective.cron import crontab
from collective.cron import events as e

class CrontabRegistryManager(object):
    implements(ICrontabRegistryManager)
    adapts(ICrontab)
    read_only = FieldProperty(ICrontabRegistryManager["read_only"])
    def __init__(self, context):
        self.context = context
        self.read_only = getattr(self.context, 'read_only', True)

    @property
    def cronsettings(self):
        reg = getUtility(IRegistry)
        try:
            settings = reg.forInterface(IRegistryCrontab)
        except KeyError, ex:
            raise RegistryCrontabNotReady('Registry is not ready yet: %s' % ex)
        return settings

    def _get_crontab(self):
        if self.cronsettings.crontab is None:
            self.cronsettings.crontab = []
        return self.cronsettings.crontab
    def _set_crontab(self, value):
        if not self.read_only: # pragma: no cover  
            self.cronsettings.crontab[:] = value
    crontab = property(_get_crontab, _set_crontab)

    def _get_activated(self):
        return self.cronsettings.activated
    def _set_activated(self, value):
        if not self.read_only:
            self.cronsettings.activated = value
    activated = property(_get_activated, _set_activated)

    def dumps(self, value):
        return unicode(crontab.json.dumps(value))

    def loads(self, value):
        return crontab.json.loads(unicode(value))

    def save(self):
        if self.read_only:return
        for k in self.context.crons:
            self.save_cron(self.context.crons[k])
        # cleanup records which have no cron related
        delete = []
        for i, item in enumerate(self.crontab):
            data = self.loads(item)
            try:
                self.context.by_uid(
                    data.get('uid', None))
            except Exception, ex:
                delete.append(i)
        delete.sort()
        delete.reverse()
        for item in delete:
            self.crontab.pop(item)
        self.activated = self.context.activated

    def save_cron(self, cron):
        if self.read_only:return
        uid = cron.uid
        # search for an already serialized cron with same uid
        idx = None
        for i, c in enumerate(self.cronsettings.crontab):
            try:
                found = uid == self.loads(c).get('uid', None)
            except Exception, ex:
                found = False
            if found:
                idx = i
                break
        scron = self.dumps(cron.dump())
        if idx is not None:
            self.cronsettings.crontab.pop(idx)
        self.cronsettings.crontab.append(scron)

@adapter(IRegistryCrontab, IRecordModifiedEvent)
def synchronize_queue_edited(itema, itemb):
    plone = getSite()
    try:
        crt = crontab.Crontab.load()
        notify(
            e.CrontabSynchronisationEvent(
                plone, crt))
    except RegistryCrontabNotReady, ex: # pragma: no cover  
        pass

@adapter(IRegistryCrontab, IRecordAddedEvent)
def synchronize_queue_added(itema, itemb):
    try:
        plone = getSite()
        crt = crontab.Crontab.load()
        notify(
            e.CrontabSynchronisationEvent(
                plone, crt))
    except RegistryCrontabNotReady, ex:
        pass

@adapter(IRegistryCrontab, IRecordRemovedEvent)
def synchronize_queue_removed(itema, itemb): # pragma: no cover   
    try:
        plone = getSite()
        crt = crontab.Crontab.load()
        notify(
            e.CrontabSynchronisationEvent(
                plone, crt))
    except RegistryCrontabNotReady, ex: # pragma: no cover  
        pass

# vim:set et sts=4 ts=4 tw=80:
