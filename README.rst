Introduction
============

.. contents::

collective.cron is a cron-like asynchronous tasks system based on top of plone.app.async and plone.app.registry.
The implementation does not have for now all the bells and wistles of a nice UI.
However the simple interface does all the stuff and the underlying job manager works reliably.

Finaly, you can register your tasks easily.


Note that at the moment, we have 100% test coverage. This do not prevent bugs altogether, but it keeps us from making big mistakes.

The design is modern and modular, imagine that you can even easily change from plone.app.async to another job system.

The buildout infrastructure
===========================
- base.cfg                -> base buildout informations
- buildout.cfg            -> base buildout for the current plone version
- test-4.0.x.cfg          -> test buildout for plone4.0
- test-4.1.x.cfg          -> test buildout for plone4.1
- test-4.2.x.cfg          -> test buildout for plone4.2

The most important things are in base.cfg.
If you plan to integrate collective.cron to your buildout, please refer to the plone.app.async documentation.

- For now we use the unreleased version of plone.app.async : https://github.com/plone/plone.app.async

Note for tests
==============
- Tests can unpredictibly crash because of monkey patchs to datetime.
  This is a false positive. Just relaunch them if you see something similar ::

      ConflictError: database conflict error (oid 0x2549d9dd3cf6b59b, serial this txn started with 0x0399e4b3adb993bb 2012-10-14 09:23:40.716776, serial currently committed 0x0399e4b3ae733c77 2012-10-14 09:23:40.886752)

collective.cron 1.0 => collective.cron 2.0
==========================================
- in 1.0, each cron task was a content.
  This was then tedious to replicate and maintain accross multiple instances and plone versions.
  One of the goal of collective.cron 2.0 is to avoid at most to have persistance, specially specialized contents to minimize all the common migration problems we have with an objects database.
  Thus a choice has been made to heavily use plone.app.registry as a configuration backend.

- Thus, there is no migration prepared from collective.cron 1.0 to 2.0
  It is up to you to do it.
  Specially, you will have to clean the database of all specific collective.cron 1.0 based & persistent content before upgrading.
  Indeed, as the design of tasks is really different, we can't do any automatic migration.

- First with collective.cron 1.x in your buildout

        - Search, record settings then delete all IBackend content
        - Delete all jobresults & persistent contents
        - Cleanup all the zc.async queue

- Next, deactivate collective.cron 1.x and activate collective.cron 2.x in your buildout

    - Adapt your adapters and content types to work with collective.cron 2.0 (inputs/mark items to work on)
    - add equivalent crons records to the crontab setting of the backends job

Credits
========
Companies
---------
|makinacom|_

  * `Planet Makina Corpus <http://www.makina-corpus.org>`_
  * `Contact us <mailto:python@makina-corpus.org>`_

.. |makinacom| image:: http://depot.makina-corpus.org/public/logo.gif
.. _makinacom:  http://www.makina-corpus.com

Authors
-------

- kiorky  <kiorky@cryptelium.net>

Contributors
------------

Repository
==========

- `github <https://github.com/collective/collective.cron>`_


Design
======
- collective.cron lets you register crons which run periodically in your system.
- Each plone site has a crontab.
- This crontab is used by many components to execute the cron jobs.
- There is a central dashboard which will list all tasks registered on the site crontab.
- The tasks configuration is based on plone.app.registry but is designed to be replaceable (component).
- The tasks execution is based on plone.app.async but is designed to be also replaceable (component).

- The cron manager will ensure to restore all cron jobs for all plone sites at zope restart.

Crontab
-------
A crontab is the collection of all cron registered to a plone site.
A crontab can be (de)activated globally.
Each crontab sub element (the crontab, the crons & associated logs) defines a dump method which creates a JSON representation of the object.

The major attributes for a crontab are:

    - crons: An ordered dict of crons. Key is the cron uid
    - activated: globally power switch for the crontab
    - manager: the manager is responsible for the crontab persistence
    - save(): save the crontab
    - save_cron(cron): save the cron

When a crontab is saved, it emits a ``ModifiedCrontabEvent``.

Cron
----
The major attributes for a cron are:

    - **name**: will be the queried name to search jobs
    - **periodicity**: give the next time execution
    - **environ**: An optionnal jsonencoded mapping of values which will be given to the task
    - **logs_limit**: logs to keep (default : 5, limit : 25)
    - uid: internal id for the crontab machinery
    - user: the user the task will run as, its up to you to make the task run as this user
    - activated: the activation status of the cron
    - logs: give the last logs of the cron prior executions from most recent to older
    - crontab: A possibly null reference to the parent crontab

A note on the user which is only **a stocked value**. you can see ``collective.cron.utils.su_plone`` to help you switch to that user.
IT IS UP TO YOU TO SWITCH TO THAT USER **IN YOUR JOBRUNNER**.

Log
---
The major attributes for a log are:

    - date: date of logging
    - status: status ::= NOTRUN | FAILURE | WARN | OK
    - message: the logs

Crontab registry manager
------------------------
Based on top of plone.app.registry, collective.cron record the crontab current status in the site registry.
It adapts a crontab.

    - activated: boolean switch status of the crontab
    - cronsettings: the raw manager settings (.crontab, .activated)
    - crons: list of serialized strings representations of the crons
    - read_only: if true, changes will be a NOOP

When a record is touched (added, edited, removed), events are fired to syncronize the queue.

Crontab manager
---------------
This component is responsible when a CrontabSynchronisationEvent is fired to synchronise the crontab with the job queuing system.
It will remove unrelated jobs and schedule new jobs.
It adapts a plonesite and a crontab.

When the crontab is saved emits a ``ModifiedCrontabEvent`` which in turns is redirected as a ``CrontabSynchronisationEvent`` to let the manager synchronize the queue.

When the server restarts, a ``ServerRestartEvent`` is called to re-register any cron job that would have been wiped from the queue.

Cron manager
------------
This component is responsible for the execution and presence in the queue of a particular cronjob. It can register or remove the job execution of a cron.
This is a friendly proxy to the "Queue manager".

It adapts a plonesite and a cron.

When a cronjob is registered, the job queued is a cron jobrunner wrapper responsible for:

    - Sending a ``StartedCronJobEvent``
    - Running the relevant JobRunner (a named adapter adapting the plonesite, and the cron)
    - Sending a ``FinishedCronJobEvent``
    - logging the execution
    - Scheduling the next execution

JobRunner
---------
A cron jobrunner is a named adapter which:
    - adapts the plonesite and the current cron
    - implements IJobRunbner, and specially defines a **run** method.

A base class exists in collective cron, just inherit from it.
This is a complicated definition to have a class like this::

    from collective.cron import crontab
    class MyCronJob(crontab.Runner):
        def run(self):
            print "foo"

Registered in zcml like that::

    <adapter factory=".module.MyCronJob" name="mycronjob"/>

And then, you will have to register a cron called ``mycronjob`` in your plonesite.

Queue manager
-------------
This component will manage the jobs inside the job queue.
You will have enough methods to know for a specific cron if a job is present, what is its status...

You can also register, or delete items from the running queue
It adapts a plonesite.

Crontab Queue Marker (plone.app.async specific)
-----------------------------------------------
Responsible to mark infos in the async queue to make the reload of jobs at Zope restart possible.

Detailed documentation
======================
There are 3 ways to register tasks:

    - via the API
    - via the UI
    - via Generic Setup (profile)


