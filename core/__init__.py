"""core 模块：算法核心，不依赖任何 UI 库"""
from .constants import get_default_params, get_parameter_schema
from .data_loader import load_8760_from_path, load_8760_from_file
from .simulation import simulate_8760, simulate_detailed_8760
from .financial import calc_irr, run_financial_evaluation
from .optimizer import (
    optimize_capacity_heuristic,
    optimize_capacity_pulp,
    optimize_capacity_debug,
)
from .charts import (
    make_resource_analysis_figure,
    make_daily_dispatch_figure,
)
from .exporter import (
    export_financial_tables_to_bytes,
    export_full_report_to_bytes,
)
from .tariff_data import TARIFF_DATA, PROVINCES
from .tariff_calculator import calc_monthly_tariff_fee

from .tariff_calculator import (
    calc_monthly_tariff_fee,
    calc_annual_tariff_fee,
    calc_user_avg_price,
)