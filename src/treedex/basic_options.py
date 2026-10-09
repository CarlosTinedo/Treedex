"""Options for the table-backed line, area, bar, and funnel builders."""

from copy import deepcopy
import inspect
import json
import math
from numbers import Real

import pandas as pd
import plotly.express as px

BASIC_PLOT_TYPES = ("line", "area", "bar", "funnel")
PARAMETERS = {
    kind: {name: param.default for name, param in inspect.signature(getattr(px, kind)).parameters.items()
           if name != "data_frame"}
    for kind in BASIC_PLOT_TYPES
}
COLUMNS = {
    "color", "line_group", "line_dash", "symbol", "pattern_shape", "hover_name", "text",
    "facet_row", "facet_col", "animation_frame", "animation_group", "base", "sort_by",
    "error_x", "error_x_minus", "error_y", "error_y_minus",
}
MULTI_COLUMNS = {"x", "y", "hover_data", "custom_data"}
BOOLS = {"markers", "log_x", "log_y", "sort_descending"}
NUMBERS = {
    "facet_col_wrap": {"min": 0, "step": 1},
    "facet_row_spacing": {"min": 0, "max": 1, "step": 0.01},
    "facet_col_spacing": {"min": 0, "max": 1, "step": 0.01},
    "opacity": {"min": 0, "max": 1, "step": 0.05},
    "color_continuous_midpoint": {},
    "width": {"min": 10, "step": 1}, "height": {"min": 10, "step": 1},
}
CHOICES = {
    "orientation": [("Auto", ""), ("Vertical", "v"), ("Horizontal", "h")],
    "line_shape": [(name, name) for name in ("linear", "spline", "hv", "vh", "hvh", "vhv")],
    "render_mode": [(name, name) for name in ("auto", "svg", "webgl")],
    "barmode": [(name, name) for name in ("relative", "group", "overlay")],
    "groupnorm": [("None", ""), ("Fraction", "fraction"), ("Percent", "percent")],
}
JSON_TYPES = {
    "category_orders": dict, "labels": dict, "hover_data_format": dict,
    "color_discrete_sequence": list, "color_discrete_map": dict,
    "line_dash_sequence": list, "line_dash_map": dict,
    "symbol_sequence": list, "symbol_map": dict,
    "pattern_shape_sequence": list, "pattern_shape_map": dict,
    "range_x": list, "range_y": list, "range_color": list,
}
LABELS = {
    "x": "X axis", "y": "Y axis", "color": "Color by", "line_group": "Group lines by",
    "line_dash": "Dash by", "symbol": "Symbol by", "pattern_shape": "Pattern by",
    "hover_name": "Hover title", "hover_data": "Extra hover data", "text": "Text labels",
    "base": "Bar base", "markers": "Show markers", "sort_by": "Sort rows by",
    "sort_descending": "Descending order", "facet_row": "Facet rows", "facet_col": "Facet columns",
    "error_x": "X error +", "error_x_minus": "X error −", "error_y": "Y error +", "error_y_minus": "Y error −",
    "color_discrete_palette": "Discrete palette", "color_discrete_sequence": "Custom colors",
    "color_discrete_map": "Color map", "color_continuous_scale": "Continuous scale",
    "color_continuous_midpoint": "Color midpoint", "text_auto": "Automatic text",
    "width": "Width (px)", "height": "Height (px)", "groupnorm": "Stack normalization",
}
# Controls are packed into balanced pages with at most eleven fields plus Build.
FIELD_ORDER = (
    "x y color line_group line_dash symbol pattern_shape text hover_name hover_data custom_data "
    "title subtitle template markers sort_by sort_descending "
    "facet_row facet_col facet_col_wrap facet_row_spacing facet_col_spacing "
    "error_x error_x_minus error_y error_y_minus animation_frame animation_group "
    "color_discrete_palette color_discrete_sequence color_discrete_map "
    "color_continuous_scale range_color color_continuous_midpoint "
    "line_dash_sequence line_dash_map symbol_sequence symbol_map pattern_shape_sequence pattern_shape_map "
    "opacity line_shape render_mode groupnorm barmode base text_auto "
    "orientation log_x log_y range_x range_y category_orders labels hover_data_format width height"
).split()


