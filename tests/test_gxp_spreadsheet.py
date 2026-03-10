import base64
import hashlib

from odoo.exceptions import UserError
from odoo.tests.common import SavepointCase


class TestGxpSpreadsheetControl(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sheet_model = cls.env['gxp.controlled.sheet']
        cls.version_model = cls.env['gxp.sheet.version']
        cls.sign_wizard_model = cls.env['gxp.sign.wizard']
        cls.change_model = cls.env['gxp.change.control']
        cls.audit_model = cls.env['gxp.audit.event']

    def _create_sheet(self):
        return self.sheet_model.create({
            'name': 'Balance calculation',
            'intended_use': 'Batch release calculation',
        })

    def _create_version(self, sheet):
        raw = b'controlled spreadsheet payload'
        return self.version_model.create({
            'sheet_id': sheet.id,
            'version_major': 1,
            'version_minor': 0,
            'file_name': 'sheet.xlsx',
            'file_binary': base64.b64encode(raw),
            'change_summary': 'Initial issue',
        }), raw

    def test_create_sheet_and_version_hash(self):
        sheet = self._create_sheet()
        version, raw = self._create_version(sheet)
        self.assertTrue(sheet.code.startswith('SHT-'))
        self.assertEqual(version.file_sha256, hashlib.sha256(raw).hexdigest())

    def test_effective_version_is_locked_and_unique(self):
        sheet = self._create_sheet()
        version1, _ = self._create_version(sheet)
        version2 = self.version_model.create({
            'sheet_id': sheet.id,
            'version_major': 1,
            'version_minor': 1,
            'file_name': 'sheet2.xlsx',
            'file_binary': base64.b64encode(b'new payload'),
            'change_summary': 'Revision',
        })
        self.env['gxp.signature.event'].create({
            'res_model': 'gxp.sheet.version',
            'res_id': version1.id,
            'version_id': version1.id,
            'signer_id': self.env.user.id,
            'signer_name_snapshot': self.env.user.name,
            'sign_meaning': 'approval',
            'record_sha256_at_sign': version1.file_sha256,
        })
        version1.action_make_effective()
        self.assertEqual(version1.state, 'effective')
        with self.assertRaises(UserError):
            version1.write({'change_summary': 'forbidden'})

        self.env['gxp.signature.event'].create({
            'res_model': 'gxp.sheet.version',
            'res_id': version2.id,
            'version_id': version2.id,
            'signer_id': self.env.user.id,
            'signer_name_snapshot': self.env.user.name,
            'sign_meaning': 'approval',
            'record_sha256_at_sign': version2.file_sha256,
        })
        version2.action_make_effective()
        self.assertEqual(version2.state, 'effective')
        self.assertEqual(version1.state, 'superseded')

    def test_unlink_blocked_on_regulated_models(self):
        sheet = self._create_sheet()
        version, _ = self._create_version(sheet)
        with self.assertRaises(UserError):
            sheet.unlink()
        with self.assertRaises(UserError):
            version.unlink()

    def test_change_control_requires_linked_version_for_close(self):
        sheet = self._create_sheet()
        change = self.change_model.create({
            'sheet_id': sheet.id,
            'reason_for_change': 'Fix formula',
            'risk_assessment': 'Low',
            'impact_assessment': 'Medium',
            'implementation_plan': 'Retest and deploy',
        })
        with self.assertRaises(UserError):
            change.action_close()

    def test_audit_event_created(self):
        sheet = self._create_sheet()
        events = self.audit_model.search([
            ('model_name', '=', 'gxp.controlled.sheet'),
            ('record_id', '=', sheet.id),
            ('event_type', '=', 'create'),
        ])
        self.assertTrue(events)


    def test_visual_helpers_and_onboarding_action(self):
        sheet = self._create_sheet()
        self.assertTrue(sheet.canvas_html)
        self.assertGreaterEqual(sheet.compliance_score, 0)
        action = sheet.action_open_onboarding()
        self.assertEqual(action.get('res_model'), 'gxp.onboarding.wizard')
