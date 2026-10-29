# Neotec Attendance

Version 0.3.0 is a reusable attendance-exception and notification **development release** for Frappe / ERPNext / HRMS. Each installed site has independent settings, companies, employees, approvals and logs. No external tenant registry or cross-site data aggregation is used.

## What changed

- **Neotec Attendance Settings**: per-site activation, reporting date, notification time, catch-up range, channels and audience switches.
- Explicit per-company employee populations with branch, department and employment-type filters. An empty configuration selects nobody.
- Explicit company-to-HR recipient routing; reporting managers receive only direct-report rows. Employee/user exclusions apply to routing. HR roles alone do not subscribe people.
- Normal times, punch windows, holiday lists and punch interpretation come from HRMS Shift Assignment / Shift Type. No fixed office hours or Friday assumption.
- Purpose-based exception form and reusable, optional country-labelled templates. Legacy exceptions remain Custom and retain their values.
- Readiness and routing-preview buttons. Notifications remain disabled until the site administrator opts in.

## Install on a test bench

```bash
bench get-app https://github.com/neodev24/neotec_attendance.git --branch main
bench --site TEST_SITE install-app neotec_attendance
bench --site TEST_SITE migrate
bench build --app neotec_attendance
bench restart
```

Do not get-app over an existing hand-created app directory. Back up / commit local changes before switching that installation to this repository.

## Upgrade an existing GitHub installation

```bash
cd apps/neotec_attendance
git status --short
# Continue only if the working tree is clean.
git pull --ff-only origin main
cd ../..
bench --site TEST_SITE migrate
bench build --app neotec_attendance
bench --site TEST_SITE clear-cache
bench restart
```

Migrate each chosen site separately. One bench shares code across its sites; upgrading code can affect every site with this app installed. Do not treat a shared-bench upgrade as isolated to a single site.

## Configure

Search Desk for **Neotec Attendance Settings** as System Manager. Keep Enabled off, configure companies and populations, choose recipients and exclusions, then use Check Readiness and Preview Recipient Routing. See [HR usage guide](docs/USER_GUIDE.md) and [multi-site rollout](docs/MULTISITE_ROLLOUT.md).

Legacy `neotec_attendance_*` site_config keys are no longer used. They are not imported automatically: enabling old experimental settings must not subscribe a site or recipient accidentally. Reconfigure explicitly in the new form.

## Validation and compatibility

```bash
python -m unittest discover -v
python -m compileall -q neotec_attendance
```

34 local rule and mocked-adapter/routing tests pass. CI checks Python 3.10 and 3.12; **it does not install or certify Frappe v15/v16**. Official branch sources were checked for the holiday API signature difference. Run live framework integration UAT on one v15 and one v16 test environment before wider rollout.

[Known limitations](PILOT_LIMITATIONS.md) · [Release notes](docs/RELEASE_NOTES.md)