def default_basic_options(kind):
    options = deepcopy(PARAMETERS[kind])
    options.update(title=f"{kind.title()} plot", template="plotly_white", hover_data=[], custom_data=[],
                   hover_data_format=None, color_discrete_palette="Plotly")
    if kind in ("line", "area"):
        options.update(sort_by=None, sort_descending=False)
    return options


def option_pages(kind):
    available = default_basic_options(kind)
    fields = [name for name in FIELD_ORDER if name in available]
    page_count = math.ceil(len(fields) / 11)
    page_size, extra = divmod(len(fields), page_count)
    pages = []
    start = 0
    for page in range(page_count):
        end = start + page_size + (page < extra)
        pages.append(fields[start:end])
        start = end
    return pages


def normalize_basic_options(kind, stored, frame):
    options = default_basic_options(kind)
    options.update({key: value for key, value in (stored or {}).items() if key in options})
    for name in COLUMNS & options.keys():
        if options[name] not in frame.columns:
            options[name] = None
    numeric = list(frame.select_dtypes(include="number").columns)
    columns = list(frame.columns)
    for name in MULTI_COLUMNS:
        value = options.get(name) or []
        if not isinstance(value, list):
            value = [value]
        options[name] = [col for col in value if col in columns]
    default_x = "X" if "X" in frame else ("Species" if "Species" in frame else next(iter(columns), None))
    default_y = "Y" if "Y" in numeric else next(iter(numeric), None)
    if kind == "funnel":
        default_x, default_y = default_y, default_x
    for name, default in (("x", default_x), ("y", default_y)):
        # Preserve an explicitly cleared axis so validation can explain it.
        if not options[name] and (stored or {}).get(name) != [] and default is not None:
            options[name] = [default]
    if options.get("hover_name") is None and "Species" in frame:
        options["hover_name"] = "Species"
    return options


def basic_kwargs(kind, options):
    kwargs = {name: deepcopy(options.get(name, default)) for name, default in PARAMETERS[kind].items()}
    for name in JSON_TYPES.keys() & (kwargs.keys() | {"hover_data_format"}):
        value = options.get(name)
        if value is None or value == "":
            value = None
        elif name.endswith("_map") and value == "identity":
            pass
        else:
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except ValueError as exc:
                    raise ValueError(f"{name.replace('_', ' ').capitalize()} must be valid JSON.") from exc
            if not isinstance(value, JSON_TYPES[name]):
                raise ValueError(f"{name.replace('_', ' ').capitalize()} must be a JSON {'array' if JSON_TYPES[name] is list else 'object'}.")
            if isinstance(value, list) and not value:
                raise ValueError(f"{name.replace('_', ' ').capitalize()} cannot be an empty array.")
        kwargs[name] = value
    hover_format = kwargs.pop("hover_data_format", None)
    if hover_format is not None:
        if not all(isinstance(value, (bool, str)) for value in hover_format.values()):
            raise ValueError("Hover formats must map columns to true, false, or format strings.")
        kwargs["hover_data"] = {**{col: True for col in (kwargs.get("hover_data") or [])}, **hover_format}
    else:
        kwargs["hover_data"] = kwargs.get("hover_data") or None
    for name in ("x", "y"):
        value = kwargs.get(name)
        if isinstance(value, list) and len(value) == 1:
            kwargs[name] = value[0]
    if kwargs.get("color_discrete_sequence") is None:
        kwargs["color_discrete_sequence"] = getattr(px.colors.qualitative, options.get("color_discrete_palette") or "Plotly")
    if "text_auto" in kwargs and isinstance(kwargs["text_auto"], str):
        if kwargs["text_auto"].lower() in ("true", "false", ""):
            kwargs["text_auto"] = kwargs["text_auto"].lower() == "true"
    if "text_auto" in kwargs and kwargs["text_auto"] is None:
        kwargs["text_auto"] = False
    kwargs["facet_col_wrap"] = kwargs.get("facet_col_wrap") or 0
    for name in BOOLS & kwargs.keys():
        kwargs[name] = bool(kwargs[name])
    kwargs["custom_data"] = kwargs.get("custom_data") or None
    return kwargs


