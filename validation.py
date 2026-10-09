"""Pure validation of template values before the ORM creates any accounts."""

# These IDs are referenced by the standard Indonesian company/journal/tax providers.
ACCOUNT_ALIASES = {
    'l10n_id_51000020': 'l10n_id_51000010',
}
REQUIRED_ACCOUNTS = {
    'l10n_id_11110001': 'asset_cash',
    'l10n_id_11120001': 'asset_cash',
    'l10n_id_11210010': 'asset_receivable',
    'l10n_id_11210011': 'asset_receivable',
    'l10n_id_11210012': 'asset_receivable',
    'l10n_id_11210013': 'asset_receivable',
    'l10n_id_11210030': 'asset_current',
    'l10n_id_11210040': 'asset_prepayments',
    'l10n_id_11300180': 'asset_current',
    'l10n_id_21100010': 'liability_payable',
    'l10n_id_21100011': 'liability_payable',
    'l10n_id_21100012': 'liability_payable',
    'l10n_id_21221010': 'liability_current',
    'l10n_id_28110030': 'liability_current',
    'l10n_id_41000010': 'income',
    'l10n_id_42500010': 'expense_direct_cost',
    'l10n_id_51000010': 'expense_direct_cost',
    'l10n_id_81100030': 'income_other',
    'l10n_id_91100020': 'expense',
    'l10n_id_99900001': 'expense',
    'l10n_id_99900002': 'income_other',
    'l10n_id_99900003': 'expense',
    'l10n_id_99900004': 'income_other',
}

STOCK_FIELDS = {
    'property_stock_valuation_account_id', 'account_stock_valuation_id',
    'account_stock_expense_id', 'account_stock_variation_id',
}
MANDATORY_COMPANY_FIELDS = {
    'default_cash_difference_income_account_id', 'default_cash_difference_expense_account_id',
    'account_default_pos_receivable_account_id', 'income_currency_exchange_account_id',
    'expense_currency_exchange_account_id', 'account_journal_early_pay_discount_loss_account_id',
    'account_journal_early_pay_discount_gain_account_id', 'expense_account_id', 'income_account_id',
    'account_stock_valuation_id', 'deferred_expense_account_id', 'deferred_revenue_account_id',
    'account_journal_suspense_account_id', 'transfer_account_id',
}
REFERENCE_TYPES = {
    'property_account_receivable_id': {'asset_receivable'},
    'account_default_pos_receivable_account_id': {'asset_receivable'},
    'property_account_payable_id': {'liability_payable'},
    'income_account_id': {'income', 'income_other'},
    'income_currency_exchange_account_id': {'income', 'income_other'},
    'expense_account_id': {'expense', 'expense_other', 'expense_direct_cost'},
    'expense_currency_exchange_account_id': {'expense', 'expense_other'},
    'account_stock_expense_id': {'expense', 'expense_other', 'expense_direct_cost'},
    'account_stock_variation_id': {'expense', 'expense_other', 'expense_direct_cost'},
    'property_stock_valuation_account_id': {'asset_current'},
    'account_stock_valuation_id': {'asset_current'},
    'tax_receivable_account_id': {'asset_receivable', 'asset_current'},
    'tax_payable_account_id': {'liability_payable', 'liability_current'},
    'default_cash_difference_income_account_id': {'income', 'income_other'},
    'default_cash_difference_expense_account_id': {'expense', 'expense_other'},
    'account_journal_early_pay_discount_gain_account_id': {'income', 'income_other'},
    'account_journal_early_pay_discount_loss_account_id': {'expense', 'expense_other'},
}


def validate_account_csv(reader):
    required = {'id', 'code', 'name', 'account_type', 'reconcile'}
    if not required.issubset(reader.fieldnames or []):
        raise ValueError('account CSV is missing mandatory columns')
    seen = set()
    for row in reader:
        key = row['id']
        if not key or key in seen:
            raise ValueError(f'account CSV has an empty or duplicate ID: {key!r}')
        seen.add(key)
        if row['reconcile'] not in ('True', 'False'):
            raise ValueError(f'{key}: CSV reconcile must be True or False')


def remap_references(value, aliases):
    """Remap exact template references without creating extra account records."""
    if isinstance(value, dict):
        return {key: remap_references(item, aliases) for key, item in value.items()}
    if isinstance(value, list):
        return [remap_references(item, aliases) for item in value]
    if isinstance(value, tuple):
        return tuple(remap_references(item, aliases) for item in value)
    if isinstance(value, str):
        return aliases.get(value, value)
    return value


