"""Normalization and validation for the dashboard scatter controls."""

from __future__ import annotations

from copy import deepcopy

import pandas as pd


DEFAULT_SCATTER_OPTIONS = {
    "x": None, "y": None, "color": None, "symbol": None, "size": None,
    "text": None, "hover_name": "Species", "hover_data": [],
    "facet_row": None, "facet_col": None, "facet_col_wrap": 0,
    "facet_row_spacing": None, "facet_col_spacing": None,
    "error_x": None, "error_x_minus": None, "error_y": None,
    "error_y_minus": None, "animation_frame": None, "animation_group": None,
    "opacity": 1.0, "size_max": 28, "color_discrete_palette": "Plotly",
    "color_continuous_scale": "Viridis", "range_color_min": None,
    "range_color_max": None, "color_continuous_midpoint": None,
    "marginal_x": None, "marginal_y": None, "render_mode": "auto",
    "log_x": False, "log_y": False, "range_x_min": None,
    "range_x_max": None, "range_y_min": None, "range_y_max": None,
    "orientation": None, "trendline": None, "trendline_scope": "trace",
    "trendline_color_override": None, "title": "Scatter plot", "subtitle": None,
    "template": "plotly_white",
}

COLUMN_OPTIONS = {
    "x", "y", "color", "symbol", "size", "text", "hover_name",
    "facet_row", "facet_col", "error_x", "error_x_minus", "error_y",
    "error_y_minus", "animation_frame", "animation_group",
}


def normalize_scatter_options(options, frame: pd.DataFrame):
    """Return stored options made safe for the current data frame."""
    normalized = deepcopy(DEFAULT_SCATTER_OPTIONS)
    normalized.update({
        key: value for key, value in (options or {}).items() if key in normalized
    })
    columns = set(frame.columns)
    numeric = set(frame.select_dtypes(include="number").columns)
    nonnegative = {
        column for column in numeric
        if not pd.to_numeric(frame[column], errors="coerce").dropna().empty
        and pd.to_numeric(frame[column], errors="coerce").dropna().ge(0).all()
        and pd.to_numeric(frame[column], errors="coerce").dropna().gt(0).any()
    }
    for key in COLUMN_OPTIONS:
        if normalized.get(key) not in columns:
            normalized[key] = None
    for key in ("x", "y"):
        if normalized.get(key) not in numeric:
            normalized[key] = None
    for key in ("error_x", "error_x_minus", "error_y", "error_y_minus"):
        if normalized.get(key) not in nonnegative:
            normalized[key] = None
    if normalized.get("size") not in nonnegative:
        normalized["size"] = None
    normalized["hover_data"] = [
        column for column in (normalized.get("hover_data") or []) if column in columns
    ]
    numeric_columns = list(frame.select_dtypes(include="number").columns)
    if normalized["x"] is None and numeric_columns:
        normalized["x"] = "X" if "X" in numeric else numeric_columns[0]
    if normalized["y"] is None and numeric_columns:
        normalized["y"] = "Y" if "Y" in numeric else numeric_columns[min(1, len(numeric_columns) - 1)]
    if normalized["hover_name"] is None and "Species" in columns:
        normalized["hover_name"] = "Species"
    return normalized


def validate_scatter_options(options, frame: pd.DataFrame):
    """Return user-facing validation errors for a normalized configuration."""
    errors = []
    if not options.get("x") or not options.get("y"):
        errors.append("Choose numeric X and Y columns.")
    for key, label in (("opacity", "Opacity"),):
        value = options.get(key)
        if value is None or not 0 <= value <= 1:
            errors.append(f"{label} must be between 0 and 1.")
    if options.get("size_max") is None or options["size_max"] <= 0:
        errors.append("Maximum marker size must be greater than 0.")
    for key, label in (
        ("facet_row_spacing", "Facet row spacing"),
        ("facet_col_spacing", "Facet column spacing"),
    ):
        value = options.get(key)
        if value is not None and not 0 <= value <= 1:
            errors.append(f"{label} must be between 0 and 1.")
    if options.get("facet_col_wrap", 0) < 0:
        errors.append("Facet column wrap cannot be negative.")
    for low, high, label in (
        ("range_x_min", "range_x_max", "X-axis range"),
        ("range_y_min", "range_y_max", "Y-axis range"),
        ("range_color_min", "range_color_max", "Color range"),
    ):
        minimum, maximum = options.get(low), options.get(high)
        if (minimum is None) != (maximum is None):
            errors.append(f"{label} needs both minimum and maximum values.")
        elif minimum is not None and minimum >= maximum:
            errors.append(f"{label} minimum must be less than its maximum.")
    for axis, key in (("X", "x"), ("Y", "y")):
        if options.get(f"log_{axis.lower()}") and options.get(key) in frame:
            values = pd.to_numeric(frame[options[key]], errors="coerce").dropna()
            if not values.empty and values.le(0).any():
                errors.append(f"{axis}-axis log scale requires positive values.")
    if options.get("facet_row") and options.get("facet_col_wrap"):
        errors.append("Facet column wrap cannot be used together with row facets.")
    if (options.get("marginal_x") or options.get("marginal_y")) and options.get("facet_col_wrap"):
        errors.append("Marginal plots cannot be combined with facet column wrapping.")
    for minus, positive, label in (
        ("error_x_minus", "error_x", "Negative X errors"),
        ("error_y_minus", "error_y", "Negative Y errors"),
    ):
        if options.get(minus) and not options.get(positive):
            errors.append(f"{label} require the corresponding positive error column.")
    if options.get("animation_group") and not options.get("animation_frame"):
        errors.append("Animation group requires an animation frame column.")
    return errors


def pair(options, minimum, maximum):
    """Return a Plotly range pair only when both values are present."""
    if options.get(minimum) is None or options.get(maximum) is None:
        return None
    return [options[minimum], options[maximum]]
