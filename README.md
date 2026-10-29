# Neotec Attendance

Development pilot 0.2.0. Intended for Frappe/ERPNext/HRMS v15 and v16; framework integration is not yet verified. Do not enable production sending before site UAT.

## Install on a test bench

```bash
bench get-app https://github.com/neodev24/neotec_attendance.git --branch main
bench --site TEST_SITE install-app neotec_attendance
bench --site TEST_SITE migrate
bench restart
```

For the previously hand-created app, commit or back up its local changes before replacing its repository. Do not run get-app over that existing directory. No automatic migration from the legacy preview code is claimed.

## Features

Dated/permanent company, department and employee exceptions; HR approval; version history; expiry notices; reduced working hours; overnight window; flexible weekly offs; calculated checkout; outage exclusion; daily employee/HR/manager notifications and monthly reviews. Sending defaults off; employee cohort defaults empty. No employee identities, credentials or production logs are shipped.

## Testing

```bash
python -m unittest test_policy -v
```

The CI matrix tests Python 3.10 and 3.12 rule logic. It does NOT install Frappe or certify either Frappe major version. See PILOT_LIMITATIONS.md for the remaining integration work, configuration and UAT requirements.
