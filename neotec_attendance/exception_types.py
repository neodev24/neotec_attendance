from .policy_engine import RULE_FIELDS

TYPE_FIELDS = {
    'Reduced Hours': ('required_hours',),
    'Changed Hours': ('start_time', 'end_time'),
    'Overnight Work': ('start_time', 'end_time', 'overnight'),
    'Check-in Only': ('punch_mode',),
    'Weekly Off Change': ('weekly_off',),
    'Emergency Break': ('break_start', 'break_end', 'break_paid'),
    'Site or Device Outage': ('outage',),
}


def apply_type(doc):
    kind = doc.get('exception_type') or 'Custom'
    if kind == 'Custom':
        return
    if kind not in TYPE_FIELDS:
        raise ValueError('Unsupported exception type')
    for name in RULE_FIELDS:
        doc['override_' + name] = int(name in TYPE_FIELDS[kind])
    if kind == 'Check-in Only':
        doc['punch_mode'] = 'Check-in only'
    if kind == 'Overnight Work':
        doc['overnight'] = 1
    if kind == 'Site or Device Outage':
        doc['outage'] = 1
