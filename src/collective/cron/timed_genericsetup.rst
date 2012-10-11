
Manage (add, edit, remove, run) tasks via Generic Setup
--------------------------------------------------------

- The configuration file used to configure your crons is ``crons.xml``.
- You can export crons presents in the site, this will result in a ``crons.xml`` in the output.
- You can **add**, **edit** or **remove** crons referenced by their ``uid``.
- If you are adding a cron the mandatory elements are ``uid``, ``name`` & ``periodicity``.
- If you are editing the mandatory element is ``uid``.
- You can set the following:

    - uid: **Think to give meaningful & uniques uid, UID is unique identifier!**
    - name
    - periodicity
    - environ (default: **'{}'**)
    - activated (default: **False**)

- You cannot add logs.
- if a task is already there with the same uid -> this is an edit.


In the following documentation, we use the api.
But of course in the real life, you hust have to:

    - write the crons.xml
    - run the generisSetup step **collective.cron.setupCrons** on your profile.

setup
++++++++
::

    >>> import time
    >>> from collective.cron import interfaces as i
    >>> from collective.cron.testing import set_now
    >>> from collective.cron import crontab as mcrontab
    >>> from collective.cron import utils
    >>> from zope.component import getMultiAdapter
    >>> import datetime, pytz
    >>> from zc.async.testing import wait_for_result
    >>> layer['crontab'].save()
    >>> import transaction
    >>> get_jobs = lambda:[a for a in layer['queue']]


Import
++++++++++
::

    >>> plone = layer['portal']
    >>> purl = plone.absolute_url()
    >>> crt = mcrontab.Crontab()
    >>> exportimport = getMultiAdapter((plone, crt), i.IExportImporter)


Add
~~~~~
The most complete declaration to add or edit is ::

    >>> CRONS = """<?xml version="1.0"?>
    ... <crons>
    ...   <cron uid="foogsuid" name="foo" activated="true"
    ...         periodicity="*/1 * * * *" >
    ...       <environ> <![CDATA[ {"foo":"bar"} ]]> </environ>
    ...   </cron>
    ...   <!-- YOU CAN OMIT ENVIRON  & activated-->
    ...   <cron uid="foogsuid2" name="foo2" periodicity="*/1 * * * *" />
    ...   <cron uid="foogsuid3" name="foo3" periodicity="*/1 * * * *" />
    ... </crons> """
    >>> TZ = pytz.timezone('Europe/Paris')
    >>> set_now(datetime.datetime(2008,1,1,1,1, tzinfo=TZ))
    >>> exportimport.do_import(CRONS)
    >>> crt1 = mcrontab.Crontab.load()
    >>> crt1.crons
    OrderedDict([(u'foogsuid', cron: foo/foogsuid [ON:2008-01-01 00:02:00] {u'foo': u'bar'}), (u'foogsuid2', cron: foo2/foogsuid2 [OFF]), (u'foogsuid3', cron: foo3/foogsuid3 [OFF])])

Delete & reregister
~~~~~~~~~~~~~~~~~~~~~~
As always with generic setup to remove a cron, just add a ``remove="true"`` inside the declaration.
To remove, just add ``remove="true"`` to the attributes.
The order is import as you can re register jobs with same name after::

    >>> CRONSD = """<?xml version="1.0"?>
    ... <crons>
    ...   <cron uid="foogsuid2" name="foo2" remove="true" periodicity="*/1 * * * *" />
    ...   <cron uid="foogsuid2" name="foo2changed" periodicity="*/3 * * * *"/>
    ...   <cron uid="foogsuid3" remove="true"/>
    ... </crons> """
    >>> exportimport.do_import(CRONSD)
    >>> crt2 = mcrontab.Crontab.load()
    >>> crt2.crons
    OrderedDict([(u'foogsuid', cron: foo/foogsuid [ON:2008-01-01 00:02:00] {u'foo': u'bar'}), (u'foogsuid2', cron: foo2changed/foogsuid2 [OFF])])

Edit
~~~~~~~~~~
You can edit every part of a cron::

    >>> CRONSE = """<?xml version="1.0"?>
    ... <crons>
    ...   <cron uid="foogsuid2" name="foo2editeé" activated="True"  periodicity="*/4 * * * *">
    ...       <environ><![CDATA[ {"foo":"bar", "miche":"muche"} ]]></environ>
    ...   </cron>
    ... </crons> """
    >>> exportimport.do_import(CRONSE)
    >>> crt3 = mcrontab.Crontab.load()
    >>> crt3.crons
    OrderedDict([(u'foogsuid', cron: foo/foogsuid [ON:2008-01-01 00:02:00] {u'foo': u'bar'}), (u'foogsuid2', cron: foo2editeé/foogsuid2 [ON:2008-01-01 00:04:00] {u'foo': u'bar', u'miche': u'muche'})])

Export
++++++
You can also export crons present in the site::

    >>> ret = exportimport.do_export()
    >>> waited = """<?xml version="1.0" encoding="UTF-8"?>
    ... <crons>
    ...   <cron uid="foogsuid" name="foo" activated="True" periodicity="*/1 * * * *">
    ...     <environ><![CDATA[
    ... {"foo": "bar"}
    ... ]]>
    ...     </environ>
    ...   </cron>
    ...   <cron uid="foogsuid2" name="foo2editeé" activated="True" periodicity="*/4 * * * *">
    ...     <environ><![CDATA[
    ... {"miche": "muche", "foo": "bar"}
    ... ]]>
    ...     </environ>
    ...   </cron>
    ... </crons>"""
    >>> ret == waited
    True

Teardown
+++++++++++
::

    >>> layer['crontab'].save()

