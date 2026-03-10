from odoo import api, fields, models


class GxpAuditMixin(models.AbstractModel):
    _name = 'gxp.audit.mixin'
    _description = 'GxP Audit helper'

    @api.model
    def _gxp_client_context(self):
        request = self.env['ir.http'].sudo()._request_stack.top
        if not request:
            return {
                'session_identifier': self.env.context.get('session_id') or 'n/a',
                'client_ip': 'n/a',
                'user_agent': 'n/a',
            }
        return {
            'session_identifier': request.session.sid,
            'client_ip': request.httprequest.remote_addr,
            'user_agent': request.httprequest.user_agent.string,
        }

    def _gxp_format_chatter_body(self, event_type, reason=None, changes=None):
        changes = changes or []
        lines = [
            '<p><strong>Evento GxP:</strong> %s</p>' % event_type,
            '<p><strong>Usuario:</strong> %s</p>' % self.env.user.name,
        ]
        if reason:
            lines.append('<p><strong>Motivo:</strong> %s</p>' % reason)
        if changes:
            rows = []
            for change in changes[:10]:
                rows.append(
                    '<tr><td>%s</td><td>%s</td><td>%s</td></tr>' % (
                        change.get('field_name') or '-',
                        change.get('old_value') or '-',
                        change.get('new_value') or '-',
                    )
                )
            lines.append(
                '<table class="table table-sm table-condensed">'
                '<thead><tr><th>Campo</th><th>Antes</th><th>Después</th></tr></thead>'
                '<tbody>%s</tbody></table>' % ''.join(rows)
            )
        return ''.join(lines)

    def _gxp_post_chatter_audit(self, event_type, reason=None, changes=None):
        for record in self:
            if not hasattr(record, 'message_post'):
                continue
            if 'use_chatter_audit' in record._fields and not record.use_chatter_audit:
                continue
            body = record._gxp_format_chatter_body(event_type, reason=reason, changes=changes)
            record.message_post(body=body, message_type='comment', subtype='mail.mt_note')

    def _gxp_log_event(self, event_type, reason=None, changes=None, linked_signature_id=False):
        client_data = self._gxp_client_context()
        Audit = self.env['gxp.audit.event'].sudo()
        changes = changes or []
        for record in self:
            if not changes:
                Audit.create({
                    'event_datetime': fields.Datetime.now(),
                    'user_id': self.env.user.id,
                    'session_identifier': client_data['session_identifier'],
                    'client_ip': client_data['client_ip'],
                    'user_agent': client_data['user_agent'],
                    'model_name': record._name,
                    'record_id': record.id,
                    'record_display_name': record.display_name,
                    'event_type': event_type,
                    'reason': reason,
                    'linked_signature_id': linked_signature_id,
                })
                continue
            for change in changes:
                Audit.create({
                    'event_datetime': fields.Datetime.now(),
                    'user_id': self.env.user.id,
                    'session_identifier': client_data['session_identifier'],
                    'client_ip': client_data['client_ip'],
                    'user_agent': client_data['user_agent'],
                    'model_name': record._name,
                    'record_id': record.id,
                    'record_display_name': record.display_name,
                    'event_type': event_type,
                    'field_name': change.get('field_name'),
                    'old_value_text': change.get('old_value'),
                    'new_value_text': change.get('new_value'),
                    'reason': reason,
                    'linked_signature_id': linked_signature_id,
                    'hash_before': change.get('hash_before'),
                    'hash_after': change.get('hash_after'),
                })
        self._gxp_post_chatter_audit(event_type, reason=reason, changes=changes)
