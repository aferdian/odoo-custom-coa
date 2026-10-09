"""Validator tests using repository CSV/template fixtures; no Odoo runtime needed."""
import ast
import csv
import importlib.util
from copy import deepcopy
from io import StringIO
from pathlib import Path
import unittest

ADDON = Path(__file__).resolve().parents[1]
REPO = ADDON.parents[1]
spec = importlib.util.spec_from_file_location('coa_validation', ADDON / 'validation.py')
validation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validation)


def read_csv(path):
    with path.open() as source:
        rows = list(csv.DictReader(source))
    result = {}
    for row in rows:
        if row['id']:
            key = row['id']
            result[key] = {}
        for field, value in row.items():
            if field != 'id' and value and '/' not in field:
                result[key][field] = ast.literal_eval(value) if field in ('reconcile', 'non_trade') else value
        if any('/' in field and value for field, value in row.items()):
            line = {field.split('/')[1]: value for field, value in row.items() if '/' in field and value}
            result[key].setdefault('repartition_line_ids', []).append((0, 0, line))
    return result


class TemplateLiteral(ast.NodeTransformer):
    def visit_Attribute(self, node):
        if ast.unparse(node) == 'self.env.company.id':
            return ast.Constant(1)
        return self.generic_visit(node)

    def visit_Call(self, node):
        if ast.unparse(node.func) == 'self.env._':
            return node.args[0]
        return self.generic_visit(node)


def template_return(tree, name):
    function = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name)
    value = next(node.value for node in ast.walk(function) if isinstance(node, ast.Return))
    return ast.literal_eval(TemplateLiteral().visit(value))


def schema(model):
    account = ('many2one', 'account.account', False)
    fields = {
        'res.company': {name: account for name in validation.MANDATORY_COMPANY_FIELDS},
        'account.account': {name: account for name in validation.STOCK_FIELDS},
        'account.journal': {'default_account_id': account},
        'account.tax.group': {'tax_payable_account_id': account, 'tax_receivable_account_id': account},
        'account.tax': {'repartition_line_ids': ('one2many', 'account.tax.repartition.line', False)},
        'account.tax.repartition.line': {'account_id': account},
        'account.fiscal.position': {'account_ids': ('one2many', 'account.fiscal.position.account', False)},
        'account.fiscal.position.account': {'account_src_id': account, 'account_dest_id': account},
        'res.partner': {'property_account_receivable_id': account, 'property_account_payable_id': account},
    }
    return fields.get(model, {})


