from odoo import _, fields, models


class GxpOnboardingWizard(models.TransientModel):
    _name = 'gxp.onboarding.wizard'
    _description = 'Asistente de uso GxP Spreadsheet Control'

    step = fields.Selection([
        ('intro', 'Introducción'),
        ('registro', 'Registro maestro'),
        ('versionado', 'Versionado y hash'),
        ('firma', 'Firma electrónica'),
        ('auditoria', 'Audit trail'),
        ('cierre', 'Checklist final'),
    ], default='intro', required=True)
    guide_html = fields.Html(string='Guía', compute='_compute_guide_html', sanitize=False)

    def _compute_guide_html(self):
        guides = {
            'intro': _('<h3>Bienvenido padrino 👋</h3><p>Este asistente te guía para operar en modo GxP de forma segura.</p>'),
            'registro': _('<h3>1) Alta de hoja controlada</h3><ul><li>Crea la ficha maestra.</li><li>Define intended use e impacto GxP.</li><li>Configura revisión periódica.</li></ul>'),
            'versionado': _('<h3>2) Carga de versión</h3><ul><li>Sube Excel original.</li><li>Verifica hash SHA-256.</li><li>No sobrescribas versiones efectivas.</li></ul>'),
            'firma': _('<h3>3) Firma electrónica</h3><ul><li>Reautenticación obligatoria.</li><li>Firma de revisión y aprobación.</li><li>El hash firmado queda enlazado.</li></ul>'),
            'auditoria': _('<h3>4) Auditoría</h3><ul><li>Revisa eventos por usuario/IP.</li><li>Valida cambios de estado y descargas.</li><li>Consulta la pestaña Mensajería para trazabilidad legible en contexto.</li><li>Exporta evidencia para inspección.</li></ul>'),
            'cierre': _('<h3>Checklist MVP ✅</h3><p>Hoja + versión + firmas + auditoría + control de cambios + revisión periódica.</p>'),
        }
        for wizard in self:
            wizard.guide_html = guides.get(wizard.step, guides['intro'])

    def action_next(self):
        order = ['intro', 'registro', 'versionado', 'firma', 'auditoria', 'cierre']
        for wizard in self:
            idx = order.index(wizard.step)
            wizard.step = order[min(idx + 1, len(order) - 1)]
        return self._reopen()

    def action_prev(self):
        order = ['intro', 'registro', 'versionado', 'firma', 'auditoria', 'cierre']
        for wizard in self:
            idx = order.index(wizard.step)
            wizard.step = order[max(idx - 1, 0)]
        return self._reopen()

    def _reopen(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }
