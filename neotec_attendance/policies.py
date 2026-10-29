"""Frappe/HRMS v15/v16 policy pilot. No writes to Employee Checkin or Attendance."""
from datetime import timedelta
from hashlib import sha256
from html import escape
import frappe
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime, get_datetime
from .policy_engine import resolve, window

POLICY = 'Neotec Attendance Exception'
LOG = 'Neotec Attendance Delivery'


class AttendanceException(Document):
    def validate(self):
        from .exception_types import apply_type
        try:
            apply_type(self)
        except ValueError as exc:
            frappe.throw(str(exc))
        if not self.reason: frappe.throw('Management decision / reason is required')
        if not self.permanent and not self.valid_to: frappe.throw('End date is required unless permanent')
        if self.valid_to and getdate(self.valid_to) < getdate(self.valid_from): frappe.throw('End date precedes start date')
        if self.scope == 'Employee':
            if not self.employee: frappe.throw('Select employee')
            if frappe.db.get_value('Employee', self.employee, 'company') != self.company: frappe.throw('Employee company mismatch')
        if self.scope == 'Department' and not self.department: frappe.throw('Select department')
        if self.override_required_hours and not 0 < float(self.required_hours or 0) <= 24: frappe.throw('Required hours must be between 0 and 24')
        if self.override_weekly_off:
            days = str(self.weekly_off or '').split(',') if self.weekly_off else []
            if any(x.strip() not in ('0','1','2','3','4','5','6') for x in days): frappe.throw('Weekly offs: comma separated Monday=0 through Sunday=6')
        if self.override_break_start != self.override_break_end: frappe.throw('Override both break start and end together')
        if self.override_break_start:
            if not self.break_start or not self.break_end: frappe.throw('Enter both approved break times')
        if self.override_outage and self.outage and self.permanent: frappe.throw('Outage exclusions require an end date')
        if int(self.grace_minutes or 0) < 0 or int(self.collection_after_minutes or 0) < 0: frappe.throw('Windows cannot be negative')

    def before_submit(self):
        if frappe.session.user != 'Administrator' and 'HR Manager' not in frappe.get_roles(): frappe.throw('HR Manager approval required', frappe.PermissionError)
        if self.owner == frappe.session.user and frappe.session.user != 'Administrator': frappe.throw('A different HR Manager must approve the request')
        self.approved_by = frappe.session.user
        self.approved_on = now_datetime()
        # Reject ambiguity before an exception takes effect, including future overlaps.
        peers = frappe.get_all(POLICY, filters={'docstatus':1, 'company':self.company}, fields=['*'])
        peers.append(self.as_dict())
        peers[-1]['docstatus'] = 1
        employees = frappe.get_all('Employee', filters={'company':self.company,'status':'Active'}, fields=['name','company','department'])
        dates = {getdate(self.valid_from)}
        for p in peers:
            if getdate(p.valid_from) >= getdate(self.valid_from) and (self.permanent or getdate(p.valid_from) <= getdate(self.valid_to)): dates.add(getdate(p.valid_from))
        for employee in employees:
            for day in dates:
                try:
                    from .hrms_adapter import shift_for_day, baseline
                    from .settings import get_settings, company_config
                    employee_doc = frappe.get_doc('Employee', employee.name)
                    settings = get_settings()
                    config = company_config(employee.company, settings) or frappe._dict(required_hours=0)
                    shift = shift_for_day(employee_doc, day)
                    rules = resolve(employee, peers, day, baseline(shift, config, settings))
                    if not rules['outage']:
                        window(day, rules)
                except ValueError as exc: frappe.throw(str(exc))

    def before_cancel(self):
        if frappe.session.user != 'Administrator' and 'HR Manager' not in frappe.get_roles(): frappe.throw('HR Manager cancellation required', frappe.PermissionError)


