from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


class GxpControlledSheet(models.Model):
    _name = 'gxp.controlled.sheet'
    _description = 'Controlled Spreadsheet Master'
    _inherit = ['mail.thread', 'gxp.audit.mixin']

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, default='New', copy=False, tracking=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.user.company_id)
    owner_id = fields.Many2one('res.users', required=True, default=lambda self: self.env.user)
    business_process = fields.Char()
    intended_use = fields.Text(required=True)
    predicate_rule_reference = fields.Char()
    gxp_impact = fields.Selection([('none', 'None'), ('low', 'Low'), ('medium', 'Medium'), ('high', 'High')], default='low')
    data_integrity_impact = fields.Text()
    record_type = fields.Char()
    is_part11_record = fields.Boolean(default=True)
    rely_on_electronic_record = fields.Boolean(default=True)
    current_version_id = fields.Many2one('gxp.sheet.version')
    status = fields.Selection([
        ('draft', 'Draft'),
        ('under_assessment', 'Under Assessment'),
        ('approved_for_use', 'Approved for Use'),
        ('retired', 'Retired'),
    ], default='draft', tracking=True)
    periodic_review_frequency_months = fields.Integer(default=12)
    next_review_date = fields.Date()
    folder_path = fields.Char()
    notes = fields.Text()
    use_chatter_audit = fields.Boolean(default=True, string='Publicar auditoría en mensajería')
    version_ids = fields.One2many('gxp.sheet.version', 'sheet_id')

    compliance_score = fields.Integer(compute='_compute_visual_helpers', string='Score de cumplimiento')
    workflow_hint = fields.Char(compute='_compute_visual_helpers', string='Siguiente paso sugerido')
    canvas_html = fields.Html(compute='_compute_visual_helpers', sanitize=False)

    _sql_constraints = [
        ('code_company_unique', 'unique(code, company_id)', 'Code must be unique per company.'),
    ]

    @api.model
    def create(self, vals):
        if vals.get('code', 'New') == 'New':
            vals['code'] = self.env['ir.sequence'].next_by_code('gxp.controlled.sheet') or 'New'
        record = super().create(vals)
        record._gxp_log_event('create')
        return record

    def write(self, vals):
        tracked = {'name', 'owner_id', 'intended_use', 'gxp_impact', 'periodic_review_frequency_months', 'status', 'active'}
        changes = []
        for record in self:
            for field_name in tracked.intersection(vals.keys()):
                old = record[field_name]
                new = vals[field_name]
                changes.append({'field_name': field_name, 'old_value': str(old), 'new_value': str(new)})
        result = super().write(vals)
        if changes:
            self._gxp_log_event('write', changes=changes)
        return result


    @api.depends('status', 'current_version_id', 'version_ids', 'next_review_date')
    def _compute_visual_helpers(self):
        mapping = {
            'draft': ('Registrar primera versión', 25),
            'under_assessment': ('Completar revisión y firma', 55),
            'approved_for_use': ('Monitorear revisión periódica', 90),
            'retired': ('Registro retirado', 100),
        }
        for rec in self:
            hint, score = mapping.get(rec.status, ('Revisar estado', 10))
            version = rec.current_version_id.version_label if rec.current_version_id else 'Sin versión efectiva'
            rec.workflow_hint = hint
            rec.compliance_score = score
            rec.canvas_html = (
                '<div class="gxp-canvas">'
                '<div class="gxp-pill">Estado: %s</div>'
                '<div class="gxp-pill">Versión vigente: %s</div>'
                '<div class="gxp-pill">Próxima revisión: %s</div>'
                '<div class="gxp-progress"><span style="width:%s%%"></span></div>'
                '<p><strong>Tip:</strong> %s</p>'
                '</div>'
            ) % (rec.status, version, rec.next_review_date or 'No programada', score, hint)

    def action_open_onboarding(self):
        wizard = self.env['gxp.onboarding.wizard'].create({})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'gxp.onboarding.wizard',
            'view_mode': 'form',
            'res_id': wizard.id,
            'target': 'new',
        }

    def unlink(self):
        raise UserError('Regulated records cannot be deleted; archive them instead.')

    def action_under_assessment(self):
        self.write({'status': 'under_assessment'})
        self._gxp_log_event('state_change', reason='Moved to under assessment')

    def action_approved_for_use(self):
        self.write({'status': 'approved_for_use'})
        self._gxp_log_event('state_change', reason='Approved for use')

    def action_retire(self, reason):
        if not reason:
            raise UserError('Retirement reason is required.')
        self.write({'status': 'retired', 'active': False})
        self._gxp_log_event('archive', reason=reason)

    def action_schedule_next_review(self):
        for rec in self:
            today = fields.Date.context_today(rec)
            rec.next_review_date = today + relativedelta(months=rec.periodic_review_frequency_months)
