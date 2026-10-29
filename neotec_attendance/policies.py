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
                    rules = resolve(employee, peers, day)
                    window(day, rules)
                except ValueError as exc: frappe.throw(str(exc))

    def before_cancel(self):
        if frappe.session.user != 'Administrator' and 'HR Manager' not in frappe.get_roles(): frappe.throw('HR Manager cancellation required', frappe.PermissionError)


def _policies(company):
    return frappe.get_all(POLICY, filters={'company': company, 'docstatus':1}, fields=['*'])


def evaluate(employee, day):
    emp = frappe.get_doc('Employee', employee)
    day = getdate(day)
    row = dict(employee=employee, employee_name=emp.employee_name, date=str(day), company=emp.company, department=emp.department, reports_to=emp.reports_to, email=emp.company_email, punches=[], attendance=[])
    if emp.status != 'Active' or (emp.date_of_joining and day < getdate(emp.date_of_joining)):
        return dict(row, finding='Outside active employment', actionable=False)
    try: rules = resolve(emp.as_dict(), _policies(emp.company), day)
    except ValueError as exc: return dict(row, finding=str(exc), actionable=False, setup_issue=True)
    row['rules'] = rules
    row['attendance'] = frappe.get_all('Attendance', filters={'employee':employee,'attendance_date':day,'docstatus':1}, fields=['status','working_hours','late_entry','early_exit'])
    if rules['outage']: return dict(row, finding='Access disruption reported — HR verification required', actionable=False)
    offs = {int(x.strip()) for x in str(rules['weekly_off'] or '').split(',') if x.strip()}
    if day.weekday() in offs: return dict(row, finding='Approved weekly off', actionable=False)
    # Weekly offs come from effective policy; retain public holidays from employee calendar.
    calendar = emp.holiday_list or frappe.db.get_value('Company',emp.company,'default_holiday_list')
    if not calendar: return dict(row, finding='Holiday calendar missing', actionable=False, setup_issue=True)
    cal = frappe.get_doc('Holiday List',calendar)
    if not getdate(cal.from_date) <= day <= getdate(cal.to_date): return dict(row, finding='Holiday calendar expired / not yet valid', actionable=False, setup_issue=True)
    if frappe.db.exists('Holiday',{'parent':calendar,'parenttype':'Holiday List','holiday_date':day,'weekly_off':0}): return dict(row, finding='Public holiday', actionable=False)
    leave = frappe.get_all('Leave Application',filters={'employee':employee,'docstatus':1,'status':'Approved','from_date':['<=',day],'to_date':['>=',day]},fields=['half_day','half_day_date'])
    for item in leave:
        if not item.half_day: return dict(row,finding='Approved leave',actionable=False)
        if not item.half_day_date or getdate(item.half_day_date)==day: return dict(row,finding='Half-day leave — manual review',actionable=False)
    start,end,ready = window(day,rules)
    if now_datetime() < ready: return dict(row,finding='Shift / grace period incomplete',actionable=False)
    # Data completeness is an explicit integration watermark, never inferred from newest punch.
    watermark = frappe.conf.get('neotec_attendance_sync_through')
    close = end + timedelta(minutes=int(rules['collection_after_minutes'] or 0))
    if not watermark or get_datetime(watermark) <= close: return dict(row,finding='Awaiting verified source synchronization',actionable=False,setup_issue=True)
    raw = frappe.get_all('Employee Checkin',filters={'employee':employee,'time':['between',[start-timedelta(hours=1),close]],'skip_auto_attendance':0},fields=['time','log_type'],order_by='time')
    row['punches'] = [str(p.time) for p in raw]
    if not raw: return dict(row,finding='No punches — review required',actionable=True)
    if rules['punch_mode']=='Check-in only':
        row['calculated_checkout'] = str(end)
        row['calculated_checkout_note'] = 'Policy-calculated only; not actual presence or approved overtime'
        return dict(row,finding='Check-in recorded; checkout calculated by approved policy',actionable=False)
    if len(raw)%2: return dict(row,finding='Unpaired punch — review required',actionable=True)
    hours = sum((raw[i+1].time-raw[i].time).total_seconds()/3600 for i in range(0,len(raw),2))
    if rules['break_start'] and rules['break_end']:
        # Requires review until paid/unpaid interval reconciliation is implemented.
        return dict(row,finding='Approved emergency break — manual hours review',actionable=False,recorded_hours=hours)
    return dict(row,finding='Short recorded hours — review required' if hours < float(rules['required_hours']) else 'Punch pairs recorded',actionable=hours < float(rules['required_hours']),recorded_hours=round(hours,2))


