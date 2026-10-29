# Attendance Exceptions — HR User Guide

## Before you start

This is a development pilot. Keep automatic sending disabled until HR reviews the cohort, recipients, calendars, source-sync completeness and sample reports. The form is available by searching **Neotec Attendance Exception** in the Desk search bar. HR User can create/save requests; HR Manager can approve by submitting. A different HR Manager must approve the creator's request, except Administrator override.

The app evaluates records for review only. It does not edit standard Attendance, salary deductions, overtime approvals or device punches.

## Form layout

| Tab | Contents |
|---|---|
| Policy & Validity | Employee/department/company scope, validity, permanence, priority, reason and evidence |
| Working Rules | Hours, overnight approval, punch requirements, weekly offs, emergency break and disruption |
| Approval & Activity | Approver, approval time, amended-from reference; use timeline below for changes/comments |

The form uses two columns per section; Frappe controls responsive stacking. Enable only the override checkboxes you need. A visible value does not affect attendance unless its override is checked. An unchecked override inherits a rule. A checked override with a cleared Yes/No value explicitly disables that rule.

## Create and approve

1. Open the exception list and select **Add Neotec Attendance Exception**.
2. Select Scope and Company. For Employee, select the employee; for Department select the department. Company scope applies across that company.
3. Enter Valid From and Valid To. Both dates are inclusive. For an ongoing agreement, check Permanent instead of entering an end date. Outage exclusions cannot be permanent.
4. Keep Priority at 0 unless HR intentionally needs a higher-priority exception within the same scope. Employee rules override department rules, which override company rules. Equal-priority changes to the same setting are conflicts.
5. Describe the management decision and attach evidence as required by your internal process.
6. In Working Rules enable the specific overrides and enter approved values.
7. Save. A draft has no effect.
8. A different HR Manager opens the draft, reviews it and selects Submit. Submission records the approver and time. No employee/manager approval portal is implemented yet.
9. Preview the effective result for the employee/date before enabling production emails.

## Examples

| Requirement | Override selections | Values / notes |
|---|---|---|
| Five-hour day, 1–15 November | Required hours | 5. If actual shift must end at 15:00, also change End time to 15:00; reducing hours alone keeps the original punch window. |
| Ongoing five-hour agreement | Required hours + Permanent | 5; specify the start date and approval reason. |
| Work from 10:00 until 23:00 | End time, optionally Required hours | 23:00; set the target hours independently. A longer collection window is not overtime approval. |
| Overnight 19:00–04:00 | Start time, End time, Overnight | 19:00, 04:00, checked Overnight. End belongs to next calendar day. Adjacent shift overlap remains a manual review limitation. |
| Check-in only | Punch mode | Check-in only. Checkout is calculated from approved end time and is never recorded as an actual device event. |
| Sunday instead of Friday off | Weekly off | 6. Replaces the weekly-off set. |
| Friday and Saturday off | Weekly off | 4,5. |
| Emergency break | Break start + Break end; optional Paid break | Enter both times. This pilot records approval but leaves paid/unpaid hours reconciliation to HR. |
| Site/device disruption | Outage | Check override and Outage; enter verified start and end dates. Missing punches are excluded from employee reminders. Do not guess outage dates from expired sessions. |

Baseline in this pilot: 10:00–19:00, nine hours, Friday off, alternating punch pairs. Public holidays are read separately from the employee calendar. Changing weekly offs does not change public holidays.

## Activity and validity

- Use Comments on the standard document timeline for decisions, explanations and follow-up.
- Track Changes is enabled. Standard Version history records field changes; approval and cancellation also appear through the document lifecycle. This is ordinary Frappe history, not a tamper-proof external audit ledger.
- Submitted does not necessarily mean currently effective. A submitted future policy waits until Valid From; a submitted expired policy remains in history but is ignored by the evaluator.
- To revise an approved exception: Cancel, Amend, edit and obtain fresh approval. Cancellation prevents application of that policy, including historical reevaluation; historical payroll snapshots are not implemented.

## Daily and monthly notifications

| Recipient | Content |
|---|---|
| Employee | Actionable missing/unpaired punches or short-hours flags for yesterday |
| Reporting manager | Only configured employees who currently report directly to that manager |
| HR User / HR Manager | Pilot-cohort daily review plus pending/expiring/expired exception notices |
| Employee monthly review | On the 28th, findings for the 1st–27th |

The job runs hourly but acts after 21:00 site time. This version reviews yesterday, not a live same-day shift. No repeat escalation or recovery for a fully missed send day is implemented. Email and in-app alert delivery are deduplicated by recipient/date/category. Email Queue records distinguish queued, sent and failed delivery; a delivery audit entry does not itself mean the email arrived.

Kishan/Mohsin exclusions are configuration, not source-code defaults. The excluded-recipient list currently suppresses reporting-manager digests only. HR-role recipients are separately resolved; review their role membership before activation. HR users receive the configured cohort and policy notices without enterprise company-permission filtering. Do not broaden use across companies until recipient scoping is completed and tested.

## Next steps for the administrator

1. Update the app safely and run migrate so the layout is applied to existing forms.
2. Open the form, hard-refresh and verify the three tabs and paired fields.
3. Review an employee five-hour sample, an overnight sample and two-weekly-off sample on a TEST site.
4. Configure the explicit employee cohort and excluded reporting-manager recipients.
5. Set the first approved reporting date after restoration; avoid outage-backlog reminders.
6. Connect the source integration's verified sync-through timestamp. Do not set it to current time just to bypass the completeness guard.
7. Verify employee, HR and manager email recipients and notification visibility using test data. The app does not provide a recipient-routing settings screen yet.
8. Complete site UAT on both Frappe/HRMS v15 and v16. Python rule tests are not framework certification.
9. Only after those checks, enable sending for the pilot and monitor Email Queue, Error Log and Neotec Attendance Delivery.

The app currently does not change payroll, create actual automatic checkout punches, provide employee self-service, support reporting-manager approval, or calculate paid/unpaid breaks automatically.
