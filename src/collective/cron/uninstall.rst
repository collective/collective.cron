==========================
Uninstall collective.cron
==========================

Get a browser::

    >>> from collective.cron import crontab as mcrontab
    >>> from lxml import html
    >>> plone = layer['portal']
    >>> purl = plone.absolute_url()
    >>> oldcrontab = layer['crontab'].manager.cronsettings.crontab
    >>> oldactivated = layer['crontab'].manager.cronsettings.activated

Saving the crontab, registering one cronjob::

    >>> layer['crontab'].save()
    >>> len(layer['queue'])
    1

Uinstall the product::

    >>> browser = Browser.new(purl, login=True)
    >>> browser.getLink('Site Setup').click()
    >>> browser.getLink('Add-ons').click()
    >>> '@@cron-settings' in browser.contents
    True
    >>> browser.getControl('collective.cron').click()
    >>> browser.getControl('Deactivate').click()

Product is uninstalled, the jobs are away & the configlet too.::

    >>> 'collective.cron' in [dict(a.items())['value']
    ... for a in html.fromstring(
    ... browser.contents).xpath(
    ... "//form[@action='http://localhost/plone/portal_quickinstaller/installProducts']"
    ... )[0].xpath('.//li/input')]
    True
    >>> len(layer['queue'])
    0
    >>> '@@cron-settings' in browser.contents
    False

Reinstall it & reload the cron for other tests::

    >>> browser.getLink('Site Setup').click()
    >>> browser.getLink('Add-ons').click()
    >>> browser.getControl('collective.cron').click()
    >>> browser.getControl('Activate').click()
    >>> layer['crontab'].manager.cronsettings.crontab    = oldcrontab
    >>> layer['crontab'].manager.cronsettings.activated  = oldactivated
    >>> cr = mcrontab.Crontab.load()
    >>> noecho = [layer['crontab'].add_cron(cr.crons[c]) for c in cr.crons]
    >>> layer['crontab'].save()

.. vim:set ft=doctest:
