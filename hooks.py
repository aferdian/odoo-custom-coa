from odoo.exceptions import UserError


def check_fresh_company(env, company):
    if (
        company.parent_id
        or company.chart_template
        or env['account.account'].sudo().with_context(active_test=False).search_count(
            env['account.account']._check_company_domain(company), limit=1,
        )
        or env['account.move'].sudo().search_count(
            [('company_id', 'child_of', company.id)], limit=1,
        )
    ):
        raise UserError(
            'The custom Indonesian chart requires a fresh root company with no chart, '
            'accounts or accounting entries. Existing accounting data is not migrated.'
        )


def pre_init_hook(env):
    localization = env['ir.module.module'].search([('name', '=', 'l10n_id')], limit=1)
    if localization.demo:
        raise UserError(
            'Install the custom Indonesian chart in a fresh database with demo data '
            'disabled. Indonesian demo charts load before dependent addon overrides.'
        )
    check_fresh_company(env, env.company)
