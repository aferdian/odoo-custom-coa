<<<<<<< HEAD
# odoo-custom-coa
Extend Odoo Official l10n_id and replace the chart of account with your own list
=======
# Indonesian Custom Chart of Accounts — Odoo 19 Community

Depends on `l10n_id`. Replaces the complete `account.account` dataset for chart
`id` before account creation; standard Indonesian taxes and journal/company
settings remain. No upstream files are modified. CSV files are read by Odoo's
chart engine, **not** listed as manifest data.

## Accounts and compatibility

`data/template/account.account-id.csv` contains 425 accounts: all 418 rows from
`docs/coa_master.csv`, with Odoo selection values, plus seven explicitly declared
Indonesian compatibility accounts. The master now includes 21 mapped rows;
semicolons join multiple original IDs. Together the mapped and compatibility
accounts preserve IDs used by partner/company defaults, journals, tax groups,
tax repartition lines and inventory accounting.
See [dependency_inventory.md](docs/dependency_inventory.md) for the complete list.
There is no runtime fallback to the upstream account CSV.

Mapped master IDs preserve their Indonesian internal keys; unmapped master IDs
become company-scoped `account.<company_id>_custom_<code>` records;
five utility rows use Odoo's native internal IDs. Current-year profit (331020)
uses `equity_unaffected`. Heading rows remain accounts as specified in the master.
Custom codes retain six digits; seven compatibility codes retain eight digits.
Preserved default cash/bank, receivable/payable, income/expense and stock accounts
use mapped master accounts; specialized master accounts can be assigned operationally
after installation. Review these defaults before posting transactions.

## Fresh installation

1. Use Odoo **19.0 Community**, a fresh database/company, and disable demo data.
2. Add this repository's `custom_addons` directory to `addons_path` alongside
   the complete Odoo core and official addons directories.
3. Set the current root company's country to Indonesia **before** installing
   Accounting or `l10n_id`. Do not select/install a standard chart first.
4. Update the Apps list and install **Indonesian Custom Chart of Accounts**.
   Its dependency installs `l10n_id` in the same registry load.
5. Confirm 425 company accounts and standard Indonesian default taxes.

The install hook refuses demo localization and a current company with a chart,
accounts, entries or a parent. Indonesian chart loading is also refused for
existing accounting data.
Installation does not migrate other companies; upgrading the addon does not
reload an existing chart. Do not reinstall the chart to apply CSV changes.
New empty root companies may select Indonesia after the addon is installed.
Branches are outside this initial implementation's scope.

## Initialization order

In Odoo 19, `ir.module.module.write` schedules automatic chart creation on the
registry; its `_register_hook` executes the callback. The
[upstream loader](https://github.com/odoo/odoo/blob/19.0/odoo/modules/loading.py)
loads the module graph and completes model setup before calling registration
hooks (lines 407–443 and 532–539). Therefore an explicitly installed dependent
addon is registered before deferred initial creation. Installing `l10n_id` in
an earlier operation is too late. Demo localization data can call chart loading
during dependency loading; demo installation is unsupported here.

`models/chart_template.py` deliberately has no decorated chart metadata provider,
so `id` continues to belong to `l10n_id` for standard tax CSV selection. Its
`_get_chart_template_data` override calls `super()`, reads only the replacement
account CSV using `_parse_csv(..., module='l10n_id_custom_coa')`, restores stock
links, and validates the assembled dataset before `_pre_load_data`/`_load_data`.

## Tests

With a complete Odoo checkout and PostgreSQL, use a dedicated fresh test database:

```sh
python3 /path/to/odoo/odoo-bin -c /path/to/test.conf \
  -d coa_test -i l10n_id_custom_coa --without-demo=all \
  --test-enable --test-tags /l10n_id_custom_coa --stop-after-init
```

The `at_install` TransactionCase checks registration before deferred chart
initialization. Post-install cases exercise first creation, exact account counts,
standard taxes, nested references, validation errors, other charts, and refusal
to reload or change posted entries. To exercise the automatic Indonesian callback
itself, prepare the current company's Indonesian country before this command;
a default database otherwise tests explicit creation on a new Indonesian company
and reports the automatic-callback case as skipped.

Standalone validator tests need only Python:

```sh
python3 custom_addons/l10n_id_custom_coa/tests/test_validation_standalone.py
```

Odoo TransactionCase tests have **not been executed** in this reference-only
workspace: it has no Odoo runtime, psycopg2, or PostgreSQL command-line tools.
Installation-order verification is based on upstream source; database execution
remains required before production use.

Seven standalone validator tests passed locally against the actual CSV/template
fixtures. Python syntax checks passed for all nine addon Python files.
>>>>>>> 324794b (initial commit)
