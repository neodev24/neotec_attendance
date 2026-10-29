# Development release limits

Version 0.3.0 provides the configurable multi-site foundation. It is not a production-certified attendance or legal-compliance engine.

- Full Frappe/HRMS v15 and v16 integration, permission, installation and email delivery tests have not run in this environment. Local tests use independent rules and explicitly mocked framework data.
- The app does not write Employee Checkin, Attendance, salary deductions or overtime awards. Calculated checkout is displayed as calculated, never as physical attendance.
- Emergency-break approvals are recorded; paid/unpaid working-hour reconciliation remains manual. Nursing protections, legal hour limits, progressive penalties and regional statutory validation are not implemented or seeded.
- Approval is HR User draft → different HR Manager submit, with Administrator override. Reporting-manager approval, employee self-service, appeals and multi-level workflow remain pending.
- A day with multiple distinct assigned shifts is flagged for review. Extended adjacent shift windows and flexible/anytime arrival require further work. Rotating roster integration is not implemented.
- Existing full public holidays are respected. v16 half holidays are flagged for manual review. There is no inference of a statutory holiday from a country label.
- Company required-hours target is optional; 0 means short-hours checks are disabled unless an approved exception supplies a target. Shift presence window is not silently treated as paid hours.
- Daily processing reviews up to seven prior dates, subject to site start date and completed shift/synchronization windows. It is not an immediate same-day shift-end notification service.
- Monthly review covers the first through the day before the configured review day, bounded by the activation start date. It retries within the configured catch-up window and is not a finalized complete-month statement.
- Historical previews use currently stored employee/reporting-manager/calendar data. Approved exception cancellation affects subsequent historical reevaluation. Immutable payroll-period snapshots are not implemented.
- HR recipient authority is explicitly configured per company by System Manager. It is not a substitute for a full company-permission audit of the wider Frappe installation.
- Site settings and company rows are database-local. Sites on the same bench share Python code. No global admin console, automatic cross-site deployment or external license service is included.
- There are no default real employee IDs, recipient addresses, hostnames or outage dates. Template country metadata is descriptive, not a verified legal rule pack.
- Email Queue status is transport state, not proof of inbox receipt. Delivery records are audit references; queued messages retry through standard Frappe email processing.
