from pathlib import Path
from types import SimpleNamespace as NS, ModuleType
from unittest.mock import patch
import importlib.util
import unittest

class SchemaTests(unittest.TestCase):
    def schema(self):
        created={}
        def document(data):
            def insert(**kwargs):
                for field in data['fields']:
                    if field['fieldtype']=='Table':
                        self.assertIn(field['options'],created)
                self.assertEqual(len(data['fields']),len({f['fieldname'] for f in data['fields']}))
                created[data['name']]=data
            return NS(insert=insert)
        frappe=ModuleType('frappe');frappe.db=NS(exists=lambda dt,name:name in created);frappe.get_doc=document
        settings=ModuleType('neotec_attendance.settings');settings.SETTINGS='Neotec Attendance Settings'
        with patch.dict('sys.modules',{'frappe':frappe,'neotec_attendance.settings':settings}):
            spec=importlib.util.spec_from_file_location('neotec_attendance.setup_under_test',Path(__file__).parent/'neotec_attendance/setup_settings.py')
            mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
            mod.install();mod.install()
        return created

    def test_sending_defaults_off(self):
        schema=self.schema()['Neotec Attendance Settings']
        fields={f['fieldname']:f for f in schema['fields']}
        for name in ('enabled','notify_employee','notify_manager','notify_hr','monthly_enabled','email_enabled','in_app_enabled'):
            self.assertEqual(fields[name]['default'],0)

    def test_child_tables_created_before_settings(self):
        self.assertEqual(len(self.schema()),5)

    def test_settings_only_system_manager_can_configure(self):
        schema=self.schema()['Neotec Attendance Settings']
        self.assertEqual([r['role'] for r in schema['permissions']],['System Manager'])

if __name__=='__main__': unittest.main()
