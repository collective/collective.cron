
Manage (add, edit, remove, run) tasks via the web interface
-------------------------------------------------------------

setup
++++++++
::

    >>> import lxml
    >>> import time
    >>> from collective.cron import interfaces as i
    >>> from collective.cron.testing import set_now
    >>> from collective.cron import crontab as mcrontab
    >>> from collective.cron import utils
    >>> import datetime, pytz
    >>> layer['crontab'].save()
    >>> from zc.async.testing import wait_for_result
    >>> import transaction
    >>> get_jobs = lambda:[a for a in layer['queue']]
    >>> bcrt = mcrontab.Crontab.load()
    >>> crt = mcrontab.Crontab()
    >>> crt.save()
    >>> transaction.commit()

Creation of a jobrunner
++++++++++++++++++++++++++
We will define a cronjob to execute on the next scheduled tasks behalf
Think that you can make generic tasks which can be configured by the environ json mapping that you configure along with the cron task.
When the job is runned you can access it by ``self.cron.environ``.
::

    >>> plone = layer['portal']
    >>> purl = plone.absolute_url()
    >>> from collective.cron import crontab
    >>> class MyCronJob(crontab.Runner):
    ...     runned = []
    ...     environs = []
    ...     def run(self):
    ...         self.runned.append(1) # mutable list will be shared among all instances
    ...         self.environs.append(self.cron.environ) # mutable list will be shared among all instances
    >>> from zope.component import getGlobalSiteManager
    >>> gsm = getGlobalSiteManager()
    >>> gsm.registerAdapter(MyCronJob, name="mycronjob")
    >>> gsm.registerAdapter(MyCronJob, name="myfoojob")

Registering a job through the interface
++++++++++++++++++++++++++++++++++++++++++

We will add the related crontab to the plone site in the cron dashboard::

    >>> dstart = datetime.datetime(2008,1,1,1,3)
    >>> set_now(dstart)
    >>> browser = Browser.new(purl, login=True)
    >>> browser.getLink('Site Setup').click()
    >>> browser.getLink('Cron Dashboard').click()
    >>> '@@cron-settings' in browser.contents
    True
    >>> browser.getLink('Add a task').click()
    >>> browser.getControl(name='form.widgets.name').value = 'mycronjob'
    >>> browser.getControl(name='form.widgets.periodicity').value = '*/1 * * * *'
    >>> browser.getControl(name='form.widgets.senviron').value = '{"foo":"bar"}'
    >>> browser.getControl('Add').click()

After adding the job, it is queued, and we are back to the dashboard::

    >>> 'Crontab Preferences' in browser.contents
    True
    >>> 'A new cron was added' in browser.contents
    True
    >>> get_jobs()[0]
    <zc.async.job.Job (oid ..., db 'async') ``plone.app.async.service._executeAsUser(('', 'plone'), ('', 'plone'), ('', 'plone', 'acl_users'), 'plonemanager', collective.cron.crontab.runJob, cron: mycronjob/... [ON:2008-01-01 00:04:00] {u'foo': u'bar'})``>

We see that as a safety belt the cron is registered two minutes layer.
Effectivly, the cron reference date is NOW+1 minute when the job has never runned::

    >>> transaction.commit()
    >>> noecho = [wait_for_result(a, 1) for a in layer['queue']]
    Traceback (most recent call last):
    ...
    AssertionError: job never completed

Running now the job ::

    >>> set_now(datetime.datetime(2008,1,1,1,4))
    >>> transaction.commit()
    >>> noecho = [wait_for_result(a) for a in layer['queue']]
    >>> MyCronJob.environs
    [{u'foo': u'bar'}]
    >>> MyCronJob.runned
    [1]
    >>> job = get_jobs()[0]
    >>> job
    <zc.async.job.Job (oid ..., db 'async') ``plone.app.async.service._executeAsUser(('', 'plone'), ('', 'plone'), ('', 'plone', 'acl_users'), 'plonemanager', collective.cron.crontab.runJob, cron: mycronjob/... [ON:2008-01-01 00:05:00] (1 logs)...)``>

Now on the behalf of our timemachine, we step forward in time and see that older
cronjobs are rescheduled to execute now

    >>> set_now(datetime.datetime(2008,1,1,2,0))
    >>> job == get_jobs()[0]
    True
    >>> transaction.commit()
    >>> job == get_jobs()[0]
    True
    >>> noecho = [wait_for_result(a) for a in layer['queue']]
    >>> MyCronJob.runned
    [1, 1]

