"""matplotlib 图表（返回 Figure，不调用 plt.show）"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def make_resource_analysis_figure(df_8760):
    """2x3 资源分析图（月度发电量 + 日内出力 + 保证率）"""
    months = list(range(1, 13))
    df = df_8760.copy()
    df['month'] = pd.date_range("2026-01-01", periods=8760, freq="h").month
    df['hour_of_day'] = df.index % 24

    pv_monthly   = [(df[df['month'] == m]['pv_norm']   * 10000).sum() / 1e8 for m in months]
    wind_monthly = [(df[df['month'] == m]['wind_norm'] * 10000).sum() / 1e8 for m in months]
    hourly_pv    = df.groupby('hour_of_day')['pv_norm'].mean()
    hourly_wind  = df.groupby('hour_of_day')['wind_norm'].mean()

    pv_sorted   = np.sort(df['pv_norm'].values)[::-1]
    wind_sorted = np.sort(df['wind_norm'].values)[::-1]
    guarantee   = np.linspace(0, 100, 8760)

    fig, axes = plt.subplots(2, 3, figsize=(16, 9))

    axes[0, 0].bar(months, pv_monthly, color='#F2994A')
    axes[0, 0].set_title("光伏月度理论发电量 (亿kWh)")
    axes[0, 0].set_xlabel("月份"); axes[0, 0].grid(linestyle='--', alpha=0.5)

    axes[0, 1].plot(hourly_pv.index, hourly_pv.values, color='#F2994A', linewidth=2)
    axes[0, 1].set_title("光伏日内 24 小时平均出力特性")
    axes[0, 1].set_xlabel("日内时刻 (Hour)"); axes[0, 1].grid(linestyle='--', alpha=0.5)

    axes[0, 2].plot(guarantee, pv_sorted, color='#F2994A', linewidth=2)
    axes[0, 2].set_title("光伏电力保证率曲线")
    axes[0, 2].set_xlabel("电力保证率 (%)"); axes[0, 2].grid(linestyle='--', alpha=0.5)

    axes[1, 0].bar(months, wind_monthly, color='#2F80ED')
    axes[1, 0].set_title("风电月度理论发电量 (亿kWh)")
    axes[1, 0].set_xlabel("月份"); axes[1, 0].grid(linestyle='--', alpha=0.5)

    axes[1, 1].plot(hourly_wind.index, hourly_wind.values, color='#2F80ED', linewidth=2)
    axes[1, 1].set_title("风电日内 24 小时平均出力特性")
    axes[1, 1].set_xlabel("日内时刻 (Hour)"); axes[1, 1].grid(linestyle='--', alpha=0.5)

    axes[1, 2].plot(guarantee, wind_sorted, color='#2F80ED', linewidth=2)
    axes[1, 2].set_title("风电电力保证率曲线")
    axes[1, 2].set_xlabel("电力保证率 (%)"); axes[1, 2].grid(linestyle='--', alpha=0.5)

    plt.tight_layout()
    return fig


def make_daily_dispatch_figure(dispatch_df, day):
    """某一天的逐时源荷匹配图（堆叠柱 + 负荷曲线）"""
    start = (day - 1) * 24
    end = start + 24
    hours = np.arange(1, 25)
    sub = dispatch_df.iloc[start:end]

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(hours, sub['pv_gen_wan'],  width=0.7, label='光伏出力', color='#F2994A')
    ax.bar(hours, sub['wind_gen_wan'], width=0.7, bottom=sub['pv_gen_wan'],
           label='风电出力', color='#56CCF2')
    ax.bar(hours, sub['bess_dis_wan'], width=0.7,
           bottom=sub['pv_gen_wan'] + sub['wind_gen_wan'],
           label='储能放电', color='#27AE60')
    ax.bar(hours, sub['grid_buy_wan'], width=0.7,
           bottom=sub['pv_gen_wan'] + sub['wind_gen_wan'] + sub['bess_dis_wan'],
           label='外购电', color='#EB5757')
    ax.plot(hours, sub['load_wan'], color='#1F497D', marker='o',
            linewidth=2, markersize=4, label='用电负荷')
    ax.bar(hours, sub['bess_ch_wan'], width=0.35, label='储能充电',
           color='#9B51E0', alpha=0.85)
    ax.bar(hours, sub['curtail_wan'], width=0.35, bottom=sub['bess_ch_wan'],
           label='弃电量', color='#95A5A6', alpha=0.65)

    ax.set_xlim(0.5, 24.5)
    ax.set_xticks(hours)
    ax.set_xlabel("小时"); ax.set_ylabel("功率 (万kW)")
    ax.set_title(f"第 {day} 天源荷匹配情况")
    ax.grid(axis='y', linestyle='--', alpha=0.4)
    ax.legend(loc='upper right', ncol=4, fontsize=9)
    plt.tight_layout()
    return fig