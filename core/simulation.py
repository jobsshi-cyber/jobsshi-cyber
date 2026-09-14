"""8760 小时仿真"""
import numpy as np
import pandas as pd


def simulate_8760(df_8760, cap_res, params):
    """逐时仿真（单位：万kW）"""
    pv_kw       = cap_res['PV_kW']
    wind_kw     = cap_res['Wind_kW']
    bess_p_kw   = cap_res['BESS_kW']
    bess_e_kwh  = cap_res['BESS_kWh']

    eta_ch  = params.get('eta_ch', 0.95)
    eta_dis = params.get('eta_dis', 0.95)
    soc_min = params.get('soc_min', 0.10)
    soc_max = params.get('soc_max', 0.90)

    soc = bess_e_kwh * 0.5
    pv_arr   = df_8760['pv_norm'].values
    wind_arr = df_8760['wind_norm'].values
    load_arr = df_8760['load'].values

    pv_gen_arr   = pv_kw   * pv_arr
    wind_gen_arr = wind_kw * wind_arr

    bess_ch  = np.zeros(8760); bess_dis = np.zeros(8760)
    grid_buy = np.zeros(8760); curtail  = np.zeros(8760)

    for t in range(8760):
        p_gen  = pv_gen_arr[t] + wind_gen_arr[t]
        p_load = load_arr[t]
        diff   = p_gen - p_load
        if diff > 0:
            max_ch = (bess_e_kwh * soc_max - soc) / eta_ch
            p_ch = min(diff, bess_p_kw, max_ch)
            soc += p_ch * eta_ch
            bess_ch[t] = p_ch
            curtail[t] = diff - p_ch
        else:
            deficit = -diff
            max_dis = (soc - bess_e_kwh * soc_min) * eta_dis
            p_dis = min(deficit, bess_p_kw, max_dis)
            soc -= p_dis / eta_dis
            bess_dis[t] = p_dis
            grid_buy[t] = deficit - p_dis

    return pd.DataFrame({
        'hour':          np.arange(1, 8761),
        'pv_gen_wan':    pv_gen_arr   / 10000.0,
        'wind_gen_wan':  wind_gen_arr / 10000.0,
        'bess_ch_wan':   bess_ch      / 10000.0,
        'bess_dis_wan':  bess_dis     / 10000.0,
        'grid_buy_wan':  grid_buy     / 10000.0,
        'curtail_wan':   curtail      / 10000.0,
        'load_wan':      load_arr     / 10000.0,
    })


def simulate_detailed_8760(df_8760, cap_res, params):
    """与 simulate_8760 完全等价（保留原函数名，兼容旧代码）"""
    return simulate_8760(df_8760, cap_res, params)