After execution the job is rescheduled, always !

    >>> get_jobs()
    [<zc.async.job.Job (oid ..., db 'async') ``plone.app.async.service._executeAsUser(('', 'plone'), ('', 'plone'), ('', 'plone', 'acl_users'), 'plonemanager', collective.cron.crontab.runJob, cron: mycronjob/... [ON:2008-01-01 01:01:00] (2 logs)...)``>]


Toggle the cron activation
++++++++++++++++++++++++++++++++
Deactivate it::

    >>> browser.getLink('Cron Dashboard').click()
    >>> browser.getLink('mycronjob').click()
    >>> browser.getLink(id='edit-cron').click()
    >>> browser.getControl(name='form.widgets.activated:list').value = []
    >>> browser.getControl('Apply').click()
    >>> len(get_jobs()) > 0
    False
    >>> transaction.commit()

Reactivate it::

   >>> browser.getLink('Cron Dashboard').click()
   >>> browser.getLink('mycronjob').click()
   >>> browser.getLink(id='edit-cron').click()
   >>> browser.getControl(name='form.widgets.activated:list').value = ['selected']
   >>> browser.getControl('Apply').click()
   >>> len(get_jobs()) > 0
   True
   >>> transaction.commit()

Toggle the crontab activation
++++++++++++++++++++++++++++++++
Deactivate it by clicking on the deactivate link (javascript link)::

    >>> browser.getLink('Cron Dashboard').click()
    >>> browser.getForm('cron_toggle_form').submit()
    >>> len(get_jobs()) > 0
    False
    >>> transaction.commit()

Reactivate it by clicking on the activate link (javascript link)::

    >>> browser.getLink('Cron Dashboard').click()
    >>> browser.getForm('cron_toggle_form').submit()
    >>> len(get_jobs()) > 0
    True
    >>> transaction.commit()

Edit a cron
++++++++++++++
We can change the name and some other infos of a cron

    >>> browser.getLink('Cron Dashboard').click()
    >>> browser.getLink('mycronjob').click()
    >>> browser.getLink(id='edit-cron').click()
    >>> browser.getControl(name='form.widgets.name').value = 'myfoojob'
    >>> browser.getControl(name='form.widgets.periodicity').value = '*/10 * * * *'
    >>> browser.getControl(name='form.widgets.senviron').value = '{"foo":"moo"}'
    >>> browser.getControl('Apply').click()
    >>> transaction.commit()

Older jobs have been removed, only the one for this renamed job is present::

    >>> browser.getLink('Cron Dashboard').click()
    >>> get_jobs()
    [<zc.async.job.Job (oid ..., db 'async') ``plone.app.async.service._executeAsUser(('', 'plone'), ('', 'plone'), ('', 'plone', 'acl_users'), 'plonemanager', collective.cron.crontab.runJob, cron: myfoojob/... [ON:2008-01-01 01:10:00] (2 logs)...)``>]

Trigger a job execution
+++++++++++++++++++++++++
You can force a job execution on the cron dashboard

Transfert to **2:04**, next job is at **2:10**::

    >>> set_now(datetime.datetime(2008,1,1,2,4))
    >>> transaction.commit()
    >>> noecho = [wait_for_result(a, 1) for a in layer['queue']]
    Traceback (most recent call last):
    ...
    AssertionError: job never completed
    >>> MyCronJob.runned
    [1, 1]

To force the run of the job, just go to the cron and click on ``Run``.
Doing a little hack to reproduce the JS executed by clicking on *"Run*"::

    >>> browser.getLink('myfoojob').click()
    >>> browser.getControl(name='cron_action').value = 'run-cron'
    >>> browser.getForm('cron_action_form').submit()
    >>> browser.contents.strip().replace('\n', ' ')
    '<!DOCTYPE html...Cron .../myfoojob was queued...

Job has been runned (see the logs increment), and also rescheduled::

    >>> time.sleep(1)
    >>> transaction.commit()
    >>> len(MyCronJob.runned) < 3 and wait_for_result(layer['queue'][0], 3) or None

    >>> get_jobs()
    [<zc.async.job.Job (oid ..., db 'async') ``plone.app.async.service._executeAsUser(('', 'plone'), ('', 'plone'), ('', 'plone', 'acl_users'), 'plonemanager', collective.cron.crontab.runJob, cron: myfoojob/... [ON:2008-01-01 01:10:00] (3 logs)...)``>]
    >>> MyCronJob.runned
    [1, 1, 1]
    >>> MyCronJob.environs[-1]
    {u'foo': u'moo'}

