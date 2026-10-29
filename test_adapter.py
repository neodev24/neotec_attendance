"""Adapter contract tests with explicit fake data; not Frappe integration tests."""
from datetime import datetime, date
from pathlib import Path
from types import SimpleNamespace as NS, ModuleType
from unittest.mock import patch
import importlib.util
import unittest


def load_adapter(frappe):
    utils = ModuleType('frappe.utils')
    utils.getdate = lambda value: date.fromisoformat(str(value)[:10])
    with patch.dict('sys.modules', {'frappe': frappe, 'frappe.utils': utils}):
        spec = importlib.util.spec_from_file_location('neotec_attendance.adapter_under_test', Path(__file__).parent/'neotec_attendance/hrms_adapter.py')
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        return mod


class AdapterTests(unittest.TestCase):
    def test_overnight_strict_pair(self):
        mod=load_adapter(NS())
        rows=[NS(time=datetime(2026,11,1,20),log_type='IN'),NS(time=datetime(2026,11,2,4),log_type='OUT')]
        hours,missing=mod.punch_hours(rows,'Strictly based on Log Type in Employee Checkin','Every Valid Check-in and Check-out')
        self.assertEqual(hours,8);self.assertFalse(missing)

    def test_consecutive_ins_are_not_fabricated(self):
        mod=load_adapter(NS())
        rows=[NS(time=datetime(2026,11,1,8),log_type='IN'),NS(time=datetime(2026,11,1,9),log_type='IN')]
        self.assertEqual(mod.punch_hours(rows,'Strictly based on Log Type in Employee Checkin',''),(None,True))

    def test_out_without_in_is_not_complete(self):
        mod=load_adapter(NS())
        self.assertEqual(mod.punch_hours([NS(time=datetime(2026,11,1,17),log_type='OUT')],'Strictly based on Log Type in Employee Checkin',''),(None,True))

    def test_break_counting_follows_shift_calculation(self):
        mod=load_adapter(NS())
        rows=[NS(time=datetime(2026,11,1,h),log_type='') for h in (8,12,13,17)]
        self.assertEqual(mod.punch_hours(rows,'Alternating entries','Every Valid Check-in and Check-out'),(8,False))
        self.assertEqual(mod.punch_hours(rows,'Alternating entries','First Check-in and Last Check-out'),(9,False))

    def test_historical_assignment_not_discarded_by_status(self):
        calls=[]
        def get_all(doctype,**kwargs):
            calls.append(kwargs)
            return [NS(shift_type='Historical',end_date=date(2026,11,5))]
        mod=load_adapter(NS(get_all=get_all,get_doc=lambda dt,name:NS(name=name)))
        shift=mod.shift_for_day(NS(name='E',default_shift='Fallback'),'2026-11-01')
        self.assertEqual(shift.name,'Historical')
        self.assertNotIn('status',calls[0]['filters'])

    def test_multiple_assignments_require_review(self):
        mod=load_adapter(NS(get_all=lambda *a,**kw:[NS(shift_type='A',end_date=None),NS(shift_type='B',end_date=None)]))
        with self.assertRaises(ValueError): mod.shift_for_day(NS(name='E',default_shift=None),'2026-11-01')

    def test_default_shift_when_no_assignment(self):
        mod=load_adapter(NS(get_all=lambda *a,**kw:[],get_doc=lambda dt,name:NS(name=name)))
        self.assertEqual(mod.shift_for_day(NS(name='E',default_shift='Fallback'),'2026-11-01').name,'Fallback')

    def test_no_shift_is_not_a_guessed_office_schedule(self):
        mod=load_adapter(NS(get_all=lambda *a,**kw:[]))
        self.assertIsNone(mod.shift_for_day(NS(name='E',default_shift=None),'2026-11-01'))
        self.assertNotIn('start_time',mod.baseline(None,NS(required_hours=0),NS(grace_minutes=90)))

if __name__=='__main__': unittest.main()
