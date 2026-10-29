# Rollout across independent HRMS sites

## Architecture

Each site's database stores its own Attendance Settings, companies, selections, templates, exceptions and delivery history. No code changes are required for a new customer. There is no master endpoint that reads all tenant data.

Sites sharing a bench also share app code and workers. Update code once per bench, but migrate and configure the selected sites individually. A code rollback affects every installed site on that bench; a database rollback must use the matching site's backup.

## Upgrade from the pilot

Back up site data and commit/back up local app edits first. If the app was created by hand, do not overwrite the directory with bench get-app. Reconcile its Git history separately.

The migration adds Settings, company/population/recipient/exclusion child tables and optional templates, then updates the exception layout without deleting existing rule fields. Existing exception records remain Custom. Existing site_config experimental settings are ignored; no automatic enablement or recipient import takes place. The old preview notification job is stopped to avoid double sending. No existing attendance or check-in is corrected.

## Validation gates

1. Choose one v15 and one v16 TEST site. Install/migrate/build and restart. Confirm blank, disabled settings and no outbound messages.
2. Verify both installed and upgraded exception forms, template copying, draft exclusion, approval, cancellation/amendment and activity history.
3. Configure two companies with different hours, calendar/off days and HR recipients. Verify company isolation and filters; employee/user exclusions must suppress every route.
4. Test historical/default shifts, midnight work, explicit IN/OUT, alternating punches, paid-hour target, holiday lookup and invalid/multiple-shift setup alerts. Existing exception data must remain unchanged.
5. Confirm incomplete source synchronization suppresses employee reminders. Verify an approved outage exclusion and activation cutoff prevent outage-backlog alerts.
6. Preview routes with test users. Enable only the TEST site's settings, use test email accounts, run the scheduler twice, check duplicate prevention, mail failure/retry and in-app notifications. Verify monthly date boundaries and catch-up.
7. After both versions pass, roll out to a small customer/site batch, review findings and delivery logs, then expand. Maintain a site inventory with bench, app commit, Frappe/HRMS major, backup, migration result, configuration owner and activation state.

Do not enable all 49+ sites at once. No automated fleet deployment is shipped in this version.

## Sources checked for adapter contracts

- https://github.com/frappe/hrms/blob/version-15/hrms/hr/doctype/shift_assignment/shift_assignment.py
- https://github.com/frappe/hrms/blob/version-16/hrms/hr/doctype/shift_assignment/shift_assignment.py
- https://github.com/frappe/erpnext/blob/version-15/erpnext/setup/doctype/employee/employee.py
- https://github.com/frappe/erpnext/blob/version-16/erpnext/setup/doctype/employee/employee.py

These source checks do not replace runtime integration tests. No legal-compliance certification is claimed.