def validate_chart(data, fields_for, account_types, properties):
    accounts = data.get('account.account', {})
    if not accounts:
        raise ValueError('custom account CSV is empty or missing')
    codes = set()
    for key, values in accounts.items():
        if not isinstance(key, str) or '.' in key:
            raise ValueError(f'{key!r}: account IDs must be unqualified company-scoped keys')
        for field in ('code', 'name', 'account_type'):
            if not values.get(field):
                raise ValueError(f'{key}: missing mandatory {field}')
        code = values['code']
        if not isinstance(code, str) or not code.isdigit() or len(code) < 6:
            raise ValueError(f'{key}: code must contain at least six digits')
        if code in codes:
            raise ValueError(f'{key}: duplicate account code {code}')
        codes.add(code)
        if values['account_type'] not in account_types:
            raise ValueError(f'{key}: invalid account_type {values["account_type"]}')
        if not isinstance(values.get('reconcile'), bool):
            raise ValueError(f'{key}: reconcile must be a boolean')
        if values['account_type'] in ('asset_receivable', 'liability_payable') and not values['reconcile']:
            raise ValueError(f'{key}: receivable/payable accounts must allow reconciliation')
        if values.get('active') is False:
            raise ValueError(f'{key}: template accounts must be active')
    for key, expected in REQUIRED_ACCOUNTS.items():
        if key not in accounts or accounts[key]['account_type'] != expected:
            raise ValueError(f'{key}: mandatory compatibility account must have type {expected}')
    for source, target in ACCOUNT_ALIASES.items():
        if source in accounts or target not in accounts:
            raise ValueError(f'{source}: alias must resolve exclusively to {target}')
    utilities = {
        'account_journal_suspense_account_id': 'asset_current',
        'account_journal_payment_debit_account_id': 'asset_current',
        'account_journal_payment_credit_account_id': 'asset_current',
        'transfer_account_id': 'asset_current',
        'unaffected_earnings_account': 'equity_unaffected',
    }
    for key, expected in utilities.items():
        if key not in accounts or accounts[key]['account_type'] != expected:
            raise ValueError(f'{key}: mandatory utility account must have type {expected}')
        if key != 'unaffected_earnings_account' and not accounts[key]['reconcile']:
            raise ValueError(f'{key}: utility account must allow reconciliation')
    if sum(v['account_type'] == 'equity_unaffected' for v in accounts.values()) != 1:
        raise ValueError('exactly one current-year earnings account is required')

    def account_ref(value, path, mandatory=False):
        if not value and not mandatory:
            return
        if not isinstance(value, str) or value not in accounts:
            raise ValueError(f'{path}: missing or invalid custom account reference {value!r}')
        expected = REFERENCE_TYPES.get(path.rsplit('.', 1)[-1])
        if expected and accounts[value]['account_type'] not in expected:
            raise ValueError(f'{path}: invalid account type for reference {value!r}')

    def walk(model, values, path):
        fields = fields_for(model)
        if model == 'account.tax.repartition.line' and values.get('repartition_type') == 'tax':
            account_ref(values.get('account_id'), f'{path}.account_id', True)
        if model == 'account.tax.group':
            for name in ('tax_receivable_account_id', 'tax_payable_account_id'):
                account_ref(values.get(name), f'{path}.{name}', True)
        for name, value in values.items():
            field_type, relation, required = fields.get(name, (None, None, False))
            field_path = f'{path}.{name}'
            if name in STOCK_FIELDS or (relation == 'account.account' and field_type == 'many2one'):
                account_ref(value, field_path, required or name in STOCK_FIELDS)
            elif field_type in ('one2many', 'many2many') and value:
                for command in value:
                    if isinstance(command, str):
                        if relation == 'account.account':
                            account_ref(command, field_path)
                        continue
                    if not isinstance(command, (tuple, list)) or not command:
                        raise ValueError(f'{field_path}: invalid relational command {command!r}')
                    operation = command[0]
                    if relation == 'account.account':
                        if operation == 6:
                            for ref in command[2]:
                                account_ref(ref, field_path, True)
                        elif operation in (3, 4):
                            account_ref(command[1], field_path, True)
                        else:
                            raise ValueError(f'{field_path}: account references must use declared CSV IDs')
                    elif operation in (0, 1):
                        walk(relation, command[2], field_path)

    template = data.get('template_data', {})
    for name in ('property_account_receivable_id', 'property_account_payable_id',
                 'property_stock_valuation_account_id'):
        account_ref(template.get(name), f'template_data.{name}', True)
    for name, value in template.items():
        if name in STOCK_FIELDS:
            account_ref(value, f'template_data.{name}', True)
        elif name in properties:
            relation = fields_for(properties[name]).get(name, (None, None, False))[1]
            if relation == 'account.account':
                account_ref(value, f'template_data.{name}')
        elif fields_for('res.company').get(name, (None, None, False))[1] == 'account.account':
            account_ref(value, f'template_data.{name}')
    company_values = data.get('res.company', {})
    if not company_values:
        raise ValueError('mandatory company settings are missing')
    for key, values in company_values.items():
        for name in MANDATORY_COMPANY_FIELDS:
            account_ref(values.get(name), f'res.company[{key}].{name}', True)
    for key in ('bank', 'cash'):
        value = data.get('account.journal', {}).get(key, {}).get('default_account_id')
        account_ref(value, f'account.journal[{key}].default_account_id', True)
        if accounts[value]['account_type'] != 'asset_cash':
            raise ValueError(f'account.journal[{key}]: default account must have type asset_cash')
    for model, records in data.items():
        if model != 'template_data':
            for key, values in records.items():
                walk(model, values, f'{model}[{key}]')
