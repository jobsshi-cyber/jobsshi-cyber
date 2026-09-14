"""
基于1192号文的输配电费计算器
"""


def calc_monthly_tariff_fee(
    province: str,
    voltage_level: str,
    tariff_mode: str,              # "single"（单一制）或 "two_part"（两部制）
    access_capacity: float,         # 接入公共电网容量（kVA 或 kW）
    avg_load_rate: float = None,    # 平均负荷率，None 则用省份默认估算值
    grid_energy_kwh: float = 0.0,   # 月度下网电量（kWh）
):
    """
    计算月度输配电费（元）

    参数：
        province:        省份名称
        voltage_level:   电压等级
        tariff_mode:     "single" 或 "two_part"
        access_capacity: 接入容量（kVA）
        avg_load_rate:   平均负荷率（0~1），None 则用省份默认值
        grid_energy_kwh: 月度下网电量（kWh），用于计算线损费用

    返回：
        dict，含各项费用明细
    """
    from .tariff_data import TARIFF_DATA

    if province not in TARIFF_DATA:
        raise ValueError(f"未找到省份 [{province}] 的电价数据")

    province_data = TARIFF_DATA[province]
    if voltage_level not in province_data["voltage_levels"]:
        raise ValueError(f"省份 [{province}] 不支持电压等级 [{voltage_level}]")

    v_data = province_data["voltage_levels"][voltage_level]

    # 若未指定平均负荷率，用省份默认估算值
    if avg_load_rate is None:
        avg_load_rate = province_data.get("avg_load_rate", 0.75)

    line_loss_rate = province_data.get("line_loss_rate", 0.0) / 100.0

    # ---- 1. 现行容（需）量电费 ----
    # 两部制：按容量电价（元/千伏安·月）× 接入容量（kVA）
    if tariff_mode == "two_part":
        cap_price = v_data.get("capacity_price")
        if cap_price is None:
            raise ValueError(f"省份 [{province}] 电压等级 [{voltage_level}] 不支持两部制")
        current_capacity_fee = cap_price * access_capacity # 1. 现行容（需）量电费 = 容量电价 × 接入容量

    else:
        # 单一制：无容（需）量电费
        current_capacity_fee = 0.0

    # ---- 2. 1192号文新增：电量电价折算部分 ----
    # 所在电压等级电量电价标准 × 平均负荷率 × 730 × 接入容量
    energy_price = v_data.get("two_part_energy") or v_data.get("single_price")
    if energy_price is None:
        energy_price = 0.0

    added_fee = energy_price * avg_load_rate * 730 * access_capacity

    # ---- 3. 线损费用（按下网电量） ----
    line_loss_fee = grid_energy_kwh * line_loss_rate * energy_price if energy_price else 0.0

    # ---- 4. 合计 ----
    total = current_capacity_fee + added_fee + line_loss_fee

    return {
        "current_capacity_fee": current_capacity_fee,   # 现行容（需）量电费（元/月）
        "added_fee": added_fee,                          # 1192号文新增部分（元/月）
        "line_loss_fee": line_loss_fee,                  # 线损费用（元/月）
        "total_monthly": total,                          # 月度合计（元/月）
        "total_annual": total * 12,                      # 年度合计（元/年）
        "energy_price_used": energy_price,               # 使用的电量电价（元/kWh）
        "avg_load_rate_used": avg_load_rate,             # 使用的平均负荷率
        "capacity_price_used": v_data.get("capacity_price") if tariff_mode == "two_part" else None,
    }

import math


