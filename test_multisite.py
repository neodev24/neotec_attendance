import unittest
from datetime import datetime, timedelta
from neotec_attendance.policy_engine import resolve, window, selected_employees, recipient_allowed
from neotec_attendance.exception_types import apply_type

class SiteRules(unittest.TestCase):
    def test_no_business_defaults(self):
        rules = resolve({'name': 'E', 'company': 'A'}, [], '2026-11-01')
        self.assertIsNone(rules['start_time'])
        self.assertIsNone(rules['weekly_off'])
        self.assertIsNone(rules['required_hours'])
        with self.assertRaises(ValueError): window('2026-11-01', rules)

    def test_site_baselines_do_not_leak(self):
        a = resolve({'name': 'E', 'company': 'A'}, [], '2026-11-01', {'start_time': '08:00', 'end_time': '16:00'})
        b = resolve({'name': 'E', 'company': 'A'}, [], '2026-11-01', {'start_time': '12:00', 'end_time': '20:00'})
        self.assertEqual(window('2026-11-01', a)[0].hour, 8)
        self.assertEqual(window('2026-11-01', b)[0].hour, 12)

    def test_opt_in_only(self):
        employees = [{'name':'E1','company':'A','status':'Active'}, {'name':'E2','company':'B','status':'Active'}]
        self.assertEqual(selected_employees(employees, [], [], []), [])
        self.assertEqual(selected_employees(employees, [{'company':'A','enabled':1}], [], []), [])

    def test_employee_cannot_cross_company(self):
        employees = [{'name':'E1','company':'A','status':'Active'}, {'name':'E2','company':'B','status':'Active'}]
        self.assertEqual([e['name'] for e in selected_employees(employees, [{'company':'A','enabled':1}], ['E1','E2'], [])], ['E1'])

    def test_exclusion_and_department_filters(self):
        employees = [{'name':n,'company':'A','status':'Active','department':d} for n,d in [('E1','D1'),('E2','D1'),('E3','D2')]]
        out = selected_employees(employees,[{'company':'A','enabled':1,'include_all_active':1,'department':'D1'}],[],['E2'])
        self.assertEqual([e['name'] for e in out],['E1'])

    def test_role_alone_is_not_routing_permission(self):
        self.assertFalse(recipient_allowed('A','hr@example.test','HR Manager',[],[]))
        route=[{'company':'A','user':'hr@example.test','audience':'HR Manager','enabled':1}]
        self.assertTrue(recipient_allowed('A','hr@example.test','HR Manager',route,[]))
        self.assertFalse(recipient_allowed('B','hr@example.test','HR Manager',route,[]))
        self.assertFalse(recipient_allowed('A','hr@example.test','HR Manager',route,['hr@example.test']))

    def test_company_boundary_for_employee_policy(self):
        policy={'name':'P','company':'B','scope':'Employee','employee':'E1','docstatus':1,'valid_from':'2026-01-01','permanent':1,'override_required_hours':1,'required_hours':5}
        self.assertEqual(resolve({'name':'E1','company':'A'},[policy],'2026-11-01',{'required_hours':8})['required_hours'],8)

    def test_timedelta_time_and_overnight(self):
        rules={'start_time':timedelta(hours=20),'end_time':timedelta(hours=4),'overnight':1}
        a,b,c=window('2026-11-01',rules | {'collection_after_minutes':60,'grace_minutes':120})
        self.assertEqual(b.date().isoformat(),'2026-11-02')
        self.assertEqual((b-a).total_seconds()/3600,8)
        self.assertEqual(c.hour,6)

    def test_type_removes_irrelevant_override_flags(self):
        doc={'exception_type':'Reduced Hours','required_hours':5,'override_outage':1,'outage':1}
        apply_type(doc)
        self.assertEqual(doc['override_required_hours'],1)
        self.assertEqual(doc['override_outage'],0)

    def test_custom_preserves_existing_overrides(self):
        doc={'exception_type':'Custom','override_weekly_off':1,'weekly_off':'5,6'}
        before=dict(doc);apply_type(doc);self.assertEqual(doc,before)

if __name__ == '__main__': unittest.main()
