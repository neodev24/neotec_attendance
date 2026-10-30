"""Presentation/schema upgrades never overwrite saved Single or child-table values."""
import frappe
from .settings import SETTINGS


def field(name, kind='Data', options=None, **kw):
    item = dict(fieldname=name, label=name.replace('_', ' ').title(), fieldtype=kind)
    item.update(kw)
    if options is not None:
        item['options'] = options
    return item


def ensure(name, fields, child=False, single=False):
    if not frappe.db.exists('DocType', name):
        doc = dict(doctype='DocType', name=name, module='Neotec Attendance', custom=1,
                   istable=int(child), issingle=int(single), track_changes=1, fields=fields)
        if not child:
            doc['permissions'] = [dict(role='System Manager', read=1, write=1, create=1)]
        frappe.get_doc(doc).insert(ignore_permissions=True)
        return
    doc = frappe.get_doc('DocType', name)
    existing = {f.fieldname: f.as_dict() for f in doc.fields}
    ordered = []
    for spec in fields:
        current = existing.pop(spec['fieldname'], {})
        current.update(spec)
        ordered.append(current)
    # Preserve customer-added fields and their metadata.
    ordered.extend(spec for key, spec in existing.items() if key != 'setup_help')
    doc.set('fields', [])
    for spec in ordered:
        doc.append('fields', spec)
    doc.track_changes = 1
    doc.save(ignore_permissions=True)
    frappe.clear_cache(doctype=name)


