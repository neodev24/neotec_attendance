from pathlib import Path
from types import SimpleNamespace as NS, ModuleType
from unittest.mock import patch
from copy import deepcopy
import importlib.util
import unittest

class Field:
    def __init__(self,data): self.data=dict(data);self.fieldname=data['fieldname']
    def as_dict(self): return dict(self.data)

class Doc:
    def __init__(self,data,registry,test):
        self.data=deepcopy(data);self.fields=[Field(f) for f in data['fields']]
        self.registry=registry;self.test=test
    def insert(self,**kwargs):
        for field in self.fields:
            if field.data['fieldtype']=='Table': self.test.assertIn(field.data['options'],self.registry)
        self.registry[self.data['name']]=self
        return self
    def set(self,key,value): setattr(self,key,value)
    def append(self,key,value): getattr(self,key).append(Field(value))
    def save(self,**kwargs):
        self.data['fields']=[f.as_dict() for f in self.fields]
        return self

class SchemaTests(unittest.TestCase):
    def schema(self,customize=False):
        created={}
        def document(*args):
            if isinstance(args[0],dict): return Doc(args[0],created,self)
            return created[args[1]]
        frappe=ModuleType('frappe');frappe.db=NS(exists=lambda dt,name:name in created);frappe.get_doc=document;frappe.clear_cache=lambda **kw:None
        settings=ModuleType('neotec_attendance.settings');settings.SETTINGS='Neotec Attendance Settings'
        with patch.dict('sys.modules',{'frappe':frappe,'neotec_attendance.settings':settings}):
            spec=importlib.util.spec_from_file_location('neotec_attendance.setup_under_test',Path(__file__).parent/'neotec_attendance/setup_settings.py')
            mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
            mod.install()
            if customize:
                created[settings.SETTINGS].append('fields',dict(fieldname='customer_reference',label='Customer Reference',fieldtype='Data'))
                created[settings.SETTINGS].saved_single_values={'enabled':1,'start_date':'2026-11-01'}
            first=[f.fieldname for f in created[settings.SETTINGS].fields]
            mod.install()
            self.assertEqual(first,[f.fieldname for f in created[settings.SETTINGS].fields])
        return created

    def test_sending_defaults_off(self):
        schema=self.schema()['Neotec Attendance Settings']
        fields={f.fieldname:f.data for f in schema.fields}
        for name in ('enabled','notify_employee','notify_manager','notify_hr','monthly_enabled','email_enabled','in_app_enabled'):
            self.assertEqual(fields[name]['default'],0)

    def test_child_tables_created_before_settings(self): self.assertEqual(len(self.schema()),5)

    def test_settings_only_system_manager_can_configure(self):
        schema=self.schema()['Neotec Attendance Settings']
        self.assertEqual([r['role'] for r in schema.data['permissions']],['System Manager'])

    def test_five_ordered_setup_tabs(self):
        doc=self.schema()['Neotec Attendance Settings']
        tabs=[f.data['label'] for f in doc.fields if f.data['fieldtype']=='Tab Break']
        self.assertEqual(tabs,['1. Setup Guide','2. Companies & Employees','3. Notifications','4. Schedule','5. Review & Activate'])

    def test_preserve_custom_field_and_saved_activation(self):
        doc=self.schema(customize=True)['Neotec Attendance Settings']
        self.assertIn('customer_reference',[f.fieldname for f in doc.fields])
        self.assertEqual(doc.saved_single_values,{'enabled':1,'start_date':'2026-11-01'})

    def test_no_duplicate_fields_on_repeated_upgrade(self):
        for doc in self.schema().values():
            names=[f.fieldname for f in doc.fields]
            self.assertEqual(len(names),len(set(names)))

    def test_child_dialogs_have_columns_and_guidance(self):
        for name in ('Neotec Attendance Company','Neotec Attendance Recipient','Neotec Attendance Exclusion'):
            doc=self.schema()[name]
            self.assertTrue(any(f.data['fieldtype']=='Column Break' for f in doc.fields))
            self.assertTrue(any(f.data.get('description') for f in doc.fields))

if __name__=='__main__': unittest.main()