class TestValidation(unittest.TestCase):
    def setUp(self):
        source = REPO / 'odoo-reference/addons/l10n_id'
        tree = ast.parse((source / 'models/template_id.py').read_text())
        self.data = {
            'template_data': template_return(tree, '_get_id_template_data'),
            'res.company': template_return(tree, '_get_id_res_company'),
            'account.journal': template_return(tree, '_get_id_account_journal'),
            'account.account': read_csv(ADDON / 'data/template/account.account-id.csv'),
            'account.tax': read_csv(source / 'data/template/account.tax-id.csv'),
            'account.tax.group': read_csv(source / 'data/template/account.tax.group-id.csv'),
        }
        self.data['account.account']['l10n_id_11300180'].update(
            template_return(tree, '_get_id_account_account')['l10n_id_11300180'],
        )
        self.data['res.company'][1].update(
            account_journal_suspense_account_id='account_journal_suspense_account_id',
            transfer_account_id='transfer_account_id',
        )
        self.data = validation.remap_references(self.data, validation.ACCOUNT_ALIASES)
        tree = ast.parse((REPO / 'references/account/models/account_account.py').read_text())
        selection = next(node.value for node in ast.walk(tree)
                         if isinstance(node, ast.keyword) and node.arg == 'selection'
                         and isinstance(node.value, ast.List)
                         and any(isinstance(item, ast.Tuple) and isinstance(item.elts[0], ast.Constant)
                                 and item.elts[0].value == 'asset_receivable' for item in node.value.elts))
        self.types = dict(ast.literal_eval(selection))

    def validate(self, data=None):
        validation.validate_chart(self.data if data is None else data, schema, self.types, {
            'property_account_receivable_id': 'res.partner',
            'property_account_payable_id': 'res.partner',
        })

    def test_actual_inventory_and_all_upstream_references(self):
        self.validate()
        self.assertEqual(len(self.data['account.account']), 425)
        with (REPO / 'docs/coa_master.csv').open() as source:
            master = list(csv.DictReader(source))
        self.assertEqual(len(master), 418)
        self.assertEqual(sum(bool(row['odoo_reference_id']) for row in master), 21)
        for row in master:
            refs = row['odoo_reference_id'].split(';') if row['odoo_reference_id'] else []
            key = refs[0] if refs else 'custom_' + row['code']
            self.assertEqual(self.data['account.account'][key]['code'], row['code'])
            for ref in refs:
                self.assertEqual(validation.ACCOUNT_ALIASES.get(ref, ref), key)

    def test_csv_structure_and_unique_ids(self):
        with (ADDON / 'data/template/account.account-id.csv').open() as source:
            validation.validate_account_csv(csv.DictReader(source))
        for source in ('id,code\na,1\n', 'id,code,name,account_type,reconcile\na,1,A,expense,False\na,2,B,expense,False\n'):
            with self.assertRaises(ValueError):
                validation.validate_account_csv(csv.DictReader(StringIO(source)))

    def test_missing_and_duplicate_accounts(self):
        for change in (
            lambda d: d.update({'account.account': {}}),
            lambda d: d['account.account'].pop('l10n_id_11210012'),
            lambda d: d['account.account']['l10n_id_11110001'].update(code='111301'),
            lambda d: d['account.account']['l10n_id_11210010'].update(reconcile=False),
            lambda d: d['account.account']['l10n_id_11110001'].update(account_type='invalid'),
        ):
            data = deepcopy(self.data)
            change(data)
            with self.assertRaises(ValueError):
                self.validate(data)

    def test_company_journal_tax_group_stock_reference_errors(self):
        cases = [
            ('res.company', 1, 'income_account_id'),
            ('account.journal', 'bank', 'default_account_id'),
            ('account.tax.group', 'default_tax_group', 'tax_payable_account_id'),
            ('account.account', 'l10n_id_11300180', 'account_stock_expense_id'),
        ]
        for model, key, field in cases:
            for ref in ('missing', 17, False):
                with self.subTest(model=model, field=field, ref=ref):
                    data = deepcopy(self.data)
                    data[model][key][field] = ref
                    with self.assertRaisesRegex(ValueError, 'reference'):
                        self.validate(data)

    def test_property_account_role(self):
        data = deepcopy(self.data)
        data['template_data']['property_account_receivable_id'] = 'l10n_id_41000010'
        with self.assertRaisesRegex(ValueError, 'account type'):
            self.validate(data)

    def test_nested_tax_and_fiscal_position_references(self):
        for ref in ('missing', 99, False):
            data = deepcopy(self.data)
            data['account.tax']['tax_ST4']['repartition_line_ids'][1][2]['account_id'] = ref
            with self.assertRaisesRegex(ValueError, 'reference'):
                self.validate(data)
        data = deepcopy(self.data)
        data['account.fiscal.position'] = {'test': {'account_ids': [(0, 0, {
            'account_src_id': 'l10n_id_41000010', 'account_dest_id': 'missing',
        })]}}
        with self.assertRaisesRegex(ValueError, 'reference'):
            self.validate(data)

    def test_stock_alias_is_explicit_and_unique(self):
        self.assertEqual(self.data['account.account']['l10n_id_11300180']['account_stock_expense_id'],
                         'l10n_id_51000010')
        self.assertNotIn('l10n_id_51000020', self.data['account.account'])
        data = deepcopy(self.data)
        data['account.account']['l10n_id_11300180']['account_stock_expense_id'] = 'l10n_id_51000020'
        with self.assertRaisesRegex(ValueError, 'reference'):
            self.validate(data)


if __name__ == '__main__':
    unittest.main(verbosity=2)
