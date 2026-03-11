from odoo import api, fields, models
from odoo.exceptions import UserError


class GxpChangeControl(models.Model):
    _name = 'gxp.change.control'
    _description = 'GxP Change Control'
    _inherit = ['gxp.audit.mixin']

    change_no = fields.Char(default='New', copy=False, required=True)
    sheet_id = fields.Many2one('gxp.controlled.sheet', required=True)
    requested_by = fields.Many2one('res.users', default=lambda self: self.env.user)
    requested_at = fields.Datetime(default=fields.Datetime.now)
    reason_for_change = fields.Text(required=True)
    risk_assessment = fields.Text(required=True)
    impact_assessment = fields.Text(required=True)
    implementation_plan = fields.Text(required=True)
    approval_state = fields.Selection([('draft', 'Draft'), ('approved', 'Approved'), ('closed', 'Closed')], default='draft')
    linked_new_version_id = fields.Many2one('gxp.sheet.version')
    closure_summary = fields.Text()
    closed_by = fields.Many2one('res.users')
    closed_at = fields.Datetime()

    @api.model
    def create(self, vals):
        if vals.get('change_no', 'New') == 'New':
            vals['change_no'] = self.env['ir.sequence'].next_by_code('gxp.change.control') or 'New'
        return super().create(vals)

    def action_close(self):
        for rec in self:
            if not rec.linked_new_version_id:
                raise UserError('Cannot close change control without linked new version.')
            rec.write({'approval_state': 'closed', 'closed_by': self.env.user.id, 'closed_at': fields.Datetime.now()})
            rec._gxp_log_event('state_change', reason='Change control closed')

    def unlink(self):
        raise UserError('Change control records cannot be deleted.')