View & delete a log
+++++++++++++++++++++
Run the job 20 times for having a bunch of logs::

    >>> def exec_job():
    ...     set_now(datetime.datetime(2008,1,1,2,4))
    ...     cron = get_jobs()[0].args[5]
    ...     manager = getMultiAdapter((plone, cron), i.ICronManager)
    ...     manager.register_job(force=True)
    ...     transaction.commit()
    ...     return wait_for_result(get_jobs()[0])
    >>> runned = []
    >>> runned.append(exec_job())
    >>> runned.append(exec_job())
    >>> runned.append(exec_job())
    >>> runned.append(exec_job())
    >>> runned.append(exec_job())
    >>> runned.append(exec_job())
    >>> runned.append(exec_job())
    >>> runned.append(exec_job())
    >>> runned.append(exec_job())
    >>> runned.append(exec_job())
    >>> runned.append(exec_job())
    >>> runned.append(exec_job())
    >>> runned.append(exec_job())
    >>> runned.append(exec_job())
    >>> runned.append(exec_job())
    >>> runned.append(exec_job())
    >>> runned.append(exec_job())
    >>> runned.append(exec_job())
    >>> runned.append(exec_job())
    >>> runned.append(exec_job())
    >>> runned.append(exec_job())
    >>> cron = get_jobs()[0].args[5]
    >>> len(cron.logs)
    24

Logs are available directlythrought the cron dashboard
We see only the last five.
They are ordered in FIFO and not via date::

    >>> browser.getLink('myfoojob').click()
    >>> '10/24 last logs' in browser.contents
    True
    >>> browser.getControl(name='logs_to_delete').value = ['14']
    >>> browser.getControl(name='logdelete').click()
    >>> 'Selected logs have been deleted' in browser.contents
    True
    >>> '10/23 last logs' in browser.contents
    True

Removing all logs::

    >>> browser.getControl(name='alllogs_to_delete').value = True
    >>> browser.getControl(name='logdeletetop').click()
    >>> 'All logs have been deleted' in browser.contents
    True
    >>> 'last logs' in browser.contents
    False

Delete a cron from the crontab
++++++++++++++++++++++++++++++++
::

    >>> browser.getLink('Cron Dashboard').click()
    >>> browser.getLink('Add a task').click()
    >>> browser.getControl(name='form.widgets.name').value = 'foodeletecron'
    >>> browser.getControl(name='form.widgets.periodicity').value = '*/1 * * * *'
    >>> browser.getControl('Add').click()
    >>> browser.getLink('Cron Dashboard').click()
    >>> browser.getLink('foodeletecron').click()

Doing a little hack to reproduce the JS executed by clicking on "Delete".
::

    >>> browser.getControl(name='cron_action').value = 'delete-cron'
    >>> browser.getForm('cron_action_form').submit()
    >>> browser.contents.strip().replace('\n', ' ')
    '<!DOCTYPE html...Cron .../foodeletecron was deleted...

And, we are back to the dashboard::

    >>> browser.url
    'http://localhost/plone/@@cron-settings'

Delete a cron from the dasboard
+++++++++++++++++++++++++++++++++++
::
    >>> browser.getLink('Cron Dashboard').click()
    >>> browser.getLink('Add a task').click()
    >>> browser.getControl(name='form.widgets.name').value = 'foodeletecron'
    >>> browser.getControl(name='form.widgets.periodicity').value = '*/1 * * * *'
    >>> browser.getControl('Add').click()
    >>> browser.getLink('Cron Dashboard').click()

Doing a little hack to reproduce the JS executed by clicking on "Delete".
::

    >>> cron = crontab.Crontab.load().by_name('foodeletecron')[0]
    >>> browser.getControl(name='uids_to_delete').value = [cron.uid]
    >>> browser.getControl('Send').click()
    >>> browser.contents.strip().replace('\n', ' ')
    '<!DOCTYPE html...Cron .../foodeletecron was deleted...

And, we are back to the dashboard::

    >>> browser.url
    'http://localhost/plone/@@cron-settings'


Teardown
+++++++++
::

    >>> bcrt.save()
    >>> noecho = gsm.unregisterAdapter(MyCronJob, name="myfoojob")
    >>> noecho = gsm.unregisterAdapter(MyCronJob, name="mycronjob")
    >>> transaction.commit()

