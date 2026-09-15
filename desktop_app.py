import os
import sys
import pulp
import time
import threading
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import openpyxl
import threading
import tkinter as tk
import sys, os
import math
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core import (
    get_default_params, get_parameter_schema,
    load_8760_from_path, simulate_8760, simulate_detailed_8760,
    run_financial_evaluation, calc_irr,
    optimize_capacity_pulp, optimize_capacity_debug,
    make_resource_analysis_figure,
    export_financial_tables_to_bytes, export_full_report_to_bytes,
    PROVINCES, TARIFF_DATA, calc_monthly_tariff_fee,   # ★ 新增这一行
    calc_annual_tariff_fee, calc_user_avg_price,
)
import ctypes
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from tkinter import ttk, filedialog, messagebox
from matplotlib.widgets import Button
from pathlib import Path

def enable_dpi_awareness():
    """
    在创建任何 Tk 窗口之前调用，启用高 DPI 感知。
    避免 Windows 把窗口粗暴缩放，导致字体和控件错位。
    """
    try:
        # Windows 8.1+ 的 Per-Monitor DPI 感知
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            # Windows Vista+ 的系统 DPI 感知（降级方案）
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def fit_window_to_screen(window, requested_width=None, requested_height=None,
                         margin=24):
    """将 Tk 窗口限制在当前屏幕工作区内并居中。"""
    window.update_idletasks()

    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    available_width = max(320, screen_width - margin * 2)
    available_height = max(240, screen_height - margin * 2)

    width = requested_width or window.winfo_reqwidth()
    height = requested_height or window.winfo_reqheight()
    width = min(max(320, int(width)), available_width)
    height = min(max(240, int(height)), available_height)
    x = max(margin, (screen_width - width) // 2)
    y = max(margin, (screen_height - height) // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")

def resource_path(relative):
    """兼容 PyInstaller 打包后的路径"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative)


def find_font_file():
    """查找项目内的字体文件，兼容源码运行和 PyInstaller 打包路径。"""
    candidates = (
        resource_path("fonts/SourceHanSansCN-Regular.otf"),
        resource_path("SourceHanSansCN-Regular.otf"),
    )
    return next((path for path in candidates if os.path.isfile(path)), candidates[0])

def register_font_for_tkinter(font_path):
    """把字体注册到当前进程，Tkinter 就能识别"""
    if sys.platform != 'win32':
        return
    FR_PRIVATE = 0x10
    path = str(Path(font_path).resolve())
    ctypes.windll.gdi32.AddFontResourceExW(path, FR_PRIVATE, 0)

def register_font_for_matplotlib(font_path):
    """注册给 matplotlib"""
    import matplotlib.font_manager as fm
    fm.fontManager.addfont(font_path)
    return fm.FontProperties(fname=font_path).get_name()

# 设置 Matplotlib 中文显示
plt.rcParams['font.sans-serif'] = ['SimHei', 'Source Han Sans CN', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


# =============================================================
# 1. 内部收益率 (IRR) 与财务现金流计算模块
# =============================================================






# =============================================================
# 2. 交互式参数配置模块 (GUI 窗口版)
# =============================================================
def get_user_parameters():
    schema = get_parameter_schema()

    root = tk.Tk()
    root.title("边界条件（预设值）")

    try:
        dpi_scale = root.winfo_fpixels('1i') / 96.0
    except Exception:
        dpi_scale = 1.0
    root.tk.call('tk', 'scaling', 1.333 * dpi_scale)

    base_w, base_h = 860, 820
    fit_window_to_screen(root, int(base_w * dpi_scale), int(base_h * dpi_scale))
    root.resizable(True, True)

    final_params = {}
    entries = {}

    main_frame = ttk.Frame(root, padding="10")
    main_frame.pack(fill=tk.BOTH, expand=True)

    groups = {}
    for group_name, label_text, key, default_val, val_type in schema:
        if group_name not in groups:
            lf = ttk.LabelFrame(main_frame, text=f" {group_name} ", padding="10")
            lf.pack(fill=tk.X, pady=4, padx=5)
            groups[group_name] = {"frame": lf, "row": 0, "col": 0}

        group_info = groups[group_name]
        lf = group_info["frame"]
        row = group_info["row"]
        col = group_info["col"]

        lbl = ttk.Label(lf, text=label_text, width=32, anchor="e")
        lbl.grid(row=row, column=col*2, padx=5, pady=3, sticky="e")

        entry = ttk.Entry(lf, width=15)
        entry.insert(0, str(default_val))
        entry.grid(row=row, column=col*2+1, padx=5, pady=3, sticky="w")
        
        entries[key] = (entry, default_val, val_type, label_text)

        if col == 1:
            group_info["col"] = 0
            group_info["row"] += 1
        else:
            group_info["col"] = 1

    def reset_defaults():
        for key, (entry, default_val, _, _) in entries.items():
            entry.delete(0, tk.END)
            entry.insert(0, str(default_val))

    def on_confirm():
        nonlocal final_params
        temp_params = {}
        for key, (entry, default_val, val_type, label_text) in entries.items():
            raw_val = entry.get().strip()
            if not raw_val:
                val = default_val
            else:
                try:
                    val = val_type(raw_val)
                except ValueError:
                    messagebox.showerror("输入错误", f"字段 [{label_text}] 输入格式非法！\n已恢复为默认值: {default_val}")
                    return
            temp_params[key] = val

        final_params = temp_params
        root.destroy()

    def on_close():
        nonlocal final_params
        final_params = {key: val_type(default_val) for key, (_, default_val, val_type, _) in entries.items()}
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)

    btn_frame = ttk.Frame(main_frame, padding="10")
    btn_frame.pack(fill=tk.X, pady=5)

    btn_reset = ttk.Button(btn_frame, text="重置为默认值", command=reset_defaults)
    btn_reset.pack(side=tk.LEFT, padx=20)

    btn_confirm = ttk.Button(btn_frame, text="确认并继续运行", command=on_confirm)
    btn_confirm.pack(side=tk.RIGHT, padx=20)

    # === 自动适配窗口大小 ===
    fit_window_to_screen(root)                  # 内容较大时自动限制在屏幕内
    # ========================

    root.mainloop()
    return final_params


# =============================================================
# 3. 预分析图表绘制模块
# =============================================================
def plot_pre_optimization_analysis(df_8760):
    print("\n>>> 正在生成风电、光伏资源与负荷特性预分析图表...")
    
    months = list(range(1, 13))
    pv_monthly_gen, wind_monthly_gen, load_monthly_energy = [], [], []
    
    # 建立独立数据副本防止影响外部变量
    df_analysis = df_8760.copy()
    df_analysis['month'] = pd.date_range("2026-01-01", periods=8760, freq="h").month
    df_analysis['hour_of_day'] = df_analysis.index % 24

    for m in months:
        df_m = df_analysis[df_analysis['month'] == m]
        pv_monthly_gen.append((df_m['pv_norm'] * 10000.0).sum() / 1e8)
        wind_monthly_gen.append((df_m['wind_norm'] * 10000.0).sum() / 1e8)
        load_monthly_energy.append(df_m['load'].sum() / 1e8)

    pv_sorted = np.sort(df_analysis['pv_norm'].values)[::-1]
    wind_sorted = np.sort(df_analysis['wind_norm'].values)[::-1]
    guarantee_rate = np.linspace(0, 100, 8760)

    hourly_pv = df_analysis.groupby('hour_of_day')['pv_norm'].mean()
    hourly_wind = df_analysis.groupby('hour_of_day')['wind_norm'].mean()
    hourly_load = df_analysis.groupby('hour_of_day')['load'].mean()

    # 创建统一的 3 行 3 列画板，第三行用于展示负荷特性。
    fig, axes = plt.subplots(3, 3, figsize=(16, 12))
    fig.canvas.manager.set_window_title("新能源资源与负荷特性预分析")

    fig.canvas.manager.set_window_title("新能源资源与负荷特性预分析")

    # ------------------ Row 1: 光伏资源特性 ------------------
    # 1. 光伏月度发电量
    axes[0, 0].bar(months, pv_monthly_gen, width=0.6, color='#F2994A', label='光伏(基准1万kW)')
    axes[0, 0].set_title("光伏月度理论发电量 (亿kWh)", fontsize=11, fontweight='bold')
    axes[0, 0].set_xlabel("月份")
    axes[0, 0].set_ylabel("发电量 (亿kWh)")
    axes[0, 0].set_xticks(months)
    axes[0, 0].grid(True, linestyle='--', alpha=0.5)
    axes[0, 0].legend()

    # 2. 光伏日内平均出力
    axes[0, 1].plot(hourly_pv.index, hourly_pv.values, color='#F2994A', linewidth=2, label='光伏平均出力系数')
    axes[0, 1].set_title("光伏日内 24 小时平均出力特性", fontsize=11, fontweight='bold')
    axes[0, 1].set_xlabel("日内时刻 (Hour)")
    axes[0, 1].set_ylabel("归一化出力系数")
    axes[0, 1].set_xticks(range(0, 24, 3))
    axes[0, 1].grid(True, linestyle='--', alpha=0.5)
    axes[0, 1].legend()

    # 3. 光伏保证率曲线
    axes[0, 2].plot(guarantee_rate, pv_sorted, color='#F2994A', linewidth=2, label='光伏出力持续曲线')
    axes[0, 2].set_title("光伏电力保证率曲线", fontsize=11, fontweight='bold')
    axes[0, 2].set_xlabel("电力保证率 (%)")
    axes[0, 2].set_ylabel("归一化出力系数")
    axes[0, 2].grid(True, linestyle='--', alpha=0.5)
    axes[0, 2].legend()

    # ------------------ Row 2: 风电资源特性 ------------------
    # 4. 风电月度发电量
    axes[1, 0].bar(months, wind_monthly_gen, width=0.6, color='#2F80ED', label='风电(基准1万kW)')
    axes[1, 0].set_title("风电月度理论发电量 (亿kWh)", fontsize=11, fontweight='bold')
    axes[1, 0].set_xlabel("月份")
    axes[1, 0].set_ylabel("发电量 (亿kWh)")
    axes[1, 0].set_xticks(months)
    axes[1, 0].grid(True, linestyle='--', alpha=0.5)
    axes[1, 0].legend()

    # 5. 风电日内平均出力
    axes[1, 1].plot(hourly_wind.index, hourly_wind.values, color='#2F80ED', linewidth=2, label='风电平均出力系数')
    axes[1, 1].set_title("风电日内 24 小时平均出力特性", fontsize=11, fontweight='bold')
    axes[1, 1].set_xlabel("日内时刻 (Hour)")
    axes[1, 1].set_ylabel("归一化出力系数")
    axes[1, 1].set_xticks(range(0, 24, 3))
    axes[1, 1].grid(True, linestyle='--', alpha=0.5)
    axes[1, 1].legend()

    # 6. 风电保证率曲线
    axes[1, 2].plot(guarantee_rate, wind_sorted, color='#2F80ED', linewidth=2, label='风电出力持续曲线')
    axes[1, 2].set_title("风电电力保证率曲线", fontsize=11, fontweight='bold')
    axes[1, 2].set_xlabel("电力保证率 (%)")
    axes[1, 2].set_ylabel("归一化出力系数")
    axes[1, 2].grid(True, linestyle='--', alpha=0.5)
    axes[1, 2].legend()

    # ------------------ Row 3: 负荷特性 ------------------
    # 7. 负荷逐月用电量
    axes[2, 0].bar(months, load_monthly_energy, width=0.6,
                   color='#27AE60', label='负荷')
    axes[2, 0].set_title("负荷逐月用电量", fontsize=11, fontweight='bold')
    axes[2, 0].set_xlabel("月份")
    axes[2, 0].set_ylabel("用电量 (亿kWh)")
    axes[2, 0].set_xticks(months)
    axes[2, 0].grid(True, linestyle='--', alpha=0.5)
    axes[2, 0].legend()

    # 8. 负荷日内 24 小时平均出力
    axes[2, 1].plot(hourly_load.index, hourly_load.values,
                    color='#27AE60', linewidth=2, marker='o',
                    label='负荷平均出力')
    axes[2, 1].set_title("负荷日内 24 小时平均出力特性",
                         fontsize=11, fontweight='bold')
    axes[2, 1].set_xlabel("日内时刻 (Hour)")
    axes[2, 1].set_ylabel("平均出力 (kW)")
    axes[2, 1].set_xticks(range(0, 24, 3))
    axes[2, 1].grid(True, linestyle='--', alpha=0.5)
    axes[2, 1].legend()

    # 第三个单元暂不放置图表，保持 3×3 网格布局整齐。
    axes[2, 2].axis('off')

    # ------------------ 底部按钮与提示文本配置 ------------------
    plt.tight_layout(rect=[0, 0.14, 1, 1], pad=2.0)

    # 提示红字（往上移了一点，原来 0.075 → 现在 0.10）
    fig.text(0.5, 0.10, "请认真核实电源出力特性，然后选择下一步操作：",
             ha='center', va='center', fontsize=12, fontweight='bold', color='#D32F2F')

    # 状态容器
    status = {'choice': 'exit'}

    def on_manual(event):
        status['choice'] = 'manual'
        plt.close(fig)

    def on_auto(event):
        status['choice'] = 'auto'
        plt.close(fig)

    def on_exit(event):
        status['choice'] = 'exit'
        plt.close(fig)

    # 三个按钮的坐标轴位置（y 从 0.02 提到 0.03，避免贴着窗口边缘）
    ax_manual = fig.add_axes([0.20, 0.03, 0.14, 0.045])
    ax_auto   = fig.add_axes([0.42, 0.03, 0.14, 0.045])
    ax_exit   = fig.add_axes([0.64, 0.03, 0.14, 0.045])

    btn_manual = Button(ax_manual, '手动调整项目配置', color='#FFF3E0', hovercolor='#FFE0B2')
    btn_auto   = Button(ax_auto,   '自动优化项目配置', color='#E8F5E9', hovercolor='#C8E6C9')
    btn_exit   = Button(ax_exit,   '退    出', color='#FFEBEE', hovercolor='#FFCDD2')

    btn_manual.on_clicked(on_manual)
    btn_auto.on_clicked(on_auto)
    btn_exit.on_clicked(on_exit)

    # 防止按钮被垃圾回收
    fig._btn_manual = btn_manual
    fig._btn_auto   = btn_auto
    fig._btn_exit   = btn_exit

    # 将图表窗口限制在屏幕工作区内，避免最大化或全屏遮挡任务栏。
    try:
        figure_window = fig.canvas.manager.window
        figure_window.update_idletasks()
        screen_width = figure_window.winfo_screenwidth()
        screen_height = figure_window.winfo_screenheight()
        margin = 24
        figure_width = min(int(16 * 100), screen_width - margin * 2)
        figure_height = min(int(12 * 100), screen_height - margin * 2)
        figure_x = max(margin, (screen_width - figure_width) // 2)
        figure_y = max(margin, (screen_height - figure_height) // 2)
        figure_window.geometry(
            f"{figure_width}x{figure_height}+{figure_x}+{figure_y}"
        )
    except Exception:
        pass

    plt.show()

    return status['choice']



# =============================================================
# 通用：带进度对话框的后台任务执行器
# =============================================================
def run_with_progress_dialog(task_func, task_desc="正在计算，请稍候...",
                             hint="（过程可能需要 1~3 分钟，请勿关闭窗口）"):
    """
    在后台线程执行 task_func，主线程显示进度对话框 + 实时日志。
    求解过程中的所有 print 输出都会显示在窗口里。
    """
    import io
    container = {'result': None, 'error': None, 'done': False}

    dlg = tk.Tk()
    dlg.title("请稍候")
    dlg.resizable(False, False)
    dlg.attributes('-topmost', True)

    w, h = 640, 420
    dlg.update_idletasks()
    sw, sh = dlg.winfo_screenwidth(), dlg.winfo_screenheight()
    dlg.geometry(f"{w}x{h}+{(sw - w)//2}+{(sh - h)//2}")

    tk.Label(dlg, text="⏳ 正在运行", font=("Microsoft YaHei UI", 13, "bold"),
             fg="#1F497D").pack(pady=(12, 4))
    tk.Label(dlg, text=task_desc, font=("Microsoft YaHei UI", 10),
             wraplength=600, justify="center").pack(pady=(2, 6))

    progress = ttk.Progressbar(dlg, mode='indeterminate', length=580)
    progress.pack(pady=4)
    progress.start(15)

    # ---------- 实时日志区 ----------
    log_frame = ttk.LabelFrame(dlg, text=" 运行日志 ", padding=4)
    log_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)

    log_text = tk.Text(log_frame, height=12, font=("Consolas", 9),
                       wrap="word", bg="#F8F8F8", relief="flat")
    scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=log_text.yview)
    log_text.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    elapsed_var = tk.StringVar(value="已用时: 0 秒")
    tk.Label(dlg, textvariable=elapsed_var, font=("Microsoft YaHei UI", 9),
             fg="#666666").pack(pady=(0, 8))

    dlg.protocol("WM_DELETE_WINDOW", lambda: None)
    dlg.update()

    # ---------- 重定向 stdout，把 print 的内容写进 log_text ----------
    class _Redirector:
        def __init__(self, widget):
            self.widget = widget
        def write(self, s):
            if not self.widget.winfo_exists():
                return
            self.widget.configure(state='normal')
            self.widget.insert('end', s)
            self.widget.see('end')
            self.widget.configure(state='disabled')
        def flush(self):
            pass

    original_stdout = sys.stdout
    sys.stdout = _Redirector(log_text)
    sys.stderr = sys.stdout

    def worker():
        try:
            container['result'] = task_func()
        except Exception as e:
            container['error'] = e
        finally:
            container['done'] = True

    threading.Thread(target=worker, daemon=True).start()

    start_time = time.time()

    def poll():
        if container['done']:
            progress.stop()
            # ★ 恢复 stdout，非常重要
            sys.stdout = original_stdout
            sys.stderr = original_stdout
            dlg.destroy()
            return
        elapsed_var.set(f"已用时: {int(time.time() - start_time)} 秒")
        dlg.after(200, poll)

    dlg.after(200, poll)
    dlg.mainloop()

    if container['error'] is not None:
        raise container['error']
    return container['result']



def show_daily_dispatch_window(dispatch_df):
    """
    交互式窗口：逐日查看源荷匹配情况。
    - 顶部：天数、日期、上/下箭头按钮、跳转输入框
    - 主体：当日 24 小时堆叠柱状图（光伏 + 风电 + 储能放电 + 外购电 = 满足负荷）
    """
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    import datetime

    root = tk.Toplevel()
    root.title("逐日源荷匹配查看")

    try:
        dpi_scale = root.winfo_fpixels('1i') / 96.0
    except Exception:
        dpi_scale = 1.0

    base_w, base_h = 1200, 720
    root.geometry(f"{int(base_w * dpi_scale)}x{int(base_h * dpi_scale)}")

    N_DAYS = 365

    # ==================== 顶部导航栏 ====================
    nav = tk.Frame(root, bg="#5B9BD5", height=int(55 * dpi_scale))
    nav.pack(fill=tk.X)
    nav.pack_propagate(False)

    # 天数标签（黄色方块）
    day_label = tk.Label(
        nav, text="第 1 天", bg="#FFD966", fg="#000000",
        font=("Microsoft YaHei UI", 13, "bold"),
        padx=18, pady=6, relief=tk.RAISED, borderwidth=2,
    )
    day_label.pack(side=tk.LEFT, padx=(10, 3), pady=8)

    # 日期标签（黄色方块）
    date_label = tk.Label(
        nav, text="1月1日", bg="#FFD966", fg="#000000",
        font=("Microsoft YaHei UI", 13, "bold"),
        padx=18, pady=6, relief=tk.RAISED, borderwidth=2,
    )
    date_label.pack(side=tk.LEFT, padx=3, pady=8)

    # ==================== 主绘图区 ====================
    fig = Figure(figsize=(12, 6), dpi=100)
    ax = fig.add_subplot(111)

    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

    # ==================== 状态与辅助 ====================
    current_day = [1]   # 用列表便于闭包内修改

    def get_date_str(day):
        d = datetime.date(2026, 1, 1) + datetime.timedelta(days=day - 1)
        return f"{d.month}月{d.day}日"

    def render(day):
        start = (day - 1) * 24
        end = start + 24
        hours = np.arange(1, 25)

        pv       = dispatch_df['pv_gen_wan'].iloc[start:end].values
        wind     = dispatch_df['wind_gen_wan'].iloc[start:end].values
        bess_dis = dispatch_df['bess_dis_wan'].iloc[start:end].values
        bess_ch  = dispatch_df['bess_ch_wan'].iloc[start:end].values
        grid_buy = dispatch_df['grid_buy_wan'].iloc[start:end].values
        curtail  = dispatch_df['curtail_wan'].iloc[start:end].values
        load     = dispatch_df['load_wan'].iloc[start:end].values

        ax.clear()

        # ---- 堆叠柱：光伏 + 风电 + 储能放电 + 外购电 ----
        ax.bar(hours, pv, width=0.7, label='光伏出力',
               color='#F2994A', edgecolor='white', linewidth=0.3)
        ax.bar(hours, wind, width=0.7, bottom=pv, label='风电出力',
               color='#56CCF2', edgecolor='white', linewidth=0.3)

        # ---- 光伏、风电超过用电负荷的部分：单斜线纹理 ----
        renewable_total = pv + wind
        pv_excess = np.maximum(pv - load, 0.0)
        wind_excess = np.maximum(renewable_total - load, 0.0) - pv_excess
        with plt.rc_context({'hatch.linewidth': 2.4}):
            ax.bar(hours, pv_excess, width=0.7,
                   bottom=np.minimum(pv, load),
                   color='none', edgecolor='white', linewidth=0.3,
                   hatch='///', label='_nolegend_', zorder=3)
            ax.bar(hours, wind_excess, width=0.7,
                   bottom=np.maximum(pv, load),
                   color='none', edgecolor='white', linewidth=0.3,
                   hatch='///', label='_nolegend_', zorder=3)

        ax.bar(hours, bess_dis, width=0.7, bottom=pv + wind,
               label='储能放电', color='#27AE60', edgecolor='white', linewidth=0.3)
        ax.bar(hours, grid_buy, width=0.7, bottom=pv + wind + bess_dis,
               label='外购电', color='#EB5757', edgecolor='white', linewidth=0.3)

        # ---- 负荷曲线 ----
        ax.plot(hours, load, color='#1F497D', marker='o',
                linewidth=2, markersize=4, label='用电负荷')

        # ---- 储能充电 + 弃电量（窄柱，堆叠在堆叠柱右侧） ----
        # 底部为储能充电（紫色），上部为弃电量（灰色）
        if (curtail.max() > 0.001) or (bess_ch.max() > 0.001):
            ax.bar(hours, bess_ch, width=0.35,
                   label='储能充电', color='#9B51E0', alpha=0.85,
                   edgecolor='white', linewidth=0.3)
            ax.bar(hours, curtail, width=0.35, bottom=bess_ch,
                   label='弃电量', color='#95A5A6', alpha=0.65,
                   edgecolor='gray', linewidth=0.5)

        ax.set_xlim(0.5, 24.5)
        plot_max = max(
            np.max(pv + wind + bess_dis + grid_buy),
            np.max(bess_ch + curtail),
            np.max(load),
            0.1,
        )
        # 图例位于绘图区上方，预留足够高度避免最高柱体与图例重叠。
        ax.set_ylim(0, plot_max * 1.28)
        ax.set_xticks(hours)
        ax.set_xlabel("小时", fontsize=11)
        ax.set_ylabel("功率 (万kW)", fontsize=11)
        ax.set_title(f"第 {day} 天 ({get_date_str(day)}) 源荷匹配情况",
                     fontsize=12, fontweight='bold')
        ax.grid(True, linestyle='--', alpha=0.4, axis='y')
        ax.legend(loc='upper right', ncol=4, fontsize=9, framealpha=0.9)

        fig.tight_layout()
        canvas.draw()

        # ---- 更新导航栏文字 ----
        day_label.config(text=f"第 {day} 天")
        date_label.config(text=get_date_str(day))
        day_entry.delete(0, tk.END)
        day_entry.insert(0, str(day))

    def change_day(delta):
        new_day = max(1, min(N_DAYS, current_day[0] + delta))
        current_day[0] = new_day
        render(new_day)

    def jump_to_day():
        try:
            d = int(day_entry.get().strip())
            d = max(1, min(N_DAYS, d))
            current_day[0] = d
            render(d)
        except ValueError:
            pass

    # ==================== 导航按钮 ====================
    btn_up = tk.Button(nav, text="▲", font=("Arial", 12, "bold"),
                       width=3, bg="#FFFFFF", activebackground="#E0E0E0",
                       command=lambda: change_day(+1))
    btn_up.pack(side=tk.LEFT, padx=2, pady=8)

    btn_down = tk.Button(nav, text="▼", font=("Arial", 12, "bold"),
                         width=3, bg="#FFFFFF", activebackground="#E0E0E0",
                         command=lambda: change_day(-1))
    btn_down.pack(side=tk.LEFT, padx=2, pady=8)

    # 跳转输入框
    tk.Label(nav, text="跳转到第", bg="#5B9BD5", fg="white",
             font=("Microsoft YaHei UI", 11)).pack(side=tk.LEFT, padx=(30, 5))
    day_entry = tk.Entry(nav, width=6, font=("Arial", 11))
    day_entry.insert(0, "1")
    day_entry.pack(side=tk.LEFT)
    tk.Label(nav, text="天", bg="#5B9BD5", fg="white",
             font=("Microsoft YaHei UI", 11)).pack(side=tk.LEFT, padx=5)
    tk.Button(nav, text="确定", command=jump_to_day).pack(side=tk.LEFT, padx=5)

    # 键盘快捷键：↑/→ 下一天，↓/← 上一天
    root.bind('<Up>',    lambda e: change_day(+1))
    root.bind('<Right>', lambda e: change_day(+1))
    root.bind('<Down>',  lambda e: change_day(-1))
    root.bind('<Left>',  lambda e: change_day(-1))
    day_entry.bind('<Return>', lambda e: jump_to_day())

    # 初始渲染
    render(1)
    root.mainloop()

# =============================================================
# 6. 合并后的参数调整与财务分析综合 GUI 模块
# =============================================================
def open_parameter_adjustment_window(cap_res, df_8760, params, export_excel_path=None):
    # ============================================================
    # 第一步：提前定义所有 UI 变量（必须放在函数最开头）
    # 这样任何内部函数都能通过闭包访问到它们
    # ============================================================


    pv_wan = cap_res.get("PV_kW", 0.0) / 10000.0
    wind_wan = cap_res.get("Wind_kW", 0.0) / 10000.0
    bess_p_wan = cap_res.get("BESS_kW", 0.0) / 10000.0
    p_kw = cap_res.get("BESS_kW", 0.0)
    e_kwh = cap_res.get("BESS_kWh", 0.0)
    bess_h = (e_kwh / p_kw) if p_kw > 0 else 2.0

    root = tk.Tk()
    root.title("绿电直连容量优化与财务分析")

    # ============================================================
    # 在这里定义所有 UI 变量（必须有 root 之后才能创建 StringVar）
    # 位置放在所有内部函数之前，保证闭包能访问到
    # ============================================================
    var_pv_theo = tk.StringVar()
    var_pv_act = tk.StringVar()
    var_wind_theo = tk.StringVar()
    var_wind_act = tk.StringVar()
    var_curtail = tk.StringVar()
    var_self_use = tk.StringVar()
    var_self_use_ratio = tk.StringVar()
    var_tot_dyn = tk.StringVar()
    var_tot_static = tk.StringVar()
    var_inv_pv = tk.StringVar()
    var_inv_wind = tk.StringVar()
    var_inv_bess = tk.StringVar()
    var_irr_pre = tk.StringVar()
    var_irr_post = tk.StringVar()
    var_irr_equity = tk.StringVar()

    try:
        dpi_scale = root.winfo_fpixels('1i') / 96.0
    except Exception:
        dpi_scale = 1.0

    root.tk.call('tk', 'scaling', 1.333 * dpi_scale)
    base_w, base_h = 800, 820
    win_w = int(base_w * dpi_scale)
    win_h = int(base_h * dpi_scale)
    fit_window_to_screen(root, win_w, win_h)
    root.resizable(True, True)

    # ============================================================
    # 创建标签页容器（Notebook）
    # ============================================================
    results_panel = ttk.Frame(root)
    results_panel.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=(0, 5))

    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    # 标签页 1：边界条件参数
    tab_parameters = ttk.Frame(notebook)
    notebook.add(tab_parameters, text="  边界条件参数  ")

    # 标签页 2：容量/电价与收益率调整
    tab_capacity = ttk.Frame(notebook)
    notebook.add(tab_capacity, text="  容量/电价与收益率  ")

    # 标签页 3：输配电费与年平均电价
    tab_tariff = ttk.Frame(notebook)
    notebook.add(tab_tariff, text="  输配电费与年平均电价  ")

    # 标签页 4：查看结果
    tab_extra = ttk.Frame(notebook)
    notebook.add(tab_extra, text="  查看结果  ")
    # ============================================================

    def update_entry(entry, value_str):
        entry.delete(0, tk.END)
        entry.insert(0, value_str)

    # ==================== 边界条件参数 ====================
    # 与“参数配置”窗口共用同一 schema，避免两个阶段的参数定义不一致。
    parameter_entries = {}
    parameter_buttons = ttk.Frame(tab_parameters, padding=8)
    parameter_buttons.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=4)

    parameter_canvas = tk.Canvas(tab_parameters, highlightthickness=0)
    parameter_scroll = ttk.Scrollbar(
        tab_parameters, orient="vertical", command=parameter_canvas.yview
    )
    parameter_content = ttk.Frame(parameter_canvas)
    parameter_content.bind(
        "<Configure>",
        lambda event: parameter_canvas.configure(
            scrollregion=parameter_canvas.bbox("all")
        ),
    )
    parameter_canvas.create_window((0, 0), window=parameter_content, anchor="nw")
    parameter_canvas.configure(yscrollcommand=parameter_scroll.set)
    parameter_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    parameter_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    parameter_groups = {}
    for group_name, label_text, key, default_val, val_type in get_parameter_schema():
        if group_name not in parameter_groups:
            frame = ttk.LabelFrame(parameter_content, text=f" {group_name} ", padding=8)
            frame.pack(fill=tk.X, padx=10, pady=4)
            parameter_groups[group_name] = {"frame": frame, "row": 0, "col": 0}

        group_info = parameter_groups[group_name]
        row, col = group_info["row"], group_info["col"]
        frame = group_info["frame"]
        ttk.Label(frame, text=label_text, width=34, anchor="e").grid(
            row=row, column=col * 2, padx=5, pady=3, sticky="e"
        )
        entry = ttk.Entry(frame, width=15)
        entry.insert(0, str(params.get(key, default_val)))
        entry.grid(row=row, column=col * 2 + 1, padx=5, pady=3, sticky="w")
        parameter_entries[key] = (entry, default_val, val_type, label_text)

        if col == 1:
            group_info["col"] = 0
            group_info["row"] += 1
        else:
            group_info["col"] = 1

    def reset_parameter_boundaries():
        for key, (entry, default_val, _, _) in parameter_entries.items():
            entry.delete(0, tk.END)
            entry.insert(0, str(default_val))

    def apply_parameter_boundaries(show_error=True, sync_price_entry=True):
        """读取边界条件标签页并写回 params，供后续仿真和财务计算使用。"""
        updated_params = {}
        for key, (entry, default_val, val_type, label_text) in parameter_entries.items():
            raw_value = entry.get().strip()
            try:
                updated_params[key] = val_type(
                    raw_value if raw_value else default_val
                )
            except (TypeError, ValueError):
                if show_error:
                    messagebox.showerror(
                        "输入错误",
                        f"字段 [{label_text}] 输入格式非法！\n"
                        f"请输入 {val_type.__name__} 类型的数值。",
                    )
                return False

        params.update(updated_params)
        if sync_price_entry:
            update_entry(entry_price, f"{params['price_self_use']:.4f}")
        return True

    ttk.Button(
        parameter_buttons, text="重置为默认值",
        command=reset_parameter_boundaries
    ).pack(side=tk.LEFT, padx=10)
    ttk.Button(
        parameter_buttons, text="应用边界条件",
        command=lambda: apply_and_recalculate()
    ).pack(side=tk.RIGHT, padx=10)

    # ==================== 区域 1：容量/电价调整 ====================
    frame_cap_price = ttk.LabelFrame(tab_capacity, text=" 容量/电价调整 ", padding=15)
    frame_cap_price.pack(fill=tk.X, padx=15, pady=8)

    ttk.Label(frame_cap_price, text="光伏装机容量 (万kW):").grid(row=0, column=0, padx=8, pady=6, sticky="e")
    entry_pv = ttk.Entry(frame_cap_price, width=14)
    entry_pv.insert(0, f"{float(pv_wan):.4f}")
    entry_pv.grid(row=0, column=1, padx=8, pady=6)

    ttk.Label(frame_cap_price, text="风电装机容量 (万kW):").grid(row=0, column=2, padx=8, pady=6, sticky="e")
    entry_wind = ttk.Entry(frame_cap_price, width=14)
    entry_wind.insert(0, f"{float(wind_wan):.4f}")
    entry_wind.grid(row=0, column=3, padx=8, pady=6)

    ttk.Label(frame_cap_price, text="储能 PCS 功率 (万kW):").grid(row=1, column=0, padx=8, pady=6, sticky="e")
    entry_bess_p = ttk.Entry(frame_cap_price, width=14)
    entry_bess_p.insert(0, f"{float(bess_p_wan):.4f}")
    entry_bess_p.grid(row=1, column=1, padx=8, pady=6)

    ttk.Label(frame_cap_price, text="储能时长 (小时):").grid(row=1, column=2, padx=8, pady=6, sticky="e")
    entry_bess_h = ttk.Entry(frame_cap_price, width=14)
    entry_bess_h.insert(0, f"{float(bess_h):.2f}")
    entry_bess_h.grid(row=1, column=3, padx=8, pady=6)

    ttk.Label(frame_cap_price, text="自发自用电价 (元/kWh):").grid(row=2, column=0, padx=8, pady=6, sticky="e")
    entry_price = ttk.Entry(frame_cap_price, width=14)
    entry_price.insert(0, f"{params.get('price_self_use', 0.30):.4f}")
    entry_price.grid(row=2, column=1, padx=8, pady=6)
    boundary_price_entry = parameter_entries.get("price_self_use", (None,))[0]
    if boundary_price_entry is not None:
        entry_price.bind(
            "<KeyRelease>",
            lambda event: update_entry(boundary_price_entry, entry_price.get()),
        )
        boundary_price_entry.bind(
            "<KeyRelease>",
            lambda event: update_entry(entry_price, boundary_price_entry.get()),
        )

    # ==================== 区域 2：收益率调整 ====================
    frame_irr = ttk.LabelFrame(tab_capacity, text=" 收益率调整 ", padding=15)
    frame_irr.pack(fill=tk.X, padx=15, pady=8)

    ttk.Label(frame_irr, text="资本金 IRR (%):").grid(row=0, column=0, padx=8, pady=6, sticky="e")
    entry_equity_irr = ttk.Entry(frame_irr, width=14)
    entry_equity_irr.insert(0, "8.00")
    entry_equity_irr.grid(row=0, column=1, padx=8, pady=6, sticky="w")

    btn_irr_to_price = ttk.Button(frame_irr, text=" 收益率→电价 ", command=lambda: calc_price_from_irr())
    btn_irr_to_price.grid(row=0, column=2, padx=6, pady=6)

    # ==================== 区域 2.6：输配电费与年平均电价计算 ====================
    # 报装容量（kVA）：最大负荷 / 0.9（功率因数）/ 0.8（最大负荷率），向上取整为 100 的倍数
    max_load_kw = float(df_8760['load'].max())
    access_capacity_raw = max_load_kw / 0.9 / 0.8
    access_capacity_default = math.ceil(access_capacity_raw / 100.0) * 100

    frame_tariff = ttk.LabelFrame(tab_tariff, text=" 输配电费与年平均电价计算 ", padding=10)
    frame_tariff.pack(fill=tk.X, padx=15, pady=8)

    # 省份（默认甘肃）
    ttk.Label(frame_tariff, text="省份:").grid(row=0, column=0, padx=5, pady=3, sticky="e")
    default_province = "甘肃" if "甘肃" in PROVINCES else PROVINCES[0]
    combo_province = ttk.Combobox(frame_tariff, values=PROVINCES, width=12, state="readonly")
    combo_province.set(default_province)
    combo_province.grid(row=0, column=1, padx=5, pady=3)

    # 电压等级（默认 110千伏及以上）
    ttk.Label(frame_tariff, text="电压等级:").grid(row=0, column=2, padx=5, pady=3, sticky="e")
    combo_voltage = ttk.Combobox(frame_tariff, width=16, state="readonly")
    combo_voltage.grid(row=0, column=3, padx=5, pady=3)

    def on_province_change(*args):
        prov = combo_province.get()
        volts = list(TARIFF_DATA[prov]["voltage_levels"].keys())
        combo_voltage["values"] = volts
        target = "110千伏及以上"
        if target in volts:
            combo_voltage.set(target)
        elif volts:
            combo_voltage.set(volts[-1])

    combo_province.bind("<<ComboboxSelected>>", on_province_change)
    on_province_change()

    # 用电分类（单选）
    ttk.Label(frame_tariff, text="用电分类:").grid(row=1, column=0, padx=5, pady=3, sticky="e")
    mode_var = tk.StringVar(value="单一容量制（1192号文新规）")
    frame_mode = ttk.Frame(frame_tariff)
    frame_mode.grid(row=1, column=1, columnspan=3, padx=5, pady=3, sticky="w")
    for _txt in ("单一制（限小用户，规模以上用户不建议）",
                 "两部制", "单一容量制（1192号文新规）"):
        ttk.Radiobutton(frame_mode, text=_txt, variable=mode_var, value=_txt).pack(side=tk.LEFT, padx=8)

    # 报装容量
    ttk.Label(frame_tariff, text="报装容量 (kVA):").grid(row=2, column=0, padx=5, pady=3, sticky="e")
    entry_cap = ttk.Entry(frame_tariff, width=12)
    entry_cap.insert(0, f"{access_capacity_default:.0f}")
    entry_cap.grid(row=2, column=1, padx=5, pady=3)
    ttk.Label(frame_tariff,
              text="（功率因数 0.9、最大负荷率 0.8，按最大负荷折算，向上取整为 100kVA 倍数）",
              foreground="gray").grid(row=2, column=2, columnspan=2, padx=5, pady=3, sticky="w")

    # ---- 标准信息提示图标 ⓘ ----
    TIP_SYMBOL = "ⓘ"
    TIP_FONT = ("Segoe UI", 12, "bold")
    TIP_COLOR = "#0078D4"

    # 平均负荷率
    ttk.Label(frame_tariff, text="平均负荷率:").grid(row=3, column=0, padx=5, pady=3, sticky="e")
    entry_alr = ttk.Entry(frame_tariff, width=12)
    entry_alr.insert(0, f"{params.get('avg_load_rate', 0.65):.2f}")
    entry_alr.grid(row=3, column=1, padx=5, pady=3)
    lbl_alr_tip = tk.Label(frame_tariff, text=TIP_SYMBOL, fg=TIP_COLOR,
                           font=TIP_FONT, cursor="hand2")
    lbl_alr_tip.grid(row=3, column=2, padx=(0, 10), pady=3, sticky="w")

    # 系统运行费折价
    ttk.Label(frame_tariff, text="系统运行费折价 (元/kWh):").grid(row=4, column=0, padx=5, pady=3, sticky="e")
    entry_sys = ttk.Entry(frame_tariff, width=12)
    entry_sys.insert(0, f"{params.get('system_operation_fee', 0.094982):.6f}")
    entry_sys.grid(row=4, column=1, padx=5, pady=3)
    lbl_sys_tip = tk.Label(frame_tariff, text=TIP_SYMBOL, fg=TIP_COLOR,
                           font=TIP_FONT, cursor="hand2")
    lbl_sys_tip.grid(row=4, column=2, padx=(0, 10), pady=3, sticky="w")

    # 政府性基金及附加
    ttk.Label(frame_tariff, text="政府性基金及附加 (元/kWh):").grid(row=5, column=0, padx=5, pady=3, sticky="e")
    entry_gov = ttk.Entry(frame_tariff, width=12)
    entry_gov.insert(0, f"{params.get('gov_fund', 0.022925):.6f}")
    entry_gov.grid(row=5, column=1, padx=5, pady=3)
    lbl_gov_tip = tk.Label(frame_tariff, text=TIP_SYMBOL, fg=TIP_COLOR,
                           font=TIP_FONT, cursor="hand2")
    lbl_gov_tip.grid(row=5, column=2, padx=(0, 10), pady=3, sticky="w")

    # ---- Tooltip ----
    class _ToolTip:
        def __init__(self, widget, text):
            self.widget = widget
            self.text = text
            self.tw = None
            widget.bind("<Enter>", self._show)
            widget.bind("<Leave>", self._hide)
        def _show(self, _=None):
            if self.tw:
                return
            x = self.widget.winfo_rootx() + 25
            y = self.widget.winfo_rooty() + 22
            self.tw = tk.Toplevel(self.widget)
            self.tw.wm_overrideredirect(True)
            self.tw.wm_geometry(f"+{x}+{y}")
            tk.Label(self.tw, text=self.text, justify=tk.LEFT,
                     background="#FFFFE0", relief=tk.SOLID, borderwidth=1,
                     font=("Microsoft YaHei UI", 9), wraplength=400).pack(ipadx=6, ipady=4)
        def _hide(self, _=None):
            if self.tw:
                self.tw.destroy()
                self.tw = None

    _ToolTip(lbl_alr_tip, "平均负荷率：可参考省电力公司代理购电价格公示。\n默认 0.65。")
    _ToolTip(lbl_sys_tip, "系统运行费折价：可参考省电力公司代理购电价格公示。\n默认 0.094982 元/kWh。")
    _ToolTip(lbl_gov_tip,
             "政府性基金及附加包含：\n"
             "  国家重大水利工程建设基金：0.1125 分钱\n"
             "  可再生能源电价附加：1.9 分钱\n"
             "  大中型水库移民后期扶持资金：0.26 分钱\n"
             "  地方水库移民后期扶持资金：0.02 分钱\n"
             "合计默认 0.022925 元/kWh。")

    # ============================================================
    # 结果展示区（tk.Text 可复制，预填字段名占位）
    # ============================================================
    result_frame = ttk.LabelFrame(tab_tariff, text=" 计算结果（可选中复制） ", padding=5)
    result_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 8))

    result_text = tk.Text(result_frame, height=18,
                          font=("Consolas", 10),
                          bg="#F8F8F8", fg="#1F497D",
                          wrap="none", relief="flat",
                          selectbackground="#B3D9FF")
    result_scroll = ttk.Scrollbar(result_frame, orient="vertical",
                                  command=result_text.yview)
    result_text.configure(yscrollcommand=result_scroll.set)
    result_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # 空白模板（字段名占位）
    EMPTY_TEMPLATE = (
        "【输配电费】用电分类：                 电压等级：\n"
        "  电度电费    :                                 元/年\n"
        "  容量电费    :                                 元/年\n"
        "  1192新增部分:                                 元/年\n"
        "  输配电费合计:                                 元/年\n"
        "\n"
        "【年度用电量与电费明细】\n"
        "  年自发自用电量 :                              万kWh\n"
        "  年下网电量     :                              万kWh\n"
        "  年总用电量     :                              万kWh\n"
        "  自发自用电费   :                              万元/年\n"
        "  外购电费       :                              万元/年\n"
        "  系统运行费     :                              万元/年\n"
        "\n"
        "【用户年平均电价】=                            元/kWh\n"
    )

    def _set_result_text(widget, text):
        widget.config(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert("1.0", text)
        widget.config(state="disabled")

    _set_result_text(result_text, EMPTY_TEMPLATE)

    def calc_tariff():
        try:
            if not apply_parameter_boundaries():
                return
            prov = combo_province.get()
            volt = combo_voltage.get()
            mode_label = mode_var.get()
            cap = float(entry_cap.get())
            alr = float(entry_alr.get())
            sys_fee = float(entry_sys.get())
            gov_fee = float(entry_gov.get())

            if mode_label == "单一制":
                mode = "single"
            elif mode_label == "两部制":
                mode = "two_part"
            else:
                mode = "single_capacity_1192"

            pv_kw = float(entry_pv.get()) * 10000.0
            wind_kw = float(entry_wind.get()) * 10000.0
            bess_p_kw = float(entry_bess_p.get()) * 10000.0
            bess_h = float(entry_bess_h.get())
            bess_e_kwh = bess_p_kw * bess_h
            cap_for_sim = {'PV_kW': pv_kw, 'Wind_kW': wind_kw,
                           'BESS_kW': bess_p_kw, 'BESS_kWh': bess_e_kwh}
            dispatch_df_full = simulate_detailed_8760(df_8760, cap_for_sim, params)

            grid_buy_kwh = float(dispatch_df_full['grid_buy_wan'].sum() * 1e4)
            curtail_kwh  = float(dispatch_df_full['curtail_wan'].sum()  * 1e4)
            bess_loss_kwh = float((dispatch_df_full['bess_ch_wan'].sum()
                                   - dispatch_df_full['bess_dis_wan'].sum()) * 1e4)
            total_gen_kwh = float((dispatch_df_full['pv_gen_wan'].sum()
                                   + dispatch_df_full['wind_gen_wan'].sum()) * 1e4)
            self_use_kwh = total_gen_kwh - curtail_kwh - bess_loss_kwh

            tariff = calc_annual_tariff_fee(
                province=prov, voltage_level=volt,
                tariff_mode=mode,
                access_capacity_kva=cap,
                avg_load_rate=alr,
                grid_energy_kwh=grid_buy_kwh,
            )

            avg = calc_user_avg_price(
                self_use_kwh=self_use_kwh,
                grid_buy_kwh=grid_buy_kwh,
                price_self_use=float(entry_price.get()),
                price_buy=params.get('price_buy', 0.45),
                tariff_fee_annual=tariff['total_annual'],
                system_op_fee_per_kwh=sys_fee,
                gov_fund_per_kwh=gov_fee,
            )

            lines = [
                f"【输配电费】用电分类：{mode_label}    电压等级：{volt}",
                f"  电度电费    : {tariff['energy_fee']:>15,.2f} 元/年",
                f"  容量电费    : {tariff['capacity_fee']:>15,.2f} 元/年",
                f"  1192新增部分: {tariff['added_fee']:>15,.2f} 元/年",
                f"  输配电费合计: {tariff['total_annual']:>15,.2f} 元/年",
                "",
                f"【年度用电量与电费明细】",
                f"  年自发自用电量 : {self_use_kwh/1e4:>12,.2f} 万kWh",
                f"  年下网电量     : {grid_buy_kwh/1e4:>12,.2f} 万kWh",
                f"  年总用电量     : {avg['total_load']/1e4:>12,.2f} 万kWh",
                f"  自发自用电费   : {avg['self_use_fee']/1e4:>12,.2f} 万元/年",
                f"  外购电费       : {avg['grid_buy_fee']/1e4:>12,.2f} 万元/年",
                f"  系统运行费     : {avg['system_fee']/1e4:>12,.2f} 万元/年",
                "",
                f"【用户年平均电价】= {avg['avg_price']:.4f} 元/kWh",
            ]
            _set_result_text(result_text, "\n".join(lines))

        except Exception as e:
            messagebox.showerror("计算失败", str(e))

    ttk.Button(frame_tariff, text="计算输配电费与年平均电价",
               command=calc_tariff).grid(row=6, column=0, columnspan=4, pady=8)

    # ==================== 区域 2.5：查看结果 ====================
    frame_result = ttk.LabelFrame(tab_extra, text=" 查看结果 ", padding=10)
    frame_result.pack(fill=tk.X, padx=15, pady=8)

    btn_export_excel = ttk.Button(frame_result, text=" 导出财务报表 ",
                                  command=lambda: export_all_tables_to_excel())
    btn_export_excel.grid(row=0, column=0, padx=15, pady=6)

    btn_daily_view = ttk.Button(frame_result, text=" 查看逐日源荷匹配 ",
                                command=lambda: show_daily_dispatch_view())
    btn_daily_view.grid(row=0, column=1, padx=15, pady=6)

    frame_result.grid_columnconfigure(0, weight=1)
    frame_result.grid_columnconfigure(1, weight=1)

    # ==================== 区域 3：运营指标 ====================
    frame_operation = ttk.LabelFrame(results_panel, text=" 运营指标（可选中复制） ", padding=5)
    frame_operation.pack(fill=tk.X, padx=15, pady=8)

    result_text_options = {
        "font": ("Consolas", 10),
        "bg": "#F8F8F8",
        "fg": "#1F497D",
        "wrap": "none",
        "relief": "flat",
        "selectbackground": "#B3D9FF",
    }
    operation_text = tk.Text(frame_operation, height=7,
                             **result_text_options)
    operation_scroll = ttk.Scrollbar(frame_operation, orient="vertical",
                                     command=operation_text.yview)
    operation_text.configure(yscrollcommand=operation_scroll.set)
    operation_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    operation_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    operation_template = (
        " 光伏年理论发电量 :                         亿kWh  | 理论利用小时数 :       h\n"
        " 光伏年实际发电量 :                         亿kWh  | 实际利用小时数 :       h\n"
        " 风电年理论发电量 :                         亿kWh  | 理论利用小时数 :       h\n"
        " 风电年实际发电量 :                         亿kWh  | 实际利用小时数 :       h\n"
        " 年总弃电量       :                         亿kWh  | 综合弃电率     :       %\n"
        " 自发自用电量     :                         亿kWh  | 电网补充购电量 :       亿kWh\n"
        " 自发自用电量占比 :                         %     | 用户全年总用电量 :       亿kWh\n"
    )
    _set_result_text(operation_text, operation_template)

    # ==================== 区域 4：财务指标 ====================
    frame_finance = ttk.LabelFrame(results_panel, text=" 财务指标（可选中复制） ", padding=5)
    frame_finance.pack(fill=tk.X, padx=15, pady=8)

    finance_text = tk.Text(frame_finance, height=10,
                           **result_text_options)
    finance_scroll = ttk.Scrollbar(frame_finance, orient="vertical",
                                   command=finance_text.yview)
    finance_text.configure(yscrollcommand=finance_scroll.set)
    finance_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    finance_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    finance_template = (
        " 总投资（动态） :                         亿元\n"
        " 总投资（静态） :                         亿元\n"
        " 光伏投资       :                         万元\n"
        " 风电投资       :                         万元\n"
        " 储能投资       :                         万元\n"
        " 全部投资内部收益率（税前） :             %\n"
        " 全部投资内部收益率（税后） :             %\n"
        " 资本金内部收益率 :                         %\n"
    )
    _set_result_text(finance_text, finance_template)

    # ==================== 内部计算函数 ====================
    last_financial_result = {}

    def run_simulation():
        if not apply_parameter_boundaries(sync_price_entry=False):
            return None, None, None
        try:
            curr_pv_wan = float(entry_pv.get().strip())
            curr_wind_wan = float(entry_wind.get().strip())
            curr_bess_p_wan = float(entry_bess_p.get().strip())
            curr_bess_h = float(entry_bess_h.get().strip())
        except ValueError:
            messagebox.showerror("输入错误", "请输入有效的数值格式！")
            return None, None, None

        pv_kw = curr_pv_wan * 10000.0
        wind_kw = curr_wind_wan * 10000.0
        bess_p_kw = curr_bess_p_wan * 10000.0
        bess_e_kwh = bess_p_kw * curr_bess_h

        pv_norm_sum = df_8760['pv_norm'].sum()
        wind_norm_sum = df_8760['wind_norm'].sum()

        pv_theo_yi = (pv_kw * pv_norm_sum) / 1e8
        wind_theo_yi = (wind_kw * wind_norm_sum) / 1e8

        soc = bess_e_kwh * 0.5
        curtail_total_kwh = 0.0
        direct_load_total_kwh = 0.0
        grid_buy_total_kwh = 0.0
        bess_ch_total_kwh = 0.0
        bess_dis_total_kwh = 0.0

        for t in range(8760):
            p_pv = pv_kw * df_8760.loc[t, 'pv_norm']
            p_wind = wind_kw * df_8760.loc[t, 'wind_norm']
            p_gen = p_pv + p_wind
            p_load = df_8760.loc[t, 'load']
            direct_load_total_kwh += min(p_gen, p_load)

            diff = p_gen - p_load
            if diff > 0:
                ch_possible = min(diff, bess_p_kw,
                                  (bess_e_kwh * params.get('soc_max', 0.9) - soc) / params.get('eta_ch', 0.95))
                soc += ch_possible * params.get('eta_ch', 0.95)
                curtail_total_kwh += (diff - ch_possible)
                bess_ch_total_kwh += ch_possible
            else:
                deficit = -diff
                dis_possible = min(deficit, bess_p_kw,
                                   (soc - bess_e_kwh * params.get('soc_min', 0.1)) * params.get('eta_dis', 0.95))
                soc -= dis_possible / params.get('eta_dis', 0.95)
                grid_buy_total_kwh += (deficit - dis_possible)
                bess_dis_total_kwh += dis_possible

        curtail_yi = curtail_total_kwh / 1e8
        grid_buy_yi = grid_buy_total_kwh / 1e8
        total_theo = pv_theo_yi + wind_theo_yi + 1e-6
        pv_act_yi = pv_theo_yi - (curtail_yi * (pv_theo_yi / total_theo))
        wind_act_yi = wind_theo_yi - (curtail_yi * (wind_theo_yi / total_theo))

        curr_cap_res = {'PV_kW': pv_kw, 'Wind_kW': wind_kw, 'BESS_kW': bess_p_kw, 'BESS_kWh': bess_e_kwh}
        curr_df_sim = pd.DataFrame({
            'pv_gen_wan': [pv_act_yi * 1e4],
            'wind_gen_wan': [wind_act_yi * 1e4],
            'bess_dis_wan': [bess_dis_total_kwh / 10000.0],
            'bess_ch_wan': [bess_ch_total_kwh / 10000.0],
            'curtail_wan': [curtail_yi * 1e4],
            'direct_load_wan': [direct_load_total_kwh / 10000.0],
        })

        sim_info = {
            'pv_theo_yi': pv_theo_yi, 'pv_theo_hours': pv_norm_sum,
            'pv_act_yi': pv_act_yi, 'pv_act_hours': (pv_act_yi * 1e8) / pv_kw if pv_kw > 0 else 0.0,
            'wind_theo_yi': wind_theo_yi, 'wind_theo_hours': wind_norm_sum,
            'wind_act_yi': wind_act_yi, 'wind_act_hours': (wind_act_yi * 1e8) / wind_kw if wind_kw > 0 else 0.0,
            'curtail_yi': curtail_yi, 'curtail_rate': (curtail_yi / total_theo) * 100.0,
            'self_use_yi': pv_act_yi + wind_act_yi, 'grid_buy_yi': grid_buy_yi,
            'load_total_yi': df_8760['load'].sum() / 1e8
        }

        return curr_cap_res, curr_df_sim, sim_info

    def do_calculation(calc_price_override=None):
        nonlocal last_financial_result
        try:
            curr_price = calc_price_override if calc_price_override is not None else float(entry_price.get().strip())
        except ValueError:
            messagebox.showerror("输入错误", "请输入有效的自发自用电价！")
            return None

        curr_cap_res, curr_df_sim, sim_info = run_simulation()
        if curr_cap_res is None:
            return None

        fin_res = run_financial_evaluation(curr_cap_res, curr_df_sim, params, custom_price_buy=curr_price)
        last_financial_result = fin_res

        update_entry(entry_equity_irr, f"{fin_res['irr_equity'] * 100.0:.2f}")

        var_pv_theo.set(f"光伏年理论发电量 : {sim_info['pv_theo_yi']:.4f} 亿kWh  | 理论利用小时数 : {sim_info['pv_theo_hours']:.1f} h")
        var_pv_act.set(f"光伏年实际发电量 : {sim_info['pv_act_yi']:.4f} 亿kWh  | 实际利用小时数 : {sim_info['pv_act_hours']:.1f} h")
        var_wind_theo.set(f"风电年理论发电量 : {sim_info['wind_theo_yi']:.4f} 亿kWh  | 理论利用小时数 : {sim_info['wind_theo_hours']:.1f} h")
        var_wind_act.set(f"风电年实际发电量 : {sim_info['wind_act_yi']:.4f} 亿kWh  | 实际利用小时数 : {sim_info['wind_act_hours']:.1f} h")
        var_curtail.set(f"年总弃电量       : {sim_info['curtail_yi']:.4f} 亿kWh  | 综合弃电率     : {sim_info['curtail_rate']:.2f} %")
        var_self_use.set(f"自发自用电量     : {sim_info['self_use_yi']:.4f} 亿kWh  | 电网补充购电量 : {sim_info['grid_buy_yi']:.4f} 亿kWh")

        self_use_ratio = (sim_info['self_use_yi'] / sim_info['load_total_yi'] * 100.0) if sim_info['load_total_yi'] > 0 else 0.0
        var_self_use_ratio.set(f"自发自用电量占比 : {self_use_ratio:.2f} %     | 用户全年总用电量 : {sim_info['load_total_yi']:.4f} 亿kWh")

        operation_lines = [
            var_pv_theo.get(),
            var_pv_act.get(),
            var_wind_theo.get(),
            var_wind_act.get(),
            var_curtail.get(),
            var_self_use.get(),
            var_self_use_ratio.get(),
        ]
        _set_result_text(operation_text, "\n".join(operation_lines))

        var_tot_dyn.set(f"总投资（动态） : {fin_res['total_project_inv_wan'] / 10000.0:.4f} 亿元")
        var_tot_static.set(f"总投资（静态） : {fin_res['total_static_inv_wan'] / 10000.0:.4f} 亿元")
        var_inv_pv.set(f"光伏投资       : {fin_res['inv_pv_wan']:.2f} 万元")
        var_inv_wind.set(f"风电投资       : {fin_res['inv_wind_wan']:.2f} 万元")
        var_inv_bess.set(f"储能投资       : {fin_res['inv_bess_total_wan']:.2f} 万元")
        var_irr_pre.set(f"全部投资内部收益率（税前） : {fin_res['irr_pre_tax'] * 100.0:.2f} %")
        var_irr_post.set(f"全部投资内部收益率（税后） : {fin_res['irr_post_tax'] * 100.0:.2f} %")
        var_irr_equity.set(f"资本金内部收益率 : {fin_res['irr_equity'] * 100.0:.2f} %")

        finance_lines = [
            var_tot_dyn.get(),
            var_tot_static.get(),
            var_inv_pv.get(),
            var_inv_wind.get(),
            var_inv_bess.get(),
            var_irr_pre.get(),
            var_irr_post.get(),
            var_irr_equity.get(),
        ]
        _set_result_text(finance_text, "\n".join(finance_lines))

        return fin_res

    def apply_and_recalculate():
        """应用边界条件并立即刷新运营和财务指标。"""
        if apply_parameter_boundaries():
            do_calculation()

    def on_parameter_enter(event):
        apply_and_recalculate()
        return "break"

    for parameter_entry, _, _, _ in parameter_entries.values():
        parameter_entry.bind("<Return>", on_parameter_enter)
        parameter_entry.bind("<KP_Enter>", on_parameter_enter)

    def calc_irr_from_cap_price():
        do_calculation()

    def calc_price_from_irr():
        try:
            target_irr = float(entry_equity_irr.get().strip()) / 100.0
        except ValueError:
            messagebox.showerror("格式错误", "请输入正确的资本金 IRR！")
            return

        curr_cap_res, curr_df_sim, _ = run_simulation()
        if curr_cap_res is None:
            return

        low, high = 0.001, 10.0
        for _ in range(30):
            mid = (low + high) / 2.0
            res = run_financial_evaluation(curr_cap_res, curr_df_sim, params, custom_price_buy=mid)
            if res['irr_equity'] < target_irr:
                low = mid
            else:
                high = mid

        update_entry(entry_price, f"{high:.4f}")
        params["price_self_use"] = high
        boundary_price_entry = parameter_entries.get("price_self_use", (None,))[0]
        if boundary_price_entry is not None:
            update_entry(boundary_price_entry, f"{high:.4f}")
        do_calculation()

    def export_all_tables_to_excel():
        nonlocal last_financial_result
        if not last_financial_result or 'df_cost' not in last_financial_result:
            last_financial_result = do_calculation()
        if not last_financial_result:
            messagebox.showwarning("提示", "计算失败，无法生成有效的财务报表！")
            return None

        file_path = "全套财务测算表.xlsx"
        try:
            data = export_financial_tables_to_bytes(last_financial_result)
            with open(file_path, 'wb') as f:
                f.write(data)
            import os
            full_path = os.path.abspath(file_path)
            messagebox.showinfo("成功", f"全套财务报表已成功导出至当前目录：\n{full_path}")
        except Exception as e:
            messagebox.showerror("导出失败", f"导出失败：\n{str(e)}")

    def show_daily_dispatch_view():
        try:
            pv_kw = float(entry_pv.get().strip()) * 10000.0
            wind_kw = float(entry_wind.get().strip()) * 10000.0
            bess_p_kw = float(entry_bess_p.get().strip()) * 10000.0
            bess_h = float(entry_bess_h.get().strip())
        except ValueError:
            messagebox.showerror("输入错误", "请输入有效的数值格式！")
            return

        bess_e_kwh = bess_p_kw * bess_h
        cap = {
            'PV_kW': pv_kw, 'Wind_kW': wind_kw,
            'BESS_kW': bess_p_kw, 'BESS_kWh': bess_e_kwh,
        }
        dispatch_df = simulate_detailed_8760(df_8760, cap, params)
        show_daily_dispatch_window(dispatch_df)

    btn_cap_to_irr = ttk.Button(frame_cap_price, text=" 开始计算 ",
                                command=calc_irr_from_cap_price)
    btn_cap_to_irr.grid(row=3, column=0, columnspan=4, pady=10)

    def on_equity_irr_enter(event):
        calc_price_from_irr()
        return "break"

    entry_equity_irr.bind('<Return>', on_equity_irr_enter)
    entry_equity_irr.bind('<KP_Enter>', on_equity_irr_enter)
    root.bind('<Return>', lambda event: do_calculation())
    root.bind('<KP_Enter>', lambda event: do_calculation())

    do_calculation()

    # 定一个合理的初始尺寸，用户可自行调整
    init_w = int(820 * dpi_scale)
    init_h = int(820 * dpi_scale)
    fit_window_to_screen(root, init_w, init_h)

    root.mainloop()

    if export_excel_path and last_financial_result.get('cash_flow_df') is not None:
        last_financial_result['cash_flow_df'].to_excel(
            export_excel_path, index=False, sheet_name="资本金净现金流量"
        )
        print(f"窗口已关闭，调参后的资本金净现金流量表已自动保存至: {export_excel_path}")

    return last_financial_result

# =============================================================
# 7. 主程序入口
# =============================================================
if __name__ == "__main__":
    # 文件顶部（或 __main__ 开头）
    enable_dpi_awareness()
    # ---- 先注册字体，再创建任何 Tk 窗口 ----
    FONT_FILE = find_font_file()
    if os.path.exists(FONT_FILE):
        register_font_for_tkinter(FONT_FILE)
        font_name = register_font_for_matplotlib(FONT_FILE)
        print(f"[字体] 已加载: {font_name}")
    else:
        print(f"[字体] 未找到 {FONT_FILE}，将使用系统默认字体")

    # matplotlib 全局字体
    plt.rcParams['font.sans-serif'] = ['Source Han Sans CN', 'SimHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False


    DEBUG_FAST_SOLVER = True   # True=调试快速模式；False=真实 PuLP 优化
    params = get_user_parameters()

    excel_file = resource_path("8760小时模拟原始数据.xlsx")
    if os.path.exists(excel_file):
        print(f"\n读取数据文件: {excel_file}")
        df_pv = pd.read_excel(excel_file, sheet_name='光伏逐小时数据', skiprows=2)
        df_wind = pd.read_excel(excel_file, sheet_name='风电逐小时数据', skiprows=2)
        df_load = pd.read_excel(excel_file, sheet_name='负荷逐小时数据', skiprows=2)

        pv_norm = pd.to_numeric(df_pv.iloc[0:8760, 5], errors='coerce').fillna(0).values
        wind_norm = pd.to_numeric(df_wind.iloc[0:8760, 5], errors='coerce').fillna(0).values
        load_kw = pd.to_numeric(df_load.iloc[0:8760, 5], errors='coerce').fillna(0).values * 10000.0
    else:
        root = tk.Tk()
        root.withdraw()
        error_msg = f"未找到基础数据文件：\n【 {excel_file} 】\n\n请确认安装包中包含该文件后重新运行程序！"
        messagebox.showerror("缺少基础数据文件", error_msg)
        print(f"\n[错误] {error_msg}")
        exit(1)

    df_8760 = pd.DataFrame({'pv_norm': pv_norm, 'wind_norm': wind_norm, 'load': load_kw})

    # 展现预分析图形，用户选择下一步
    user_choice = plot_pre_optimization_analysis(df_8760)

    if user_choice == 'exit':
        print("\n用户选择退出，程序结束。")
        sys.exit(0)

    # ---------- 分流：手动调整 或 自动优化 ----------
    if user_choice == 'manual':
        print("\n>>> 已选择[手动调整]模式，跳过 PuLP 寻优，直接进入参数调整界面...")
        cap_res, df_sim = optimize_capacity_debug(df_8760, params, verbose=True)
    else:  # user_choice == 'auto'
        print("\n>>> 已选择[自动优化]模式，正在启动 PuLP 求解...")
        cap_res, df_sim = run_with_progress_dialog(
            task_func=lambda: optimize_capacity_pulp(
                df_8760, params,
                load_self_use_ratio=0.35,   # Tkinter 版固定 35%
                verbose=True,
            ),
            task_desc="正在使用 PuLP 求解 8760 小时混合整数线性规划模型，\n计算风光储最优容量配置……",
            hint="（求解通常需要 1~3 分钟，请耐心等待，请勿关闭窗口）"
        )

    # ---------- 财务评估 ----------
    print("\n>>> 正在计算初始配置下的财务指标...")
    fin_eval = run_with_progress_dialog(
        task_func=lambda: run_financial_evaluation(cap_res, df_sim, params),
        task_desc="正在构建全生命周期现金流并计算 IRR……",
        hint="（通常几秒内完成）"
    )

    bess_duration = cap_res['BESS_kWh'] / cap_res['BESS_kW'] if cap_res['BESS_kW'] > 0 else 0.0

    print("\n================== 最佳推荐容量配置结果 ==================")
    print(f" - 推荐光伏装机容量 : {cap_res['PV_kW']/10000.0:.2f} 万kW")
    print(f" - 推荐风电装机容量 : {cap_res['Wind_kW']/10000.0:.2f} 万kW")
    print(f" - 推荐储能功率容量 : {cap_res['BESS_kW']/10000.0:.2f} 万kW")
    print(f" - 推荐储能能量容量 : {cap_res['BESS_kWh']/10000.0:.2f} 万kWh (优化时长: {bess_duration:.2f} 小时)")
    print("------------------ 分项投资与财务评估 ------------------")
    print(f" - 光伏静态投资     : {fin_eval['inv_pv_wan']:.2f} 万元")
    print(f" - 风电静态投资     : {fin_eval['inv_wind_wan']:.2f} 万元")
    print(f" - 储能静态投资     : {fin_eval['inv_bess_total_wan']:.2f} 万元")
    print(f" - 项目静态总投资   : {fin_eval['total_static_inv_wan'] / 10000.0:.4f} 亿元 ({fin_eval['total_static_inv_wan']:.2f} 万元)")
    print(f" - 建设期利息       : {fin_eval['interest_construction_wan']:.2f} 万元")
    print(f" - 流动资金         : {fin_eval['working_capital_wan']:.2f} 万元")
    print(f" - 项目总投资(动态) : {fin_eval['total_project_inv_wan'] / 10000.0:.4f} 亿元 ({fin_eval['total_project_inv_wan']:.2f} 万元)")
    print(f" - 项目资本金       : {fin_eval['equity_wan']:.2f} 万元")
    print(f" - 项目全投资IRR(税前): {fin_eval['irr_pre_tax']*100.0:.2f} %")
    print(f" - 项目全投资IRR(税后): {fin_eval['irr_post_tax']*100.0:.2f} %")
    print(f" - 资本金 IRR       : {fin_eval['irr_equity']*100.0:.2f} %")
    print("========================================================")

    _data = export_full_report_to_bytes(df_8760, cap_res, fin_eval)
    with open("新能源特性分析及容量优化结果表.xlsx", 'wb') as _f:
        _f.write(_data)
    print(">>> 成功生成 Excel 报告：新能源特性分析及容量优化结果表.xlsx")

print("\n正在启动参数调整 GUI 界面...")
# 必须使用 final_res 接收函数返回值
final_res = open_parameter_adjustment_window(cap_res, df_8760, params)