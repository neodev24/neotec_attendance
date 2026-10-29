"""v15/v16 adapter; historical shift dates and holiday API differences are explicit."""
from datetime import timedelta
from inspect import signature
import frappe
from frappe.utils import getdate
from .policy_engine import clock


def shift_for_day(employee, day):
    day = getdate(day)
    assignments = frappe.get_all('Shift Assignment', filters={
        'employee': employee.name, 'docstatus': 1, 'start_date': ['<=', day]},
        fields=['shift_type', 'end_date'])
    names = {r.shift_type for r in assignments if not r.end_date or getdate(r.end_date) >= day}
    if len(names) > 1:
        raise ValueError('Multiple shifts on this date require manual review')
    name = next(iter(names), None) or employee.default_shift
    return frappe.get_doc('Shift Type', name) if name else None


def holiday_calendar(employee, shift, day):
    from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee
    if shift and shift.get('holiday_list'):
        return shift.holiday_list
    fn = get_holiday_list_for_employee
    kwargs = {'as_on': day} if 'as_on' in signature(fn).parameters else {}
    return fn(employee.name, False, **kwargs)


def baseline(shift, config, settings):
    if not shift:
        return {'grace_minutes': settings.grace_minutes or 0}
    start = clock(shift.start_time)
    end = clock(shift.end_time)
    return {'start_time': start.isoformat(), 'end_time': end.isoformat(),
            'overnight': int(end <= start), 'weekly_off': None,
            'required_hours': config.required_hours or None,
            'punch_mode': 'Pairs',
            'collection_after_minutes': shift.allow_check_out_after_shift_end_time or 0,
            'grace_minutes': settings.grace_minutes or 0}


def punch_hours(raw, mode, calculation):
    """Return (hours, missing_pair); ambiguous/invalid sequences never get fabricated."""
    pairs = []
    if mode == 'Strictly based on Log Type in Employee Checkin':
        opened = None
        for row in raw:
            if row.log_type == 'IN' and opened is None:
                opened = row.time
            elif row.log_type == 'OUT' and opened is not None:
                pairs.append((opened, row.time)); opened = None
            else:
                return None, True
        if opened is not None:
            return None, True
    else:
        if len(raw) % 2:
            return None, True
        pairs = [(raw[i].time, raw[i+1].time) for i in range(0, len(raw), 2)]
    if not pairs:
        return 0, False
    if calculation == 'First Check-in and Last Check-out':
        return (pairs[-1][1] - pairs[0][0]).total_seconds()/3600, False
    return sum((b-a).total_seconds()/3600 for a,b in pairs), False
