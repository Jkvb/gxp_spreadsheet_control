from odoo import fields, models
from odoo.exceptions import UserError


class GxpCatalogBusinessProcess(models.Model):
    _name = 'gxp.catalog.business.process'
    _description = 'Catálogo de procesos de negocio GxP'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    active = fields.Boolean(default=True)
    description = fields.Text()

    _sql_constraints = [
        ('gxp_catalog_business_process_code_uniq', 'unique(code)', 'El código del proceso debe ser único.'),
    ]


class GxpCatalogRecordType(models.Model):
    _name = 'gxp.catalog.record.type'
    _description = 'Catálogo de tipo de registro GxP'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    active = fields.Boolean(default=True)
    description = fields.Text()

    _sql_constraints = [
        ('gxp_catalog_record_type_code_uniq', 'unique(code)', 'El código del tipo de registro debe ser único.'),
    ]


class GxpCatalogPredicateRule(models.Model):
    _name = 'gxp.catalog.predicate.rule'
    _description = 'Catálogo de predicate rules GxP'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    active = fields.Boolean(default=True)
    description = fields.Text()

    _sql_constraints = [
        ('gxp_catalog_predicate_rule_code_uniq', 'unique(code)', 'El código de la regla debe ser único.'),
    ]