def evaluate(employee, day, settings=None):
    from .settings import get_settings, company_config
    from .hrms_adapter import shift_for_day, baseline, holiday_calendar, punch_hours
    settings = settings or get_settings()
    emp = frappe.get_doc('Employee', employee)
    day = getdate(day)
    row = dict(employee=employee, employee_name=emp.employee_name, date=str(day),
               company=emp.company, reports_to=emp.reports_to, email=emp.company_email,
               punches=[], attendance=[])
    def finding(text, actionable=False, setup_issue=False, **extra):
        return dict(row, finding=text, actionable=actionable, setup_issue=setup_issue, **extra)
    config = company_config(emp.company, settings)
    if not config:
        return finding('Company not enabled in Attendance Settings', setup_issue=True)
    if emp.status != 'Active' or (emp.date_of_joining and day < getdate(emp.date_of_joining)) or (emp.relieving_date and day > getdate(emp.relieving_date)):
        return finding('Outside active employment')
    policies = frappe.get_all(POLICY, filters={'company': emp.company, 'docstatus': 1}, fields=['*'])
    try:
        shift = shift_for_day(emp, day)
        rules = resolve(emp.as_dict(), policies, day, baseline(shift, config, settings))
        row['rules'] = rules
        if rules['outage']:
            return finding('Approved disruption — HR verification required')
        if not shift:
            return finding('Assigned/default shift missing', setup_issue=True)
        row['shift'] = shift.name
        start, end, ready = window(day, rules)
    except ValueError as exc:
        return finding(str(exc), setup_issue=True)
    row['attendance'] = frappe.get_all('Attendance', filters={
        'employee': employee, 'attendance_date': day, 'docstatus': 1},
        fields=['status', 'working_hours', 'late_entry', 'early_exit'])
    calendar = holiday_calendar(emp, shift, day)
    if not calendar:
        return finding('Holiday calendar missing', setup_issue=True)
    cal = frappe.get_doc('Holiday List', calendar)
    if not getdate(cal.from_date) <= day <= getdate(cal.to_date):
        return finding('Holiday calendar does not cover this date', setup_issue=True)
    holiday = frappe.db.get_value('Holiday', {'parent': calendar, 'parenttype': 'Holiday List', 'holiday_date': day}, ['weekly_off', 'half_day'], as_dict=True) if frappe.get_meta('Holiday').has_field('half_day') else frappe.db.get_value('Holiday', {'parent': calendar, 'parenttype': 'Holiday List', 'holiday_date': day}, ['weekly_off'], as_dict=True)
    if holiday and holiday.get('half_day'):
        return finding('Half holiday — manual review')
    if holiday and not holiday.weekly_off:
        return finding('Public holiday')
    if rules['weekly_off'] is None:
        if holiday and holiday.weekly_off:
            return finding('Scheduled weekly off')
    else:
        offs = {int(x.strip()) for x in str(rules['weekly_off'] or '').split(',') if x.strip()}
        if day.weekday() in offs:
            return finding('Exception weekly off')
    leaves = frappe.get_all('Leave Application', filters={
        'employee': employee, 'docstatus': 1, 'status': 'Approved',
        'from_date': ['<=', day], 'to_date': ['>=', day]}, fields=['half_day', 'half_day_date'])
    for leave in leaves:
        if not leave.half_day:
            return finding('Approved leave')
        if not leave.half_day_date or getdate(leave.half_day_date) == day:
            return finding('Half-day leave — manual review')
    if now_datetime() < ready:
        return finding('Shift / grace period incomplete')
    close = end + timedelta(minutes=int(rules['collection_after_minutes'] or 0))
    if not shift.last_sync_of_checkin or get_datetime(shift.last_sync_of_checkin) <= close:
        return finding('Awaiting shift check-in synchronization', setup_issue=True)
    open_time = start - timedelta(minutes=shift.begin_check_in_before_shift_start_time or 0)
    raw = frappe.get_all('Employee Checkin', filters={
        'employee': employee, 'time': ['between', [open_time, close]], 'skip_auto_attendance': 0},
        fields=['time', 'log_type', 'shift'], order_by='time')
    # Do not attribute punches from another shift to this review.
    if any(p.shift and p.shift != shift.name for p in raw):
        return finding('Conflicting shift punches — manual review', setup_issue=True)
    row['punches'] = [str(p.time) for p in raw]
    if not raw:
        return finding('No punches — review required', actionable=True)
    if rules['punch_mode'] == 'Check-in only':
        if shift.determine_check_in_and_check_out == 'Strictly based on Log Type in Employee Checkin' and not any(p.log_type == 'IN' for p in raw):
            return finding('Check-in missing — review required', actionable=True)
        return finding('Check-in recorded; checkout is policy-calculated only', calculated_checkout=str(end))
    hours, missing = punch_hours(raw, shift.determine_check_in_and_check_out, shift.working_hours_calculation_based_on)
    if missing:
        return finding('Unpaired punch — review required', actionable=True)
    if rules['break_start'] or rules['break_end']:
        return finding('Approved emergency break — manual hours review', recorded_hours=hours)
    short = bool(rules['required_hours'] and hours < float(rules['required_hours']))
    return finding('Short recorded hours — review required' if short else 'Punches recorded',
                   actionable=short, recorded_hours=round(hours, 2))


