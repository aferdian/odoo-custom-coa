from copy import deepcopy
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from ..hooks import pre_init_hook
from ..models.chart_template import AccountChartTemplate


@tagged('post_install', '-at_install')
class TestCustomIndonesianChart(TransactionCase):
    def setUp(self):
        super().setUp()
        self.company = self.env['res.company'].create({
            'name': 'Custom Indonesian COA test',
            'country_id': self.env.ref('base.id').id,
            'currency_id': self.env.ref('base.IDR').id,
        })
        self.chart = self.env['account.chart.template'].with_company(self.company)
        self.accounts = self.env['account.account'].with_company(self.company)

    def _data(self):
        return self.chart._get_chart_template_data('id')

    def _company_accounts(self):
        return self.accounts.search(self.accounts._check_company_domain(self.company))

    def test_replacement_before_first_creation(self):
        expected = self.chart._parse_csv(
            'id', 'account.account', module='l10n_id_custom_coa',
        )
        observed = []
        original = type(self.chart)._load_data

        def inspect(chart, data):
            self.assertFalse(self._company_accounts())
            self.assertEqual(set(data['account.account']), set(expected))
            observed.append(True)
            return original(chart, data)

        with patch.object(type(self.chart), '_load_data', inspect):
            self.chart.try_loading('id', self.company)
        self.assertEqual(observed, [True])
        actual = self._company_accounts()
        self.assertEqual(len(actual), len(expected))
        self.assertEqual(set(actual.mapped('code')), {v['code'] for v in expected.values()})
        for key, values in expected.items():
            account = self.chart.ref(key)
            self.assertEqual(account.code, values['code'])
            self.assertEqual(account.account_type, values['account_type'])

    def test_automatic_current_company_initialization(self):
        company = self.env.company
        if company.country_id != self.env.ref('base.id'):
            self.skipTest('Requires current company country Indonesia before addon installation')
        chart = self.env['account.chart.template'].with_company(company)
        expected = chart._parse_csv('id', 'account.account', module='l10n_id_custom_coa')
        actual = self.env['account.account'].with_company(company).search(
            self.env['account.account']._check_company_domain(company),
        )
        self.assertEqual(company.chart_template, 'id')
        self.assertEqual(len(actual), len(expected))
        self.assertEqual(set(actual.mapped('code')), {v['code'] for v in expected.values()})
        self.assertFalse(hasattr(self.env.registry, '_auto_install_template'))

    def test_standard_taxes_and_stock_links_preserved(self):
        data = self._data()
        for model in ('account.tax', 'account.tax.group'):
            expected = self.chart._parse_csv('id', model, module='l10n_id')
            for key, values in expected.items():
                for field, value in values.items():
                    self.assertEqual(data[model][key][field], value)
        self.assertEqual(data['account.account']['l10n_id_11300180']['account_stock_expense_id'],
                         'l10n_id_51000010')
        self.chart.try_loading('id', self.company)
        self.assertEqual(self.company.account_sale_tax_id, self.chart.ref('tax_ST4'))
        self.assertEqual(self.company.account_purchase_tax_id, self.chart.ref('tax_PT4'))
        groups = self.env['account.tax.group'].search([('company_id', '=', self.company.id)])
        for group in groups:
            self.assertIn(group.tax_payable_account_id, self._company_accounts())
            self.assertIn(group.tax_receivable_account_id, self._company_accounts())
        taxes = self.env['account.tax'].search([('company_id', '=', self.company.id)])
        for line in taxes.invoice_repartition_line_ids + taxes.refund_repartition_line_ids:
            if line.account_id:
                self.assertIn(line.account_id, self._company_accounts())
        for key in ('bank', 'cash'):
            self.assertIn(self.chart.ref(key).default_account_id, self._company_accounts())

    def test_invalid_references_fail_before_creation(self):
        original = self._data()
        cases = [
            ('res.company', self.company.id, 'income_account_id', 'missing'),
            ('account.journal', 'bank', 'default_account_id', 'missing'),
            ('account.tax.group', 'default_tax_group', 'tax_payable_account_id', 'missing'),
            ('account.account', 'l10n_id_11300180', 'account_stock_expense_id', 'missing'),
            ('template_data', None, 'property_account_receivable_id', False),
        ]
        for model, key, field, value in cases:
            with self.subTest(model=model, field=field):
                data = deepcopy(original)
                target = data[model] if key is None else data[model][key]
                target[field] = value
                with self.assertRaisesRegex(UserError, 'reference'):
                    self.chart._validate_id_custom_chart(data)
        data = deepcopy(original)
        data['account.tax']['tax_ST4']['repartition_line_ids'] = [
            Command.create({'repartition_type': 'tax', 'account_id': 'missing'}),
        ]
        with self.assertRaisesRegex(UserError, 'reference'):
            self.chart._validate_id_custom_chart(data)
        self.assertFalse(self._company_accounts())

    def test_missing_csv_and_invalid_accounts(self):
        with patch.object(type(self.chart), '_parse_csv', return_value={}):
            with self.assertRaisesRegex(UserError, 'empty or missing'):
                self._data()
        for change, message in (
            (lambda d: d['account.account'].pop('l10n_id_11300180'), 'compatibility'),
            (lambda d: d['account.account']['l10n_id_11210010'].update(reconcile=False), 'reconciliation'),
            (lambda d: d['account.account']['l10n_id_11110001'].update(account_type='wrong'), 'account_type'),
            (lambda d: d['account.account']['l10n_id_11110001'].update(code='111301'), 'duplicate'),
        ):
            data = deepcopy(self._data())
            change(data)
            with self.assertRaisesRegex(UserError, message):
                self.chart._validate_id_custom_chart(data)

    def test_existing_chart_is_not_reloaded(self):
        self.chart.try_loading('id', self.company)
        accounts = self._company_accounts()
        with self.assertRaisesRegex(UserError, 'fresh root company'):
            self.chart.try_loading('id', self.company)
        with self.assertRaises(UserError):
            pre_init_hook(self.chart.env)
        self.assertEqual(self._company_accounts(), accounts)

    def test_posted_entries_are_untouched(self):
        self.chart.try_loading('id', self.company)
        move = self.env['account.move'].with_company(self.company).create({
            'journal_id': self.chart.ref('general').id,
            'line_ids': [
                Command.create({'name': 'Debit', 'account_id': self.chart.ref('l10n_id_11110001').id,
                                'debit': 100}),
                Command.create({'name': 'Credit', 'account_id': self.chart.ref('l10n_id_41000010').id,
                                'credit': 100}),
            ],
        })
        move.action_post()
        before = move.line_ids.read(['account_id', 'debit', 'credit'])
        with self.assertRaises(UserError):
            self.chart.try_loading('id', self.company)
        self.assertEqual(move.state, 'posted')
        self.assertEqual(move.line_ids.read(['account_id', 'debit', 'credit']), before)

    def test_other_chart_is_unchanged(self):
        original = super(AccountChartTemplate, self.chart)._get_chart_template_data('generic_coa')
        self.assertEqual(self.chart._get_chart_template_data('generic_coa'), original)


@tagged('at_install', '-post_install')
class TestOverrideRegistration(TransactionCase):
    def test_override_registered_before_deferred_initialization(self):
        # Executed during load_module_graph, before the final _register_hook loop.
        chart = self.env['account.chart.template']
        self.assertEqual(
            chart._get_chart_template_data.__func__.__module__,
            'odoo.addons.l10n_id_custom_coa.models.chart_template',
        )
        self.assertEqual(
            chart._get_chart_template_data('id')['account.account']['l10n_id_11110001']['code'],
            '111110',
        )
        if self.env.company.country_id == self.env.ref('base.id'):
            self.assertFalse(self.env.company.chart_template)
            self.assertTrue(hasattr(self.env.registry, '_auto_install_template'))
