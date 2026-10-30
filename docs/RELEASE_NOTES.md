# 0.3.1 development release

Reorganized Attendance Settings into five guided setup tabs. Added two-column field groups, aligned company/employee/recipient/exclusion row dialogs, field descriptions, and an activation checklist. Readiness and recipient previews display readable tables instead of raw JSON. Templates reuse the exception working-rule layout.

Existing custom DocType schemas are updated on migration; saved Single values, employee/recipient rows and customer-added fields remain intact. Empty exclusion rows now require an employee or user. Sending defaults remain off; migration never changes the stored activation value.

Local checks: 38 tests pass, including repeatable schema migration and saved-value/custom-field preservation checks using framework fakes; Python and JavaScript syntax checks pass. Visual rendering and live Frappe v15/v16 integration remain unverified.

# 0.3.0 development release

Reusable site-local configuration replaces the fixed pilot cohort and office schedule. Added company/population filters, explicit HR routing, global user exclusions, channel switches, reusable optional country-labelled templates, simplified exception types, source-sync guard, HRMS shift/holiday adapters, recipient preview and readiness checks. Daily catch-up is configurable and monthly reviews can retry within that range.

Local validation: 34 rule and mocked-adapter/router tests; Python compilation. CI matrix runs Python 3.10/3.12 tests. v15/v16 framework installation, permissions, custom DocType controllers, client scripts, scheduler and email queueing still require UAT.

Sending defaults off; no legacy site_config activation is imported. Existing exceptions remain Custom, preserving advanced rules. The legacy scheduler is stopped. The release does not mutate check-ins, Attendance, payroll or source sync timestamps.