def validate_basic_options(kind, options, frame):
    errors = []
    if frame.empty:
        errors.append("The current data contains no rows.")
    for axis in ("x", "y"):
        if not options.get(axis):
            errors.append(f"Choose at least one {axis.upper()} column.")
    if len(options.get("x") or []) > 1 and len(options.get("y") or []) > 1:
        errors.append("Choose multiple columns on only one axis at a time.")
    for name, bounds in NUMBERS.items():
        value = options.get(name)
        if value is None:
            continue
        if not isinstance(value, Real) or not math.isfinite(value):
            errors.append(f"{name.replace('_', ' ').capitalize()} must be a finite number.")
        elif ("min" in bounds and value < bounds["min"]) or ("max" in bounds and value > bounds["max"]):
            errors.append(f"{name.replace('_', ' ').capitalize()} is outside the allowed range ({bounds.get('min', 'no minimum')}–{bounds.get('max', 'no maximum')}).")
        elif bounds.get("step") == 1 and int(value) != value:
            errors.append(f"{name.replace('_', ' ').capitalize()} must be a whole number.")
    if options.get("facet_row") and options.get("facet_col_wrap"):
        errors.append("Facet column wrap cannot be used together with row facets.")
    if options.get("animation_group") and not options.get("animation_frame"):
        errors.append("Animation group requires an animation frame column.")
    for axis in ("x", "y"):
        positive, negative = f"error_{axis}", f"error_{axis}_minus"
        if options.get(negative) and not options.get(positive):
            errors.append(f"Negative {axis.upper()} errors require the positive error column.")
        for name in (positive, negative):
            col = options.get(name)
            if col in frame:
                values = pd.to_numeric(frame[col], errors="coerce")
                if not values.map(lambda value: pd.notna(value) and math.isfinite(value) and value >= 0).all():
                    errors.append(f"{name.replace('_', ' ').capitalize()} needs finite, nonnegative values.")
        if options.get(f"log_{axis}"):
            for col in options.get(axis) or []:
                values = pd.to_numeric(frame[col], errors="coerce")
                if values.isna().any() or values.le(0).any():
                    errors.append(f"Log {axis.upper()} requires positive numeric values.")
                    break
    try:
        kwargs = basic_kwargs(kind, options)
        for name in ("range_x", "range_y", "range_color"):
            value = kwargs.get(name)
            if value is not None:
                if len(value) != 2 or any(isinstance(v, (list, dict)) or v is None for v in value):
                    errors.append(f"{name.replace('_', ' ').capitalize()} needs two endpoints.")
                elif all(isinstance(v, Real) for v in value) and (not all(math.isfinite(v) for v in value) or value[0] >= value[1]):
                    errors.append(f"{name.replace('_', ' ').capitalize()} needs a finite minimum smaller than its maximum.")
        for name in ("category_orders", "labels"):
            mapping = kwargs.get(name) or {}
            unknown = set(mapping) - set(frame.columns) - {"variable", "value"}
            if unknown:
                errors.append(f"{name.replace('_', ' ').capitalize()} contains unknown columns: {', '.join(sorted(unknown))}.")
            expected = list if name == "category_orders" else str
            if not all(isinstance(value, expected) for value in mapping.values()):
                errors.append(f"{name.replace('_', ' ').capitalize()} has invalid values.")
        if isinstance(kwargs.get("hover_data"), dict) and set(kwargs["hover_data"]) - set(frame.columns):
            errors.append("Hover formats contain unknown columns.")
    except (ValueError, TypeError, AttributeError) as exc:
        errors.append(str(exc))
    return errors
