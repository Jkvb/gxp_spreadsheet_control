from odoo import fields, models
from odoo.exceptions import UserError


class GxpAuditEvent(models.Model):
    _name = 'gxp.audit.event'
    _description = 'GxP Audit Event'
    _order = 'event_datetime desc, id desc'

    event_datetime = fields.Datetime(required=True, default=fields.Datetime.now, index=True)
    user_id = fields.Many2one('res.users', required=True, index=True)
    session_identifier = fields.Char()
    client_ip = fields.Char()
    user_agent = fields.Char()
    model_name = fields.Char(required=True, index=True)
    record_id = fields.Integer(required=True, index=True)
    record_display_name = fields.Char()
    event_type = fields.Selection([
        ('create', 'Create'),
        ('write', 'Write'),
        ('state_change', 'State Change'),
        ('sign', 'Sign'),
        ('download', 'Download'),
        ('export', 'Export'),
        ('login_fail', 'Login fail'),
        ('permission_denied', 'Permission denied'),
        ('review_due', 'Review due'),
        ('archive', 'Archive'),
    ], required=True)
    field_name = fields.Char()
    old_value_text = fields.Text()
    new_value_text = fields.Text()
    reason = fields.Text()
    linked_signature_id = fields.Many2one('gxp.signature.event')
    hash_before = fields.Char()
    hash_after = fields.Char()

    def write(self, vals):
        raise UserError('Audit trail is immutable.')

    def unlink(self):
        raise UserError('Audit trail is immutable.')
