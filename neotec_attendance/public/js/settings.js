function neotec_escape(value) {
    return frappe.utils.escape_html(String(value === undefined || value === null ? '' : value));
}
function neotec_table(headers, rows) {
    return '<div class="table-responsive"><table class="table table-bordered"><thead><tr>' +
        headers.map(h => '<th>' + neotec_escape(h) + '</th>').join('') + '</tr></thead><tbody>' +
        rows.map(row => '<tr>' + row.map(v => '<td>' + neotec_escape(v) + '</td>').join('') + '</tr>').join('') +
        '</tbody></table></div>';
}
function neotec_settings_result(frm, title, content) {
    frm.fields_dict.setup_status.$wrapper.html('<h5>' + neotec_escape(title) + '</h5>' + content);
    frappe.msgprint({title: title, message: content, wide: true});
}
frappe.ui.form.on('Neotec Attendance Settings', {
    refresh(frm) {
        frm.set_intro(frm.doc.enabled
            ? __('Attendance notifications are enabled on this site. Review recipients before changing the population.')
            : __('Setup mode: attendance notifications are off. Follow tabs 1–5, save, and preview before activation.'),
            frm.doc.enabled ? 'orange' : 'blue');
        frm.add_custom_button(__('Check Readiness'), () => {
            if (frm.is_dirty()) return frappe.msgprint(__('Save the settings first. This check uses saved values.'));
            frappe.call({method: 'neotec_attendance.settings.readiness', callback(r) {
                const data = r.message || {};
                let body = '<p><b>' + __('Selected employees') + ':</b> ' + neotec_escape(data.employee_count || 0) +
                    '<br><b>' + __('Site timezone') + ':</b> ' + neotec_escape(data.timezone) +
                    '<br><b>' + __('Included companies') + ':</b> ' + neotec_escape((data.companies || []).join(', ') || __('None')) + '</p>';
                if ((data.issues || []).length) body += neotec_table([__('Employee'), __('Setup item to review')], data.issues.map(i => [i.employee, i.issue]));
                else body += '<p>' + __('No setup issues were detected by this check. Verify sample attendance and test delivery before activation.') + '</p>';
                body += '<p>' + __('This preview sends no messages. It does not certify payroll or full configuration correctness.') + '</p>';
                neotec_settings_result(frm, __('Attendance Setup Review'), body);
            }});
        });
        frm.add_custom_button(__('Preview Recipient Routing'), () => {
            if (frm.is_dirty()) return frappe.msgprint(__('Save the settings first. This preview uses saved values.'));
            frappe.call({method: 'neotec_attendance.policies.routing_preview', callback(r) {
                const rows = [];
                for (const group of r.message || []) {
                    for (const target of group.recipients || []) rows.push([
                        group.company, target.audience, target.email || target.user,
                        (target.employees || []).join(', ')
                    ]);
                }
                const body = rows.length
                    ? neotec_table([__('Company'), __('Audience'), __('Recipient'), __('Employees included')], rows)
                    : '<p>' + __('No daily recipients match the saved settings and yesterday’s findings. Check the population, audience switches, HR recipient rows and exclusions. Employee reminders appear only for actionable findings.') + '</p>';
                neotec_settings_result(frm, __('Daily Recipients — No Messages Sent'), body + '<p>' + __('This is the daily routing preview. Monthly review uses its separate switch and schedule.') + '</p>');
            }});
        });
    }
});