@frappe.whitelist()
def preview(date=None):
    from .settings import get_settings, cohort
    frappe.only_for('System Manager')
    settings = get_settings()
    day = getdate(date) if date else now_datetime().date() - timedelta(days=1)
    return [evaluate(emp['name'], day, settings) for emp in cohort(settings)]

@frappe.whitelist()
def routing_preview(date=None):
    from .settings import get_settings, cohort
    frappe.only_for('System Manager')
    settings = get_settings()
    day = getdate(date) if date else now_datetime().date() - timedelta(days=1)
    rows = [evaluate(emp['name'], day, settings) for emp in cohort(settings)]
    return [{'company': company, 'recipients': _targets(company, items, settings),
             'employees': [r['employee'] for r in items]}
            for company, items in _by_company(rows).items()]


def _by_company(rows):
    groups = {}
    for row in rows:
        groups.setdefault(row['company'], []).append(row)
    return groups


def _targets(company, rows, settings):
    from .settings import excluded_users
    excluded = excluded_users(settings)
    excluded_emails = {frappe.db.get_value('User', user, 'email') for user in excluded}
    targets = []
    def add(user, audience, items, address=None):
        if user in excluded:
            return
        if user and not frappe.db.get_value('User', user, 'enabled'):
            return
        address = address or (frappe.db.get_value('User', user, 'email') if user else None)
        if address in excluded_emails or not (address or user):
            return
        targets.append(dict(user=user, email=address, audience=audience,
                            employees=[r['employee'] for r in items]))
    if settings.notify_employee:
        for row in rows:
            if row.get('actionable'):
                add(frappe.db.get_value('Employee', row['employee'], 'user_id'),
                    'Employee', [row], row.get('email'))
    if settings.notify_manager:
        teams = {}
        for row in rows:
            if row.get('reports_to'):
                teams.setdefault(row['reports_to'], []).append(row)
        for manager, items in teams.items():
            mgr = frappe.db.get_value('Employee', manager, ['company', 'user_id', 'status'], as_dict=True)
            if mgr and mgr.company == company and mgr.status == 'Active':
                add(mgr.user_id, 'Reporting Manager', items)
    if settings.notify_hr:
        subscribed = set()
        for route in settings.hr_recipients:
            if route.enabled and route.company == company and route.user not in subscribed:
                if route.audience in frappe.get_roles(route.user):
                    add(route.user, 'HR', rows)
                    subscribed.add(route.user)
    return targets


def _deliver(target, subject, rows, key, settings):
    name = sha256(key.encode()).hexdigest()[:40]
    if frappe.db.exists(LOG, name):
        return
    user, email = target.get('user'), target.get('email')
    can_email = bool(settings.email_enabled and email)
    can_in_app = bool(settings.in_app_enabled and user)
    if not (can_email or can_in_app):
        return
    # Store and queue in one transaction. Duplicate key races roll back in caller.
    doc = frappe.get_doc({'doctype': LOG, 'recipient': email or user,
                          'category': subject, 'details': frappe.as_json(rows)})
    doc.insert(ignore_permissions=True, set_name=name)
    body = '<p>Please review the attendance findings below. These are not automatic payroll deductions.</p><table><tr><th>Date</th><th>Employee</th><th>Punches</th><th>Finding</th></tr>'
    for row in rows:
        values = (row['date'], row['employee_name'], ', '.join(row.get('punches', [])), row['finding'])
        body += '<tr>' + ''.join('<td>' + escape(str(v)) + '</td>' for v in values) + '</tr>'
    body += '</table>'
    if can_email:
        queue = frappe.sendmail(recipients=[email], subject=subject, message=body)
        if not queue:
            frappe.throw('Email was not queued')
        doc.db_set('email_queue', queue.name)
    if can_in_app:
        frappe.get_doc({'doctype': 'Notification Log', 'for_user': user,
                       'type': 'Alert', 'subject': subject, 'email_content': body}).insert(ignore_permissions=True)


