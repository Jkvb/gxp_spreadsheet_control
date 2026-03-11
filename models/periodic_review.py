from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class GxpPeriodicReview(models.Model):
    _name = 'gxp.periodic.review'
    _description = 'Periodic Review'
    _inherit = ['gxp.audit.mixin']

    sheet_id = fields.Many2one('gxp.controlled.sheet', required=True)
    version_id = fields.Many2one('gxp.sheet.version')
    review_due_date = fields.Date(required=True)
    review_started_at = fields.Datetime()
    reviewed_by = fields.Many2one('res.users')
    review_result = fields.Selection([('continue', 'Continue'), ('revise', 'Revise'), ('retire', 'Retire')])
    review_notes = fields.Text()
    next_review_date = fields.Date()

    @api.model
    def cron_generate_due_reviews(self):
        today = fields.Date.context_today(self)
        sheets = self.env['gxp.controlled.sheet'].search([
            ('active', '=', True), ('next_review_date', '!=', False), ('next_review_date', '<=', today)
        ])
        for sheet in sheets:
            review = self.create({
                'sheet_id': sheet.id,
                'version_id': sheet.current_version_id.id,
                'review_due_date': sheet.next_review_date,
            })
            review._gxp_log_event('review_due', reason='Periodic review created by cron')
            sheet.next_review_date = today + relativedelta(months=sheet.periodic_review_frequency_months)
