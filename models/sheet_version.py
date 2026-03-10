import base64
import hashlib

from odoo import api, fields, models
from odoo.exceptions import UserError


class GxpSheetVersion(models.Model):
    _name = 'gxp.sheet.version'
    _description = 'Controlled Spreadsheet Version'
    _inherit = ['mail.thread', 'gxp.audit.mixin']
    _order = 'sheet_id, version_major desc, version_minor desc, id desc'

    sheet_id = fields.Many2one('gxp.controlled.sheet', required=True, ondelete='restrict')
    version_major = fields.Integer(default=1, required=True)
    version_minor = fields.Integer(default=0, required=True)
    version_label = fields.Char(compute='_compute_version_label', store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_review', 'In Review'),
        ('pending_approval', 'Pending Approval'),
        ('effective', 'Effective'),
        ('superseded', 'Superseded'),
        ('retired', 'Retired'),
        ('cancelled', 'Cancelled'),
    ], default='draft', tracking=True)
    file_name = fields.Char(required=True)
    file_binary = fields.Binary(required=True, attachment=True)
    file_mimetype = fields.Char()
    file_size = fields.Integer()
    file_sha256 = fields.Char(index=True)
    pdf_snapshot_binary = fields.Binary(attachment=True)
    pdf_snapshot_sha256 = fields.Char()
    change_summary = fields.Text(required=True)
    effective_date = fields.Datetime()
    superseded_by_id = fields.Many2one('gxp.sheet.version')
    previous_version_id = fields.Many2one('gxp.sheet.version')
    is_locked = fields.Boolean(default=False)
    created_by = fields.Many2one('res.users', default=lambda self: self.env.user)
    reviewed_by = fields.Many2one('res.users')
    approved_by = fields.Many2one('res.users')
    reviewed_at = fields.Datetime()
    approved_at = fields.Datetime()
    signature_ids = fields.One2many('gxp.signature.event', 'version_id')

    _sql_constraints = [
        ('version_unique', 'unique(sheet_id, version_major, version_minor)', 'Version numbers must be unique per sheet.'),
    ]

    @api.depends('version_major', 'version_minor')
    def _compute_version_label(self):
        for rec in self:
            rec.version_label = 'v%s.%s' % (rec.version_major, rec.version_minor)

    @api.model
    def create(self, vals):
        vals = self._prepare_hash_vals(vals)
        rec = super().create(vals)
        rec._gxp_log_event('create', changes=[{'field_name': 'file_sha256', 'new_value': rec.file_sha256}])
        return rec

    def write(self, vals):
        for rec in self:
            if rec.is_locked or rec.state in ('effective', 'superseded', 'retired'):
                raise UserError('Effective or signed versions are immutable. Create a new version instead.')
        vals = self._prepare_hash_vals(vals)
        result = super().write(vals)
        self._gxp_log_event('write')
        return result

    def unlink(self):
        raise UserError('Regulated version records cannot be deleted.')

    def _prepare_hash_vals(self, vals):
        file_binary = vals.get('file_binary')
        if file_binary:
            raw = base64.b64decode(file_binary)
            vals['file_sha256'] = hashlib.sha256(raw).hexdigest()
            vals['file_size'] = len(raw)
        pdf_binary = vals.get('pdf_snapshot_binary')
        if pdf_binary:
            vals['pdf_snapshot_sha256'] = hashlib.sha256(base64.b64decode(pdf_binary)).hexdigest()
        return vals

    def _has_valid_signature(self, meaning):
        self.ensure_one()
        return bool(self.signature_ids.filtered(lambda s: s.sign_meaning == meaning and s.is_valid))

    def action_submit_review(self):
        self.write({'state': 'in_review'})
        self._gxp_log_event('state_change', reason='Submitted for review')

    def action_back_to_draft(self, reason):
        if not reason:
            raise UserError('A reason is required to return to draft.')
        self.write({'state': 'draft'})
        self._gxp_log_event('state_change', reason=reason)

    def action_to_pending_approval(self):
        for rec in self:
            if not rec._has_valid_signature('review'):
                raise UserError('Review signature is required before approval step.')
        self.write({'state': 'pending_approval'})
        self._gxp_log_event('state_change', reason='Review signed')

    def action_make_effective(self):
        for rec in self:
            if not rec._has_valid_signature('approval'):
                raise UserError('Approval signature is required.')
            if rec.sheet_id.version_ids.filtered(lambda v: v.state == 'effective' and v.id != rec.id):
                prev = rec.sheet_id.version_ids.filtered(lambda v: v.state == 'effective' and v.id != rec.id)
                prev.write({'state': 'superseded', 'superseded_by_id': rec.id, 'is_locked': True})
            rec.write({'state': 'effective', 'effective_date': fields.Datetime.now(), 'is_locked': True})
            rec.sheet_id.write({'current_version_id': rec.id, 'status': 'approved_for_use'})
            rec._gxp_log_event('state_change', reason='Version made effective')

    def action_retire(self, reason):
        if not reason:
            raise UserError('Retirement reason is mandatory.')
        if not self._has_valid_signature('retirement'):
            raise UserError('Retirement signature required.')
        self.write({'state': 'retired', 'is_locked': True})
        self._gxp_log_event('archive', reason=reason)

    def action_download_controlled(self):
        self._gxp_log_event('download', reason='Controlled download')
        return True
