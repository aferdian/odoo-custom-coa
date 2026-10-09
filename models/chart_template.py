import csv

from odoo import models
from odoo.exceptions import UserError
from odoo.tools import file_open

from ..hooks import check_fresh_company
from ..validation import ACCOUNT_ALIASES, remap_references, validate_account_csv, validate_chart


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    def _load(self, template_code, company, install_demo, force_create=True):
        if template_code == 'id':
            check_fresh_company(self.env, company)
        return super()._load(template_code, company, install_demo, force_create)

    def _get_chart_template_data(self, template_code):
        data = super()._get_chart_template_data(template_code)
        if template_code != 'id':
            return data
        try:
            with file_open('l10n_id_custom_coa/data/template/account.account-id.csv', 'r') as source:
                validate_account_csv(csv.DictReader(source))
        except (FileNotFoundError, ValueError) as error:
            raise UserError(f'Invalid custom Indonesian account CSV: {error}') from error
        # Replace the whole dictionary; decorated providers only merge records.
        data['account.account'] = self._parse_csv(
            'id', 'account.account', module='l10n_id_custom_coa',
        )
        data['template_data']['code_digits'] = '6'
        # These links belong to the Indonesian account provider, not its CSV.
        data['account.account'].get('l10n_id_11300180', {}).update({
            'account_stock_expense_id': 'l10n_id_51000020',
            'account_stock_variation_id': 'l10n_id_42500010',
        })
        for values in data['res.company'].values():
            values.update({
                'account_journal_suspense_account_id': 'account_journal_suspense_account_id',
                'transfer_account_id': 'transfer_account_id',
                'bank_account_code_prefix': '1113',
                'cash_account_code_prefix': '1111',
                'transfer_account_code_prefix': '111993',
            })
        data = remap_references(data, ACCOUNT_ALIASES)
        self._validate_id_custom_chart(data)
        return data

    def _validate_id_custom_chart(self, data):
        def fields_for(model):
            return {
                name: (field.type, getattr(field, 'comodel_name', None), field.required)
                for name, field in self.env[model]._fields.items()
            }

        account_types = dict(
            self.env['account.account']._fields['account_type']._description_selection(self.env)
        )
        properties = self._get_property_accounts(
            data['template_data'].get('additional_properties', {}),
        )
        try:
            validate_chart(data, fields_for, account_types, properties)
        except ValueError as error:
            raise UserError(f'Invalid custom Indonesian chart: {error}') from error
