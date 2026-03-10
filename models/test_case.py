from odoo import fields, models


class GxpTestCase(models.Model):
    _name = 'gxp.test.case'
    _description = 'Validation Test Case'

    validation_package_id = fields.Many2one('gxp.validation.package', required=True, ondelete='cascade')
    test_id = fields.Char(required=True)
    title = fields.Char(required=True)
    requirement_reference = fields.Char()
    preconditions = fields.Text()
    steps = fields.Text()
    expected_result = fields.Text()
    actual_result = fields.Text()
    executed_by = fields.Many2one('res.users')
    executed_at = fields.Datetime()
    status = fields.Selection([('not_run', 'Not run'), ('pass', 'Pass'), ('fail', 'Fail')], default='not_run')
    evidence_attachment_ids = fields.Many2many('ir.attachment', string='Evidence')
    deviation_reference = fields.Char()
