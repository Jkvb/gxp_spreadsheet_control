from odoo import fields, models
from odoo.exceptions import UserError


class GxpSignatureEvent(models.Model):
    _name = 'gxp.signature.event'
    _description = 'Electronic Signature Event'
    _order = 'sign_datetime desc, id desc'

    res_model = fields.Char(required=True)
    res_id = fields.Integer(required=True)
    version_id = fields.Many2one('gxp.sheet.version', required=True, ondelete='restrict')
    signer_id = fields.Many2one('res.users', required=True, ondelete='restrict')
    signer_name_snapshot = fields.Char(required=True)
    sign_datetime = fields.Datetime(required=True, default=fields.Datetime.now)
    sign_meaning = fields.Selection([
        ('review', 'Review'),
        ('approval', 'Approval'),
        ('authorship', 'Authorship'),
        ('verification', 'Verification'),
        ('retirement', 'Retirement'),
    ], required=True)
    signature_method = fields.Selection([
        ('password_reauth', 'Password reauthentication'),
        ('future_mfa', 'Future MFA'),
        ('biometric', 'Biometric'),
    ], default='password_reauth', required=True)
    signature_hash_context = fields.Char()
    comment = fields.Text()
    record_sha256_at_sign = fields.Char(required=True)
    is_valid = fields.Boolean(default=True)

    def write(self, vals):
        raise UserError('Electronic signatures are immutable.')

    def unlink(self):
        raise UserError('Electronic signatures cannot be deleted.')
