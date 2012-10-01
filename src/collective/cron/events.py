#!/usr/bin/env python
# -*- coding: utf-8 -*-
from zope.interface import implements
from zope.component.interfaces import ObjectEvent
from collective.cron import interfaces as i

class StartedCronJobEvent(ObjectEvent):
    implements(i.IStartedCronJobEvent)
    def __init__(self, object, cron):
        ObjectEvent.__init__(self, object)
        self.cron = cron

class FinishedCronJobEvent(ObjectEvent):
    implements(i.IFinishedCronJobEvent)
    def __init__(self, object, cron):
        ObjectEvent.__init__(self, object)
        self.cron = cron

class ModifiedCrontabEvent(ObjectEvent):
    implements(i.IModifiedCrontabEvent)
    def __init__(self, object):
        ObjectEvent.__init__(self, object)

class ServerRestartEvent(ObjectEvent):
    implements(i.IServerRestartEvent)
    def __init__(self, object, crontab):
        ObjectEvent.__init__(self, object)
        self.crontab = crontab

class CrontabSynchronisationEvent(ObjectEvent):
    implements(i.ICrontabSynchronisationEvent)
    def __init__(self, object, crontab):
        ObjectEvent.__init__(self, object)
        self.crontab = crontab

# vim:set et sts=4 ts=4 tw=80:
