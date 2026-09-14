"""参数默认值与 UI 无关的常量定义"""

def get_default_params():
    return {
        'spec_invest_pv':        3000.0,
        'spec_invest_wind':      4200.0,
        'spec_invest_bess_e':     450.0,
        'spec_invest_bess_p':     350.0,
        'construction_period':      1.0,
        'working_cap_spec':        30.0,
        'N_pv': 25, 'N_wind': 20, 'N_bess': 25,
        'bess_life': 10, 'wind_extend_spec': 450.0,
        # 涉网经济技术参数（新增）
        'price_buy': 0.45,
        'price_self_use': 0.30,
        'avg_load_rate': 0.65,
        'system_operation_fee': 0.094982,
        'gov_fund': 0.022925,
        # 储能技术指标
        'eta_ch': 0.95, 'eta_dis': 0.95,
        'soc_min': 0.10, 'soc_max': 0.90,
        # 财务与税费
        'r': 0.08, 'loan_interest_long': 0.035, 'equity_ratio': 0.20,
        'vat_rate': 0.13, 'urban_tax_rate': 0.05, 'edu_tax_rate': 0.05,
        'income_tax_rate': 0.25, 'surplus_reserve_rate': 0.10,
        'repair_rate': 0.005, 'insurance_rate': 0.0025,
        'staff_count': 10.0, 'avg_wage': 12.0, 'welfare_rate': 0.60,
        'material_cost_rate': 15.0, 'other_cost_rate': 20.0,
    }


def get_parameter_schema():
    return [
        # ---- 1. 投资单价与建设参数 ----
        ("1. 投资单价与建设参数", "1.1 光伏单位投资 (元/kW):",      "spec_invest_pv",        3000.0, float),
        ("1. 投资单价与建设参数", "1.2 风电单位投资 (元/kW):",      "spec_invest_wind",      4200.0, float),
        ("1. 投资单价与建设参数", "1.3 储能电芯容量单位投资 (元/kWh):", "spec_invest_bess_e",     450.0, float),
        ("1. 投资单价与建设参数", "1.4 储能 PCS 功率单位投资 (元/kW):", "spec_invest_bess_p",     350.0, float),
        ("1. 投资单价与建设参数", "1.5 建设期 (年):",               "construction_period",      1.0, float),
        ("1. 投资单价与建设参数", "1.6 流动资金单价 (元/kW):",      "working_cap_spec",        30.0, float),

        # ---- 2. 运行寿命参数 ----
        ("2. 运行寿命参数", "2.1 光伏组件运行寿命 (年):", "N_pv",  25, int),
        ("2. 运行寿命参数", "2.2 风电机组运行寿命 (年):", "N_wind", 20, int),
        ("2. 运行寿命参数", "2.3 储能系统运行寿命 (年):", "N_bess", 25, int),
        ("2. 运行寿命参数", "2.4 储能电芯寿命 (年):",     "bess_life", 10, int),
        ("2. 运行寿命参数", "2.5 风电20年延寿成本 (元/kW):", "wind_extend_spec", 450.0, float),

        # ---- 3. 涉网经济技术参数（新增）----
        ("3. 涉网经济技术参数", "3.1 公共电网购电电价 (元/kWh):",  "price_buy", 0.45, float),
        ("3. 涉网经济技术参数", "3.2 自发自用电价 (元/kWh):",      "price_self_use", 0.30, float),
        ("3. 涉网经济技术参数", "3.3 平均负荷率:",                  "avg_load_rate", 0.65, float),
        ("3. 涉网经济技术参数", "3.4 系统运行费折价 (元/kWh):",     "system_operation_fee", 0.094982, float),
        ("3. 涉网经济技术参数", "3.5 政府性基金及附加 (元/kWh):",  "gov_fund", 0.022925, float),

        # ---- 4. 储能技术指标（原 3，去掉电价）----
        ("4. 储能技术指标", "4.1 储能充电效率 eta_ch:",     "eta_ch", 0.95, float),
        ("4. 储能技术指标", "4.2 储能放电效率 eta_dis:",    "eta_dis", 0.95, float),
        ("4. 储能技术指标", "4.3 储能 SOC 下限 soc_min:",   "soc_min", 0.10, float),
        ("4. 储能技术指标", "4.4 储能 SOC 上限 soc_max:",   "soc_max", 0.90, float),

        # ---- 5. 财务与税费参数（原 4）----
        ("5. 财务与税费参数", "5.1 基准折现率 r (如 0.05):",       "r",  0.08, float),
        ("5. 财务与税费参数", "5.2 长期贷款利率 (如 0.042):",       "loan_interest_long", 0.035, float),
        ("5. 财务与税费参数", "5.3 资本金比例 (如 0.20):",          "equity_ratio", 0.20, float),
        ("5. 财务与税费参数", "5.4 增值税率 (如 0.13):",            "vat_rate", 0.13, float),
        ("5. 财务与税费参数", "5.5 城市维护建设税率 (占增值税):",    "urban_tax_rate", 0.05, float),
        ("5. 财务与税费参数", "5.6 教育费附加比例 (占增值税):",      "edu_tax_rate", 0.05, float),
        ("5. 财务与税费参数", "5.7 企业所得税率 (如 0.25):",        "income_tax_rate", 0.25, float),
        ("5. 财务与税费参数", "5.8 盈余公积金比例 (如 0.10):",      "surplus_reserve_rate", 0.10, float),
        ("5. 财务与税费参数", "5.9 年固定修理费率 (如 0.015):",     "repair_rate", 0.005, float),
        ("5. 财务与税费参数", "5.10 年保险费率 (如 0.0025):",       "insurance_rate", 0.0025, float),
        ("5. 财务与税费参数", "5.11 项目定员 (人):",                "staff_count", 10.0, float),
        ("5. 财务与税费参数", "5.12 人均年工资 (万元/人):",         "avg_wage", 12.0, float),
        ("5. 财务与税费参数", "5.13 福利费率 (如 0.60):",           "welfare_rate", 0.60, float),
        ("5. 财务与税费参数", "5.14 年材料费率 (元/kW):",           "material_cost_rate", 15.0, float),
        ("5. 财务与税费参数", "5.15 年其它费用率 (元/kW):",         "other_cost_rate", 20.0, float),
    ]