frappe.ui.form.on('Neotec Attendance Exception', {
    setup(frm) {
        frm.set_query('employee', () => ({filters: {company: frm.doc.company, status: 'Active'}}));
        frm.set_query('template', () => ({filters: {disabled: 0}}));
    },
    exception_type(frm) {
        if (frm.doc.docstatus !== 0) return;
        const kind = frm.doc.exception_type;
        if (kind === 'Check-in Only') frm.set_value('punch_mode', 'Check-in only');
        if (kind === 'Overnight Work') frm.set_value('overnight', 1);
        if (kind === 'Site or Device Outage') frm.set_value('outage', 1);
    },
    async template(frm) {
        if (!frm.doc.template || frm.doc.docstatus !== 0) return;
        const template = await frappe.db.get_doc('Neotec Attendance Template', frm.doc.template);
        if (template.disabled) return frappe.throw(__('This template is disabled.'));
        const fields = ['start_time','end_time','required_hours','weekly_off','punch_mode','overnight',
            'collection_after_minutes','grace_minutes','break_start','break_end','break_paid','outage'];
        const values = {exception_type: template.exception_type || 'Custom'};
        for (const key of fields) {
            values[key] = template[key];
            values['override_' + key] = template['override_' + key] || 0;
        }
        await frm.set_value(values);
        frappe.show_alert({message: __('Template values copied. Review validity and reason before saving.'), indicator: 'blue'});
    }
});
