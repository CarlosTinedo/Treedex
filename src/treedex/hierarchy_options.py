"""Table-backed controls for sunburst, treemap, and icicle charts."""

from copy import deepcopy
import inspect
import json
import math
from numbers import Real

import pandas as pd
import plotly.express as px

HIERARCHY_PLOT_TYPES = ("sunburst", "treemap", "icicle")
PARAMETERS = {
    kind: {name: param.default for name, param in inspect.signature(getattr(px, kind)).parameters.items()
           if name != "data_frame"}
    for kind in HIERARCHY_PLOT_TYPES
}
COLUMNS = {"names", "values", "parents", "ids", "color", "hover_name"}
MULTI_COLUMNS = {"path", "hover_data", "custom_data"}
JSON_TYPES = {
    "color_discrete_sequence": list, "color_discrete_map": dict, "range_color": list,
    "labels": dict, "hover_data_format": dict,
}
NUMBERS = {
    "maxdepth": {"min": -1, "step": 1}, "color_continuous_midpoint": {},
    "width": {"min": 10, "step": 1}, "height": {"min": 10, "step": 1},
}
CHOICES = {
    "hierarchy_mode": [("Columns from root to leaves", "path"), ("Node and parent rows", "nodes")],
    "branchvalues": [("Total including children", "total"), ("Additional to children", "remainder")],
}
LABELS = {
    "hierarchy_mode": "Hierarchy source", "path": "Hierarchy levels (in order)",
    "values": "Sector values", "names": "Node names", "ids": "Node IDs", "parents": "Parent IDs",
    "root_label": "Root label", "color": "Color by", "hover_name": "Hover title",
    "hover_data": "Extra hover data", "custom_data": "Custom data", "maxdepth": "Visible depth",
    "branchvalues": "Parent values", "color_discrete_palette": "Discrete palette",
    "color_continuous_scale": "Continuous scale", "color_continuous_midpoint": "Color midpoint",
    "width": "Width (px)", "height": "Height (px)",
}
FIELD_ORDER = (
    "hierarchy_mode path values root_label names ids parents branchvalues maxdepth "
    "color hover_name hover_data custom_data hover_data_format title subtitle "
    "color_discrete_palette color_discrete_sequence color_discrete_map "
    "color_continuous_scale range_color color_continuous_midpoint labels template width height"
).split()


def default_hierarchy_options(kind):
    options = deepcopy(PARAMETERS[kind])
    options.update(hierarchy_mode="path", path=[], root_label="All species", branchvalues="total",
                   maxdepth=-1, title=f"{kind.title()} chart", template="plotly_white",
                   hover_data=[], custom_data=[], hover_data_format=None, color_discrete_palette="Plotly")
    return options


def option_pages(kind):
    fields = [name for name in FIELD_ORDER if name in default_hierarchy_options(kind)]
    page_count = math.ceil(len(fields) / 11)
    size, extra = divmod(len(fields), page_count)
    pages, start = [], 0
    for page in range(page_count):
        end = start + size + (page < extra)
        pages.append(fields[start:end])
        start = end
    return pages


def normalize_hierarchy_options(kind, stored, frame):
    options = default_hierarchy_options(kind)
    options.update({key: value for key, value in (stored or {}).items() if key in options})
    for name in COLUMNS:
        if options[name] not in frame.columns:
            options[name] = None
    for name in MULTI_COLUMNS:
        value = options[name] or []
        if not isinstance(value, list):
            value = [value]
        options[name] = list(dict.fromkeys(col for col in value if col in frame))
    if "path" not in (stored or {}) and len(frame.columns):
        options["path"] = ["Species" if "Species" in frame else frame.columns[0]]
    return options


def hierarchy_kwargs(kind, options):
    kwargs = {name: deepcopy(options.get(name, default)) for name, default in PARAMETERS[kind].items()}
    for name, expected in JSON_TYPES.items():
        value = options.get(name)
        if value is None or value == "":
            value = None
        elif name == "color_discrete_map" and value == "identity":
            pass
        else:
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except ValueError as exc:
                    raise ValueError(f"{name.replace('_', ' ').capitalize()} must be valid JSON.") from exc
            if not isinstance(value, expected):
                raise ValueError(f"{name.replace('_', ' ').capitalize()} must be a JSON {'array' if expected is list else 'object'}.")
        if name != "hover_data_format":
            kwargs[name] = value
        else:
            if value is not None and not all(isinstance(item, (bool, str)) for item in value.values()):
                raise ValueError("Hover formats must map columns to true, false, or format strings.")
            kwargs["hover_data"] = ({**{col: True for col in (options.get('hover_data') or [])}, **value}
                                   if value is not None else options.get("hover_data") or None)
    colors = kwargs.get("color_discrete_sequence")
    if colors is not None and (not colors or not all(isinstance(color, str) for color in colors)):
        raise ValueError("Custom colors must be a nonempty JSON array of CSS colors.")
    if colors is None:
        palette = getattr(px.colors.qualitative, options.get("color_discrete_palette") or "Plotly", None)
        if not isinstance(palette, list):
            raise ValueError("Choose an available discrete palette.")
        kwargs["color_discrete_sequence"] = palette
    mapping = kwargs.get("color_discrete_map")
    if isinstance(mapping, dict) and not all(isinstance(value, str) for value in mapping.values()):
        raise ValueError("Color map values must be CSS color strings.")
    if not all(isinstance(value, str) for value in (kwargs.get("labels") or {}).values()):
        raise ValueError("Label values must be strings.")
    kwargs["custom_data"] = kwargs.get("custom_data") or None
    if options.get("hierarchy_mode") == "nodes":
        kwargs["path"] = None
    else:
        kwargs.update(names=None, ids=None, parents=None)
        kwargs["path"] = ([px.Constant(options["root_label"])] if options.get("root_label") else []) + list(options.get("path") or [])
    return kwargs


