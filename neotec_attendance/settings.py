"""Site-local, company-scoped configuration. No cross-site service calls."""
import frappe
from frappe.model.document import Document
from .policy_engine import selected_employees

SETTINGS = 'Neotec Attendance Settings'


class AttendanceSettings(Document):
    def validate(self):
        companies = [r.company for r in self.companies]
        if len(companies) != len(set(companies)):
            frappe.throw('Use one configuration row per company')
        if self.enabled and not self.start_date:
            frappe.throw('Set the first reporting date before enabling notifications')
        if not 1 <= int(self.monthly_day or 0) <= 28:
            frappe.throw('Monthly review day must be between 1 and 28')
        if not 1 <= int(self.catchup_days or 0) <= 7:
            frappe.throw('Catch-up days must be between 1 and 7')
        if int(self.grace_minutes or 0) < 0:
            frappe.throw('Grace minutes cannot be negative')
        for config in self.companies:
            if not 0 <= float(config.required_hours or 0) <= 24:
                frappe.throw('Company required hours must be 0–24')
        for exclusion in self.exclusions:
            if not exclusion.employee and not exclusion.user:
                frappe.throw('Each exclusion needs an employee or a user')
        for row in self.hr_recipients:
            if row.company not in companies:
                frappe.throw('Configure the recipient company first')
            if row.audience not in ('HR Manager', 'HR User') or row.audience not in frappe.get_roles(row.user):
                frappe.throw('The selected HR recipient must hold the specified role')
            if not frappe.db.get_value('User', row.user, 'enabled'):
                frappe.throw('Notification recipient is disabled')
        if self.enabled and not (self.email_enabled or self.in_app_enabled):
            frappe.throw('Enable at least one notification channel')


def get_settings():
    return frappe.get_single(SETTINGS)


def company_config(company, settings=None):
    settings = settings or get_settings()
    return next((r for r in settings.companies if r.company == company and r.enabled), None)


def cohort(settings=None):
    settings = settings or get_settings()
    employees = frappe.get_all('Employee', filters={'status': 'Active'},
        fields=['name', 'company', 'status', 'department', 'branch', 'employment_type'])
    return selected_employees(employees, [r.as_dict() for r in settings.companies],
        [r.employee for r in settings.employees], [r.employee for r in settings.exclusions if r.employee])


def excluded_users(settings=None):
    settings = settings or get_settings()
    users = {r.user for r in settings.exclusions if r.user}
    for row in settings.exclusions:
        if row.employee:
            user = frappe.db.get_value('Employee', row.employee, 'user_id')
            if user:
                users.add(user)
    return users


@frappe.whitelist()
def readiness():
    frappe.only_for('System Manager')
    settings = get_settings()
    employees = cohort(settings)
    findings = []
    for employee in employees:
        doc = frappe.get_doc('Employee', employee['name'])
        if not (doc.company_email or doc.user_id):
            findings.append({'employee': doc.name, 'issue': 'No notification address'})
        if not doc.reports_to:
            findings.append({'employee': doc.name, 'issue': 'No reporting manager'})
        if not doc.default_shift and not frappe.db.exists('Shift Assignment', {'employee': doc.name, 'docstatus': 1}):
            findings.append({'employee': doc.name, 'issue': 'No shift assignment or default shift'})
    from .policies import evaluate
    for employee in employees:
        try:
            row = evaluate(employee['name'], frappe.utils.add_days(frappe.utils.today(), -1), settings)
            if row.get('setup_issue'):
                findings.append({'employee': employee['name'], 'issue': row['finding']})
        except Exception:
            findings.append({'employee': employee['name'], 'issue': 'Evaluation failed; inspect Error Log'})
    return {'enabled': bool(settings.enabled), 'timezone': frappe.db.get_single_value('System Settings', 'time_zone'),
            'companies': [r.company for r in settings.companies if r.enabled],
            'employee_count': len(employees), 'issues': findings}
