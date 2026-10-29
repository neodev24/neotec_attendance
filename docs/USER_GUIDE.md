# HR attendance configuration and exceptions

## 1 Set up this site

A System Manager opens **Neotec Attendance Settings**. Leave Enabled off until review and tests are complete.

1. Set Start Date to the first approved reporting date; older daily backlog is excluded. Use the site's timezone for Run After. Set Catch-up Days (1–7) and Monthly Day (1–28).
2. In Companies add one row per company. Enable only the companies in the pilot.
3. For each company choose Include All Active, or leave it off and add specific employees under Employees. Optional department, branch and employment-type filters apply in both modes. Empty selections do not select everyone.
4. Set Required Hours only if the company has an agreed target. Zero leaves short-hours checks off unless an exception supplies a target. Do not confuse the span of an office shift with paid working hours.
5. Add HR Recipients with Company, User and the user's HR Manager / HR User role. Merely having an HR role does not subscribe someone. Reporting managers are resolved from Employee.reports_to and receive only their direct reports within the company.
6. Add employee and/or user exclusions. Excluded employees leave the report population. Excluded users receive no emails or in-app alerts, including HR digests.
7. Choose employee reminders, reporting-manager digests, HR digests, monthly review and email/in-app channels independently.
8. Save. Use Check Readiness and Preview Recipient Routing. Both operate on saved settings and send nothing. Preview yesterday's date using the server command below if needed.
9. Verify source synchronization settings on each Shift Type. The engine waits until Last Sync of Checkin is later than the effective collection window. Do not advance it without establishing source-data completeness.

## 2 Confirm the normal schedule

The app uses submitted Shift Assignments covering the work date, then Employee.default_shift when no assignment exists. Missing and multiple shifts are setup/manual-review findings. It reads shift start/end, collection margins, IN/OUT interpretation, working-hour calculation and holiday list from HRMS. On v16 the dated employee holiday lookup is used when supported. Weekly offs normally come from the applicable holiday list.

No office hours, fixed weekday off, employee identities or recipient addresses are embedded in the app. Do not change a customer's schedule merely to match a sample.

## 3 Create an exception

Open **Neotec Attendance Exception**. Select an optional Template, then Exception Type, scope, company, employee/department, inclusive start/end dates, reason and supporting evidence. Permanent exceptions require a start date but no end date; outage exclusions must have an end date.

| Type | Relevant fields |
|---|---|
| Reduced Hours | Expected daily hours; normal start/end remain inherited |
| Changed Hours | New start and end times |
| Overnight Work | Start and end times; overnight enabled automatically |
| Check-in Only | Check-in required; end is policy-calculated only |
| Weekly Off Change | Replacement weekday set, Monday=0 through Sunday=6 |
| Emergency Break | Start/end and paid/unpaid flag; hours still require manual reconciliation |
| Site or Device Outage | Dated disruption exclusion; no employee punch reminders |
| Custom | Individual advanced overrides, including combined decisions |

For a five-hour day that must end earlier, use Custom with End Time and Required Hours, or create a combined template. Reducing required hours alone does not move the checkout window. For Friday + Saturday use 4,5 only when those are the approved days for that company/employee; these are examples, not legal defaults.

Employee scope overrides department, which overrides company. Higher priority wins within a scope. Equal-priority competing changes to the same rule are rejected. Exceptions from another company never apply.

Save creates a draft only. A different HR Manager must Submit to approve; Administrator may override. A submitted future policy waits until Valid From; an expired policy stays in history and stops applying. To revise an approved record, Cancel → Amend → approve again.

## 4 Reusable templates

HR Manager opens **Neotec Attendance Template**, enters a unique title, optional country and description, and fills the approved rule values. Use Custom for combined advanced rules. Template defaults are not statutory claims. HR User can read templates but cannot edit them.

Selecting a template copies its values into a draft exception. Existing submitted exceptions are unaffected by later template changes. Validity, scope, evidence and approval remain on each exception. Disabled templates cannot be selected through the form.

## 5 Activity, reminders and reports

Track Changes and the standard document timeline retain changes, comments and approval/cancellation events. This is standard Frappe history, not a tamper-proof external ledger.

Employee reminders contain actionable findings. Manager digests contain only direct-report rows. Explicit company HR recipients receive the company's cohort and pending/expiring/recently expired policy notices. No payroll deductions are made.

Each enabled channel is queued once per recipient/company/category/date using a persistent delivery key. Inspect **Neotec Attendance Delivery**, **Email Queue** and **Error Log** after test runs. An in-app alert has no link to a log that another role cannot read. Sent email means transport acceptance, not inbox receipt.

The monthly review contains completed dates before the configured review day. It is an early review, not a completed month or finalized payroll statement.

## 6 Preview and next steps

```bash
bench --site YOUR_TEST_SITE execute neotec_attendance.settings.readiness
bench --site YOUR_TEST_SITE execute neotec_attendance.policies.preview --kwargs '{"date":"2026-11-02"}'
bench --site YOUR_TEST_SITE execute neotec_attendance.policies.routing_preview
```

Replace the sample date with a completed workday. These are administrator-only operations and do not send emails. Test one v15 and one v16 site, then enable a small employee cohort with test recipients. See MULTISITE_ROLLOUT.md for the deployment sequence and PILOT_LIMITATIONS.md for unfinished features.
