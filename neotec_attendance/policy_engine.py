"""Framework-independent rules. Business defaults must be supplied by HRMS/settings."""
from datetime import date, datetime, time, timedelta

RULE_FIELDS = ('start_time', 'end_time', 'required_hours', 'weekly_off', 'punch_mode',
               'overnight', 'collection_after_minutes', 'grace_minutes', 'break_start',
               'break_end', 'break_paid', 'outage')


def clock(value):
    if isinstance(value, timedelta):
        seconds = int(value.total_seconds())
        if not 0 <= seconds < 86400:
            raise ValueError('Time must be within one day')
        return time(seconds // 3600, seconds % 3600 // 60, seconds % 60)
    if isinstance(value, time):
        return value
    if not value:
        raise ValueError('Start and end times require an assigned shift or approved exception')
    return time.fromisoformat(str(value))


def resolve(employee, policies, day, baseline=None):
    day = date.fromisoformat(str(day)[:10])
    rules = {key: None for key in RULE_FIELDS}
    rules.update(overnight=0, collection_after_minutes=0, grace_minutes=0,
                 break_paid=0, outage=0, sources=[])
    rules.update(baseline or {})
    scopes = {'Company': 1, 'Department': 2, 'Employee': 3}
    selected = []
    for p in policies:
        if p.get('company') != employee.get('company'):
            continue
        if p.get('docstatus') != 1 or not p.get('valid_from') or str(p['valid_from'])[:10] > str(day):
            continue
        if not p.get('permanent') and (not p.get('valid_to') or str(p['valid_to'])[:10] < str(day)):
            continue
        scope = p.get('scope')
        if scope not in scopes:
            raise ValueError('Unsupported policy scope')
        if scope == 'Employee' and p.get('employee') != employee['name']:
            continue
        if scope == 'Department' and p.get('department') != employee.get('department'):
            continue
        selected.append(p)
    assigned = {}
    for p in sorted(selected, key=lambda p: (scopes[p['scope']], int(p.get('priority') or 0))):
        rank = (scopes[p['scope']], int(p.get('priority') or 0))
        for field in RULE_FIELDS:
            if not p.get('override_' + field):
                continue
            if assigned.get(field) == rank:
                raise ValueError('Conflicting approved policies for ' + field)
            rules[field] = p.get(field)
            assigned[field] = rank
        rules['sources'].append(p['name'])
    return rules


def window(day, rules):
    day = date.fromisoformat(str(day)[:10])
    start = datetime.combine(day, clock(rules['start_time']))
    end = datetime.combine(day, clock(rules['end_time']))
    if end <= start:
        if not rules['overnight']:
            raise ValueError('Overnight approval required')
        end += timedelta(days=1)
    return start, end, end + timedelta(minutes=max(
        int(rules['collection_after_minutes'] or 0), int(rules['grace_minutes'] or 0)))


def selected_employees(employees, companies, selections, exclusions):
    """All filters are company scoped; opt-in and exclusions are explicit."""
    configs = {c['company']: c for c in companies if c.get('enabled')}
    chosen = set(selections)
    excluded = set(exclusions)
    result = []
    for employee in employees:
        config = configs.get(employee.get('company'))
        if not config or employee['name'] in excluded or employee.get('status') != 'Active':
            continue
        if not config.get('include_all_active') and employee['name'] not in chosen:
            continue
        if any(config.get(k) and employee.get(k) != config[k]
               for k in ('department', 'branch', 'employment_type')):
            continue
        result.append(employee)
    return result


def recipient_allowed(company, user, audience, routes, excluded_users):
    return bool(user and user not in set(excluded_users) and any(
        r.get('enabled') and r.get('company') == company and r.get('user') == user
        and r.get('audience') == audience for r in routes))
