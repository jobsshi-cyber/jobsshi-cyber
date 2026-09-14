"""
省级电网输配电价数据（2025年第三监管周期）

数据来源：国家发改委公开的省级电网输配电价表
单位：电量电价 元/千瓦时；容(需)量电价 元/千瓦·月 或 元/千伏安·月
"""

# =============================================================
# 数据结构说明：
#   province: 省份名称
#   voltage: 电压等级（对应PDF中的列）
#   single_price: 单一制电量电价（元/kWh）
#   two_part_energy: 两部制电量电价（元/kWh）
#   capacity_price: 两部制容量电价（元/千伏安·月）
#   demand_price: 两部制需量电价（元/千瓦·月）
#   avg_load_rate: 平均负荷率估算值（110kV及以上工商业两部制）
#   line_loss_rate: 省内上网环节线损率
#   vat_rate: 增值税率
# =============================================================

TARIFF_DATA = {
    "北京": {
        "voltage_levels": {
            "不满1千伏":  {"single_price": 0.3800, "two_part_energy": None,   "capacity_price": None, "demand_price": None},
            "1~10(20)千伏": {"single_price": 0.3100, "two_part_energy": 0.2050, "capacity_price": 33.0, "demand_price": 52.0},
            "35~110千伏":  {"single_price": 0.2500, "two_part_energy": 0.1650, "capacity_price": 30.0, "demand_price": 48.0},
            "220千伏及以上": {"single_price": 0.2000, "two_part_energy": 0.1500, "capacity_price": 28.0, "demand_price": 45.0},
        },
        "avg_load_rate": 0.75,     # 估算值，实际以当地公布为准
        "line_loss_rate": 3.11,
    },
    "天津": {
        "voltage_levels": {
            "不满1千伏":  {"single_price": 0.2836, "two_part_energy": 0.2158, "capacity_price": 27.0, "demand_price": 43.2},
            "1~10(20)千伏": {"single_price": None,   "two_part_energy": 0.1631, "capacity_price": 27.0, "demand_price": 43.2},
            "35千伏":     {"single_price": 0.2507, "two_part_energy": 0.1402, "capacity_price": 25.0, "demand_price": 40.0},
            "110千伏":    {"single_price": 0.1864, "two_part_energy": 0.1264, "capacity_price": 25.0, "demand_price": 40.0},
            "220千伏及以上": {"single_price": 0.1534, "two_part_energy": 0.1052, "capacity_price": 23.0, "demand_price": 36.8},
        },
        "avg_load_rate": 0.75,
        "line_loss_rate": 2.54,
    },
    "河北": {
        "voltage_levels": {
            "不满1千伏":  {"single_price": 0.2150, "two_part_energy": 0.1726, "capacity_price": 23.0, "demand_price": 36.8},
            "35千伏":     {"single_price": 0.1900, "two_part_energy": 0.1476, "capacity_price": 22.0, "demand_price": 35.2},
            "110千伏":    {"single_price": 0.1650, "two_part_energy": 0.1226, "capacity_price": 21.0, "demand_price": 33.6},
            "220千伏及以上": {"single_price": 0.1400, "two_part_energy": 0.0976, "capacity_price": 20.0, "demand_price": 32.0},
        },
        "avg_load_rate": 0.75,
        "line_loss_rate": 4.08,
    },
    "冀北": {
        "voltage_levels": {
            "不满1千伏":  {"single_price": 0.1803, "two_part_energy": 0.1585, "capacity_price": 24.6, "demand_price": 39.4},
            "1~10(20)千伏": {"single_price": 0.1583, "two_part_energy": 0.1365, "capacity_price": 23.6, "demand_price": 37.8},
            "35千伏":     {"single_price": 0.1363, "two_part_energy": 0.1145, "capacity_price": 22.6, "demand_price": 36.2},
            "110千伏":    {"single_price": 0.1143, "two_part_energy": 0.0925, "capacity_price": 21.6, "demand_price": 34.6},
            "220千伏及以上": {"single_price": 0.1023, "two_part_energy": 0.0705, "capacity_price": 20.6, "demand_price": 33.0},
        },
        "avg_load_rate": 0.75,
        "line_loss_rate": 2.87,
    },
    "山西": {
        "voltage_levels": {
            "不满1千伏":  {"single_price": 0.1672, "two_part_energy": 0.1040, "capacity_price": 21.8, "demand_price": 34.8},
            "1~10(20)千伏": {"single_price": 0.1472, "two_part_energy": 0.0740, "capacity_price": 21.3, "demand_price": 34.0},
            "35千伏":     {"single_price": 0.1322, "two_part_energy": 0.0490, "capacity_price": 19.8, "demand_price": 31.6},
            "110千伏及以上": {"single_price": 0.1222, "two_part_energy": 0.0290, "capacity_price": 18.8, "demand_price": 30.0},
        },
        "avg_load_rate": 0.75,
        "line_loss_rate": 3.52,
    },
    "蒙东": {
        "voltage_levels": {
            "不满1千伏":  {"single_price": 0.3732, "two_part_energy": 0.1738, "capacity_price": 21.5, "demand_price": 34.4},
            "1~10(20)千伏": {"single_price": 0.3356, "two_part_energy": 0.1346, "capacity_price": 20.5, "demand_price": 32.8},
            "35千伏":     {"single_price": 0.2499, "two_part_energy": 0.1080, "capacity_price": 20.5, "demand_price": 32.8},
            "110(66)千伏": {"single_price": 0.1732, "two_part_energy": 0.0870, "capacity_price": 19.5, "demand_price": 31.2},
            "220千伏及以上": {"single_price": 0.1401, "two_part_energy": 0.0601, "capacity_price": 19.5, "demand_price": 31.2},
        },
        "avg_load_rate": 0.75,
        "line_loss_rate": 6.41,
    },
    "蒙西": {
        "voltage_levels": {
            "不满1千伏":  {"single_price": 0.1561, "two_part_energy": 0.0876, "capacity_price": 21.5, "demand_price": 34.4},
            "1~10(20)千伏": {"single_price": 0.1289, "two_part_energy": 0.0787, "capacity_price": 20.5, "demand_price": 32.8},
            "35千伏":     {"single_price": 0.1129, "two_part_energy": 0.0637, "capacity_price": 20.5, "demand_price": 32.8},
            "110千伏":    {"single_price": 0.1029, "two_part_energy": 0.0520, "capacity_price": 19.5, "demand_price": 31.2},
            "220千伏及以上": {"single_price": 0.0920, "two_part_energy": 0.0429, "capacity_price": 19.5, "demand_price": 31.2},
        },
        "avg_load_rate": 0.75,
        "line_loss_rate": 2.81,
    },
    "辽宁": {
        "voltage_levels": {
            "不满1千伏":  {"single_price": 0.2330, "two_part_energy": 0.1182, "capacity_price": 24.0, "demand_price": 38.4},
            "10(20)千伏及以下": {"single_price": 0.2119, "two_part_energy": 0.1053, "capacity_price": 23.0, "demand_price": 36.8},
            "110(66)千伏": {"single_price": 0.1881, "two_part_energy": 0.0840, "capacity_price": 22.0, "demand_price": 35.2},
            "220千伏及以上": {"single_price": 0.1410, "two_part_energy": 0.0571, "capacity_price": 22.0, "demand_price": 35.2},
        },
        "avg_load_rate": 0.75,
        "line_loss_rate": 3.78,
    },
    "吉林": {
        "voltage_levels": {
            "不满1千伏":  {"single_price": 0.2870, "two_part_energy": 0.1513, "capacity_price": 24.0, "demand_price": 38.4},
            "1~10(20)千伏": {"single_price": 0.2570, "two_part_energy": 0.1213, "capacity_price": 23.0, "demand_price": 36.8},
            "110(66)千伏": {"single_price": 0.2470, "two_part_energy": 0.1113, "capacity_price": 23.0, "demand_price": 36.8},
            "220千伏及以上": {"single_price": 0.2270, "two_part_energy": None,   "capacity_price": None, "demand_price": None},
        },
        "avg_load_rate": 0.75,
        "line_loss_rate": 5.17,
    },
    "黑龙江": {
        "voltage_levels": {
            "不满1千伏":  {"single_price": 0.2828, "two_part_energy": 0.1385, "capacity_price": 23.0, "demand_price": 36.8},
            "1~10(20)千伏": {"single_price": 0.2726, "two_part_energy": 0.1171, "capacity_price": 23.0, "demand_price": 36.8},
            "35千伏":     {"single_price": 0.2620, "two_part_energy": 0.1026, "capacity_price": 22.0, "demand_price": 35.2},
            "110(66)千伏及以上": {"single_price": 0.2410, "two_part_energy": 0.0763, "capacity_price": 22.0, "demand_price": 35.2},
        },
        "avg_load_rate": 0.75,
        "line_loss_rate": 6.46,
    },
    "上海": {
        "voltage_levels": {
            "不满1千伏":  {"single_price": 0.2891, "two_part_energy": 0.1781, "capacity_price": 30.0, "demand_price": 48.0},
            "1~10(20)千伏": {"single_price": 0.2446, "two_part_energy": 0.1623, "capacity_price": 28.0, "demand_price": 44.8},
            "35千伏":     {"single_price": 0.1989, "two_part_energy": 0.1268, "capacity_price": 26.0, "demand_price": 41.6},
            "110千伏":    {"single_price": 0.1656, "two_part_energy": 0.0953, "capacity_price": 24.0, "demand_price": 38.4},
            "220千伏及以上": {"single_price": 0.1076, "two_part_energy": 0.0851, "capacity_price": 22.0, "demand_price": 35.2},
        },
        "avg_load_rate": 0.75,
        "line_loss_rate": 2.61,
    },
    "江苏": {
        "voltage_levels": {
            "不满1千伏":  {"single_price": 0.2391, "two_part_energy": 0.1298, "capacity_price": 32.0, "demand_price": 51.2},
            "1~10(20)千伏": {"single_price": 0.2131, "two_part_energy": 0.1048, "capacity_price": 30.0, "demand_price": 48.0},
            "110千伏":    {"single_price": 0.1881, "two_part_energy": 0.0788, "capacity_price": 28.0, "demand_price": 44.8},
            "220千伏及以上": {"single_price": 0.1621, "two_part_energy": 0.0518, "capacity_price": 26.0, "demand_price": 41.6},
        },
        "avg_load_rate": 0.75,
        "line_loss_rate": 2.83,
    },
    "浙江": {
        "voltage_levels": {
            "不满1千伏":  {"single_price": 0.2412, "two_part_energy": 0.1250, "capacity_price": 29.5, "demand_price": 47.2},
            "1~10(20)千伏": {"single_price": 0.2114, "two_part_energy": 0.0895, "capacity_price": 27.5, "demand_price": 44.0},
            "110千伏":    {"single_price": 0.1700, "two_part_energy": 0.0767, "capacity_price": 25.5, "demand_price": 40.8},
            "220千伏及以上": {"single_price": 0.1500, "two_part_energy": 0.0663, "capacity_price": 23.5, "demand_price": 37.6},
        },
        "avg_load_rate": 0.75,
        "line_loss_rate": 3.07,
    },
    "安徽": {
        "voltage_levels": {
            "不满1千伏":  {"single_price": 0.2014, "two_part_energy": 0.1324, "capacity_price": 29.0, "demand_price": 46.4},
            "1~10(20)千伏": {"single_price": 0.1794, "two_part_energy": 0.1070, "capacity_price": 27.0, "demand_price": 43.2},
            "110千伏及以上": {"single_price": 0.1574, "two_part_energy": 0.0809, "capacity_price": 25.5, "demand_price": 40.8},
        },
        "avg_load_rate": 0.75,
        "line_loss_rate": 3.90,
    },
    "福建": {
        "voltage_levels": {
            "不满1千伏":  {"single_price": 0.1833, "two_part_energy": 0.1219, "capacity_price": 25.0, "demand_price": 40.0},
            "1~10(20)千伏": {"single_price": 0.1633, "two_part_energy": 0.1019, "capacity_price": 24.4, "demand_price": 39.0},
            "35千伏":     {"single_price": 0.1433, "two_part_energy": 0.0769, "capacity_price": 23.8, "demand_price": 38.0},
            "110千伏":    {"single_price": 0.1233, "two_part_energy": 0.0462, "capacity_price": 23.1, "demand_price": 37.0},
            "220千伏及以上": {"single_price": 0.0883, "two_part_energy": None,   "capacity_price": None, "demand_price": None},
        },
        "avg_load_rate": 0.75,
        "line_loss_rate": 3.37,
    },
    "江西": {
        "voltage_levels": {
            "不满1千伏":  {"single_price": 0.1916, "two_part_energy": 0.1485, "capacity_price": 26.4, "demand_price": 42.3},
            "1~10(20)千伏": {"single_price": 0.1716, "two_part_energy": 0.1285, "capacity_price": 25.4, "demand_price": 40.6},
            "35千伏":     {"single_price": 0.1516, "two_part_energy": 0.1085, "capacity_price": 24.4, "demand_price": 39.1},
            "110千伏":    {"single_price": 0.1316, "two_part_energy": 0.0935, "capacity_price": 23.4, "demand_price": 37.5},
        },
        "avg_load_rate": 0.75,
        "line_loss_rate": 3.68,
    },
    "山东": {
        "voltage_levels": {
            "不满1千伏":  {"single_price": 0.2401, "two_part_energy": 0.1400, "capacity_price": 25.0, "demand_price": 40.0},
            "1~10(20)千伏": {"single_price": 0.2231, "two_part_energy": 0.1230, "capacity_price": 22.5, "demand_price": 36.0},
            "35千伏":     {"single_price": 0.2061, "two_part_energy": 0.1060, "capacity_price": 22.5, "demand_price": 36.0},
            "110千伏":    {"single_price": 0.1891, "two_part_energy": 0.0890, "capacity_price": 20.0, "demand_price": 32.0},
        },
        "avg_load_rate": 0.75,
        "line_loss_rate": 3.07,
    },
    "河南": {
        "voltage_levels": {
            "不满1千伏":  {"single_price": 0.1955, "two_part_energy": 0.1655, "capacity_price": 25.0, "demand_price": 40.0},
            "1~10(20)千伏": {"single_price": 0.1680, "two_part_energy": 0.1392, "capacity_price": 23.0, "demand_price": 36.8},
            "35千伏":     {"single_price": 0.1412, "two_part_energy": 0.1125, "capacity_price": 21.0, "demand_price": 33.6},
            "110千伏及以上": {"single_price": 0.1145, "two_part_energy": 0.0980, "capacity_price": 19.0, "demand_price": 30.4},
        },
        "avg_load_rate": 0.75,
        "line_loss_rate": 4.82,
    },
    "湖北": {
        "voltage_levels": {
            "不满1千伏":  {"single_price": 0.2103, "two_part_energy": 0.1263, "capacity_price": 26.3, "demand_price": 42.0},
            "1~10(20)千伏": {"single_price": 0.1903, "two_part_energy": 0.1065, "capacity_price": 26.3, "demand_price": 42.0},
            "110千伏":    {"single_price": 0.1703, "two_part_energy": 0.0884, "capacity_price": 24.4, "demand_price": 39.0},
            "220千伏及以上": {"single_price": 0.1503, "two_part_energy": 0.0694, "capacity_price": 24.4, "demand_price": 39.0},
        },
        "avg_load_rate": 0.75,
        "line_loss_rate": 4.55,
    },
    "湖南": {
        "voltage_levels": {
            "不满1千伏":  {"single_price": 0.2609, "two_part_energy": 0.1694, "capacity_price": 22.1, "demand_price": 35.4},
            "1~10千伏":   {"single_price": 0.2409, "two_part_energy": 0.1394, "capacity_price": 22.1, "demand_price": 35.4},
            "35千伏":     {"single_price": 0.2209, "two_part_energy": 0.1104, "capacity_price": 20.1, "demand_price": 32.2},
            "110千伏及以上": {"single_price": 0.2009, "two_part_energy": 0.0852, "capacity_price": 20.1, "demand_price": 32.2},
        },
        "avg_load_rate": 0.75,
        "line_loss_rate": 4.95,
    },
    "广东": {
        "voltage_levels": {
            "不满1千伏":  {"single_price": 0.1957, "two_part_energy": 0.0979, "capacity_price": 19.4, "demand_price": 36.1},
            "1~10(20)千伏": {"single_price": 0.1708, "two_part_energy": 0.0727, "capacity_price": 16.3, "demand_price": 31.0},
            "35~110千伏":  {"single_price": 0.1282, "two_part_energy": 0.0449, "capacity_price": 16.3, "demand_price": 26.1},
            "220千伏及以上": {"single_price": 0.0913, "two_part_energy": None,   "capacity_price": None, "demand_price": 22.6},
        },
        "avg_load_rate": 0.75,
        "line_loss_rate": 3.31,
    },
    "深圳": {
        "voltage_levels": {
            "10千伏高供高计":    {"single_price": 0.1804, "two_part_energy": 0.1304, "capacity_price": 22.0, "demand_price": 46.0},
            "10千伏高供低计":    {"single_price": 0.2054, "two_part_energy": 0.1554, "capacity_price": 32.0, "demand_price": 42.0},
            "20千伏":            {"single_price": 0.1744, "two_part_energy": 0.1244, "capacity_price": 22.0, "demand_price": 46.0},
            "110千伏":           {"single_price": 0.1554, "two_part_energy": 0.1054, "capacity_price": 22.0, "demand_price": 46.0},
            "220千伏及以上":     {"single_price": 0.1304, "two_part_energy": 0.0804, "capacity_price": 22.0, "demand_price": 46.0},
        },
        "avg_load_rate": 0.75,
        "line_loss_rate": 2.11,
    },
    "广西": {
        "voltage_levels": {
            "不满1千伏":  {"single_price": 0.2606, "two_part_energy": 0.1476, "capacity_price": 24.2, "demand_price": 38.7},
            "1~10(20)千伏": {"single_price": 0.2471, "two_part_energy": 0.1054, "capacity_price": 23.3, "demand_price": 37.3},
            "35千伏":     {"single_price": 0.2296, "two_part_energy": 0.0777, "capacity_price": 21.4, "demand_price": 34.2},
            "110千伏及以上": {"single_price": 0.1199, "two_part_energy": 0.0293, "capacity_price": 20.0, "demand_price": 32.0},
        },
        "avg_load_rate": 0.75,
        "line_loss_rate": 4.67,
    },
    "海南": {
        "voltage_levels": {
            "不满1千伏":  {"single_price": 0.2553, "two_part_energy": 0.1348, "capacity_price": 26.0, "demand_price": 41.6},
            "1~10(20)千伏": {"single_price": 0.2324, "two_part_energy": 0.1180, "capacity_price": 24.0, "demand_price": 38.4},
            "110千伏":    {"single_price": 0.2103, "two_part_energy": 0.0993, "capacity_price": 22.0, "demand_price": 35.2},
            "220千伏及以上": {"single_price": 0.1893, "two_part_energy": 0.0702, "capacity_price": 20.0, "demand_price": 32.0},
        },
        "avg_load_rate": 0.75,
        "line_loss_rate": 5.37,
    },
    "重庆": {
        "voltage_levels": {
            "不满1千伏":  {"single_price": 0.2352, "two_part_energy": 0.1515, "capacity_price": 22.0, "demand_price": 35.2},
            "1~10(20)千伏": {"single_price": 0.2149, "two_part_energy": 0.1256, "capacity_price": 22.0, "demand_price": 35.2},
            "35千伏":     {"single_price": 0.1948, "two_part_energy": 0.1062, "capacity_price": 20.0, "demand_price": 32.0},
            "110千伏":    {"single_price": 0.1796, "two_part_energy": 0.0868, "capacity_price": 20.0, "demand_price": 32.0},
        },
        "avg_load_rate": 0.75,
        "line_loss_rate": 4.18,
    },
    "四川": {
        "voltage_levels": {
            "不满1千伏":  {"single_price": 0.2563, "two_part_energy": 0.1391, "capacity_price": 22.0, "demand_price": 35.0},
            "1~10(20)千伏": {"single_price": 0.2299, "two_part_energy": 0.1125, "capacity_price": 19.0, "demand_price": 30.0},
            "35千伏":     {"single_price": 0.1992, "two_part_energy": 0.0644, "capacity_price": 17.0, "demand_price": 27.0},
            "110千伏":    {"single_price": 0.1126, "two_part_energy": 0.0466, "capacity_price": 15.0, "demand_price": 24.0},
            "220千伏及以上": {"single_price": 0.0934, "two_part_energy": None,   "capacity_price": None, "demand_price": None},
        },
        "avg_load_rate": 0.75,
        "line_loss_rate": 5.64,
    },
    "贵州": {
        "voltage_levels": {
            "不满1千伏":  {"single_price": 0.2154, "two_part_energy": 0.1238, "capacity_price": 21.9, "demand_price": 35.0},
            "110千伏":    {"single_price": 0.1763, "two_part_energy": 0.0720, "capacity_price": 19.4, "demand_price": 31.0},
            "220千伏及以上": {"single_price": 0.1458, "two_part_energy": 0.0468, "capacity_price": 18.8, "demand_price": 30.0},
        },
        "avg_load_rate": 0.75,
        "line_loss_rate": 4.50,
    },
    "云南": {
        "voltage_levels": {
            "不满1千伏":  {"single_price": 0.1620, "two_part_energy": 0.1246, "capacity_price": 23.5, "demand_price": 37.6},
            "1~10(20)千伏": {"single_price": 0.1520, "two_part_energy": 0.0995, "capacity_price": 23.5, "demand_price": 37.6},
            "35千伏":     {"single_price": 0.1420, "two_part_energy": 0.0683, "capacity_price": 22.5, "demand_price": 36.0},
            "110千伏":    {"single_price": 0.1305, "two_part_energy": 0.0475, "capacity_price": 22.5, "demand_price": 36.0},
        },
        "avg_load_rate": 0.75,
        "line_loss_rate": 4.24,
    },
    "陕西（不含榆林）": {
        "voltage_levels": {
            "不满1千伏":  {"single_price": 0.2297, "two_part_energy": 0.1271, "capacity_price": 23.5, "demand_price": 37.6},
            "1~10(20)千伏": {"single_price": 0.2082, "two_part_energy": 0.1061, "capacity_price": 23.5, "demand_price": 37.6},
            "35千伏":     {"single_price": 0.1867, "two_part_energy": 0.0861, "capacity_price": 20.5, "demand_price": 32.8},
            "110千伏及以上": {"single_price": 0.1602, "two_part_energy": 0.0731, "capacity_price": 20.5, "demand_price": 32.8},
        },
        "avg_load_rate": 0.75,
        "line_loss_rate": 4.24,
    },
    "甘肃": {
        "voltage_levels": {
            "不满1千伏":  {"single_price": 0.2945, "two_part_energy": 0.1063, "capacity_price": 24.0, "demand_price": 38.4},
            "1~10(20)千伏": {"single_price": 0.2745, "two_part_energy": 0.0923, "capacity_price": 23.0, "demand_price": 36.8},
            "35千伏":     {"single_price": 0.2545, "two_part_energy": 0.0799, "capacity_price": 20.5, "demand_price": 32.8},
            "110千伏及以上": {"single_price": 0.1251, "two_part_energy": 0.0693, "capacity_price": 20.5, "demand_price": 32.8},
        },
        "avg_load_rate": 0.75,
        "line_loss_rate": 2.31,
    },
    "青海": {
        "voltage_levels": {
            "不满1千伏":  {"single_price": 0.1926, "two_part_energy": 0.0871, "capacity_price": 22.0, "demand_price": 35.2},
            "1~10(20)千伏": {"single_price": 0.1866, "two_part_energy": 0.0811, "capacity_price": 21.0, "demand_price": 33.6},
            "35千伏":     {"single_price": 0.1806, "two_part_energy": 0.0711, "capacity_price": 20.5, "demand_price": 32.8},
            "110千伏及以上": {"single_price": 0.1133, "two_part_energy": 0.0600, "capacity_price": 19.5, "demand_price": 31.2},
        },
        "avg_load_rate": 0.75,
        "line_loss_rate": 2.90,
    },
    "宁夏": {
        "voltage_levels": {
            "不满1千伏":  {"single_price": 0.1841, "two_part_energy": 0.0903, "capacity_price": 18.0, "demand_price": 28.8},
            "1~10(20)千伏": {"single_price": 0.1631, "two_part_energy": 0.0749, "capacity_price": 18.0, "demand_price": 28.8},
            "35千伏":     {"single_price": 0.1431, "two_part_energy": 0.0567, "capacity_price": 16.0, "demand_price": 25.6},
            "110千伏及以上": {"single_price": 0.1034, "two_part_energy": 0.0491, "capacity_price": 16.0, "demand_price": 25.6},
        },
        "avg_load_rate": 0.75,
        "line_loss_rate": 2.58,
    },
    "新疆": {
        "voltage_levels": {
            "不满1千伏":  {"single_price": 0.1636, "two_part_energy": 0.1202, "capacity_price": 20.0, "demand_price": 32.0},
            "1~10(20)千伏": {"single_price": 0.1606, "two_part_energy": 0.1098, "capacity_price": 20.0, "demand_price": 32.0},
            "35千伏":     {"single_price": 0.1566, "two_part_energy": 0.0808, "capacity_price": 19.0, "demand_price": 30.4},
            "110千伏及以上": {"single_price": 0.1221, "two_part_energy": 0.0485, "capacity_price": 19.0, "demand_price": 30.4},
        },
        "avg_load_rate": 0.75,
        "line_loss_rate": 3.45,
    },
}

# 省份列表（供 UI 下拉框使用）
PROVINCES = list(TARIFF_DATA.keys())