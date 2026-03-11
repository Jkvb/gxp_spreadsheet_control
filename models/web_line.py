from odoo import api, fields, models
from odoo.exceptions import UserError


class GxpSheetWebLine(models.Model):
    _name = 'gxp.sheet.web.line'
    _description = 'Editable Spreadsheet Line (Browser)'
    _order = 'version_id, row_no, id'

    version_id = fields.Many2one('gxp.sheet.version', required=True, ondelete='cascade')
    row_no = fields.Integer(required=True, default=1)
    value_1 = fields.Char('C1')
    value_2 = fields.Char('C2')
    value_3 = fields.Char('C3')
    value_4 = fields.Char('C4')
    value_5 = fields.Char('C5')
    value_6 = fields.Char('C6')
    value_7 = fields.Char('C7')
    value_8 = fields.Char('C8')
    value_9 = fields.Char('C9')
    value_10 = fields.Char('C10')

    _sql_constraints = [
        ('gxp_web_line_uniq', 'unique(version_id, row_no)', 'El número de fila debe ser único por versión.'),
    ]

    def _check_editable(self):
        for rec in self:
            if rec.version_id.is_locked or rec.version_id.state in ('effective', 'superseded', 'retired'):
                raise UserError('No se puede editar la hoja web en versiones bloqueadas o efectivas.')

    @api.model
    def create(self, vals):
        rec = super().create(vals)
        rec._check_editable()
        rec.version_id._recompute_hash_from_web_content()
        rec.version_id._gxp_log_event('write', reason='Edición web: alta de fila')
        return rec

    def write(self, vals):
        self._check_editable()
        result = super().write(vals)
        self.mapped('version_id')._recompute_hash_from_web_content()
        self.mapped('version_id')._gxp_log_event('write', reason='Edición web: modificación de fila')
        return result

    def unlink(self):
        versions = self.mapped('version_id')
        self._check_editable()
        result = super().unlink()
        versions._recompute_hash_from_web_content()
        versions._gxp_log_event('write', reason='Edición web: eliminación de fila')
        return result
