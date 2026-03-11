import base64
import hashlib

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError


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
    file_binary = fields.Binary(attachment=True)
    file_mimetype = fields.Char()
    file_size = fields.Integer()
    file_sha256 = fields.Char(index=True)

    web_edit_mode = fields.Boolean(string='Edición en navegador', help='Permite capturar y editar datos tabulares directamente en Odoo.')
    web_line_ids = fields.One2many('gxp.sheet.web.line', 'version_id', string='Contenido web')
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
    use_chatter_audit = fields.Boolean(related='sheet_id.use_chatter_audit', readonly=True)
    dummy_export = fields.Binary(compute='_compute_dummy_export')

    _sql_constraints = [
        ('version_unique', 'unique(sheet_id, version_major, version_minor)', 'Version numbers must be unique per sheet.'),
    ]

    def _compute_dummy_export(self):
        for rec in self:
            if rec.web_edit_mode and rec.web_line_ids:
                rec.dummy_export = rec._build_web_csv_binary()
            else:
                rec.dummy_export = False

    @api.depends('version_major', 'version_minor')
    def _compute_version_label(self):
        for rec in self:
            rec.version_label = 'v%s.%s' % (rec.version_major, rec.version_minor)

    @api.model
    def create(self, vals):
        vals = self._prepare_hash_vals(vals)
        if not vals.get('file_binary') and not vals.get('web_edit_mode'):
            raise UserError('Debe cargar archivo o activar edición en navegador.')
        rec = super().create(vals)
        if rec.web_edit_mode and not rec.file_sha256:
            rec._recompute_hash_from_web_content()
        rec._gxp_log_event('create', changes=[{'field_name': 'file_sha256', 'new_value': rec.file_sha256}])
        return rec

    def write(self, vals):
        if self.env.context.get('gxp_force_write'):
            vals = self._prepare_hash_vals(vals)
            return super().write(vals)
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


    def _serialize_web_content(self):
        self.ensure_one()
        payload = []
        for line in self.web_line_ids.sorted(key=lambda l: (l.row_no, l.id)):
            payload.append('|'.join([
                str(line.row_no or ''),
                line.value_1 or '', line.value_2 or '', line.value_3 or '', line.value_4 or '', line.value_5 or '',
                line.value_6 or '', line.value_7 or '', line.value_8 or '', line.value_9 or '', line.value_10 or '',
            ]))
        return '\n'.join(payload).encode('utf-8')

    def _recompute_hash_from_web_content(self):
        for rec in self:
            if not rec.web_edit_mode:
                continue
            raw = rec._serialize_web_content()
            rec.with_context(gxp_force_write=True).write({
                'file_sha256': hashlib.sha256(raw).hexdigest(),
                'file_size': len(raw),
            })

    def _has_valid_signature(self, meaning):
        self.ensure_one()
        return bool(self.signature_ids.filtered(lambda s: s.sign_meaning == meaning and s.is_valid))


    def _require_group(self, xmlid, error_message):
        if self.env.user.has_group('gxp_spreadsheet_control.group_gxp_role_admin') or self.env.user.has_group('base.group_system'):
            return
        if not self.env.user.has_group(xmlid):
            self._gxp_log_event('permission_denied', reason=error_message)
            raise AccessError(error_message)

    def _check_change_control_gate(self):
        self.ensure_one()
        has_prev_effective = bool(self.sheet_id.version_ids.filtered(lambda v: v.state == 'effective' and v.id != self.id))
        if not has_prev_effective:
            return
        cc = self.env['gxp.change.control'].search([
            ('sheet_id', '=', self.sheet_id.id),
            ('linked_new_version_id', '=', self.id),
            ('approval_state', '=', 'closed'),
        ], limit=1)
        if not cc:
            raise UserError('Se requiere Change Control cerrado y vinculado para sustituir una versión vigente.')

    def action_open_sign_wizard_review(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Firma de revisión',
            'res_model': 'gxp.sign.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sign_meaning': 'review',
                'default_res_model': self._name,
                'default_res_id': self.id,
                'default_version_id': self.id,
            }
        }

    def action_open_sign_wizard_approval(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Firma de aprobación',
            'res_model': 'gxp.sign.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sign_meaning': 'approval',
                'default_res_model': self._name,
                'default_res_id': self.id,
                'default_version_id': self.id,
            }
        }

    def action_submit_review(self):
        for rec in self:
            if rec.web_edit_mode and not rec.web_line_ids:
                raise UserError('Debe capturar contenido en la edición web antes de enviar a revisión.')
            if not rec.web_edit_mode and not rec.file_binary:
                raise UserError('Debe cargar archivo antes de enviar a revisión.')
            rec._require_group('gxp_spreadsheet_control.group_gxp_role_author', 'Solo Author/Admin puede enviar a revisión.')
        self.write({'state': 'in_review'})
        self._gxp_log_event('state_change', reason='Submitted for review')

    def action_back_to_draft(self, reason):
        if not reason:
            raise UserError('A reason is required to return to draft.')
        self.write({'state': 'draft'})
        self._gxp_log_event('state_change', reason=reason)

    def action_to_pending_approval(self):
        for rec in self:
            rec._require_group('gxp_spreadsheet_control.group_gxp_role_reviewer', 'Solo Reviewer/Admin puede pasar a aprobación.')
            if not rec._has_valid_signature('review'):
                raise UserError('Review signature is required before approval step.')
        self.write({'state': 'pending_approval'})
        self._gxp_log_event('state_change', reason='Review signed')

    def action_make_effective(self):
        for rec in self:
            rec._require_group('gxp_spreadsheet_control.group_gxp_role_approver', 'Solo Approver/Admin puede hacer vigente una versión.')
            if not rec._has_valid_signature('approval'):
                raise UserError('Approval signature is required.')
            rec._check_change_control_gate()
            if rec.sheet_id.version_ids.filtered(lambda v: v.state == 'effective' and v.id != rec.id):
                prev = rec.sheet_id.version_ids.filtered(lambda v: v.state == 'effective' and v.id != rec.id)
                prev.with_context(gxp_force_write=True).write({'state': 'superseded', 'superseded_by_id': rec.id, 'is_locked': True})
            rec.with_context(gxp_force_write=True).write({'state': 'effective', 'effective_date': fields.Datetime.now(), 'is_locked': True})
            rec.sheet_id.write({'current_version_id': rec.id, 'status': 'approved_for_use'})
            rec._gxp_log_event('state_change', reason='Version made effective')

    def action_retire(self, reason):
        self._require_group('gxp_spreadsheet_control.group_gxp_role_approver', 'Solo Approver/Admin puede retirar una versión.')
        if not reason:
            raise UserError('Retirement reason is mandatory.')
        if not self._has_valid_signature('retirement'):
            raise UserError('Retirement signature required.')
        self.with_context(gxp_force_write=True).write({'state': 'retired', 'is_locked': True})
        self._gxp_log_event('archive', reason=reason)


    def _build_web_csv_binary(self):
        self.ensure_one()
        rows = ['row,C1,C2,C3,C4,C5,C6,C7,C8,C9,C10']
        for line in self.web_line_ids.sorted(key=lambda l: (l.row_no, l.id)):
            vals = [
                str(line.row_no or ''),
                line.value_1 or '', line.value_2 or '', line.value_3 or '', line.value_4 or '', line.value_5 or '',
                line.value_6 or '', line.value_7 or '', line.value_8 or '', line.value_9 or '', line.value_10 or '',
            ]
            sanitized = ['"%s"' % v.replace('"', '""') for v in vals]
            rows.append(','.join(sanitized))
        return base64.b64encode(('\n'.join(rows)).encode('utf-8'))

    def action_open_excel(self):
        self.ensure_one()
        if self.file_binary:
            self._gxp_log_event('download', reason='Apertura de Excel controlado')
            return {
                'type': 'ir.actions.act_url',
                'url': '/web/content/gxp.sheet.version/%s/file_binary/%s?download=true' % (self.id, self.file_name or 'archivo.xlsx'),
                'target': 'self',
            }
        if self.web_edit_mode and self.web_line_ids:
            self._gxp_log_event('export', reason='Exportación CSV desde edición navegador')
            return {
                'type': 'ir.actions.act_url',
                'url': '/web/content?model=gxp.sheet.version&id=%s&field=dummy_export&filename=%s&download=true' % (self.id, (self.file_name or 'hoja_web') + '.csv'),
                'target': 'self',
            }
        raise UserError('No hay archivo Excel cargado ni contenido web para exportar.')

    def action_download_controlled(self):
        self._gxp_log_event('download', reason='Controlled download')
        return True
