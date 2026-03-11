from odoo import fields, models
from odoo.exceptions import UserError


class GxpValidationPackage(models.Model):
    _name = 'gxp.validation.package'
    _description = 'Validation Package'
    _inherit = ['gxp.audit.mixin']

    name = fields.Char(required=True)
    sheet_id = fields.Many2one('gxp.controlled.sheet', required=True)
    version_id = fields.Many2one('gxp.sheet.version', required=True)
    urs_reference = fields.Char()
    fs_reference = fields.Char()
    ds_reference = fields.Char()
    risk_assessment_summary = fields.Text()
    traceability_status = fields.Selection([('draft', 'Draft'), ('in_progress', 'In Progress'), ('complete', 'Complete')], default='draft')
    validation_state = fields.Selection([('draft', 'Draft'), ('approved', 'Approved')], default='draft')
    validation_report = fields.Text()
    approved_validation_by = fields.Many2one('res.users')
    approved_validation_at = fields.Datetime()
    test_case_ids = fields.One2many('gxp.test.case', 'validation_package_id')

    def unlink(self):
        raise UserError('Validation package cannot be deleted.')
