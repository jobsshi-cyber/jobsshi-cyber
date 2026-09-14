import io
import os
import html
import base64
import datetime
from pathlib import Path
import pandas as pd
import numpy as np
from scipy.optimize import differential_evolution
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import streamlit as st
import streamlit.components.v1 as components
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core import (
    get_default_params, get_parameter_schema,
    load_8760_from_file, simulate_8760,
    run_financial_evaluation, optimize_capacity_heuristic,
    make_resource_analysis_figure,
    export_financial_tables_to_bytes,
    calc_annual_tariff_fee, calc_user_avg_price,
)
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side


def _show_protected_text(text: str):
    """显示不可直接选中的结果文本，复制权限由开发者控制。"""
    escaped_text = html.escape(text)
    st.markdown(
        f'<div class="protected-output">{escaped_text}</div>',
        unsafe_allow_html=True,
    )


def _show_protected_figure(
    fig, height: int = 650, alt_text: str = "受保护图表"
):
    """在隔离页面中展示图像并禁用常规右键另存为操作。"""
    image_buffer = io.BytesIO()
    fig.savefig(image_buffer, format="png", dpi=150, bbox_inches="tight")
    image_data = base64.b64encode(image_buffer.getvalue()).decode("ascii")
    components.html(
        f"""
        <div class="protected-figure"
             oncontextmenu="return false;"
             ondragstart="return false;"
             onselectstart="return false;">
          <img src="data:image/png;base64,{image_data}"
               alt="{html.escape(alt_text, quote=True)}"
               draggable="false"
               oncontextmenu="return false;"
               style="display:block; width:100%; height:auto; user-select:none;
                      -webkit-user-select:none; -webkit-user-drag:none;
                      pointer-events:none;">
        </div>
        <script>
          document.addEventListener("contextmenu", function(event) {{
            event.preventDefault();
          }});
          document.addEventListener("dragstart", function(event) {{
            event.preventDefault();
          }});
        </script>
        """,
        height=height,
        scrolling=False,
    )

# =============================================================
# 0. 页面配置与字体
# =============================================================
st.set_page_config(
    page_title="绿电直连容量优化与财务分析",
    page_icon="🔋",
    layout="wide",
)

