"""Framework-independent effective policy resolution; Python 3.10+."""
from datetime import date, datetime, timedelta


def resolve(employee, policies, day):
    day = date.fromisoformat(str(day)[:10])
    rules = dict(start_time='10:00:00', end_time='19:00:00', required_hours=9,
                 weekly_off='4', punch_mode='Pairs', overnight=0,
                 collection_after_minutes=60, grace_minutes=120,
                 break_start=None, break_end=None, break_paid=0,
                 outage=0, sources=[])
    scopes = {'Company': 1, 'Department': 2, 'Employee': 3}
    selected = []
    for p in policies:
        if p.get('docstatus') != 1 or str(p['valid_from'])[:10] > str(day): continue
        if not p.get('permanent') and (not p.get('valid_to') or str(p['valid_to'])[:10] < str(day)): continue
        scope = p['scope']
        if scope == 'Employee' and p.get('employee') != employee['name']: continue
        if scope == 'Department' and (p.get('department') != employee.get('department') or p.get('company') != employee.get('company')): continue
        if scope == 'Company' and p.get('company') != employee.get('company'): continue
        selected.append(p)
    assigned = {}
    for p in sorted(selected, key=lambda p: (scopes[p['scope']], int(p.get('priority') or 0))):
        rank = (scopes[p['scope']], int(p.get('priority') or 0))
        for field in ('start_time','end_time','required_hours','weekly_off','punch_mode','overnight',
                      'collection_after_minutes','grace_minutes','break_start','break_end','break_paid','outage'):
            if not p.get('override_' + field): continue
            if assigned.get(field) == rank: raise ValueError('Conflicting approved policies for ' + field)
            rules[field] = p.get(field)
            assigned[field] = rank
        rules['sources'].append(p['name'])
    return rules


def window(day, rules):
    day = str(day)[:10]
    start = datetime.fromisoformat(day + 'T' + str(rules['start_time']))
    end = datetime.fromisoformat(day + 'T' + str(rules['end_time']))
    if end <= start:
        if not rules['overnight']: raise ValueError('Overnight approval required')
        end += timedelta(days=1)
    return start, end, end + timedelta(minutes=max(int(rules['collection_after_minutes'] or 0), int(rules['grace_minutes'] or 0)))
