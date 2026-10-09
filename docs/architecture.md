# Implementation architecture

The addon inherits `account.chart.template` and replaces only the assembled
`account.account` dictionary for `id`. `_parse_csv` receives the explicit custom
module name. It retains standard Indonesian tax data, company/journal providers,
and stock links. Chart metadata still belongs to `l10n_id`.

`docs/coa_master.csv` contains 21 mapped rows: 16 cover 17 Indonesian IDs, and five
cover native utility account IDs. One explicit alias consolidates raw-material
stock expense into COGS account 511010. The replacement CSV contains all 418
master accounts and seven mandatory compatibility rows with no suitable master
equivalent. Runtime fallback to upstream accounts is forbidden.

Validation checks raw CSV IDs before parsing, then validates unique codes, Odoo
types, reconciliation, compatibility roles and recursively nested account
references using actual ORM field metadata. Required company/partner defaults,
cash/bank journals, tax-closing counterparts, tax repartition accounts and stock
links fail with a `UserError` before account creation. Unknown optional stock
fields are still validated before the native engine filters unavailable fields.

The `pre_init_hook` rejects a populated current company and demo localization;
the `_load` guard rejects Indonesian reloads, existing accounts/entries and
branches before native cleanup can run. There is no migration or posted-entry
rewriting. Native utility IDs ensure outstanding accounts reuse CSV records;
current-year earnings already exists with `equity_unaffected`.

## Installation-order evidence

The local account `ir_module.py:62–104` queues chart creation on the registry and
executes it from `_register_hook`. The official
[Odoo 19 loader](https://github.com/odoo/odoo/blob/19.0/odoo/modules/loading.py)
loads the graph and completes model setup before its final registration-hook
loop (407–443, 532–539). Thus the custom dependency extension participates in
deferred fresh initialization when installed in the same operation. Demo charts
load earlier from dependency data and are explicitly unsupported. The addon must
be requested before Accounting/localization installs a chart separately.

## Verification

Seven standalone tests passed using actual repository template/CSV fixtures.
Python syntax and manifest checks are available without an Odoo runtime.
TransactionCase coverage includes registration during module loading, first
creation and exact account counts, standard taxes and references, invalid input,
other charts, existing charts and posted-entry preservation. These database tests
have not run locally: the workspace contains reference snippets, no importable
Odoo runtime or psycopg2, and no PostgreSQL CLI. Automatic Indonesian callback
execution requires a fresh test company with its country set before installation.
