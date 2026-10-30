"""Idempotent presentation migration; preserves existing fields and policy data."""
import frappe


def apply():
    name = 'Neotec Attendance Exception'
    if not frappe.db.exists('DocType', name):
        return
    doc = frappe.get_doc('DocType', name)
    existing = {f.fieldname: f.as_dict() for f in doc.fields}
    order = []
    def layout(name, kind, label=None, **kwargs):
        order.append(dict(fieldname=name,fieldtype=kind,label=label or '',**kwargs))
    def field(name, **kwargs):
        if name not in existing: return
        f=existing.pop(name)
        f.update(kwargs)
        order.append(f)
    layout('policy_tab','Tab Break','Policy & Validity')
    layout('intro_help','HTML',options='<div class="alert alert-info">Create a draft, select who it applies to, set validity, and enable only the rules you want to change. Save first; a different HR Manager must submit to approve. Draft and expired exceptions do not apply.</div>')
    field('template', description='Optional reusable rule values. Selecting a template copies its rules into this draft; future template edits do not change submitted exceptions.')
    field('exception_type', label='Exception Type', description='Choose a purpose. Custom keeps individual overrides for advanced cases.')
    layout('scope_section','Section Break','1. Who does this apply to?')
    field('scope',description='Employee overrides Department; Department overrides Company.',in_standard_filter=1,in_list_view=1)
    field('employee',depends_on='eval:doc.scope == "Employee"',mandatory_depends_on='eval:doc.scope == "Employee"',in_list_view=1)
    layout('scope_column','Column Break')
    field('company',in_list_view=1,in_standard_filter=1)
    field('department',depends_on='eval:doc.scope == "Department"',mandatory_depends_on='eval:doc.scope == "Department"')
    layout('validity_section','Section Break','2. Validity & Priority')
    field('valid_from',in_list_view=1)
    field('valid_to',depends_on='eval:!doc.permanent',mandatory_depends_on='eval:!doc.permanent',description='Inclusive end date. Expired exceptions remain in history.')
    layout('validity_column','Column Break')
    field('permanent',description='No end date. Cancel the approved record to end this exception.')
    field('priority',description='Higher number wins within the same scope. Keep 0 unless a deliberate override is needed.')
    layout('reason_section','Section Break','3. Management Decision')
    field('reason',description='Explain the decision, purpose and any conditions. Required for approval.')
    layout('reason_column','Column Break');field('supporting_document',description='Attach management approval or supporting evidence.')
    layout('rules_tab','Tab Break','Working Rules')
    layout('rules_help','HTML',options='<div class="alert alert-info">Unchecked overrides inherit the effective rule. Checked overrides replace it, including unchecked Yes/No values. Normal hours and holidays come from the assigned HRMS shift and calendar; targets and recipients come from Attendance Settings. Calculated checkout is not proof of presence or overtime approval.</div>')
    groups=[('hours_section','4. Working Hours', [('start_time','Change start time'),('end_time','Change end time'),('required_hours','Change required hours'),('overnight','Allow / disallow overnight work')]),('punch_section','5. Punches & Collection Window',[('punch_mode','Change punch requirement'),('collection_after_minutes','Change checkout collection window'),('grace_minutes','Change reminder grace period')]),('off_section','6. Weekly Offs',[('weekly_off','Change weekly offs')]),('break_section','7. Emergency Break — Manual Hours Review',[('break_start','Set break start'),('break_end','Set break end'),('break_paid','Set paid / unpaid break')]),('outage_section','8. Access / Device Disruption',[('outage','Set outage exclusion')])]
    descriptions={'start_time':'Site timezone. Example: 10:00:00.','end_time':'For an end time earlier than start, explicitly allow overnight work.','required_hours':'Expected hours for this exception; does not modify payroll.','weekly_off':'Comma-separated days: Monday=0, Tuesday=1, Wednesday=2, Thursday=3, Friday=4, Saturday=5, Sunday=6. Friday + Saturday: 4,5. Empty means no weekly offs.','punch_mode':'Pairs: alternating punches. Check-in only: approved calculated checkout; no synthetic device punch is created.','collection_after_minutes':'Minutes after the planned end during which punches are collected.','grace_minutes':'Minutes after planned end before evaluation can run. Daily review time and catch-up are configured per site.','break_paid':'Recorded for approval only. Paid/unpaid break-hour calculations require manual review in this pilot.','outage':'Suppress employee missing-punch alerts during an approved dated disruption. An end date is required.'}
    from .exception_types import TYPE_FIELDS
    for section,label,pairs in groups:
        layout(section,'Section Break',label)
        for i,(value,label) in enumerate(pairs):
            if i and i % 2 == 1: layout(section+'_col_'+str(i),'Column Break')
            if i and i % 2 == 0: layout(section+'_row_'+str(i),'Section Break')
            choices = [kind for kind, names in TYPE_FIELDS.items() if value in names]
            custom = '(doc.exception_type == \"Custom\" || !doc.exception_type)'
            visible = ' || '.join('doc.exception_type == ' + repr(kind) for kind in choices)
            field('override_'+value,label=label,depends_on='eval:' + custom)
            field(value,description=descriptions.get(value,''),depends_on='eval:(' + custom + ' && doc.override_' + value + ')' + (' || ' + visible if visible else ''))
    layout('audit_tab','Tab Break','Approval & Activity')
    layout('approval_section','Section Break','9. Approval Record')
    field('approved_by',no_copy=1)
    layout('approval_column','Column Break');field('approved_on',no_copy=1);field('amended_from')
    layout('audit_help','HTML',options='<div class="alert alert-info">Use the standard form timeline below for comments, changes and approval/cancellation history. Draft = not approved; Submitted = approved (effective only within validity); Cancelled = no longer applies. To change an approved exception: Cancel → Amend → obtain approval again.</div>')
    # Keep custom fields added outside this app. Replace only our own layout elements.
    owned_prefixes=('scope_','validity_','reason_','hours_','punch_','off_','break_section','outage_section','approval_')
    for key,f in existing.items():
        if f.get('fieldtype') in ('Section Break','Column Break','Tab Break','HTML') and (key.endswith('_tab') or key.endswith('_help') or key.startswith(owned_prefixes)): continue
        order.append(f)
    doc.set('fields',[])
    for f in order:
        for key in ('name','parent','parentfield','parenttype','idx','creation','modified','owner','modified_by','doctype'): f.pop(key,None)
        doc.append('fields',f)
    doc.track_changes=1
    doc.quick_entry=0
    doc.save(ignore_permissions=True)
    frappe.clear_cache(doctype=name)
    return {'doctype':name,'fields':len(doc.fields),'layout_updated':True}


