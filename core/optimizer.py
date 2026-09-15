"""容量优化（启发式 + PuLP + Debug）"""
import os
import sys
import time
import numpy as np
import pandas as pd
from .simulation import simulate_8760


def _to_summary(dispatch_df):
    """把逐时数据汇总成财务评估需要的格式"""
    return pd.DataFrame({
        'pv_gen_wan':   [dispatch_df['pv_gen_wan'].sum()],
        'wind_gen_wan': [dispatch_df['wind_gen_wan'].sum()],
        'bess_dis_wan': [dispatch_df['bess_dis_wan'].sum()],
        'bess_ch_wan':  [dispatch_df['bess_ch_wan'].sum()],
        'curtail_wan':  [dispatch_df['curtail_wan'].sum()],
        'direct_load_wan': [dispatch_df['direct_load_wan'].sum()],
    })


def optimize_capacity_heuristic(
    df_8760, params,
    load_self_use_ratio=0.30,
    verbose=False,
    pv_max=1_000_000, wind_max=1_000_000,
    bess_p_max=500_000, bess_h_max=10.0,
):
    """启发式容量优化（差分进化）"""
    from scipy.optimize import differential_evolution, NonlinearConstraint
    bounds = [
        (0, pv_max), (0, wind_max),
        (0, bess_p_max), (0, bess_h_max),
    ]

    r = params['r']
    crf_pv   = (r * (1 + r) ** params['N_pv'])   / ((1 + r) ** params['N_pv']   - 1)
    crf_wind = (r * (1 + r) ** params['N_wind']) / ((1 + r) ** params['N_wind'] - 1)
    crf_bess = (r * (1 + r) ** params['N_bess']) / ((1 + r) ** params['N_bess'] - 1)

    cache = {}

    def evaluate_metrics(x):
        pv_kw, wind_kw, bess_p_kw, bess_h = x
        cap = {'PV_kW': pv_kw, 'Wind_kW': wind_kw,
               'BESS_kW': bess_p_kw, 'BESS_kWh': bess_p_kw * bess_h}
        dispatch = simulate_8760(df_8760, cap, params)

        grid_buy_kwh = dispatch['grid_buy_wan'].sum() * 1e4
        total_load_kwh = dispatch['load_wan'].sum() * 1e4
        available_generation_kwh = (
            dispatch['pv_gen_wan'].sum() + dispatch['wind_gen_wan'].sum()
        ) * 1e4
        self_use_kwh = (
            dispatch['direct_load_wan'].sum()
            + dispatch['bess_dis_wan'].sum()
        ) * 1e4
        self_use_to_generation = (
            self_use_kwh / available_generation_kwh
            if available_generation_kwh > 0 else 0.0
        )
        self_use_to_load = (
            self_use_kwh / total_load_kwh
            if total_load_kwh > 0 else 0.0
        )
        return (
            dispatch, grid_buy_kwh, available_generation_kwh,
            self_use_kwh, self_use_to_generation, self_use_to_load,
        )

    def constraint_values(x):
        metrics = evaluate_metrics(x)
        return np.array([
            metrics[4] - 0.60,
            metrics[5] - load_self_use_ratio,
        ])

    def objective(x):
        key = (round(x[0], -3), round(x[1], -3), round(x[2], -3), round(x[3], 1))
        if key in cache:
            return cache[key]

        pv_kw, wind_kw, bess_p_kw, bess_h = x
        capex_ann = (
            crf_pv   * pv_kw   * params['spec_invest_pv']   / 10000.0 +
            crf_wind * wind_kw * params['spec_invest_wind'] / 10000.0 +
            crf_bess * bess_p_kw * bess_h * params['spec_invest_bess_e'] / 10000.0 +
            crf_bess * bess_p_kw * params['spec_invest_bess_p'] / 10000.0
        )

        dispatch, grid_buy_kwh, available_generation_kwh, self_use_kwh, \
            ratio_renew, ratio_load = evaluate_metrics(x)
        grid_cost = grid_buy_kwh * params['price_buy'] / 10000.0

        penalty = 0.0
        if ratio_load < load_self_use_ratio:
            penalty += (load_self_use_ratio - ratio_load) * 1e6

        val = capex_ann + grid_cost + penalty
        cache[key] = val
        return val

    if verbose:
        print(">>> 启动差分进化算法...")
        year_hint = "2030 年前" if abs(load_self_use_ratio - 0.30) < 1e-6 else "2030 年起"
        print(
            f">>> 约束：光伏+风电可用发电量自发自用比例 >= 60%，"
            f"负荷自发自用比例 >= {load_self_use_ratio:.0%}（{year_hint}）"
        )

    result = differential_evolution(
        objective, bounds,
        maxiter=15, popsize=12, tol=1e-3, seed=42,
        constraints=NonlinearConstraint(
            constraint_values, np.zeros(2), np.full(2, np.inf)
        ),
        disp=verbose, workers=1, polish=True,
    )

    pv_opt, wind_opt, bess_p_opt, bess_h_opt = result.x
    bess_e_opt = bess_p_opt * bess_h_opt

    if verbose:
        print(f"[启发式] 最优解: PV={pv_opt/1e4:.2f}万kW Wind={wind_opt/1e4:.2f}万kW "
              f"BESS={bess_p_opt/1e4:.2f}万kW/{bess_e_opt/1e4:.2f}万kWh "
              f"时长={bess_h_opt:.2f}h")
        print(f"[启发式] 目标函数值 = {result.fun:.2f} 万元/年")

    cap_res = {'PV_kW': pv_opt, 'Wind_kW': wind_opt,
               'BESS_kW': bess_p_opt, 'BESS_kWh': bess_e_opt}
    dispatch_df = simulate_8760(df_8760, cap_res, params)
    return cap_res, dispatch_df


