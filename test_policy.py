import unittest
from neotec_attendance.policy_engine import resolve,window
E=dict(name='E1',company='C1',department='D1')
def p(**kw):
    return dict(name='P',scope='Employee',employee='E1',company='C1',docstatus=1,valid_from='2026-10-01',valid_to='2026-10-31',**kw)
class Rules(unittest.TestCase):
    def test_expired(self): self.assertEqual(resolve(E,[p(override_required_hours=1,required_hours=5)],'2026-11-01')['required_hours'],9)
    def test_draft(self):
        a=p(override_required_hours=1,required_hours=5); a['docstatus']=0
        self.assertEqual(resolve(E,[a],'2026-10-20')['required_hours'],9)
    def test_permanent(self): self.assertEqual(resolve(E,[p(permanent=1,override_required_hours=1,required_hours=5)],'2027-01-01')['required_hours'],5)
    def test_other_employee(self):
        a=p(override_required_hours=1,required_hours=5); a['employee']='E2'
        self.assertEqual(resolve(E,[a],'2026-10-20')['required_hours'],9)
    def test_conflict(self):
        with self.assertRaises(ValueError): resolve(E,[p(override_required_hours=1,required_hours=5),p(override_required_hours=1,required_hours=6)],'2026-10-20')
    def test_overnight(self):
        r=resolve(E,[p(override_end_time=1,end_time='02:00:00',override_overnight=1,overnight=1)],'2026-10-20')
        a,b,c=window('2026-10-20',r); self.assertEqual((b-a).total_seconds()/3600,16)
    def test_weekoff(self): self.assertEqual(resolve(E,[p(override_weekly_off=1,weekly_off='4,5')],'2026-10-20')['weekly_off'],'4,5')
    def test_company_boundary(self):
        a=p(override_required_hours=1,required_hours=5); a.update(scope='Department',department='D1',company='C2')
        self.assertEqual(resolve(E,[a],'2026-10-20')['required_hours'],9)
    def test_precedence(self):
        a=p(override_required_hours=1,required_hours=6); a.update(scope='Company')
        b=p(override_required_hours=1,required_hours=5)
        self.assertEqual(resolve(E,[a,b],'2026-10-20')['required_hours'],5)
if __name__=='__main__': unittest.main()
