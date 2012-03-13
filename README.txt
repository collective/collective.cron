Introduction
============

plone.app.cron is a cron-like asynchronous tasks system based on top of plone.app.async.
It relies on a non released yet 'defer' branch of plone.app.async which give some control on jobs metadata, specially on the begin_after attribute.
The implementation  hasn't not for now all the bells and wistles of a nice UI the the underlying job manager works reliably.

Design
===========
- We have a central dashboard which will list all tasks registered on the site.

- From there, each cron task will be a content.
  plone.app.cron provide the base implementation in ``plone.app.cron.content.backend.Backend``.
  This content implement ``plone.app.interfaces.IBackend``.
  This content has some attributes:

    - Its name
    - The periodicity in the CRON Format : http://en.wikipedia.org/wiki/Crontab
    - Everything else that need to be a permanent setting.

  On the content view, you can:

    - Activate a job
    - Deactivate a job
    - Force a job run
    - View/Run other actions registered for the job registered through a viewlet.

- For all those content, you ll need to implemenent an adapter which adapts the backend and run the task.
  This adapter implement ``plone.app.interfaces.IJobRunner``.

- At the end of the job, the JobRunners manager will record the result informations (fail, warn or sucess) on a result folder on the backend.
  Those results implement ``plone.app.interfaces.IResult``.

- Those jobrunners are managed through a jobmanager.
  This one will poll and organizes jobs to plone.app.async and zc.async.
  It's job is to (un)register tasks.
  Of course, it will not submit more than once the same job specially with multiple time cron periodicities.
  This adapter implement ``plone.app.interfaces.IBackendJobManager``.

- plone.app.cron will also register the activated jobs on the zope restart if they are not anymore in the queue.

Add a task to the site
========================
There are no sample backend implementation in plone.app.cron, it's up to you to do
    The periodicity

The basic implementation details can be found and adapted from  ``plone/app/cron/tests/backend.py``. but to sumup, to add a cron-like task you need to:

    - Implement a dexterity content type: the backend with all the settings you need
    - Register it's FTI to the site through GenericSetup
    - Implement an adapter which do the "cron stuff"
    - Maybe, Make a viewlets to add actions links on the backend


