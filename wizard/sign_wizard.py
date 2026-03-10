from odoo import api, fields, models
from odoo.exceptions import AccessDenied, UserError


class GxpSignWizard(models.TransientModel):
    _name = 'gxp.sign.wizard'
    _description = 'Electronic Signature Wizard'

    user_id = fields.Many2one('res.users', default=lambda self: self.env.user, readonly=True)
    password = fields.Char(required=True)
    sign_meaning = fields.Selection([
        ('review', 'Review'),
        ('approval', 'Approval'),
        ('retirement', 'Retirement'),
    ], required=True)
    comment = fields.Text()
    res_model = fields.Char(required=True)
    res_id = fields.Integer(required=True)
    version_id = fields.Many2one('gxp.sheet.version', required=True)
    object_summary = fields.Char(readonly=True)
    file_hash = fields.Char(readonly=True)
    responsibility_confirmed = fields.Boolean()

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if res.get('version_id'):
            version = self.env['gxp.sheet.version'].browse(res['version_id'])
            res['object_summary'] = '%s - %s' % (version.sheet_id.code, version.version_label)
            res['file_hash'] = version.file_sha256
        return res

    def _validate_role_by_meaning(self):
        self.ensure_one()
        if self.sign_meaning == 'review' and not (
            self.env.user.has_group('gxp_spreadsheet_control.group_gxp_role_reviewer')
            or self.env.user.has_group('gxp_spreadsheet_control.group_gxp_role_admin')
            or self.env.user.has_group('base.group_system')
        ):
            raise UserError('Solo Reviewer/Admin puede firmar revisión.')
        if self.sign_meaning in ('approval', 'retirement') and not (
            self.env.user.has_group('gxp_spreadsheet_control.group_gxp_role_approver')
            or self.env.user.has_group('gxp_spreadsheet_control.group_gxp_role_admin')
            or self.env.user.has_group('base.group_system')
        ):
            raise UserError('Solo Approver/Admin puede firmar aprobación o retiro.')

    def _validate_signature(self):
        self.ensure_one()
        try:
            self.env.user._check_credentials(self.password)
        except AccessDenied:
            self.version_id._gxp_log_event('login_fail', reason='Failed signature re-authentication')
            raise UserError('Invalid password for signature re-authentication.')
        self._validate_role_by_meaning()
        if self.sign_meaning in ('approval', 'retirement') and not self.comment:
            raise UserError('Comment is mandatory for this signature meaning.')
        if self.user_id == self.version_id.created_by and self.sign_meaning == 'approval':
            raise UserError('Author cannot self-approve.')
        if self.version_id.state == 'effective':
            raise UserError('No puede firmar una versión ya vigente.')

    def action_sign(self):
        self.ensure_one()
        self._validate_signature()
        signature = self.env['gxp.signature.event'].create({
            'res_model': self.res_model,
            'res_id': self.res_id,
            'version_id': self.version_id.id,
            'signer_id': self.user_id.id,
            'signer_name_snapshot': self.user_id.name,
            'sign_meaning': self.sign_meaning,
            'signature_hash_context': self.file_hash,
            'comment': self.comment,
            'record_sha256_at_sign': self.version_id.file_sha256,
        })
        now = fields.Datetime.now()
        if self.sign_meaning == 'review':
            self.version_id.write({'reviewed_by': self.user_id.id, 'reviewed_at': now})
        if self.sign_meaning == 'approval':
            self.version_id.write({'approved_by': self.user_id.id, 'approved_at': now})
        self.version_id._gxp_log_event('sign', reason=self.sign_meaning, linked_signature_id=signature.id)
        return {'type': 'ir.actions.act_window_close'}
