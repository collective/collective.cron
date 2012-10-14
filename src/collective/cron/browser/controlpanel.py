import os

from zope.publisher.interfaces import IPublishTraverse
from zope.component import adapts, getUtility, getMultiAdapter
from zope import component
from zope.interface import alsoProvides, implements, Interface, Invalid
from zope import schema

from z3c.form import field, form, validator
from z3c.form.interfaces import IForm

from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.CMFCore.utils import getToolByName
from Products.Five.browser import BrowserView

from plone.z3cform import layout
from plone.registry.interfaces import IRegistry

from collective.cron import MessageFactory as _
from collective.cron.interfaces import (
    ICron,
    CronFormatError,
    is_json_dict,
    job_status,
    ICronManager,
)
from collective.cron import crontab
from Products.statusmessages.interfaces import IStatusMessage

from z3c.form.interfaces import ActionExecutionError, WidgetActionExecutionError

class FormFields(Interface):
    senviron = schema.Text(title=_('Environ (variables) as a JSON dict'),
                          constraint=is_json_dict,
                          required=False)


class IUserForm(Interface):
    """Marker for validation"""
class AddForm(form.AddForm):
    implements(IUserForm)
    @property
    def fields(self):
        fields = (field.Fields(ICron).omit(
            'crontab', 'uid', 'environ', 'logs') +
                  field.Fields(FormFields))
        return fields

    def createAndAdd(self, data):
        if data.get('senviron',  None):
            data['environ'] = crontab.json.loads(
                data['senviron'])
        ncron =  crontab.Cron.load(data)
        crt = crontab.Crontab.load()
        crt.add_cron(ncron)
        crt.save()
        IStatusMessage(self.request).addStatusMessage(
            _('A new cron was added (%s)' % ncron.uid)
        )
        self.request.response.redirect(
            self.context.absolute_url() +
            '/@@cron-settings'
        )
        return ''

class EditForm(form.EditForm):
    implements(IUserForm)
    @property
    def action(self):
        """See interfaces.IInputForm"""
        return self.request.getURL()+'?uid=%s' % self.request.form.get('uid', '')

    @property
    def fields(self):
        fields = (field.Fields(ICron).omit(
            'crontab', 'uid', 'environ', 'logs') +
                  field.Fields(FormFields))
        return fields

    def applyChanges(self, data):
        pre = self.getContent()
        crt = crontab.Crontab.load()
        content =  crt.by(uid=pre['uid'])[0]
        changes = {}
        for f in ['periodicity', 'user', 'senviron',
                  'name', 'activated', 'logs_limit',]:
            val = data.get(f, None)
            if f == 'senviron':
                val = crontab.json.loads(val)
                f = 'environ'
            oldval = getattr(content, f, None)
            if oldval != val:
                setattr(content, f, val)
                changes[f] = val
        if changes:
            crt.save()
        return changes

    def getContent(self):
        uid = self.request.form.get('uid', None)
        crons = crontab.Crontab.load().by(uid=uid)
        if crons:
            cron = crons[0]
            return {
                'uid': cron.uid,
                'name': cron.name,
                'user': cron.user,
                'logs_limit': cron.logs_limit,
                'activated': cron.activated,
                'periodicity': cron.periodicity,
                'senviron': crontab.json.dumps(cron.environ),
            }
        else: # pragma: no cover
            IStatusMessage(self.request).addStatusMessage(
                _('No such cron')
            )
            self.request.response.redirect(
                self.context.absolute_url() +
                '/@@cron-settings'
            )
            return {}

class UserValidator(validator.SimpleFieldValidator): # pragma: no cover
    def validate(self, value):
        ctx = self.view.context
        acl = getToolByName(ctx, 'acl_users')
        if value:
            vl = acl.searchUsers(id=value)
            if len(vl) < 1:
                raise Invalid(
                    _('No such user ${user}',
                      mapping={'user' : value})
                )
validator.WidgetValidatorDiscriminators(
    UserValidator, view=IUserForm, field=ICron['user'])


class ControlPanelFormView(layout.FormWrapper):
    index = ViewPageTemplateFile('cpanelformwrapper.pt')
AddFormView = layout.wrap_form(AddForm, ControlPanelFormView)
EditFormView = layout.wrap_form(EditForm, ControlPanelFormView)

class ICrontabManager(Interface):
    """."""
    def add():
        """."""
    def cron_edit():
        """."""
    def cron_view():
        """."""
    def cron_deletelog():
        """."""
    def cron_action():
        """."""
    def process_multiple():
        """."""
    def crontab_toggle():
        """."""

def postonly(func): #pragma: no cover
    def wrapper(self, *args, **kwargs):
        if not self.request.method == 'POST':
            self.request.response.redirect(
                self.context.absolute_url() +
                '/@@cron-settings'
            )
            return False
        return func(self, *args, **kwargs)
    return wrapper

