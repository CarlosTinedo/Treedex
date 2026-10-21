"""Hierarchy menus using the shared Basics layout and styling."""

from ..hierarchy_options import CHOICES, COLUMNS, JSON_TYPES, LABELS, MULTI_COLUMNS, NUMBERS, option_pages
from .basic_options import PLACEHOLDERS, plot_options_menu


def hierarchy_options_menu(kind, options, frame, page=1):
    nodes = options.get("hierarchy_mode") == "nodes"
    return plot_options_menu(
        kind, options, frame, option_pages(kind), page, prefix="hierarchy",
        columns_fields=COLUMNS, multi_fields=MULTI_COLUMNS, bool_fields=set(), number_fields=NUMBERS,
        choices_fields=CHOICES, json_fields=JSON_TYPES, labels=LABELS,
        placeholders={**PLACEHOLDERS, "values": "Count rows", "root_label": "No extra root", "maxdepth": "All levels (-1)"},
        numeric_fields={"values"}, disabled_fields={"path", "root_label"} if nodes else {"names", "ids", "parents"},
        hints={"path": "Select columns from root to leaves, e.g. Order, Family, Species. Remove and reselect to change the order.",
               "values": "Leave empty to count rows. Node rows with total parent values need explicit totals.",
               "parents": "References the Node IDs column, or Node names when IDs are omitted. Empty means a root.",
               "maxdepth": "-1 shows all hierarchy levels; a positive number limits the visible depth."},
    )
