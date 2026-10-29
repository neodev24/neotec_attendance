app_name = "neotec_attendance"
app_title = "Neotec Attendance"
app_publisher = "Neotec"
app_description = "Attendance exception policies, review and reminders"
app_email = "hosting@neotec.ai"
app_license = "mit"
required_apps = ["frappe", "erpnext", "hrms"]
after_install = "neotec_attendance.setup_policy.install"
after_migrate = "neotec_attendance.setup_policy.install"
override_doctype_class = {"Neotec Attendance Exception": "neotec_attendance.policies.AttendanceException", "Neotec Attendance Settings": "neotec_attendance.settings.AttendanceSettings"}
scheduler_events = {"hourly": ["neotec_attendance.policies.daily"]}

doctype_js = {"Neotec Attendance Exception": "public/js/exception.js", "Neotec Attendance Settings": "public/js/settings.js"}