class CrontabManager(BrowserView):
    implements((ICrontabManager, IPublishTraverse))
    template = ViewPageTemplateFile('crontab.pt')
    cron_template = ViewPageTemplateFile('cron.pt')

    def publishTraverse(self, request, name):
        return getattr(self, name, None)

    def __call__(self):
        crt = crontab.Crontab.load()
        return self.template(**{'crontab': crt})

    def cron_view(self):
        crt = crontab.Crontab.load()
        uid = self.request.form.get('uid', None)
        if not uid in crt.crons: # pragma: no cover
            self.request.response.redirect(
                self.context.absolute_url() +
                '/@@cron-settings'
            )
        return self.cron_template(**{'cron': crt.crons[uid]})

    def get_form(self, formview):
        """mark the form to allow template overrides"""
        context = self.context
        self.request.form['viewname'] = self.__name__
        zformv = formview(
            context, self.request).__of__(context)
        return zformv

    def add(self):
        """."""
        zformv = self.get_form(AddFormView)
        content = zformv()
        return content

    @postonly
    def delete_cron(self, crt, uid):
        deletion = False
        if uid in crt.crons:
            cron = crt.crons[uid]
            IStatusMessage(self.request).addStatusMessage(
                _('Cron ${uid}/${name} was deleted.',
                  mapping = {'name': cron.name,
                             'uid': cron.uid})
            )
            del crt.crons[uid]
            deletion = True
        return deletion

    @postonly
    def run_cron(self, crt, uid):
        runned = False
        if uid in crt.crons:
            cron = crt.crons[uid]
            manager = getMultiAdapter((self.context, cron), ICronManager)
            manager.register_job(force=True)
            IStatusMessage(self.request).addStatusMessage(
                _('Cron ${uid}/${name} was queued.',
                  mapping = {'name': cron.name,
                             'uid': cron.uid})
            )
            runned = True
        return runned

    def activated(self):
        crt = crontab.Crontab.load()
        return crt.activated

    @postonly
    def crontab_toggle(self):
        activated = self.request.form.get('activated', '') == "1"
        message = {
            True:  _('Crontab has been activated'),
            False: _('Crontab has been deactivated'),
        }
        if 'activated' in self.request.form:
            IStatusMessage(self.request).addStatusMessage(
                message.get(activated)
            )
            crt = crontab.Crontab.load()
            crt.activated = activated
            crt.save()
        self.request.response.redirect(
            self.context.absolute_url() +
            '/@@cron-settings'
        )

    @postonly
    def cron_action(self):
        uid = self.request.form.get('uid', None)
        action = self.request.form.get('cron_action', None)
        crt = crontab.Crontab.load()
        changed = False
        if action == 'delete-cron':
            if self.delete_cron(crt, uid):
                changed = True
        ep = self.context.absolute_url() + '/@@cron-settings'
        if action == 'run-cron':
            if self.run_cron(crt, uid):
                ep = (self.context.absolute_url() +
                      '/@@cron-settings/cron_view?uid=%s' % uid)
            else: # pragma: no cover
                IStatusMessage(self.request).addStatusMessage(
                    _('Cron not queued'),
                )
        if changed:
            crt.save()
        self.request.response.redirect(ep)

    @postonly
    def process_multiple(self):
        delete = self.request.form.get('uids_to_delete', [])
        if not isinstance(delete, list):
            delete = [delete]
        crt = crontab.Crontab.load()
        changed = False
        for i in delete:
            if self.delete_cron(crt, i):
                changed = True
        if changed:
            crt.save()
        self.request.response.redirect(
            self.context.absolute_url() +
            '/@@cron-settings'
        )

    def list_logs(self, cron, limit=10):
        data = []
        infos = {
            'logs' : data,
            'limit' : limit,
            'len' : len(cron.logs),
        }
        for idx, i in enumerate(cron.logs):
            data.append({
                'idx' : idx,
                'date' : i.date,
                'status' : i.status,
                'messages' : i.messages,
            })
        if len(data)>limit:
            infos['logs'] = data[-limit:]
        return infos

    @postonly
    def cron_deletelog(self):
        crt = crontab.Crontab.load()
        cron = crt.crons.get(self.request.form.get('uid'), '')
        changed = False
        to_delete = self.request.form.get('logs_to_delete', [])
        if not isinstance(to_delete, list):
            to_delete = [to_delete]
        if cron and self.request.form.get('alllogs_to_delete'):
            IStatusMessage(self.request).addStatusMessage(
                _('All logs have been deleted')
            )
            cron.logs = []
            changed = True
        elif cron and to_delete:
            to_delete = [int(a) for a in to_delete]
            to_delete.sort()
            to_delete.reverse()
            for item in to_delete:
                try:
                    cron.logs.pop(item)
                    changed = True
                except IndexError, e: # pragma: no cover
                    continue
            if changed:
                IStatusMessage(self.request).addStatusMessage(
                    _('Selected logs have been deleted')
                )
        if changed:
            crt.save()
        self.request.response.redirect(
            self.context.absolute_url() +
            '/@@cron-settings/cron_view?uid=%s' % cron.uid
        )

    def cron_edit(self):
        """."""
        zformv = self.get_form(EditFormView)
        content = zformv()
        return content

    def get_status(self, id):
        s = job_status.by_value.get(id, None)
        if s:
            s = s.title
        else:
            s = id
        return s

