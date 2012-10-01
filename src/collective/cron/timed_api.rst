
Manage (add, edit, remove, run) tasks via collective.cron API
--------------------------------------------------------------

setup
++++++++
::

    >>> import time
    >>> from collective.cron import interfaces as i
    >>> from collective.cron.testing import set_now
    >>> from collective.cron import crontab as mcrontab
    >>> from collective.cron import utils
    >>> import datetime, pytz
    >>> from zc.async.testing import wait_for_result
    >>> layer['crontab'].save()
    >>> import transaction
    >>> get_jobs = lambda:[a for a in layer['queue']]

Creation of a jobrunner
+++++++++++++++++++++++++++
We will define a cronjob to execute on the next scheduled tasks behalf.
Here we register global adapters, but you can of course register local adapters on a specific plonesite and they will be taken up::

    >>> plone = layer['portal']
    >>> purl = plone.absolute_url()
    >>> from collective.cron import crontab
    >>> class MyCronJob(crontab.Runner):
    ...     runned = []
    ...     environs = []
    ...     def run(self):
    ...         self.runned.append(1) # mutable list will be shared among all instances
    ...         self.environs.append(self.cron.environ)
    >>> from zope.component import getGlobalSiteManager
    >>> gsm = getGlobalSiteManager()
    >>> gsm.registerAdapter(MyCronJob, name="mycronjob")
    >>> gsm.registerAdapter(MyCronJob, name="myfoojob")

The top object of the crontab, is ... the Crontab.
Calling load make the Crontab object and reflect the registry configuration inside it.
You ll have to do that::

    >>> bcrt = mcrontab.Crontab.load()
    >>> bcrt.crons
    OrderedDict([(u'...', cron: testcron/... [ON:...])])

Think that you can configure tasks with a dict of simple values (they must be json encodable) for your jobs runners to parameterize the task.


Adding crons to the crontab
+++++++++++++++++++++++++++++
We will add the related crontab to the plone site in the cron dashboard::

    >>> dstart = datetime.datetime(2008,1,1,1,3)
    >>> set_now(dstart)
    >>> crt = mcrontab.Crontab()
    >>> cron = mcrontab.Cron(name=u'mycronjob',
    ...         activated=True,
    ...         periodicity = u'*/1 * * * *',
    ...         environ={u'foo':u'bar'},
    ...         crontab=crt)
    >>> cron
    cron: mycronjob/... [ON:2008-01-01 00:04:00] {u'foo': u'bar'}

Never register a cron to two crontab, the cron and crontab have an internal link to each other.
If you want to replicate crons between crontab objects, dump them::

    >>> crt2 = mcrontab.Crontab()
    >>> crt2.add_cron(mcrontab.Cron.load(cron.dump()))

Similar check all the cron properties except crontab & logs::

    >>> crt2.by_name('mycronjob')[0].similar(cron)
    True

You have three methods to search crons in crontab:

    - by( ``**`` kwargs) : find all cron matching the infos given in kwargs (see cron constructor)
    - by_name(value) : give all cron matching name
    - by_uid(value) : give the cron registered with uid

Record the craontab back into the site to register the jobs when you are done::

    >>> crt.save()
    >>> transaction.commit()

After adding the job, it is queued::

    >>> get_jobs()[0]
    <zc.async.job.Job (oid ..., db 'async') ``plone.app.async.service._executeAsUser(('', 'plone'), ('', 'plone'), ('', 'plone', 'acl_users'), 'test_user_1_', collective.cron.crontab.runJob, cron: mycronjob/... [ON:2008-01-01 00:04:00]...)``>

Toggle the cron activation
++++++++++++++++++++++++++++++++
At the cron level::

    >>> cron.activated = False
    >>> crt.save()
    >>> cron.activated = True
    >>> len(get_jobs()) > 0
    False

Reactivate::

    >>> cron.activated = True
    >>> crt.save()
    >>> len(get_jobs()) > 0
    True

Globally, at the crontab level (for all crons)::

    >>> crt.activated = False
    >>> crt.save()
    >>> len(get_jobs()) > 0
    False

Reactivate::

    >>> crt.activated = True
    >>> crt.save()
    >>> len(get_jobs()) > 0
    True

Edit a cron
+++++++++++++
We can change the name and some other infos of a cron

    >>> cron.name = u'myfoojob'
    >>> cron.periodicity = u'*/10 * * * *'
    >>> crt.save()

Older jobs have been removed, only the one for this renamed job is present::

    >>> get_jobs()
    [<zc.async.job.Job (oid ..., db 'async') ``plone.app.async.service._executeAsUser(('', 'plone'), ('', 'plone'), ('', 'plone', 'acl_users'), 'test_user_1_', collective.cron.crontab.runJob, cron: myfoojob/... [ON:2008-01-01 00:10:00]...)``>]

Trigger a job execution
++++++++++++++++++++++++++
You can force a job execution by using the  ``CronManager`` composant::

    >>> set_now(datetime.datetime(2008,1,1,2,4))
    >>> manager = getMultiAdapter((plone, cron), i.ICronManager)
    >>> manager.register_job(force=True)
    True
    >>> transaction.commit()

The job return the status, the messages, the uid of the cron and the plone portal path (tuple)::

    >>> wait_for_result(get_jobs()[0])
    (1, [], u'...', ('', 'plone'))
    >>> MyCronJob.runned
    [1]
    >>> MyCronJob.environs[-1]
    {u'foo': u'bar'}

And the job is rescheduled::

    >>> get_jobs()
    [<zc.async.job.Job (oid ..., db 'async') ``plone.app.async.service._executeAsUser(('', 'plone'), ('', 'plone'), ('', 'plone', 'acl_users'), 'test_user_1_', collective.cron.crontab.runJob, cron: myfoojob/... [ON:2008-01-01 01:10:00] (1 logs)...)``>]
    >>> transaction.commit()


View & delete a log
++++++++++++++++++++
Save the current state::

    >>> runnedcron = get_jobs()[0].args[5]
    >>> runnedcron.save()
    >>> ncron = crontab.Crontab.load().by_uid(cron.uid)

View::

    >>> ncron.logs
    [log: 2008-01-01 02:04:00/OK]

Delete::

    >>> noecho = ncron.logs.pop(0)
    >>> ncron.save()

Delete a cron from the crontab
++++++++++++++++++++++++++++++++++
Simply delete it from the crons indexed by uid::

    >>> del crt.crons[cron.uid]
    >>> crt.save()
    >>> get_jobs()
    []


Teardown
+++++++++
::

    >>> bcrt.save()
    >>> noecho = gsm.unregisterAdapter(MyCronJob, name="myfoojob")
    >>> noecho = gsm.unregisterAdapter(MyCronJob, name="mycronjob")
    >>> transaction.commit()

