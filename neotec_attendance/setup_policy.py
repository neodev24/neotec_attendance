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
    add('valid_from','Date',reqd=1); add('permanent','Check'); add('valid_to','Date')
    add('reason','Small Text',reqd=1); add('supporting_document','Attach')
    specs=[('start_time','Time',None,'10:00:00'),('end_time','Time',None,'19:00:00'),
        ('required_hours','Float',None,9),('weekly_off','Data',None,'4'),
        ('punch_mode','Select','Pairs\nCheck-in only','Pairs'),('overnight','Check',None,0),
        ('collection_after_minutes','Int',None,60),('grace_minutes','Int',None,120),
        ('break_start','Time',None,None),('break_end','Time',None,None),('break_paid','Check',None,0),('outage','Check',None,0)]
    for name,kind,options,default in specs:
        add('override_'+name,'Check')
        add(name,kind,options,default=default,depends_on='eval:doc.override_'+name)
    add('approved_by','Link','User',read_only=1); add('approved_on','Datetime',read_only=1)
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
    frappe.db.commit()
    return {'installed':True,'sending_enabled':bool(frappe.conf.get('neotec_attendance_policy_enabled'))}