def preview(date=None):
    day=getdate(date) if date else now_datetime().date()-timedelta(days=1)
    employees=frappe.conf.get('neotec_attendance_employees') or []
    return [evaluate(employee,day) for employee in employees]


def _hr_users():
    users=set(frappe.get_all('Has Role',filters={'parenttype':'User','role':['in',['HR Manager','HR User']]},pluck='parent'))
    return [u for u in users if u not in ('Administrator','Guest') and frappe.db.get_value('User',u,'enabled')]


def _deliver(user, subject, rows, key, email=None):
    name=sha256(key.encode()).hexdigest()[:40]
    if frappe.db.exists(LOG,name): return
    if not email: email=frappe.db.get_value('User',user,'email')
    if not email: return
    doc=frappe.get_doc({'doctype':LOG,'recipient':email,'category':subject,'details':frappe.as_json(rows)})
    doc.insert(ignore_permissions=True,set_name=name)
    body='<p>Attendance review. Flags are not automatic absence or payroll deductions.</p><ul>' + ''.join('<li>'+escape(r['date']+' | '+r['employee_name']+' | '+r['finding'])+'</li>' for r in rows)+'</ul>'
    queue=frappe.sendmail(recipients=[email],subject=subject,message=body)
    if not queue: frappe.throw('Email was not queued')
    doc.db_set('email_queue',queue.name)
    if user and frappe.db.get_value('User',user,'enabled'):
        frappe.get_doc({'doctype':'Notification Log','for_user':user,'type':'Alert','subject':subject,'email_content':body,'document_type':LOG,'document_name':doc.name}).insert(ignore_permissions=True)


def daily():
    if not frappe.conf.get('neotec_attendance_policy_enabled'): return
    current=now_datetime()
    if current.hour < 21: return
    start=frappe.conf.get('neotec_attendance_start_date')
    if not start or current.date() < getdate(start): return
    day=current.date()-timedelta(days=1)
    if day < getdate(start): return
    rows=preview(day)
    if current.day == 28:
        for employee in (frappe.conf.get('neotec_attendance_employees') or []):
            try:
                month_rows=[]
                cursor=current.date().replace(day=1)
                while cursor < current.date():
                    month_rows.append(evaluate(employee,cursor))
                    cursor += timedelta(days=1)
                user=frappe.db.get_value('Employee',employee,'user_id')
                email=frappe.db.get_value('Employee',employee,'company_email')
                _deliver(user,'Monthly attendance review',month_rows,f'monthly:{employee}:{current:%Y-%m}',email)
                frappe.db.commit()
            except Exception:
                frappe.db.rollback(); frappe.log_error(title='Monthly attendance delivery failed',message=frappe.get_traceback())
    # HR receives daily review and policy expiry/pending notices; manager only own direct reports.
    notices=[]
    for p in frappe.get_all(POLICY,filters={'docstatus':['in',[0,1]]},fields=['name','employee','scope','valid_to','permanent','docstatus']):
        state='Pending approval' if p.docstatus==0 else None
        if p.docstatus==1 and not p.permanent and p.valid_to:
            remaining=(getdate(p.valid_to)-current.date()).days
            if remaining <= 7: state='Expired' if remaining<0 else f'Expires in {remaining} days'
        if state: notices.append(dict(date=str(current.date()),employee_name=p.employee or p.scope,finding=p.name+': '+state))
    for user in _hr_users():
        try:
            _deliver(user,'Daily HR attendance and exception review',rows+notices,f'hr:{user}:{current.date()}')
            frappe.db.commit()
        except Exception:
            frappe.db.rollback(); frappe.log_error(title='Attendance HR delivery failed',message=frappe.get_traceback())
    managers={}
    for row in rows:
        if row['reports_to']: managers.setdefault(row['reports_to'],[]).append(row)
        if row.get('actionable'):
            try:
                user=frappe.db.get_value('Employee',row['employee'],'user_id')
                _deliver(user,'Attendance correction reminder',[row],f'employee:{row["employee"]}:{day}',row['email'])
                frappe.db.commit()
            except Exception:
                frappe.db.rollback(); frappe.log_error(title='Attendance employee delivery failed',message=frappe.get_traceback())
    for manager,items in managers.items():
        user=frappe.db.get_value('Employee',manager,'user_id')
        if manager in (frappe.conf.get('neotec_attendance_excluded_recipients') or []): continue
        if user and frappe.db.get_value('User',user,'enabled'):
            try:
                _deliver(user,'Daily team attendance review',items,f'manager:{manager}:{day}')
                frappe.db.commit()
            except Exception:
                frappe.db.rollback(); frappe.log_error(title='Attendance manager delivery failed',message=frappe.get_traceback())
