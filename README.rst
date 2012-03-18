Introduction
============

.. contents::

collective.cron is a cron-like asynchronous tasks system based on top of plone.app.async.
It relies on a non released yet branch of plone.app.async which give some control on jobs metadata, specially on the begin_after attribute.
The implementation hasn't not for now all the bells and wistles of a nice UI the the underlying job manager works reliably.

Design
===========
- We have a central dashboard which will list all tasks registered on the site.

- From there, each cron task will be a content.
  collective.cron provide the base implementation in ``collective.cron.content.backend.Backend``.
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

- collective.cron will also register the activated jobs on the zope restart if they are not anymore in the queue.

Add a task to the site
========================
There are no sample backend implementation in collective.cron, it's up to you to do
    The periodicity

The basic implementation details can be found and adapted from  ``collective.cron/tests/backend.py``. but to sumup, to add a cron-like task you need to:

    - Implement a dexterity content type: the backend with all the settings you need
    - Register it's FTI to the site through GenericSetup
    - Implement an adapt


The buildout infrastructure
=============================
- base.cfg                -> base buildout informations
- buildout.cfg            -> base buildout for the current plone version
- test-4.0.x.cfg          -> test buildout for plone4.0
- test-4.1.x.cfg          -> test buildout for plone4.1
- test-4.2.x.cfg          -> test buildout for plone4.2
- minitage.cfg            -> minitage variables overrider buildout

- minitage-buildout.cfg   -> minitage buildout wrappers
- minitage-test-4.0.x.cfg
- minitage-test-4.1.x.cfg
- minitage-test-4.2.x.cfg



The most important things are in base.cfg.
If you plan to integrate plone.app.cron to your buildout, please refer to the plone.app.async documentation.
However, those are some important things to do after plone.app.async buildout integration:

    - For now we uqse a special branch of plone.app.async : https://github.com/plone/plone.app.async/tree/davisagli-ui
    - we have set all important versions to pin inside the [versions] part

You can also refer to the tests buildouts and adapt for your needs



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
------------

- kiorky  <kiorky@cryptelium.net>

Contributors
-----------------


Repository
------------

- `GITHUB <https://github.com/collective/collective.cron>`_




