import frappe
from .settings import SETTINGS


def field(name, kind='Data', options=None, **kw):
    item = dict(fieldname=name, label=name.replace('_', ' ').title(), fieldtype=kind)
    item.update(kw)
    if options is not None:
        item['options'] = options
    return item


def ensure(name, fields, child=False, single=False):
    if frappe.db.exists('DocType', name):
        return
    doc = dict(doctype='DocType', name=name, module='Neotec Attendance', custom=1,
               istable=int(child), issingle=int(single), track_changes=1, fields=fields)
    if not child:
        doc['permissions'] = [dict(role='System Manager', read=1, write=1, create=1)]
    frappe.get_doc(doc).insert(ignore_permissions=True)


def install():
    f = field
    ensure('Neotec Attendance Company', [
        f('company','Link','Company',reqd=1,in_list_view=1), f('enabled','Check',in_list_view=1),
        f('include_all_active','Check',description='Off means include only explicitly selected employees.'),
        f('department','Link','Department'), f('branch','Link','Branch'),
        f('employment_type','Link','Employment Type'),
        f('required_hours','Float',description='Optional company target. Zero disables short-hours checks unless an approved exception sets a target.')], child=True)
    ensure('Neotec Attendance Employee', [f('employee','Link','Employee',reqd=1,in_list_view=1)], child=True)
    ensure('Neotec Attendance Recipient', [f('company','Link','Company',reqd=1,in_list_view=1),
        f('user','Link','User',reqd=1,in_list_view=1),
        f('audience','Select','HR Manager\nHR User',reqd=1,in_list_view=1), f('enabled','Check',default=1)], child=True)
    ensure('Neotec Attendance Exclusion', [f('employee','Link','Employee',in_list_view=1),
        f('user','Link','User',in_list_view=1), f('reason','Small Text')], child=True)
    ensure(SETTINGS, [
        f('general_section','Section Break',label='Activation and Schedule'),
        f('enabled','Check',default=0,description='Site-specific opt-in. Migrations never turn notifications on.'),
        f('start_date','Date',description='Do not send daily reminders for earlier dates.'),
        f('run_after','Time',default='21:00:00',description='Uses the site timezone.'),
        f('catchup_days','Int',default=3,description='Review 1–7 previous dates after synchronization.'),
        f('monthly_day','Int',default=28), f('grace_minutes','Int',default=120),
        f('notify_employee','Check',default=0),f('notify_manager','Check',default=0),
        f('notify_hr','Check',default=0),f('monthly_enabled','Check',default=0),
        f('email_enabled','Check',default=0),f('in_app_enabled','Check',default=0),
        f('company_section','Section Break',label='Companies and Population'),
        f('companies','Table','Neotec Attendance Company'),
        f('employees','Table','Neotec Attendance Employee',description='Used where Include All Active is off. Company and other filters still apply.'),
        f('recipient_section','Section Break',label='HR Recipients and Exclusions'),
        f('hr_recipients','Table','Neotec Attendance Recipient',description='Explicit company-to-user routing. Merely holding an HR role does not subscribe the user.'),
        f('exclusions','Table','Neotec Attendance Exclusion',description='Employee exclusions remove them from reports. User exclusions suppress all delivery channels.'),
        f('setup_help','HTML',options='<p>Keep sending disabled during setup. Configure companies, employee selection and recipients. Verify shifts, calendars, source synchronization and sample reports. Each site has separate settings and logs.</p>'),
    ], single=True)
