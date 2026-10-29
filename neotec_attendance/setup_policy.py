import frappe


def install():
    from .policies import POLICY, LOG
    fields=[]
    def add(name,kind='Data',options=None,**kw):
        f=dict(fieldname=name,label=name.replace('_',' ').title(),fieldtype=kind,**kw)
        if options is not None: f['options']=options
        fields.append(f)
    add('scope','Select','Employee\nDepartment\nCompany',reqd=1)
    add('company','Link','Company',reqd=1)
    add('employee','Link','Employee'); add('department','Link','Department')
    add('priority','Int',default=0)
    add('template','Link','Neotec Attendance Template')
    add('exception_type','Select','Custom\nReduced Hours\nChanged Hours\nOvernight Work\nCheck-in Only\nWeekly Off Change\nEmergency Break\nSite or Device Outage',default='Custom')
    add('valid_from','Date',reqd=1); add('permanent','Check'); add('valid_to','Date')
    add('reason','Small Text',reqd=1); add('supporting_document','Attach')
    specs=[('start_time','Time',None,None),('end_time','Time',None,None),
        ('required_hours','Float',None,None),('weekly_off','Data',None,None),
        ('punch_mode','Select','Pairs\nCheck-in only','Pairs'),('overnight','Check',None,0),
        ('collection_after_minutes','Int',None,60),('grace_minutes','Int',None,120),
        ('break_start','Time',None,None),('break_end','Time',None,None),('break_paid','Check',None,0),('outage','Check',None,0)]
    for name,kind,options,default in specs:
        add('override_'+name,'Check')
        add(name,kind,options,default=default,depends_on='eval:doc.override_'+name)
    add('approved_by','Link','User',read_only=1); add('approved_on','Datetime',read_only=1)
    if not frappe.db.exists('DocType', 'Neotec Attendance Template'):
        template_fields = [dict(fieldname='country',label='Country (optional)',fieldtype='Link',options='Country'), dict(fieldname='title', label='Title', fieldtype='Data', reqd=1), dict(fieldname='disabled', label='Disabled', fieldtype='Check'), dict(fieldname='description', label='Description', fieldtype='Small Text')]
        template_fields += [dict(f) for f in fields if f['fieldname'] == 'exception_type' or f['fieldname'].startswith('override_') or f['fieldname'] in ('start_time','end_time','required_hours','weekly_off','punch_mode','overnight','collection_after_minutes','grace_minutes','break_start','break_end','break_paid','outage')]
        frappe.get_doc(dict(doctype='DocType', name='Neotec Attendance Template', module='Neotec Attendance', custom=1, track_changes=1, autoname='field:title', fields=template_fields, permissions=[dict(role='HR Manager',read=1,write=1,create=1),dict(role='HR User',read=1)])).insert(ignore_permissions=True)
    if not frappe.db.exists('DocType',POLICY):
        frappe.get_doc(dict(doctype='DocType',name=POLICY,module='Neotec Attendance',custom=1,
            is_submittable=1,track_changes=1,autoname='hash',fields=fields,
            permissions=[dict(role='HR Manager',read=1,write=1,create=1,submit=1,cancel=1,amend=1,report=1),
                         dict(role='HR User',read=1,write=1,create=1,report=1)])).insert(ignore_permissions=True)
    if not frappe.db.exists('DocType',LOG):
        frappe.get_doc(dict(doctype='DocType',name=LOG,module='Neotec Attendance',custom=1,autoname='hash',
            fields=[dict(fieldname='recipient',label='Recipient',fieldtype='Data'),dict(fieldname='category',label='Category',fieldtype='Data'),
                dict(fieldname='details',label='Details',fieldtype='Long Text'),dict(fieldname='email_queue',label='Email Queue',fieldtype='Link',options='Email Queue')],
            permissions=[dict(role='HR Manager',read=1,report=1)])).insert(ignore_permissions=True)
    # Prevent the earlier scheduler from sending with the superseded rules.
    old=frappe.db.get_value('Scheduled Job Type',{'method':'neotec_attendance.notifications.run'},'name')
    if old: frappe.db.set_value('Scheduled Job Type',old,'stopped',1)
    existing = frappe.get_doc('DocType', POLICY)
    changed = False
    for fieldname in ('exception_type', 'template'):
        if not any(f.fieldname == fieldname for f in existing.fields):
            existing.append('fields', next(f for f in fields if f['fieldname'] == fieldname))
            changed = True
    if changed:
        existing.save(ignore_permissions=True)
    from .setup_settings import install as install_settings
    install_settings()
    from .form_layout import apply
    apply()
    frappe.db.commit()
    return {'installed':True,'sending_enabled':bool(frappe.db.get_single_value('Neotec Attendance Settings', 'enabled'))}
