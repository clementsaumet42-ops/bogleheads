"""Package UI — helpers de présentation pour la webapp Streamlit."""

from src.ui.charts import camembert_allocation, fan_chart_mc, heatmap_asset_location
from src.ui.components import (
    bouton_principal,
    bouton_secondaire,
    icone_lucide,
    kpi_card,
    lettrine,
    monogramme_html,
    panneau_avertissement,
    section,
    tableau_elegant,
    titre_page,
)
from src.ui.formatters import format_euro, format_kpi, format_pct, format_ratio_sharpe
from src.ui.theme import injecter_css

__all__ = [
    # formatters
    "format_euro",
    "format_pct",
    "format_kpi",
    "format_ratio_sharpe",
    # charts
    "camembert_allocation",
    "fan_chart_mc",
    "heatmap_asset_location",
    # theme
    "injecter_css",
    # components
    "titre_page",
    "kpi_card",
    "tableau_elegant",
    "bouton_principal",
    "bouton_secondaire",
    "panneau_avertissement",
    "section",
    "icone_lucide",
    "lettrine",
    "monogramme_html",
]
