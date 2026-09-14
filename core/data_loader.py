"""8760 小时数据加载"""
import pandas as pd


def _parse_excel(file_or_path):
    df_pv   = pd.read_excel(file_or_path, sheet_name='光伏逐小时数据', skiprows=2)
    df_wind = pd.read_excel(file_or_path, sheet_name='风电逐小时数据', skiprows=2)
    df_load = pd.read_excel(file_or_path, sheet_name='负荷逐小时数据', skiprows=2)

    pv_norm   = pd.to_numeric(df_pv.iloc[0:8760, 5],   errors='coerce').fillna(0).values
    wind_norm = pd.to_numeric(df_wind.iloc[0:8760, 5], errors='coerce').fillna(0).values
    load_kw   = pd.to_numeric(df_load.iloc[0:8760, 5], errors='coerce').fillna(0).values * 10000.0

    return pd.DataFrame({
        'pv_norm':   pv_norm,
        'wind_norm': wind_norm,
        'load':      load_kw,
    })


def load_8760_from_path(path):
    """从文件路径读取（Tkinter 用）"""
    return _parse_excel(path)


def load_8760_from_file(file_obj):
    """从 file-like 对象读取（Streamlit 用）"""
    return _parse_excel(file_obj)