# Neotec Attendance exception-policy pilot 0.2

This is a standalone Frappe app development pilot, not a production-certified release. It uses Python 3.10-compatible code and Frappe APIs shared by v15/v16. Neither framework version was available for integration tests. Nine framework-independent rule tests pass; all Python files compile.

## Delivered
- Exception Desk form: employee/department/company scope, priority, date validity/permanent flag, individual rule overrides, reason, attachment, HR Manager approval, cancellation/amendment.
- Standard Frappe track_changes version history and document timeline. Submitted rules are immutable; cancel/amend to change them. Drafts never affect attendance. Expired records remain auditable and stop applying automatically.
- Effective rules: employee overrides department overrides company; higher priority wins within a scope; same-priority collisions rejected. Company-scoped department matching.
- Configurable hours, overnight end date, one or two weekly offs, reduced hours, check-in-only calculated checkout, dated outage exclusions.
- Employee correction reminder, HR Manager/HR User daily digest with pending/expiring/expired policy notices, reporting-manager digest limited to direct reports. Email + in-app alerts for enabled linked users. HR receives cohort data; restrict role membership appropriately.
- Monthly review on 28th through the 27th. Delivery audit record and deterministic per-recipient/date queue key. No overtime approval, payroll update, Attendance mutation or synthetic Employee Checkin creation.
- Existing legacy notification job is stopped by install to avoid conflicting rule engines. Its source remains intact.

## Deliberate pilot limits / outstanding development
- Approved emergency breaks are recorded as policy intervals but require manual paid/unpaid hours reconciliation. No automated break payroll effect yet.
- Employee self-service request UI and reporting-manager approval workflow are not implemented. HR User creates drafts; a different HR Manager submits; Administrator may override.
- Base hours are the agreed 10:00–19:00, Friday off; it does not yet derive defaults from arbitrary Shift Types/Assignments. Punches use alternating pair interpretation, not explicit IN/OUT mode. One shift per day; overlapping adjacent extended windows need review.
- No general policy-template library, rotating roster, appeal flow, repeat escalation cadence, dashboard or automated overtime calculation yet.
- In-app alerts require linked enabled users. Delivery log is readable only by HR Manager; other recipients should use email rather than the restricted log link.
- Daily checks process yesterday after 21:00 site time (not same-day immediate reminders); monthly and daily schedules do not recover a fully missed sending day. Policies are evaluated historically using current employee/calendar data.
- Policy-scope employee enabled flags and partial unpaid/remote leave need site UAT. No claim of payroll accuracy.
- Generic HR role recipients receive the configured pilot cohort, not a company permission-filtered enterprise population. Never broaden cohort until recipient permission tests pass.
- A same-key database insert protects against duplicate queueing; email delivery retries use Frappe Email Queue. Sent means transport acceptance, not inbox receipt. Email template queueing is not yet tested on the target versions.

## Configuration (kept disabled by default)
site_config.json keys:
- neotec_attendance_policy_enabled: false (boolean)
- neotec_attendance_start_date: first approved working day after restoration; no outage backlog notifications.
- neotec_attendance_employees: []
- neotec_attendance_excluded_recipients: [] (reporting manager digests). HR role users are independently resolved; remove excluded people from the notification role cohort before enabling if necessary.
- neotec_attendance_sync_through: timestamp in site timezone supplied ONLY after the integration confirms all source punches through that time have arrived. Do not set it to now merely to bypass the guard. Missing watermark routes a setup finding to HR and suppresses employee reminders.

Configure any proposed outage interval as a dated approved exception with override_outage=1 and outage=1; dates require HR verification. Do not assume October 16 is a proven start date. Existing Absent records are displayed as recorded; they are not corrected by the policy layer.

## Required v15 AND v16 UAT
Install/migrate; create/save/submit/cancel/amend with HR User and HR Manager; verify self-approval rejection, draft exclusion, expiry boundary, permanent rule, scope hierarchy, overlap rejection, midnight window, 5-hour target, Friday-to-Sunday switch, 2 weekly offs, public holiday conflict, check-in-only distinction, break manual review, delayed source watermark, source outage, no-punch and odd-punch findings. Test two scheduler runs queue one email only; force queue failure and confirm rollback/retry; verify each manager sees only direct reports and excluded recipients receive nothing; verify role membership and company privacy; check monthly date coverage, email table escaping, delivery log access and in-app notification visibility. Only then enable notifications with a reviewed start date.
