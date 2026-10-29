frappe.ui.form.on('Neotec Attendance Settings', {
    refresh(frm) {
        frm.add_custom_button(__('Check Readiness'), () => {
            if (frm.is_dirty()) return frappe.msgprint(__('Save the settings first.'));
            frappe.call({method: 'neotec_attendance.settings.readiness', callback(r) {
                frappe.msgprint({title: __('Attendance Setup Review'), message: '<pre>' + frappe.utils.escape_html(JSON.stringify(r.message, null, 2)) + '</pre>'});
            }});
        });
        frm.add_custom_button(__('Preview Recipient Routing'), () => {
            if (frm.is_dirty()) return frappe.msgprint(__('Save the settings first.'));
            frappe.call({method: 'neotec_attendance.policies.routing_preview', callback(r) {
                frappe.msgprint({title: __('Recipients — No Emails Sent'), message: '<pre>' + frappe.utils.escape_html(JSON.stringify(r.message, null, 2)) + '</pre>'});
            }});
        });
    }
});