def apply_template():
    """Reuse the exception rule layout, without exception-only scope/validity fields."""
    name = 'Neotec Attendance Template'
    if not frappe.db.exists('DocType', name):
        return
    template = frappe.get_doc('DocType', name)
    exception = frappe.get_doc('DocType', 'Neotec Attendance Exception')
    existing = {f.fieldname: f.as_dict() for f in template.fields}
    ordered = []
    def layout(fieldname, fieldtype, label='', **kw):
        ordered.append(dict(fieldname=fieldname, fieldtype=fieldtype, label=label, **kw))
    def take(fieldname):
        if fieldname in existing:
            ordered.append(existing.pop(fieldname))
    layout('template_info_tab', 'Tab Break', 'Template Details')
    layout('template_intro', 'HTML', options='<p>A template supplies reusable rule values for new draft exceptions. It does not assign a policy to employees, activate notifications or establish legal compliance. Existing approved exceptions keep their copied values.</p>')
    layout('template_info_section', 'Section Break', 'Name and Purpose')
    take('title'); take('exception_type')
    layout('template_info_column', 'Column Break')
    take('country'); take('disabled')
    layout('template_description_section', 'Section Break', 'Instructions for HR')
    take('description')
    copying = False
    owned_layout = {'template_info_tab','template_intro','template_info_section','template_info_column','template_description_section'}
    for source in exception.fields:
        if source.fieldname == 'rules_tab':
            copying = True
        if source.fieldname == 'audit_tab':
            break
        if not copying:
            continue
        spec = source.as_dict()
        if spec.get('fieldtype') in ('Tab Break', 'Section Break', 'Column Break', 'HTML'):
            owned_layout.add(source.fieldname)
            existing.pop(source.fieldname, None)
            ordered.append(spec)
        elif source.fieldname in existing:
            saved = existing.pop(source.fieldname)
            for key in ('label', 'description', 'depends_on'):
                if key in spec:
                    saved[key] = spec[key]
            ordered.append(saved)
    for key, spec in existing.items():
        if key not in owned_layout:
            ordered.append(spec)
    template.set('fields', [])
    for spec in ordered:
        for key in ('name','parent','parentfield','parenttype','idx','creation','modified','owner','modified_by','doctype'):
            spec.pop(key, None)
        template.append('fields', spec)
    template.track_changes = 1
    template.save(ignore_permissions=True)
    frappe.clear_cache(doctype=name)