def _safe_delivery(target, subject, rows, key, settings):
    try:
        _deliver(target, subject, rows, key, settings)
        frappe.db.commit()
    except Exception:
        frappe.db.rollback()
        frappe.log_error(title='Attendance notification delivery failed', message=frappe.get_traceback())


def daily():
    from .settings import get_settings, cohort
    from .policy_engine import clock
    settings = get_settings()
    if not settings.enabled or not settings.start_date:
        return
    current = now_datetime()
    if current.time() < clock(settings.run_after):
        return
    people = cohort(settings)
    if not people:
        return
    for offset in range(1, min(int(settings.catchup_days or 1), 7) + 1):
        day = current.date() - timedelta(days=offset)
        if day < getdate(settings.start_date):
            continue
        rows = []
        for emp in people:
            try:
                rows.append(evaluate(emp['name'], day, settings))
            except Exception:
                frappe.db.rollback()
                frappe.log_error(title='Attendance evaluation failed', message=frappe.get_traceback())
                rows.append(dict(employee=emp['name'], employee_name=emp['name'], company=emp['company'],
                                 date=str(day), reports_to=None, finding='Evaluation failed — HR setup review required',
                                 actionable=False, setup_issue=True))
        for company, items in _by_company(rows).items():
            notices = []
            if offset == 1:
                for policy in frappe.get_all(POLICY, filters={'company': company, 'docstatus': ['in', [0, 1]]},
                        fields=['name', 'employee', 'scope', 'valid_to', 'permanent', 'docstatus']):
                    state = 'Pending approval' if policy.docstatus == 0 else None
                    if policy.docstatus == 1 and not policy.permanent and policy.valid_to:
                        remaining = (getdate(policy.valid_to) - current.date()).days
                        if -7 <= remaining <= 7:
                            state = 'Recently expired' if remaining < 0 else f'Expires in {remaining} days'
                    if state:
                        notices.append(dict(date=str(current.date()), employee_name=policy.employee or policy.scope,
                                            finding=policy.name + ': ' + state))
            for target in _targets(company, items, settings):
                selected = [r for r in items if r['employee'] in target['employees']]
                if target['audience'] == 'HR':
                    selected += notices
                identity = target['user'] or target['email']
                _safe_delivery(target, f"Daily attendance review — {company} — {day}", selected,
                    f"daily:{company}:{target['audience']}:{identity}:{day}", settings)
    if settings.monthly_enabled:
        _monthly(people, current, settings)


def _monthly(people, current, settings):
    review_day = current.date().replace(day=int(settings.monthly_day or 28))
    if current.date() < review_day or (current.date() - review_day).days >= int(settings.catchup_days or 1):
        return
    first = max(review_day.replace(day=1), getdate(settings.start_date))
    last = review_day - timedelta(days=1)
    if first > last:
        return
    from .settings import excluded_users
    excluded = excluded_users(settings)
    excluded_emails = {frappe.db.get_value('User', user, 'email') for user in excluded}
    for emp in people:
        doc = frappe.get_doc('Employee', emp['name'])
        if doc.user_id in excluded:
            continue
        email = doc.company_email or (frappe.db.get_value('User', doc.user_id, 'email') if doc.user_id else None)
        if email in excluded_emails:
            continue
        if doc.user_id and not frappe.db.get_value('User', doc.user_id, 'enabled'):
            continue
        try:
            rows = []
            day = first
            while day <= last:
                rows.append(evaluate(doc.name, day, settings))
                day += timedelta(days=1)
            target = dict(user=doc.user_id, email=email)
            _safe_delivery(target, f'Monthly attendance review — {first} to {last}', rows,
                f'monthly:{doc.name}:{review_day:%Y-%m}', settings)
        except Exception:
            frappe.db.rollback()
            frappe.log_error(title='Attendance monthly review failed', message=frappe.get_traceback())
