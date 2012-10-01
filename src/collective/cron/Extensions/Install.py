
from Products.CMFCore.utils import getToolByName

from collective.cron import crontab

def uninstall(portal):
    crt = crontab.Crontab().load()
    for cron in crt.crons: # pragma: no cover
        del crt.crons[cron]
    # remove items in registry
    # remove jobs
    crt.save()
    setup_tool = getToolByName(portal, 'portal_setup')
    setup_tool.runAllImportStepsFromProfile(
        'profile-collective.cron:uninstall')
    return "collective.cron uninstalled"