def install():
    f = field
    ensure('Neotec Attendance Company', [
        f('company_section','Section Break',label='Company and Employee Selection'),
        f('company','Link','Company',reqd=1,in_list_view=1,columns=4),
        f('enabled','Check',label='Include This Company',in_list_view=1,columns=2,
          description='Include this company in the configured population. This does not turn on sending.'),
        f('include_all_active','Check',label='Include All Active Employees',in_list_view=1,columns=3,
          description='Off: only employees listed in Selected Employees are included. On: all active employees matching the filters below are included.'),
        f('company_column','Column Break'),
        f('required_hours','Float',label='Daily Hours Target',in_list_view=1,columns=3,
          description='Optional approved working-hours target. Blank or 0 disables short-hours checks unless an exception sets a target. Breaks and office presence are not the same as paid working hours.'),
        f('filter_section','Section Break',label='Optional Filters — All Must Match'),
        f('department','Link','Department',description='Leave blank for all departments within this company.'),
        f('branch','Link','Branch',description='Leave blank for all branches within this company.'),
        f('filter_column','Column Break'),
        f('employment_type','Link','Employment Type',description='Leave blank for all employment types. These filters also apply to explicitly selected employees.')], child=True)
    ensure('Neotec Attendance Employee', [
        f('employee','Link','Employee',reqd=1,in_list_view=1,columns=6,
          description='Select an active employee belonging to an included company.'),
        f('employee_column','Column Break'),
        f('company','Link','Company',read_only=1,fetch_from='employee.company',in_list_view=1,columns=6,
          description='For reference. The employee’s actual company controls eligibility.')], child=True)
    ensure('Neotec Attendance Recipient', [
        f('company','Link','Company',reqd=1,in_list_view=1,columns=4,
          description='This recipient receives only this company’s configured attendance population.'),
        f('audience','Select','HR Manager\nHR User',reqd=1,in_list_view=1,columns=3,
          description='The selected user must hold this role. Role membership alone does not subscribe a user.'),
        f('recipient_column','Column Break'),
        f('user','Link','User',reqd=1,in_list_view=1,columns=4,
          description='Choose an enabled user. Add a separate row for each authorized company.'),
        f('enabled','Check',label='Receive This Company’s HR Digest',default=1,in_list_view=1,columns=1)], child=True)
    ensure('Neotec Attendance Exclusion', [
        f('employee','Link','Employee',in_list_view=1,columns=4,
          description='Removes this employee from the report population; their linked user is also excluded from delivery.'),
        f('exclusion_column','Column Break'),
        f('user','Link','User',in_list_view=1,columns=4,
          description='Suppresses delivery to this user in every audience and channel. Their employee can still appear in HR reports unless also excluded.'),
        f('exclusion_reason_section','Section Break',label='Exclusion Reason'),
        f('reason','Small Text',in_list_view=1,columns=4,
          description='Explain why the employee/user should be excluded. Select at least an employee or a user.')], child=True)
    ensure(SETTINGS, [
        f('guide_tab','Tab Break',label='1. Setup Guide'),
        f('guide_intro','HTML',options='<h4>Configure this site before enabling attendance notifications</h4><p>Each site keeps its own settings and records. Start with a small employee group and verify every recipient. Saving settings or running a preview does not send emails.</p><ol><li><b>Companies &amp; Employees:</b> include companies, choose all active employees or an explicit list, and add exclusions.</li><li><b>Notifications:</b> choose employee/manager/HR audiences, authorized company HR recipients, and delivery channels.</li><li><b>Schedule:</b> choose a reporting start date, site-local review time and catch-up window.</li><li><b>Review &amp; Activate:</b> save, run readiness and recipient previews, verify the results, then activate after testing.</li></ol><p>Normal hours and holidays come from HRMS shifts and calendars. Draft exceptions do not apply. This app does not make payroll deductions.</p>'),
        f('guide_details','HTML',options='<p><b>Selection rule:</b> company inclusion → active status → all-active or selected list → optional filters → exclusions. An empty configuration selects nobody.</p><p><b>Important:</b> this is a development release. Full v15/v16 integration and delivery testing is still required before production rollout. For instructions see the <a href="https://github.com/neodev24/neotec_attendance/blob/main/docs/USER_GUIDE.md" target="_blank" rel="noopener noreferrer">usage guide</a>.</p>'),
        f('population_tab','Tab Break',label='2. Companies & Employees'),
        f('company_section','Section Break',label='Included Companies'),
        f('companies','Table','Neotec Attendance Company',description='Add one row per company. Expand a row to set department, branch and employment-type filters. Including a company is separate from activating notifications.'),
        f('employee_section','Section Break',label='Selected Employees'),
        f('employees','Table','Neotec Attendance Employee',description='Used when Include All Active Employees is OFF for the employee’s company. If all-active is ON, this list does not restrict that company. Company filters still apply.'),
        f('exclusion_section','Section Break',label='Employee and User Exclusions'),
        f('exclusions','Table','Neotec Attendance Exclusion',description='Employee = remove from population. User = suppress their delivery. Expand a row for the reason and detailed effect.'),
        f('notifications_tab','Tab Break',label='3. Notifications'),
        f('audience_section','Section Break',label='Who Should Receive Notifications?'),
        f('notify_employee','Check',label='Employee Correction Reminders',default=0,
          description='Send only actionable missing/unpaired-punch or short-hours findings.'),
        f('notify_manager','Check',label='Reporting Manager Daily Digest',default=0,
          description='Resolve the manager from Employee → Reports To. Each manager receives only direct reports within the same company.'),
        f('audience_column','Column Break'),
        f('notify_hr','Check',label='HR Daily Review and Policy Reminders',default=0,
          description='Send company attendance review and pending/expiring/recently expired exception notices to the authorized HR recipients below.'),
        f('monthly_enabled','Check',label='Employee Monthly Attendance Review',default=0,
          description='Independent of daily correction reminders. Sends a partial-month review through the day before the configured monthly review day.'),
        f('recipient_section','Section Break',label='Authorized Company HR Recipients'),
        f('hr_recipients','Table','Neotec Attendance Recipient',description='Required for HR digests. Assign each HR User/HR Manager explicitly to a company. Reporting managers do not need to be listed here.'),
        f('channel_section','Section Break',label='Delivery Channels'),
        f('email_enabled','Check',label='Send Email',default=0,
          description='Requires a working outgoing Email Account. Check Email Queue during testing.'),
        f('channel_column','Column Break'),
        f('in_app_enabled','Check',label='Show In-App Notifications',default=0,
          description='Requires an enabled linked User account. It does not replace email for employees without a login.'),
        f('schedule_tab','Tab Break',label='4. Schedule'),
        f('general_section','Section Break',label='Daily Review Schedule'),
        f('start_date','Date',label='First Attendance Date to Review',description='No daily reminders before this date. Monthly coverage also starts no earlier than this date. Choose a date after an approved outage gap.'),
        f('run_after','Time',label='Run Daily Reviews After',default='21:00:00',description='Site timezone, not the computer’s timezone. The hourly scheduler starts a run at the next tick after this time and reviews previous dates.'),
        f('schedule_column','Column Break'),
        f('catchup_days','Int',label='Previous Days to Recheck',default=3,description='1–7 days. Revisit dates for delayed source synchronization; delivery keys prevent requeueing the same category/date.'),
        f('grace_minutes','Int',label='Minutes to Wait After Shift End',default=120,description='The evaluator waits until this grace period and the punch collection window have ended. It also waits for Shift Type → Last Sync of Checkin.'),
        f('monthly_section','Section Break',label='Monthly Review Schedule'),
        f('monthly_day','Int',label='Monthly Review Day',default=28,description='1–28. Example: 28 reviews the 1st–27th. This is an early review, not a finalized full-month report.'),
        f('monthly_column','Column Break'),
        f('schedule_note','HTML',options='<p>Enable Employee Monthly Attendance Review on the Notifications tab to use this schedule. The review can retry within the previous-days window. No automatic salary deduction or overtime award is created.</p>'),
        f('review_tab','Tab Break',label='5. Review & Activate'),
        f('review_section','Section Break',label='Save and Preview First'),
        f('review_help','HTML',options='<ol><li><b>Save</b> the settings while attendance notifications remain off.</li><li>Click <b>Check Readiness</b> to check population, missing setup and source synchronization.</li><li>Click <b>Preview Recipient Routing</b> to verify who receives each company’s data. No messages are sent.</li><li>Test actual delivery on a TEST site with test recipients, including duplicate prevention and exclusions.</li><li>Only after successful review, enable attendance notifications and Save again.</li></ol><p>If shifts, calendars, managers, email accounts or recipients are missing, fix those records first. Never advance source synchronization timestamps merely to bypass a warning.</p>'),
        f('activation_section','Section Break',label='Activation'),
        f('enabled','Check',label='Enable Attendance Notifications for This Site',default=0,
          description='Master switch. Also requires a start date, an included population, audience switches and at least one channel. Migrations never turn this switch on.'),
        f('activation_column','Column Break'),
        f('setup_status','HTML',options='<p>Use the preview buttons above after saving. Results appear here.</p>'),
    ], single=True)
