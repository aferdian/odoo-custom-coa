# Compatibility inventory

`docs/coa_master.csv` now uses `odoo_reference_id` for exact Indonesian chart IDs or native utility IDs. Semicolons express multiple source IDs mapped to one account; the first is the canonical CSV key. Blank values mean no defensible default counterpart, not a missing account. All 418 master accounts are exported.

## Mapped defaults

| Master code | Master account | Preserved / mapped chart IDs |
| --- | --- | --- |
| 111110 | Kas Kecil Kantor Pusat | `l10n_id_11110001` |
| 111301 | Bank Mandiri Operasional Utama | `l10n_id_11120001` |
| 111990 | Suspen Bank / Bank Suspense | `account_journal_suspense_account_id` |
| 111991 | Penerimaan Belum Kliring / Outstanding Receipts | `account_journal_payment_debit_account_id` |
| 111992 | Pembayaran Belum Kliring / Outstanding Payments | `account_journal_payment_credit_account_id` |
| 111993 | Transfer Internal Kas (Ayat Silang) / Liquidity Transfer | `transfer_account_id` |
| 112110 | Piutang Reseller / B2B | `l10n_id_11210010` |
| 112999 | Piutang Usaha Lainnya | `l10n_id_11210011` |
| 113999 | Persediaan Lainnya / Other Inventory | `l10n_id_11300180` |
| 114240 | Biaya Dibayar Dimuka Lainnya | `l10n_id_11210040` |
| 115010 | PPN Masukan | `l10n_id_11210030` |
| 211010 | Hutang Supplier Pihak Ke-3 (Kemasan & Packaging Box) | `l10n_id_21100010` |
| 212010 | Utang PPN Keluaran B2B | `l10n_id_21221010` |
| 213010 | Pendapatan Diterima Dimuka (Voucher / Advance Order) | `l10n_id_28110030` |
| 331020 | Laba Berjalan Periode Ini (Current Year Profit) | `unaffected_earnings_account` |
| 411010 | Penjualan Own Product - Outlet Tunai / Cash | `l10n_id_41000010` |
| 511010 | Biaya Pemakaian Bahan Baku - BOM (Beli Koperasi) | `l10n_id_51000010;l10n_id_51000020` |
| 511040 | Biaya Bahan Baku - Selisih Stok Opname Dapur | `l10n_id_42500010` |
| 811999 | Keuntungan Selisih Kas / Cash Difference Gain | `l10n_id_99900002` |
| 822020 | Selisih Kurs Mata Uang Asing (Realized / Unrealized) | `l10n_id_91100020` |
| 822999 | Kerugian Selisih Kas / Cash Difference Loss | `l10n_id_99900001` |

## Explicit compatibility accounts

These seven required roles have no suitable master counterpart. They remain declared in the custom CSV, never loaded as a runtime fallback.

| Chart ID | Account type | Role |
| --- | --- | --- |
| `l10n_id_11210012` | `asset_receivable` | VAT Receivable |
| `l10n_id_11210013` | `asset_receivable` | STLG Receivable |
| `l10n_id_21100011` | `liability_payable` | VAT Payable |
| `l10n_id_21100012` | `liability_payable` | STLG Payable |
| `l10n_id_81100030` | `income_other` | Foreign Exchange Gain |
| `l10n_id_99900003` | `expense` | Cash Discount Loss |
| `l10n_id_99900004` | `income_other` | Cash Discount Gain |

## Mapping rationale

The Indonesian template identifies the actual mandatory IDs. The generic chart CSV confirms roles (receivable/payable, valuation, deferred revenue, stock variation, cash differences, exchange gains/losses, and current-year earnings); account_account.py supplies Odoo 19 type/reconciliation constraints. Generic IDs are not injected into the Indonesian chart.

Cash defaults to petty cash at head office (111110); bank defaults to Mandiri (111301). Default customer receivables use reseller/B2B (112110), and POS fallback receivables use general other trade receivables (112999), leaving channel settlement accounts available for specific POS/payment setup. Inventory defaults to other inventory (113999); configure product-specific stock accounts operationally. These are explicit initial defaults requiring business review.

VAT purchase/sales posting uses PPN Masukan (115010) and Utang PPN Keluaran B2B (212010). Tax-group receivable/payable accounts are tax-closing counterparts, a different role from invoice VAT posting; keep the four VAT/STLG settlement accounts distinct. There is no dedicated STLG settlement row in the master.

Both COGS and raw-material stock expense resolve to material consumption (511010). The alias l10n_id_51000020 is explicitly remapped to canonical l10n_id_51000010, including stock links, before validation. Stock variation uses stock-opname differences (511040). These master accounts use expense_direct_cost, a valid expense group. Prepaid expense uses asset_prepayments (114240); cash gains use income_other (811999). Original internal IDs are preserved but type values follow the master for these compatible roles.

The combined FX master row (822020) is typed Expenses, so it serves losses only; Odoo requires an income-group account for FX gains. POS discounts (421010 etc.) are typed Income and describe sales promotions, so they are not substituted for the standard expense/income early-payment discount write-off roles. Those three required roles remain explicit compatibility accounts.

Native suspense/outstanding/transfer IDs reuse master rows 111990–111993. Current-year profit 331020 becomes equity_unaffected; retained earnings 331010 stays equity. Do not copy the generic retained_earnings type blindly: the source marks it equity_unaffected, while the master distinguishes accumulated equity from current-year profit.

The result is 425 accounts (418 master plus seven compatibility accounts). Master heading rows remain accounts as supplied. Codes remain six digits; seven compatibility rows retain their eight-digit codes. No posted entries are migrated.