def node_keys(options, frame):
    """Canonical string IDs and parent references for explicit node rows."""
    def key_text(value):
        if pd.isna(value):
            return ""
        # CSV null roots turn an integer parent column into floats (1 -> 1.0).
        if isinstance(value, Real) and math.isfinite(value) and int(value) == value:
            return str(int(value))
        return str(value)

    key = options.get("ids") or options["names"]
    ids = frame[key].map(key_text).tolist()
    parents = frame[options["parents"]].map(key_text).tolist()
    return ids, parents


def validate_hierarchy_options(kind, options, frame):
    errors = []
    if frame.empty:
        errors.append("The current data contains no rows.")
    mode = options.get("hierarchy_mode")
    if mode not in ("path", "nodes"):
        errors.append("Choose a hierarchy source.")
    if mode == "path":
        path = options.get("path") or []
        if not path:
            errors.append("Choose hierarchy columns in order, from root to leaves.")
        if options.get("branchvalues") != "total":
            errors.append("Column hierarchies require total parent values; use node rows for remainder values.")
        # Express joins levels with '/', so reject ambiguous labels before it merges nodes.
        for col in path:
            if frame[col].dropna().astype(str).str.contains("/", regex=False).any():
                errors.append("Hierarchy labels cannot contain '/' in column mode. Use node IDs and parent rows for these labels.")
                break
        if "/" in (options.get("root_label") or ""):
            errors.append("The root label cannot contain '/'.")
    if mode == "nodes":
        if not options.get("names") or not options.get("parents"):
            errors.append("Choose node names and a parent column. Root parents must be empty.")
        else:
            ids, parents = node_keys(options, frame)
            if any(not value for value in ids) or len(set(ids)) != len(ids):
                errors.append("Node IDs must be nonempty and unique. Choose an ID column when names repeat.")
            if frame[options["names"]].isna().any():
                errors.append("Node names cannot be missing.")
            if set(parents) - set(ids) - {""}:
                errors.append("Every parent ID must refer to a node in the table, or be empty for a root.")
            parent_by_id = dict(zip(ids, parents))
            done = set()
            for node in ids:
                seen = set()
                while node in parent_by_id and node not in done:
                    if node in seen:
                        errors.append("The hierarchy contains a cycle. A node cannot be its own ancestor.")
                        break
                    seen.add(node)
                    node = parent_by_id[node]
                done.update(seen)
                if errors and "cycle" in errors[-1]:
                    break
    value_col = options.get("values")
    values = None
    if value_col in frame:
        values = pd.to_numeric(frame[value_col], errors="coerce")
        if not values.map(lambda value: pd.notna(value) and math.isfinite(value) and value >= 0).all() or not values.gt(0).any():
            errors.append("Sector values must be finite, nonnegative numbers with at least one positive value.")
    if options.get("branchvalues") not in ("total", "remainder"):
        errors.append("Choose total or remainder parent values.")
    if mode == "nodes" and options.get("branchvalues") == "total" and not errors:
        ids, parents = node_keys(options, frame)
        weights = values.tolist() if values is not None else [1] * len(ids)
        totals = dict(zip(ids, weights))
        child_totals = {}
        for parent, weight in zip(parents, weights):
            if parent:
                child_totals[parent] = child_totals.get(parent, 0) + weight
        if any(weight > totals[parent] + max(1, abs(totals[parent])) * 1e-10 for parent, weight in child_totals.items()):
            errors.append("Total parent values must cover the sum of their immediate children. Supply totals or choose remainder values.")
    for name, bounds in NUMBERS.items():
        value = options.get(name)
        if value is None:
            continue
        if not isinstance(value, Real) or not math.isfinite(value):
            errors.append(f"{LABELS[name]} must be a finite number.")
        elif ("min" in bounds and value < bounds["min"]) or (bounds.get("step") == 1 and int(value) != value) or (name == "maxdepth" and value == 0):
            errors.append(f"{LABELS[name]} must be {'-1 (all levels) or a positive whole number' if name == 'maxdepth' else 'a whole number of at least 10'}.")
    try:
        kwargs = hierarchy_kwargs(kind, options)
        for name in ("labels", "hover_data"):
            if isinstance(kwargs.get(name), dict) and set(kwargs[name]) - set(frame.columns):
                errors.append(f"{name.replace('_', ' ').capitalize()} contains unknown columns.")
        color_range = kwargs.get("range_color")
        if color_range is not None and (len(color_range) != 2 or not all(isinstance(value, Real) and math.isfinite(value) for value in color_range) or color_range[0] >= color_range[1]):
            errors.append("Color range needs a finite minimum smaller than its maximum.")
    except (ValueError, TypeError, AttributeError) as exc:
        errors.append(str(exc))
    return errors
