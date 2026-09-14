"""财务评估、IRR"""
import numpy as np
import pandas as pd


def calc_irr(cash_flows):
    def npv(rate):
        return sum(cf / ((1.0 + rate) ** t) for t, cf in enumerate(cash_flows))
    low, high = -0.9, 2.0
    for _ in range(100):
        mid = (low + high) / 2.0
        val = npv(mid)
        if abs(val) < 1e-5:
            return mid
        if npv(low) * val < 0:
            high = mid
        else:
            low = mid
    return mid


def run_financial_evaluation(cap_res, df_sim, params, custom_price_buy=None):
    """与你原文件完全一致，此处省略大段注释，直接搬过来即可"""
    P_pv_kw    = cap_res['PV_kW']
    P_wind_kw  = cap_res['Wind_kW']
    E_bess_kwh = cap_res['BESS_kWh']
    P_bess_kw  = cap_res['BESS_kW']

    total_cap_kw = P_pv_kw + P_wind_kw
    price_self_use = custom_price_buy if custom_price_buy is not None else params['price_self_use']

    inv_pv_wan   = (P_pv_kw  * params['spec_invest_pv'])   / 10000.0
    inv_wind_wan = (P_wind_kw * params['spec_invest_wind']) / 10000.0
    inv_bess_e_wan = (E_bess_kwh * params['spec_invest_bess_e']) / 10000.0
    inv_bess_p_wan = (P_bess_kw  * params['spec_invest_bess_p']) / 10000.0
    inv_bess_total_wan = inv_bess_e_wan + inv_bess_p_wan
    total_static_inv_wan = inv_pv_wan + inv_wind_wan + inv_bess_total_wan

    debt_static_wan = total_static_inv_wan * (1.0 - params['equity_ratio'])
    construction_years = params.get('construction_period', 1.0)
    interest_construction_wan = debt_static_wan * 0.5 * params['loan_interest_long'] * construction_years
    working_capital_wan = (total_cap_kw * params.get('working_cap_spec', 30.0)) / 10000.0

    total_project_inv_wan = total_static_inv_wan + interest_construction_wan + working_capital_wan
    equity_wan = (total_static_inv_wan + interest_construction_wan) * params['equity_ratio'] + working_capital_wan * 0.2
    debt_total_wan = (total_static_inv_wan + interest_construction_wan) * (1.0 - params['equity_ratio'])

    annual_repair    = (total_static_inv_wan + interest_construction_wan - total_static_inv_wan * 0.1) * params['repair_rate']
    annual_insurance = (total_static_inv_wan + interest_construction_wan - total_static_inv_wan * 0.1) * params['insurance_rate']
    annual_labor     = params['staff_count'] * params['avg_wage'] * (1.0 + params['welfare_rate'])
    annual_material  = (total_cap_kw * params['material_cost_rate']) / 10000.0
    annual_other     = (total_cap_kw * params['other_cost_rate'])    / 10000.0
    annual_om_fixed  = annual_repair + annual_insurance + annual_labor + annual_material + annual_other

    total_gen_kwh = (df_sim['pv_gen_wan'].sum() + df_sim['wind_gen_wan'].sum()) * 1e4
    curtail_kwh   = df_sim['curtail_wan'].sum() * 1e4
    bess_loss_kwh = (df_sim['bess_ch_wan'].sum() - df_sim['bess_dis_wan'].sum()) * 1e4
    self_use_kwh  = total_gen_kwh - curtail_kwh - bess_loss_kwh
    annual_revenue_wan = (self_use_kwh * price_self_use) / 10000.0

    N_proj = max(params['N_pv'], params['N_wind'], params['N_bess'])
    cf_pre  = [-total_project_inv_wan]
    cf_post = [-total_project_inv_wan]
    cf_eq   = [-equity_wan]

    annual_debt_repayment = debt_total_wan / 10.0
    remaining_debt = debt_total_wan

    capex_input_vat = total_static_inv_wan * (params['vat_rate'] / (1.0 + params['vat_rate']))
    vat_input_pool = capex_input_vat
    loss_queue = [0.0] * 5
    cum_surplus = 0.0
    max_surplus = equity_wan * 0.5

    list_year = list(range(0, N_proj + 1))
    list_annual_gen      = [0.0] * (N_proj + 1)
    list_rev_no_vat      = [0.0] * (N_proj + 1)
    list_rev_with_vat    = [0.0] * (N_proj + 1)
    list_surcharge       = [0.0] * (N_proj + 1)
    list_annual_om_fixed = [0.0] * (N_proj + 1)
    list_om_no_vat       = [0.0] * (N_proj + 1)
    list_depreciation    = [0.0] * (N_proj + 1)
    list_interest        = [0.0] * (N_proj + 1)
    list_repair          = [0.0] * (N_proj + 1)
    list_labor           = [0.0] * (N_proj + 1)
    list_insurance       = [0.0] * (N_proj + 1)
    list_material        = [0.0] * (N_proj + 1)
    list_other           = [0.0] * (N_proj + 1)
    list_total_cost      = [0.0] * (N_proj + 1)
    list_profit_total    = [0.0] * (N_proj + 1)
    list_taxable_income  = [0.0] * (N_proj + 1)
    list_income_tax      = [0.0] * (N_proj + 1)
    list_net_profit      = [0.0] * (N_proj + 1)

    for year in range(1, N_proj + 1):
        mid_capex_wan = 0.0
        bess_life = params.get('bess_life', 10)
        if year < N_proj and year % bess_life == 0:
            mid_capex_wan += inv_bess_e_wan
        if year == 20 and N_proj > 20:
            mid_capex_wan += (P_wind_kw * params.get('wind_extend_spec', 450.0)) / 10000.0
        if mid_capex_wan > 0:
            vat_input_pool += mid_capex_wan * (params['vat_rate'] / (1.0 + params['vat_rate']))

        interest = remaining_debt * params['loan_interest_long'] if year <= 10 else 0.0
        depreciation = (total_static_inv_wan + interest_construction_wan - total_static_inv_wan * 0.1) / 20

        revenue_no_vat = annual_revenue_wan / (1.0 + params['vat_rate'])
        vat_output     = annual_revenue_wan - revenue_no_vat
        om_no_vat      = annual_om_fixed / (1.0 + params['vat_rate'])
        om_input_vat   = annual_om_fixed - om_no_vat

        net_vat_due = max(0.0, vat_output - om_input_vat)
        if vat_input_pool >= net_vat_due:
            vat_payable = 0.0
            vat_input_pool -= net_vat_due
        else:
            vat_payable = net_vat_due - vat_input_pool
            vat_input_pool = 0.0

        sales_surcharges = vat_payable * (params['urban_tax_rate'] + params['edu_tax_rate'])
        ebit = revenue_no_vat - annual_om_fixed - depreciation - sales_surcharges
        accounting_profit = ebit - interest

        if accounting_profit > 0:
            remaining = accounting_profit
            for idx in range(5):
                if remaining <= 0: break
                offset = min(remaining, loss_queue[idx])
                loss_queue[idx] -= offset
                remaining -= offset
            taxable_income = remaining
            loss_queue.pop(0); loss_queue.append(0.0)
        else:
            taxable_income = 0.0
            loss_queue.pop(0); loss_queue.append(abs(accounting_profit))

        if year <= 3:    rate = 0.0
        elif year <= 6:  rate = params['income_tax_rate'] * 0.5
        else:            rate = params['income_tax_rate']

        income_tax = taxable_income * rate
        net_profit = accounting_profit - income_tax

        if net_profit > 0 and cum_surplus < max_surplus:
            raw = net_profit * params['surplus_reserve_rate']
            surplus = min(raw, max_surplus - cum_surplus)
            cum_surplus += surplus
        else:
            surplus = 0.0

        cf_pre_year  = annual_revenue_wan - annual_om_fixed - sales_surcharges - mid_capex_wan
        cf_post_year = cf_pre_year - income_tax
        principal_pay = annual_debt_repayment if year <= 10 else 0.0
        cf_eq_year = cf_post_year - interest - principal_pay

        if year == N_proj:
            cf_pre_year  += working_capital_wan
            cf_post_year += working_capital_wan
            cf_eq_year   += working_capital_wan

        cf_pre.append(cf_pre_year)
        cf_post.append(cf_post_year)
        cf_eq.append(cf_eq_year)

        list_annual_gen[year]      = self_use_kwh / 10000.0
        list_rev_no_vat[year]      = revenue_no_vat
        list_rev_with_vat[year]    = annual_revenue_wan
        list_surcharge[year]       = sales_surcharges
        list_annual_om_fixed[year] = annual_om_fixed
        list_om_no_vat[year]       = om_no_vat
        list_depreciation[year]    = depreciation
        list_interest[year]        = interest
        list_repair[year]          = annual_repair
        list_labor[year]           = annual_labor
        list_insurance[year]       = annual_insurance
        list_material[year]        = annual_material
        list_other[year]           = annual_other
        list_total_cost[year]      = annual_om_fixed + depreciation + interest
        list_profit_total[year]    = accounting_profit
        list_taxable_income[year]  = taxable_income
        list_income_tax[year]      = income_tax
        list_net_profit[year]      = net_profit

        remaining_debt = max(0.0, remaining_debt - principal_pay)

    irr_pre_tax  = calc_irr(cf_pre)
    irr_post_tax = calc_irr(cf_post)
    irr_equity   = calc_irr(cf_eq)

    df_cash_flow = pd.DataFrame({
        "年份": list_year,
        "全投资所得税前净现金流量(万元)": cf_pre,
        "全投资所得税后净现金流量(万元)": cf_post,
        "资本金净现金流(万元)": cf_eq,
    })
    df_cost = pd.DataFrame({
        "年份": list_year,
        "固定修理费(万元)": list_repair,
        "工资及福利费(万元)": list_labor,
        "保险费(万元)": list_insurance,
        "材料费(万元)": list_material,
        "其它费用(万元)": list_other,
        "折旧费(万元)": list_depreciation,
        "经营成本(含运维/工资/保险等)(万元)": list_annual_om_fixed,
        "利息支出(万元)": list_interest,
        "总成本费用(万元)": list_total_cost,
    })
    df_profit = pd.DataFrame({
        "年份": list_year,
        "年发电量(万kWh)": list_annual_gen,
        "发电销售收入（万元）": list_rev_with_vat,
        "营业收入(不含税)(万元)": list_rev_no_vat,
        "营业税金及附加(万元)": list_surcharge,
        "总成本费用(万元)": list_total_cost,
        "利润总额(万元)": list_profit_total,
        "应纳税所得额(万元)": list_taxable_income,
        "所得税(万元)": list_income_tax,
        "净利润(万元)": list_net_profit,
    })

    return {
        'inv_pv_wan': inv_pv_wan,
        'inv_wind_wan': inv_wind_wan,
        'inv_bess_total_wan': inv_bess_total_wan,
        'total_static_inv_wan': total_static_inv_wan,
        'interest_construction_wan': interest_construction_wan,
        'working_capital_wan': working_capital_wan,
        'total_project_inv_wan': total_project_inv_wan,
        'equity_wan': equity_wan,
        'irr_pre_tax':  irr_pre_tax,
        'irr_post_tax': irr_post_tax,
        'irr_equity':   irr_equity,
        'cash_flow_df': df_cash_flow,
        'df_cost':      df_cost,
        'df_profit':    df_profit,
    }