def optimize_capacity_pulp(df_8760, params,
                            load_self_use_ratio=0.35,
                            verbose=False):
    """PuLP 混合整数线性规划优化（原 v2.4 版本）"""
    import pulp
    if verbose:
        print(">>> 正在构建 PuLP 混合整数线性规划优化模型...")
    prob = pulp.LpProblem("Capacity_Optimization", pulp.LpMinimize)

    P_pv_cap   = pulp.LpVariable("P_pv_cap",   lowBound=0)
    P_wind_cap = pulp.LpVariable("P_wind_cap", lowBound=0)
    P_bess_cap = pulp.LpVariable("P_bess_cap", lowBound=0)
    E_bess_cap = pulp.LpVariable("E_bess_cap", lowBound=0)

    prob += E_bess_cap >= P_bess_cap * 0.5
    prob += E_bess_cap <= P_bess_cap * 8.0

    hours = range(8760)
    P_grid_buy = pulp.LpVariable.dicts("P_grid_buy", hours, lowBound=0)
    P_ch       = pulp.LpVariable.dicts("P_ch",       hours, lowBound=0)
    P_dis      = pulp.LpVariable.dicts("P_dis",      hours, lowBound=0)
    SoC        = pulp.LpVariable.dicts("SoC",        hours, lowBound=0)
    P_curtail  = pulp.LpVariable.dicts("P_curtail",  hours, lowBound=0)

    r = params['r']
    crf_pv   = (r * (1 + r) ** params['N_pv'])   / ((1 + r) ** params['N_pv']   - 1)
    crf_wind = (r * (1 + r) ** params['N_wind']) / ((1 + r) ** params['N_wind'] - 1)
    crf_bess = (r * (1 + r) ** params['N_bess']) / ((1 + r) ** params['N_bess'] - 1)

    capex_ann = (crf_pv   * P_pv_cap   * params['spec_invest_pv']   +
                 crf_wind * P_wind_cap * params['spec_invest_wind'] +
                 crf_bess * E_bess_cap * params['spec_invest_bess_e'] +
                 crf_bess * P_bess_cap * params['spec_invest_bess_p'])

    effective_price = params['price_self_use']
    grid_cost = pulp.lpSum([P_grid_buy[t] * effective_price for t in hours])
    prob += capex_ann + grid_cost

    for t in hours:
        pv_gen   = P_pv_cap   * df_8760.loc[t, 'pv_norm']
        wind_gen = P_wind_cap * df_8760.loc[t, 'wind_norm']
        prob += df_8760.loc[t, 'load'] + P_curtail[t] == pv_gen + wind_gen + P_dis[t] - P_ch[t] + P_grid_buy[t]
        prob += P_ch[t]  <= P_bess_cap
        prob += P_dis[t] <= P_bess_cap
        if t == 0:
            prob += SoC[t] == E_bess_cap * 0.50
        else:
            prob += SoC[t] == SoC[t-1] + P_ch[t] * params['eta_ch'] - P_dis[t] / params['eta_dis']
        prob += SoC[t] >= E_bess_cap * params['soc_min']
        prob += SoC[t] <= E_bess_cap * params['soc_max']

    total_load     = df_8760['load'].sum()
    total_pv_gen   = pulp.lpSum([P_pv_cap   * df_8760.loc[t, 'pv_norm']   for t in hours])
    total_wind_gen = pulp.lpSum([P_wind_cap * df_8760.loc[t, 'wind_norm'] for t in hours])
    total_grid_buy = pulp.lpSum([P_grid_buy[t] for t in hours])
    total_self_use = total_load - total_grid_buy
    total_available_generation = total_pv_gen + total_wind_gen

    # 可用发电量只统计光伏和风电，不统计储能放电。
    prob += total_self_use >= 0.60 * total_available_generation, "SelfUse_Ratio_to_Renewable"
    prob += total_self_use >= load_self_use_ratio * total_load,      "SelfUse_Ratio_to_Load"

    if verbose:
        print(">>> 求解器正在计算最优配置...")
    bundled_cbc = None
    if hasattr(sys, "_MEIPASS"):
        bundled_cbc = os.path.join(
            sys._MEIPASS, "pulp", "solverdir", "cbc", "win", "i64", "cbc.exe"
        )
        if not os.path.isfile(bundled_cbc):
            bundled_cbc = None

    solver = (
        pulp.COIN_CMD(path=bundled_cbc, msg=False)
        if bundled_cbc
        else pulp.PULP_CBC_CMD(msg=False)
    )
    prob.solve(solver)

    pv_opt_kw     = pulp.value(P_pv_cap)
    wind_opt_kw   = pulp.value(P_wind_cap)
    bess_e_opt_kwh = pulp.value(E_bess_cap)
    bess_p_opt_kw  = pulp.value(P_bess_cap)

    df_res = pd.DataFrame({
        'hour':         range(1, 8761),
        'load_wan':     df_8760['load'].values / 10000.0,
        'pv_gen_wan':   [pv_opt_kw   * df_8760.loc[t, 'pv_norm']   / 10000.0 for t in hours],
        'wind_gen_wan': [wind_opt_kw * df_8760.loc[t, 'wind_norm'] / 10000.0 for t in hours],
        'bess_ch_wan':  [pulp.value(P_ch[t])      / 10000.0 for t in hours],
        'bess_dis_wan': [pulp.value(P_dis[t])     / 10000.0 for t in hours],
        'grid_buy_wan': [pulp.value(P_grid_buy[t])/ 10000.0 for t in hours],
        'curtail_wan':  [pulp.value(P_curtail[t]) / 10000.0 for t in hours],
    })

    cap_res = {
        "PV_kW":   pv_opt_kw,
        "Wind_kW": wind_opt_kw,
        "BESS_kWh": bess_e_opt_kwh,
        "BESS_kW":  bess_p_opt_kw,
    }

    if verbose:
        pv_sum = df_8760['pv_norm'].sum()
        wind_sum = df_8760['wind_norm'].sum()
        self_use_val = total_load - sum(pulp.value(P_grid_buy[t]) for t in hours)
        available_generation_val = pv_opt_kw * pv_sum + wind_opt_kw * wind_sum
        print(f"[PuLP] 自发自用/光伏风电可用发电量 = "
              f"{self_use_val / (available_generation_val + 1e-9) * 100:.2f}%")
        print(f"[PuLP] 自发自用/总负荷 = {self_use_val / (total_load + 1e-9) * 100:.2f}%")

    return cap_res, df_res


def optimize_capacity_debug(df_8760, params,
                             pv_kw=100000.0, wind_kw=0.0,
                             bess_kw=0.0, bess_hours=0.0,
                             verbose=True):
    """调试用假求解器：按给定容量直接生成仿真结果，不做任何优化"""
    t0 = time.time()
    cap_res = {
        'PV_kW':   float(pv_kw),
        'Wind_kW': float(wind_kw),
        'BESS_kW': float(bess_kw),
        'BESS_kWh': float(bess_kw) * float(bess_hours),
    }
    df_res = simulate_8760(df_8760, cap_res, params)

    if verbose:
        print(f"\n[DEBUG] 使用假求解器，耗时 {time.time() - t0:.2f} 秒")
        print(f"[DEBUG] PV={cap_res['PV_kW']/1e4:.2f}万kW  "
              f"Wind={cap_res['Wind_kW']/1e4:.2f}万kW  "
              f"BESS={cap_res['BESS_kW']/1e4:.2f}万kW/{cap_res['BESS_kWh']/1e4:.2f}万kWh  "
              f"年弃电={df_res['curtail_wan'].sum():.2f}万kWh")

    return cap_res, df_res