st.markdown(
    """
    <style>
    /* 结果文本不允许直接选中；如需复制请联系开发者。 */
    .protected-output {
        white-space: pre-wrap;
        user-select: none;
        -webkit-user-select: none;
        background: #f0f2f6;
        border-radius: 0.5rem;
        padding: 1rem;
        color: #1f497d;
        font-family: Consolas, "Courier New", monospace;
    }
    /* 隐藏数据表的下载菜单和图表工具栏下载入口。 */
    [data-testid="stElementToolbar"],
    [data-testid="stDataFrame"] button[title*="Download"],
    [data-testid="stDataFrame"] button[aria-label*="Download"] {
        display: none !important;
    }
    /* 输配电费指标结果不提供浏览器文本选择。 */
    [data-testid="stMetric"] {
        user-select: none;
        -webkit-user-select: none;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =============================================================
# 认证模块（自实现，30 天有效期许可）
# =============================================================
import hmac
import hashlib
import time
import bcrypt

# 用户凭据（用户名 → bcrypt 哈希）
# 明文密码：user1 = "user1_pass"，user2 = "user2_pass"
USERS_HASH = {
    "user1": "$2b$12$Rn.8pUTsjh9R55mO2CrpBee9bjLLQzt1ShQfsWg.WwwkGMcxLU2cG",
    "user2": "$2b$12$zk0MMrxiY9n96e9twD1I4.KNixXZb.mT8k9qKZTxBlmEhH6rJrSFe",
}
USER_NAMES = {"user1": "User One", "user2": "User Two"}
LICENSE_DAYS = 30
COOKIE_KEY = "Shi198611_change_this_to_a_random_string"
# 生产环境启用登录；调试时可临时改为 True。
DEBUG_SKIP_LOGIN = False

def _make_token(username: str) -> str:
    ts = str(int(time.time()))
    payload = f"{username}|{ts}"
    sig = hmac.new(COOKIE_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}|{sig}"

def _verify_token(token: str):
    if not token:
        return None
    try:
        username, ts, sig = token.split("|")
    except ValueError:
        return None
    payload = f"{username}|{ts}"
    expected = hmac.new(COOKIE_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    if time.time() - int(ts) > LICENSE_DAYS * 86400:
        return None
    return username

# 从 URL 恢复登录状态（30 天免登录）
if "auth_user" not in st.session_state:
    _token = st.query_params.get("token", "")
    _user = _verify_token(_token)
    if _user:
        st.session_state["auth_token"] = _token
        st.session_state["auth_user"] = _user

# 未登录 → 显示登录界面
if DEBUG_SKIP_LOGIN and "auth_user" not in st.session_state:
    st.session_state["auth_user"] = "debug"

if not DEBUG_SKIP_LOGIN and "auth_user" not in st.session_state:
    st.title("🔐 绿电直连容量优化与财务分析")
    st.caption(f"许可有效期 {LICENSE_DAYS} 天。如无账号请联系管理员。")

    with st.form("login_form"):
        _u = st.text_input("用户名")
        _p = st.text_input("密码", type="password")
        _ok = st.form_submit_button("登录")

    if _ok:
        if _u in USERS_HASH and bcrypt.checkpw(_p.encode("utf-8"), USERS_HASH[_u].encode("utf-8")):
            _t = _make_token(_u)
            st.session_state["auth_token"] = _t
            st.session_state["auth_user"] = _u
            st.query_params["token"] = _t
            st.rerun()
        else:
            st.error("❌ 用户名或密码错误")
    st.stop()

# 已登录 → 显示欢迎和登出
_display = USER_NAMES.get(st.session_state["auth_user"], st.session_state["auth_user"])
st.sidebar.success(f"👤 欢迎，**{_display}**")
st.sidebar.caption(f"许可有效期 {LICENSE_DAYS} 天")
if not DEBUG_SKIP_LOGIN and st.sidebar.button("🚪 退出登录"):
    st.session_state.pop("auth_token", None)
    st.session_state.pop("auth_user", None)
    st.query_params.clear()
    st.rerun()
# =============================================================

# 中文字体（把 SourceHanSansCN-Regular.otf 放到 fonts/ 目录）
FONT_PATH = Path(__file__).resolve().parent / "SourceHanSansCN-Regular.otf"
if not FONT_PATH.exists():
    FONT_PATH = Path(__file__).resolve().parent / "fonts" / "SourceHanSansCN-Regular.otf"
if os.path.exists(FONT_PATH):
    fm.fontManager.addfont(FONT_PATH)
    _fname = fm.FontProperties(fname=FONT_PATH).get_name()
    plt.rcParams['font.sans-serif'] = [_fname, 'DejaVu Sans']
else:
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


@st.cache_data(show_spinner=False)
def _load_uploaded_workbook(file_bytes):
    """缓存上传工作簿解析结果，避免普通控件变化时重复读取 Excel。"""
    from io import BytesIO

    workbook = BytesIO(file_bytes)
    df_pv = pd.read_excel(workbook, sheet_name='光伏逐小时数据', skiprows=2)
    workbook.seek(0)
    df_wind = pd.read_excel(workbook, sheet_name='风电逐小时数据', skiprows=2)
    workbook.seek(0)
    df_load = pd.read_excel(workbook, sheet_name='负荷逐小时数据', skiprows=2)

    pv_norm = pd.to_numeric(df_pv.iloc[0:8760, 5], errors='coerce').fillna(0).values
    wind_norm = pd.to_numeric(df_wind.iloc[0:8760, 5], errors='coerce').fillna(0).values
    load_kw = pd.to_numeric(df_load.iloc[0:8760, 5], errors='coerce').fillna(0).values * 10000.0
    return pd.DataFrame({'pv_norm': pv_norm, 'wind_norm': wind_norm, 'load': load_kw})


@st.cache_data(show_spinner=False)
def _prepare_resource_analysis(df_8760):
    """缓存资源预分析所需数组，避免交互时重复聚合和排序。"""
    df_analysis = df_8760.copy()
    df_analysis['month'] = pd.date_range("2026-01-01", periods=8760, freq="h").month
    df_analysis['hour_of_day'] = df_analysis.index % 24
    months = list(range(1, 13))
    pv_monthly = [
        (df_analysis[df_analysis['month'] == m]['pv_norm'] * 10000).sum() / 1e8
        for m in months
    ]
    wind_monthly = [
        (df_analysis[df_analysis['month'] == m]['wind_norm'] * 10000).sum() / 1e8
        for m in months
    ]
    load_monthly = [
        df_analysis[df_analysis['month'] == m]['load'].sum() / 1e8
        for m in months
    ]
    return (
        months,
        pv_monthly,
        wind_monthly,
        load_monthly,
        df_analysis.groupby('hour_of_day')['pv_norm'].mean(),
        df_analysis.groupby('hour_of_day')['wind_norm'].mean(),
        df_analysis.groupby('hour_of_day')['load'].mean(),
        np.sort(df_analysis['pv_norm'].values)[::-1],
        np.sort(df_analysis['wind_norm'].values)[::-1],
    )


# =============================================================
# 2. Streamlit 界面
# =============================================================
st.title("🔋 绿电直连容量优化与财务分析")

# -------------------- 侧边栏：参数配置 --------------------
with st.sidebar:
    st.header("⚙️ 参数配置")
    # 与桌面版共用同一参数 schema，确保分组、顺序、名称和默认值一致。
    parameter_schema = get_parameter_schema()
    parameter_groups = {}
    for group_name, label_text, key, default_value, value_type in parameter_schema:
        parameter_groups.setdefault(group_name, []).append(
            (label_text, key, default_value, value_type)
        )

    params = {}
    for group_name, fields in parameter_groups.items():
        with st.expander(group_name, expanded=group_name.startswith("1.")):
            for label_text, key, default_value, value_type in fields:
                widget_key = f"parameter_{key}"
                if value_type is int:
                    value = st.number_input(
                        label_text, value=int(default_value), step=1, key=widget_key
                    )
                else:
                    value = st.number_input(
                        label_text,
                        value=float(default_value),
                        step=0.01,
                        format="%.6g",
                        key=widget_key,
                    )
                params[key] = value_type(value)


# -------------------- 主区：数据上传 --------------------
st.subheader("📁 1. 上传 8760 小时数据文件")

uploaded = st.file_uploader(
    "上传 `8760小时模拟原始数据.xlsx`（含光伏、风电、负荷逐小时数据 3 个 Sheet）",
    type=['xlsx'],
)

template_path = Path(__file__).resolve().parent / "8760小时模拟模板.xlsx"
if template_path.exists():
    st.download_button(
        "📥 下载 8760 小时数据模板",
        data=template_path.read_bytes(),
        file_name="8760小时模拟模板.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        help="下载后可直接按模板格式修改或上传数据。",
    )
else:
    st.warning("数据模板文件暂不可用，请联系开发者。")

if uploaded is not None:
    try:
        df_8760 = _load_uploaded_workbook(uploaded.getvalue())
        st.session_state['df_8760'] = df_8760
        st.success(f"✅ 数据加载成功，共 {len(df_8760)} 小时。")
    except Exception as e:
        st.error(f"❌ 数据读取失败：{e}")


# -------------------- 主区：预分析图表 --------------------
st.subheader("📊 2. 资源特性预分析")

if 'df_8760' in st.session_state:
    df_8760 = st.session_state['df_8760']

    with st.expander("点击展开：光伏 / 风电资源特性图", expanded=False):
        (
            months, pv_monthly, wind_monthly, load_monthly,
            hourly_pv, hourly_wind, hourly_load, pv_sorted, wind_sorted,
        ) = _prepare_resource_analysis(df_8760)
        guarantee_rate = np.linspace(0, 100, 8760)

        # ---- 3 行 3 列画板，与桌面版预分析窗口保持一致 ----
        fig, axes = plt.subplots(3, 3, figsize=(16, 12))

        # 第一行：光伏
        axes[0, 0].bar(months, pv_monthly, width=0.6,
                       color='#F2994A', label='光伏(基准1万kW)')
        axes[0, 0].set_title("光伏月度理论发电量 (亿kWh)",
                              fontsize=11, fontweight='bold')
        axes[0, 0].set_xlabel("月份")
        axes[0, 0].set_ylabel("发电量 (亿kWh)")
        axes[0, 0].set_xticks(months)
        axes[0, 0].grid(linestyle='--', alpha=0.5)
        axes[0, 0].legend()

        axes[0, 1].plot(hourly_pv.index, hourly_pv.values,
                        color='#F2994A', linewidth=2,
                        label='光伏平均出力系数')
        axes[0, 1].set_title("光伏日内 24 小时平均出力特性",
                              fontsize=11, fontweight='bold')
        axes[0, 1].set_xlabel("日内时刻 (Hour)")
        axes[0, 1].set_ylabel("归一化出力系数")
        axes[0, 1].set_xticks(range(0, 24, 3))
        axes[0, 1].grid(linestyle='--', alpha=0.5)
        axes[0, 1].legend()

        axes[0, 2].plot(guarantee_rate, pv_sorted,
                        color='#F2994A', linewidth=2,
                        label='光伏出力持续曲线')
        axes[0, 2].set_title("光伏电力保证率曲线",
                              fontsize=11, fontweight='bold')
        axes[0, 2].set_xlabel("电力保证率 (%)")
        axes[0, 2].set_ylabel("归一化出力系数")
        axes[0, 2].grid(linestyle='--', alpha=0.5)
        axes[0, 2].legend()

        # 第二行：风电
        axes[1, 0].bar(months, wind_monthly, width=0.6,
                       color='#2F80ED', label='风电(基准1万kW)')
        axes[1, 0].set_title("风电月度理论发电量 (亿kWh)",
                              fontsize=11, fontweight='bold')
        axes[1, 0].set_xlabel("月份")
        axes[1, 0].set_ylabel("发电量 (亿kWh)")
        axes[1, 0].set_xticks(months)
        axes[1, 0].grid(linestyle='--', alpha=0.5)
        axes[1, 0].legend()

        axes[1, 1].plot(hourly_wind.index, hourly_wind.values,
                        color='#2F80ED', linewidth=2,
                        label='风电平均出力系数')
        axes[1, 1].set_title("风电日内 24 小时平均出力特性",
                              fontsize=11, fontweight='bold')
        axes[1, 1].set_xlabel("日内时刻 (Hour)")
        axes[1, 1].set_ylabel("归一化出力系数")
        axes[1, 1].set_xticks(range(0, 24, 3))
        axes[1, 1].grid(linestyle='--', alpha=0.5)
        axes[1, 1].legend()

        axes[1, 2].plot(guarantee_rate, wind_sorted,
                        color='#2F80ED', linewidth=2,
                        label='风电出力持续曲线')
        axes[1, 2].set_title("风电电力保证率曲线",
                              fontsize=11, fontweight='bold')
        axes[1, 2].set_xlabel("电力保证率 (%)")
        axes[1, 2].set_ylabel("归一化出力系数")
        axes[1, 2].grid(linestyle='--', alpha=0.5)
        axes[1, 2].legend()

        # 第三行：负荷
        axes[2, 0].bar(months, load_monthly, width=0.6,
                       color='#27AE60', label='负荷')
        axes[2, 0].set_title("负荷逐月用电量",
                              fontsize=11, fontweight='bold')
        axes[2, 0].set_xlabel("月份")
        axes[2, 0].set_ylabel("用电量 (亿kWh)")
        axes[2, 0].set_xticks(months)
        axes[2, 0].grid(linestyle='--', alpha=0.5)
        axes[2, 0].legend()

        axes[2, 1].plot(hourly_load.index, hourly_load.values,
                        color='#27AE60', linewidth=2, marker='o',
                        label='负荷平均出力')
        axes[2, 1].set_title("负荷日内 24 小时平均出力特性",
                              fontsize=11, fontweight='bold')
        axes[2, 1].set_xlabel("日内时刻 (Hour)")
        axes[2, 1].set_ylabel("平均出力 (kW)")
        axes[2, 1].set_xticks(range(0, 24, 3))
        axes[2, 1].grid(linestyle='--', alpha=0.5)
        axes[2, 1].legend()

        axes[2, 2].axis('off')

        plt.tight_layout()
        _show_protected_figure(
            fig,
            height=1080,
            alt_text="新能源资源与负荷特性预分析图",
        )
        plt.close(fig)
else:
    with st.container(border=True):
        st.caption("请先上传 8760 小时数据文件，上传后可展开查看光伏和风电资源特性分析。")


# -------------------- 自发自用比例选择 --------------------
st.subheader("⚙️ 3. 自发自用比例约束")

col_ratio, _ = st.columns([1, 3])
with col_ratio:
    self_use_option = st.radio(
        "新能源年自发自用电量 / 负荷总用电量 的最低比例：",
        options=["30%（2030 年前适用）", "35%（2030 年起适用）"],
        index=0,
        horizontal=False,
        help="政策要求：2030 年前最低 30%；2030 年起最低 35%。",
    )

load_self_use_ratio = 0.30 if self_use_option.startswith("30") else 0.35

# -------------------- 主区：容量配置与计算 --------------------
st.subheader("🎛️ 4. 容量配置与计算")

# ---- 初始化 session_state ----
if 'pv_wan_input' not in st.session_state:
    st.session_state['pv_wan_input'] = 10.0
if 'wind_wan_input' not in st.session_state:
    st.session_state['wind_wan_input'] = 0.0
if 'bess_p_wan_input' not in st.session_state:
    st.session_state['bess_p_wan_input'] = 0.0
if 'bess_h_input' not in st.session_state:
    st.session_state['bess_h_input'] = 2.0

# ---- ★ 关键：在 widget 渲染之前，应用上一次优化结果 ----
if '_opt_result' in st.session_state:
    _res = st.session_state.pop('_opt_result')
    st.session_state['pv_wan_input']     = _res['PV_kW'] / 10000.0
    st.session_state['wind_wan_input']   = _res['Wind_kW'] / 10000.0
    st.session_state['bess_p_wan_input'] = _res['BESS_kW'] / 10000.0
    st.session_state['bess_h_input'] = (
        _res['BESS_kWh'] / _res['BESS_kW'] if _res['BESS_kW'] > 0 else 2.0
    )

with st.form("capacity_form"):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        pv_wan = st.number_input("光伏装机容量 (万kW)", step=1.0, key="pv_wan_input")
    with col2:
        wind_wan = st.number_input("风电装机容量 (万kW)", step=1.0, key="wind_wan_input")
    with col3:
        bess_p_wan = st.number_input("储能 PCS 功率 (万kW)", step=0.5, key="bess_p_wan_input")
    with col4:
        bess_h = st.number_input("储能时长 (小时)", step=0.5, key="bess_h_input")

    st.write("")
    col_a, col_b = st.columns(2)
    with col_a:
        run_calc = st.form_submit_button("🔧 手动计算", type="primary", use_container_width=True)
    with col_b:
        run_auto = st.form_submit_button("🚀 自动优化", use_container_width=True)

# ---- 自动优化按钮逻辑 ----
# ---- 显示上一次自动优化的成功提示 ----
if '_opt_success_msg' in st.session_state:
    st.success(st.session_state.pop('_opt_success_msg'))
# ---- 自动优化按钮逻辑 ----
if run_auto:
    if 'df_8760' not in st.session_state:
        st.error("❌ 请先上传数据文件！")
    else:
        df_8760_local = st.session_state['df_8760']

        # 1. 跑启发式优化
        with st.spinner("⏳ 正在使用差分进化算法求解最优容量，请耐心等待（30~60 秒）..."):
            cap_res_opt, dispatch_df_opt = optimize_capacity_heuristic(
                df_8760_local, params, verbose=True,
                load_self_use_ratio=load_self_use_ratio,
            )

        # 2. 构造财务评估需要的汇总数据（不覆盖逐小时数据）
        df_sim_summary = pd.DataFrame({
            'pv_gen_wan':   [dispatch_df_opt['pv_gen_wan'].sum()],
            'wind_gen_wan': [dispatch_df_opt['wind_gen_wan'].sum()],
            'bess_dis_wan': [dispatch_df_opt['bess_dis_wan'].sum()],
            'bess_ch_wan':  [dispatch_df_opt['bess_ch_wan'].sum()],
            'curtail_wan':  [dispatch_df_opt['curtail_wan'].sum()],
        })

        # 3. 立即执行财务评估（这一步让指标能显示）
        fin_res_opt = run_financial_evaluation(cap_res_opt, df_sim_summary, params)

        # 4. 全部存进 session_state，供 rerun 后的页面使用
        st.session_state['_opt_result']  = cap_res_opt
        st.session_state['cap_res']      = cap_res_opt
        st.session_state['dispatch_df']  = dispatch_df_opt    # 逐小时数据，给逐日图用
        st.session_state['fin_res']      = fin_res_opt        # 财务结果，给指标区用

        # 5. 记录成功提示
        st.session_state['_opt_success_msg'] = (
            f"✅ 自动优化完成！（负荷自用率约束 ≥ {load_self_use_ratio*100:.0f}%）\n\n"
            "提示：使用差分进化算法求解，未必是最优配置，请结合客观条件进行调整。\n\n"
            f"优化结果：光伏 {cap_res_opt['PV_kW']/10000:.2f} 万kW，"
            f"风电 {cap_res_opt['Wind_kW']/10000:.2f} 万kW，"
            f"储能 {cap_res_opt['BESS_kW']/10000:.2f} 万kW / "
            f"{cap_res_opt['BESS_kWh']/10000:.2f} 万kWh"
        )

        st.rerun()

# ---- 手动计算按钮逻辑 ----
if run_calc:
    if 'df_8760' not in st.session_state:
        st.error("❌ 请先上传数据文件！")
    else:
        df_8760 = st.session_state['df_8760']
        pv_kw = pv_wan * 10000.0
        wind_kw = wind_wan * 10000.0
        bess_p_kw = bess_p_wan * 10000.0
        bess_e_kwh = bess_p_kw * bess_h

        cap_res = {'PV_kW': pv_kw, 'Wind_kW': wind_kw, 'BESS_kW': bess_p_kw, 'BESS_kWh': bess_e_kwh}

        with st.spinner("正在运行 8760 小时仿真与财务评估..."):
            dispatch_df = simulate_8760(df_8760, cap_res, params)

            df_sim = pd.DataFrame({
                'pv_gen_wan':  [dispatch_df['pv_gen_wan'].sum()],
                'wind_gen_wan':[dispatch_df['wind_gen_wan'].sum()],
                'bess_dis_wan':[dispatch_df['bess_dis_wan'].sum()],
                'bess_ch_wan': [dispatch_df['bess_ch_wan'].sum()],
                'curtail_wan': [dispatch_df['curtail_wan'].sum()],
            })
            fin_res = run_financial_evaluation(cap_res, df_sim, params)

            st.session_state['cap_res'] = cap_res
            st.session_state['dispatch_df'] = dispatch_df
            st.session_state['fin_res'] = fin_res

        st.success("✅ 计算完成！")

# -------------------- 主区：结果展示 --------------------
if 'fin_res' in st.session_state:
    fin_res = st.session_state['fin_res']
    dispatch_df = st.session_state['dispatch_df']

    st.subheader("📈 5. 运营指标")

    total_load = dispatch_df['load_wan'].sum()
    self_use = dispatch_df['pv_gen_wan'].sum() + dispatch_df['wind_gen_wan'].sum() \
               - dispatch_df['curtail_wan'].sum() \
               - (dispatch_df['bess_ch_wan'].sum() - dispatch_df['bess_dis_wan'].sum())
    grid_buy = dispatch_df['grid_buy_wan'].sum()
    curtail = dispatch_df['curtail_wan'].sum()

    pv_theory = st.session_state['cap_res']['PV_kW'] * st.session_state['df_8760']['pv_norm'].sum()
    wind_theory = st.session_state['cap_res']['Wind_kW'] * st.session_state['df_8760']['wind_norm'].sum()
    pv_actual = dispatch_df['pv_gen_wan'].sum() * 1e4
    wind_actual = dispatch_df['wind_gen_wan'].sum() * 1e4
    operation_text = (
        f"光伏年理论发电量 : {pv_theory / 1e8:>12.4f} 亿kWh | 理论利用小时数 : "
        f"{pv_theory / max(st.session_state['cap_res']['PV_kW'], 1e-9):>8.1f} h\n"
        f"光伏年实际发电量 : {pv_actual / 1e8:>12.4f} 亿kWh | 实际利用小时数 : "
        f"{pv_actual / max(st.session_state['cap_res']['PV_kW'], 1e-9):>8.1f} h\n"
        f"风电年理论发电量 : {wind_theory / 1e8:>12.4f} 亿kWh | 理论利用小时数 : "
        f"{wind_theory / max(st.session_state['cap_res']['Wind_kW'], 1e-9):>8.1f} h\n"
        f"风电年实际发电量 : {wind_actual / 1e8:>12.4f} 亿kWh | 实际利用小时数 : "
        f"{wind_actual / max(st.session_state['cap_res']['Wind_kW'], 1e-9):>8.1f} h\n"
        f"年总弃电量       : {curtail / 1e4:>12.4f} 亿kWh | 综合弃电率     : "
        f"{curtail / max((pv_actual + wind_actual), 1e-9) * 100:>8.2f} %\n"
        f"自发自用电量     : {self_use / 1e4:>12.4f} 亿kWh | 电网补充购电量 : "
        f"{grid_buy / 1e4:>8.4f} 亿kWh\n"
        f"自发自用电量占比 : {self_use / max(total_load, 1e-9) * 100:>12.2f} % | 用户全年总用电量 : "
        f"{total_load / 1e4:>8.4f} 亿kWh"
    )
    _show_protected_text(operation_text)
    st.caption("如需复制运营指标，请联系开发者获取权限。")

    st.subheader("💰 6. 财务指标")
    finance_text = (
        f"总投资（动态）                 : {fin_res['total_project_inv_wan'] / 10000:.4f} 亿元\n"
        f"总投资（静态）                 : {fin_res['total_static_inv_wan'] / 10000:.4f} 亿元\n"
        f"光伏投资                       : {fin_res['inv_pv_wan']:.2f} 万元\n"
        f"风电投资                       : {fin_res['inv_wind_wan']:.2f} 万元\n"
        f"储能投资                       : {fin_res['inv_bess_total_wan']:.2f} 万元\n"
        f"全部投资内部收益率（税前）     : {fin_res['irr_pre_tax'] * 100:.2f} %\n"
        f"全部投资内部收益率（税后）     : {fin_res['irr_post_tax'] * 100:.2f} %\n"
        f"资本金内部收益率               : {fin_res['irr_equity'] * 100:.2f} %"
    )
    _show_protected_text(finance_text)
    st.caption("如需复制财务指标，请联系开发者获取权限。")

    # ---------------- 财务详细数据表 ----------------
    with st.expander("📋 查看详细数据表"):
        st.info("详细数据表仅供查看。如需下载数据，请联系开发者获取权限。")
        tab1, tab2, tab3 = st.tabs(["总成本费用表", "利润与利润分配表", "现金流量表"])
        with tab1:
            st.dataframe(fin_res['df_cost'], use_container_width=True)
        with tab2:
            st.dataframe(fin_res['df_profit'], use_container_width=True)
        with tab3:
            st.dataframe(fin_res['cash_flow_df'], use_container_width=True)
else:
    # 计算前也保留指标区域，并显示与默认容量配置对应的初始值。
    st.subheader("📈 5. 运营指标")
    default_operation_text = (
        "光伏年理论发电量 :       0.0000 亿kWh | 理论利用小时数 :      0.0 h\n"
        "光伏年实际发电量 :       0.0000 亿kWh | 实际利用小时数 :      0.0 h\n"
        "风电年理论发电量 :       0.0000 亿kWh | 理论利用小时数 :      0.0 h\n"
        "风电年实际发电量 :       0.0000 亿kWh | 实际利用小时数 :      0.0 h\n"
        "年总弃电量       :       0.0000 亿kWh | 综合弃电率     :      0.00 %\n"
        "自发自用电量     :       0.0000 亿kWh | 电网补充购电量 :      0.0000 亿kWh\n"
        "自发自用电量占比 :          0.00 % | 用户全年总用电量 :      0.0000 亿kWh"
    )
    _show_protected_text(default_operation_text)
    st.caption("当前显示为默认值。执行手动计算或自动优化后将刷新为实际结果。")
    st.caption("如需复制运营指标，请联系开发者获取权限。")

    st.subheader("💰 6. 财务指标")
    default_finance_text = (
        "总投资（动态）                 : 0.0000 亿元\n"
        "总投资（静态）                 : 0.0000 亿元\n"
        "光伏投资                       : 0.00 万元\n"
        "风电投资                       : 0.00 万元\n"
        "储能投资                       : 0.00 万元\n"
        "全部投资内部收益率（税前）     : 0.00 %\n"
        "全部投资内部收益率（税后）     : 0.00 %\n"
        "资本金内部收益率               : 0.00 %"
    )
    _show_protected_text(default_finance_text)
    st.caption("当前显示为默认值。执行手动计算或自动优化后将刷新为实际结果。")
    st.caption("如需复制财务指标，请联系开发者获取权限。")

# -------------------- 输配电费及年平均到户电价计算 --------------------
st.subheader("⚡ 7. 输配电费及年平均到户电价计算")

from core import PROVINCES, TARIFF_DATA, calc_monthly_tariff_fee

col_prov, col_volt, col_mode, col_cap = st.columns([1.0, 1.15, 1.7, 1.1])

with col_prov:
    default_province_index = PROVINCES.index("甘肃") if "甘肃" in PROVINCES else 0
    province = st.selectbox("省份", PROVINCES, index=default_province_index)

province_data = TARIFF_DATA[province]
voltage_options = list(province_data["voltage_levels"].keys())

with col_volt:
    default_voltage_index = next(
        (idx for idx, value in enumerate(voltage_options) if "110" in value),
        0,
    )
    voltage_level = st.selectbox("电压等级", voltage_options, index=default_voltage_index)

with col_mode:
    mode_label = st.radio(
        "用电分类",
        ["单一制（限小用户，规模以上用户不建议）",
         "两部制", "单一容量制（1192号文新规）"],
        index=2,
    )
    tariff_mode = {
        "单一制（限小用户，规模以上用户不建议）": "single",
        "两部制": "two_part",
        "单一容量制（1192号文新规）": "single_capacity_1192",
    }[mode_label]

with col_cap:
    if 'df_8760' in st.session_state:
        max_load_kw = float(st.session_state['df_8760']['load'].max())
        default_access_capacity = float(
            np.ceil((max_load_kw / 0.9 / 0.8) / 100.0) * 100.0
        )
    else:
        default_access_capacity = 1000.0
    if "access_capacity_input" not in st.session_state:
        st.session_state["access_capacity_input"] = default_access_capacity
    access_capacity = st.number_input(
        "报装容量 (kVA)",
        step=100.0, key="access_capacity_input",
        help="按最大用电负荷 ÷ 0.9（功率因数）÷ 0.8（最大负荷率）计算，向上取整为100 kVA的倍数。",
    )
    st.caption("报装容量 = 最大负荷 ÷ 0.9（功率因数）÷ 0.8（最大负荷率），向上取整至100 kVA")

# 平均负荷率（可编辑）
default_alr = 0.65
avg_load_rate = st.number_input(
    "平均负荷率（110kV及以上工商业两部制用户平均水平，参考各省电网公司公示）",
    value=default_alr, min_value=0.0, max_value=1.0, step=0.01, format="%.2f",
    help="实际值需向当地电网企业获取，此处为估算值"
)

# 下网电量（用于计算线损费用）
if 'dispatch_df' in st.session_state:
    grid_buy_kwh = st.session_state['dispatch_df']['grid_buy_wan'].sum() * 1e4
else:
    grid_buy_kwh = st.number_input("年度下网电量 (kWh)", value=1000000.0, step=10000.0)

# 计算按钮
button_left, button_center, button_right = st.columns([4, 1.8, 4])
with button_center:
    calculate_tariff = st.button(
        "📊 计算输配电费与年平均到户电价",
        use_container_width=True,
    )

if calculate_tariff:
    try:
        result = calc_annual_tariff_fee(
            province=province,
            voltage_level=voltage_level,
            tariff_mode=tariff_mode,
            access_capacity_kva=access_capacity,
            avg_load_rate=avg_load_rate,
            grid_energy_kwh=grid_buy_kwh,
        )
        if 'dispatch_df' in st.session_state:
            dispatch = st.session_state['dispatch_df']
            total_generation = (
                dispatch['pv_gen_wan'].sum() + dispatch['wind_gen_wan'].sum()
            ) * 1e4
            curtail_kwh = dispatch['curtail_wan'].sum() * 1e4
            bess_loss_kwh = (
                dispatch['bess_ch_wan'].sum() - dispatch['bess_dis_wan'].sum()
            ) * 1e4
            self_use_kwh = total_generation - curtail_kwh - bess_loss_kwh
        else:
            self_use_kwh = 0.0
        avg_price = calc_user_avg_price(
            self_use_kwh=self_use_kwh,
            grid_buy_kwh=grid_buy_kwh,
            price_self_use=params['price_self_use'],
            price_buy=params['price_buy'],
            tariff_fee_annual=result['total_annual'],
            system_op_fee_per_kwh=params['system_operation_fee'],
            gov_fund_per_kwh=params['gov_fund'],
        )

        st.success("✅ 计算完成！")
        st.caption("输配电费及年平均到户电价结果仅供查看。如需复制结果，请联系开发者获取权限。")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("输配电电度电费", f"{result['energy_fee']:.2f} 元/年")
        c2.metric("容量电费", f"{result['capacity_fee']:.2f} 元/年")
        c3.metric("1192新增输配电费", f"{result['added_fee']:.2f} 元/年")
        c4.metric("输配电费合计", f"{result['total_annual']:.2f} 元/年")
        st.metric("用户年平均到户电价", f"{avg_price['avg_price']:.4f} 元/kWh")

        with st.expander("📋 计算明细"):
            st.write(f"- 省份：{province}")
            st.write(f"- 电压等级：{voltage_level}")
            st.write(f"- 电价模式：{mode_label}")
            st.write(f"- 报装容量：{access_capacity:.1f} kVA")
            st.write(f"- 平均负荷率：{avg_load_rate:.2f}")
            st.write(f"- 年自发自用电量：{self_use_kwh:.0f} kWh")
            st.write(f"- 年下网电量：{grid_buy_kwh:.0f} kWh")
            st.write(f"- 自发自用电费：{avg_price['self_use_fee']:.2f} 元/年")
            st.write(f"- 外购电费：{avg_price['grid_buy_fee']:.2f} 元/年")
            st.write(f"- 系统运行费：{avg_price['system_fee']:.2f} 元/年")

    except Exception as e:
        st.error(f"❌ 计算失败：{e}")

# ---------------- 逐日源荷匹配图 ----------------
if 'fin_res' in st.session_state:
    st.subheader("📊 8. 逐日源荷匹配")

    # ---- 初始化日期选择状态 ----
    if 'day_selector' not in st.session_state:
        st.session_state['day_selector'] = 1
    if 'day_input' not in st.session_state:
        st.session_state['day_input'] = st.session_state['day_selector']

    def sync_day_input():
        st.session_state['day_input'] = st.session_state['day_selector']

    def confirm_day_input():
        day = min(365, max(1, int(st.session_state['day_input'])))
        st.session_state['day_selector'] = day
        st.session_state['day_input'] = day

    def select_previous_day():
        day = max(1, st.session_state['day_selector'] - 1)
        st.session_state['day_selector'] = day
        st.session_state['day_input'] = day

    def select_next_day():
        day = min(365, st.session_state['day_selector'] + 1)
        st.session_state['day_selector'] = day
        st.session_state['day_input'] = day

    # ---- 一行布局：文字 + 左右箭头 + 日期输入 + 确认按钮 ----
    with st.form("day_navigation_form", clear_on_submit=False):
        c_label, c_prev, c_next, c_day, c_confirm, _ = st.columns(
            [1.2, 0.9, 0.9, 1.1, 0.9, 8]
        )

        with c_label:
            st.markdown("**选择查看的日：**")

        with c_prev:
            st.form_submit_button(
                "◀ 前一天", key="prev_day_btn",
                help="前一天", use_container_width=True,
                on_click=select_previous_day,
            )

        with c_next:
            st.form_submit_button(
                "后一天 ▶", key="next_day_btn",
                help="后一天", use_container_width=True,
                on_click=select_next_day,
            )

        with c_day:
            st.number_input(
                "输入日期",
                min_value=1,
                max_value=365,
                step=1,
                key="day_input",
                label_visibility="collapsed",
            )

        with c_confirm:
            st.form_submit_button(
                "确认日期",
                key="confirm_day_btn",
                on_click=confirm_day_input,
                use_container_width=True,
            )

    # ---- 滑块（隐藏 label，也隐藏 1 / 365 刻度） ----
    st.markdown("""
    <style>
    /* 隐藏滑块两端的 min/max 刻度数字 */
    [data-testid="stSliderTickBarMin"],
    [data-testid="stSliderTickBarMax"] {
        display: none;
    }
    /* 让日期按钮高度与数字输入框一致 */
    [data-testid="stFormSubmitButton"] button {
        height: 38px !important;
        min-height: 38px !important;
        padding: 0 8px !important;
        margin-top: 0 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.slider(
        "", min_value=1, max_value=365, key="day_selector",
        label_visibility="collapsed", on_change=sync_day_input,
    )

    day = st.session_state['day_selector']
    start = (day - 1) * 24
    end = start + 24
    hours = np.arange(1, 25)
    sub = dispatch_df.iloc[start:end]

    fig, ax = plt.subplots(figsize=(12, 5))
    pv_day = sub['pv_gen_wan'].to_numpy()
    wind_day = sub['wind_gen_wan'].to_numpy()
    load_day = sub['load_wan'].to_numpy()
    bess_dis_day = sub['bess_dis_wan'].to_numpy()
    grid_buy_day = sub['grid_buy_wan'].to_numpy()
    bess_ch_day = sub['bess_ch_wan'].to_numpy()
    curtail_day = sub['curtail_wan'].to_numpy()
    ax.bar(hours, pv_day, width=0.7, label='光伏出力', color='#F2994A')
    ax.bar(hours, wind_day, width=0.7, bottom=pv_day,
           label='风电出力', color='#56CCF2')
    renewable_day = pv_day + wind_day
    pv_excess_day = np.maximum(pv_day - load_day, 0.0)
    wind_excess_day = np.maximum(renewable_day - load_day, 0.0) - pv_excess_day
    with plt.rc_context({'hatch.linewidth': 2.4}):
        ax.bar(hours, pv_excess_day, width=0.7,
               bottom=np.minimum(pv_day, load_day),
               color='none', edgecolor='white', hatch='///',
               label='_nolegend_', zorder=3)
        ax.bar(hours, wind_excess_day, width=0.7,
               bottom=np.maximum(pv_day, load_day),
               color='none', edgecolor='white', hatch='///',
               label='_nolegend_', zorder=3)
    ax.bar(hours, bess_dis_day, width=0.7,
           bottom=renewable_day,
           label='储能放电', color='#27AE60')
    ax.bar(hours, grid_buy_day, width=0.7,
           bottom=renewable_day + bess_dis_day,
           label='外购电', color='#EB5757')
    ax.plot(hours, load_day, color='#1F497D', marker='o',
            linewidth=2, markersize=4, label='用电负荷')

    ax.bar(hours, bess_ch_day, width=0.35, label='储能充电', color='#9B51E0', alpha=0.85)
    ax.bar(hours, curtail_day, width=0.35, bottom=bess_ch_day,
           label='弃电量', color='#95A5A6', alpha=0.65)

    ax.set_xlim(0.5, 24.5)
    plot_max = max(
        np.max(renewable_day + bess_dis_day + grid_buy_day),
        np.max(bess_ch_day + curtail_day),
        np.max(load_day),
        0.1,
    )
    ax.set_ylim(0, plot_max * 1.28)
    ax.set_xticks(hours)
    ax.set_xlabel("小时")
    ax.set_ylabel("功率 (万kW)")
    ax.set_title(f"第 {day} 天源荷匹配情况")
    ax.grid(axis='y', linestyle='--', alpha=0.4)
    ax.legend(loc='upper right', ncol=4, fontsize=9)

    plt.tight_layout()
    _show_protected_figure(fig)
    plt.close(fig)
    st.caption("逐日源荷匹配图仅供查看。如需下载图片，请联系开发者获取权限。")
