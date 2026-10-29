"""Exercise the actual notification router with isolated framework fakes."""
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace as NS, ModuleType
from unittest.mock import patch
import importlib.util
import unittest


@contextmanager
def router(excluded=()):
    frappe=ModuleType('frappe')
    users={'hr_a':{'enabled':1,'email':'hr_a@example.test'},'hr_b':{'enabled':1,'email':'hr_b@example.test'},
           'mgr_a':{'enabled':1,'email':'mgr_a@example.test'},'e1':{'enabled':1,'email':'e1@example.test'}}
    def value(dt,name,fields,**kw):
        if dt=='User': return users.get(name,{}).get(fields)
        if dt=='Employee' and name=='M1': return NS(company='A',user_id='mgr_a',status='Active')
        if dt=='Employee' and name=='E1': return 'e1'
        return None
    frappe.db=NS(get_value=value)
    frappe.whitelist=lambda: lambda fn:fn
    frappe.get_roles=lambda user:['HR Manager'] if user.startswith('hr_') else []
    settings_module=ModuleType('neotec_attendance.settings')
    settings_module.excluded_users=lambda settings:set(excluded)
    utils=ModuleType('frappe.utils')
    for key in ('getdate','now_datetime','get_datetime'): setattr(utils,key,lambda *a:None)
    docmodule=ModuleType('frappe.model.document');docmodule.Document=object
    with patch.dict('sys.modules',{'frappe':frappe,'frappe.utils':utils,'frappe.model.document':docmodule,'neotec_attendance.settings':settings_module}):
        spec=importlib.util.spec_from_file_location('neotec_attendance.routing_under_test',Path(__file__).parent/'neotec_attendance/policies.py')
        mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        yield mod


def settings():
    return NS(notify_employee=1,notify_manager=1,notify_hr=1,hr_recipients=[
        NS(enabled=1,company='A',user='hr_a',audience='HR Manager'),
        NS(enabled=1,company='B',user='hr_b',audience='HR Manager')])


class RoutingTests(unittest.TestCase):
    def test_hr_company_isolation(self):
        rows=[dict(employee='E1',company='A',actionable=True,email='e1@example.test',reports_to='M1')]
        with router() as mod:
            targets=mod._targets('A',rows,settings())
        self.assertEqual({t['user'] for t in targets},{'e1','mgr_a','hr_a'})
        self.assertNotIn('hr_b',{t['user'] for t in targets})

    def test_exclusion_suppresses_hr_manager_and_employee(self):
        rows=[dict(employee='E1',company='A',actionable=True,email='e1@example.test',reports_to='M1')]
        with router(('e1','mgr_a','hr_a')) as mod:
            self.assertEqual(mod._targets('A',rows,settings()),[])

    def test_manager_gets_only_direct_reports(self):
        rows=[dict(employee='E1',company='A',actionable=False,email=None,reports_to='M1'),
              dict(employee='E2',company='A',actionable=False,email=None,reports_to=None)]
        with router() as mod:
            targets=mod._targets('A',rows,settings())
        manager=next(t for t in targets if t['audience']=='Reporting Manager')
        self.assertEqual(manager['employees'],['E1'])

    def test_switches_disable_delivery_audiences(self):
        cfg=settings();cfg.notify_employee=cfg.notify_manager=cfg.notify_hr=0
        with router() as mod:
            self.assertEqual(mod._targets('A',[dict(employee='E1',actionable=True,reports_to='M1')],cfg),[])

if __name__=='__main__': unittest.main()