def calc_annual_tariff_fee(
    province: str,
    voltage_level: str,
    tariff_mode: str,               # "single" / "two_part" / "single_capacity_1192"
    access_capacity_kva: float,     # 报装容量（kVA）
    avg_load_rate: float,           # 平均负荷率
    grid_energy_kwh: float,         # 年下网电量（kWh）
):
    """
    计算年度输配电费（元/年）

    - single:                电度输配电价（单一制）× 下网电量
    - two_part:              电度输配电价（两部制）× 下网电量
                             + 容量输配电价 × 报装容量 × 12
    - single_capacity_1192:  电度输配电价（两部制）× 平均负荷率 × 730 × 报装容量 × 12
                             + 容量输配电价 × 报装容量 × 12
    """
    from .tariff_data import TARIFF_DATA

    if province not in TARIFF_DATA:
        raise ValueError(f"未找到省份 [{province}] 的电价数据")
    province_data = TARIFF_DATA[province]
    if voltage_level not in province_data["voltage_levels"]:
        raise ValueError(f"省份 [{province}] 不支持电压等级 [{voltage_level}]")

    v_data = province_data["voltage_levels"][voltage_level]

    energy_price_single   = v_data.get("single_price") or 0.0
    energy_price_two_part = v_data.get("two_part_energy") or 0.0
    capacity_price        = v_data.get("capacity_price") or 0.0

    if tariff_mode == "single":
        # 单一制：只按下网电量计电度电费
        energy_fee   = energy_price_single * grid_energy_kwh
        capacity_fee = 0.0
        added_fee    = 0.0

    elif tariff_mode == "two_part":
        # 两部制：电度 + 容量
        energy_fee   = energy_price_two_part * grid_energy_kwh
        capacity_fee = capacity_price * access_capacity_kva * 12
        added_fee    = 0.0

    elif tariff_mode == "single_capacity_1192":
        # 1192号文单一容量制
        # 电度电价折算部分：电量电价 × 平均负荷率 × 730h × 报装容量(kVA) × 12个月
        added_fee    = energy_price_two_part * avg_load_rate * 730 * access_capacity_kva * 12
        capacity_fee = capacity_price * access_capacity_kva * 12
        energy_fee   = 0.0

    else:
        raise ValueError(f"未知的 tariff_mode: {tariff_mode}")

    total = energy_fee + capacity_fee + added_fee

    return {
        "energy_fee":   energy_fee,      # 电度电费（元/年）
        "capacity_fee": capacity_fee,    # 容量电费（元/年）
        "added_fee":    added_fee,       # 1192号文新增部分（元/年）
        "total_annual": total,           # 合计（元/年）
    }


def calc_user_avg_price(
    self_use_kwh: float,            # 年自发自用电量（kWh）
    grid_buy_kwh: float,            # 年下网电量（kWh）
    price_self_use: float,          # 自发自用电价（元/kWh）
    price_buy: float,               # 公共电网购电电价（元/kWh）
    tariff_fee_annual: float,       # 年输配电费（元）
    system_op_fee_per_kwh: float,   # 系统运行费折价（元/kWh）
    gov_fund_per_kwh: float,        # 政府性基金及附加（元/kWh）
):
    """
    用户年平均电价（元/kWh）：

    年平均电价 = (年总电能量电费 + 输配电费 + 系统运行费) / 年总用电量 + 政府性基金

    其中：
        年总电能量电费 = 自发自用电费 + 外购电费
        自发自用电费  = 自发自用电量 × 自发自用电价
        外购电费      = 公共电网购电电价 × 下网电量
        系统运行费    = 系统运行费折价 × 下网电量（按1192号文要求按下网电量缴纳）
        年总用电量    = 自发自用电量 + 下网电量
    """
    total_load = self_use_kwh + grid_buy_kwh
    if total_load <= 0:
        return {
            "self_use_fee": 0.0, "grid_buy_fee": 0.0, "energy_fee": 0.0,
            "system_fee": 0.0, "tariff_fee": 0.0, "total_load": 0.0,
            "avg_price": 0.0,
        }

    self_use_fee = self_use_kwh * price_self_use
    grid_buy_fee = grid_buy_kwh * price_buy
    energy_fee   = self_use_fee + grid_buy_fee
    system_fee   = system_op_fee_per_kwh * grid_buy_kwh

    avg_price = (energy_fee + tariff_fee_annual + system_fee) / total_load + gov_fund_per_kwh

    return {
        "self_use_fee": self_use_fee,
        "grid_buy_fee": grid_buy_fee,
        "energy_fee":   energy_fee,
        "system_fee":   system_fee,
        "tariff_fee":   tariff_fee_annual,
        "total_load":   total_load,
        "avg_price":    avg_price,
    }