"""Hierarchy figures with species membership on every sector, including parents."""

import pandas as pd
import plotly.express as px

from ..hierarchy_options import hierarchy_kwargs, node_keys, validate_hierarchy_options
from ..treedexcolors import sel_color


def make_hierarchy_plot(kind, frame, selected_species=None, **options):
    errors = validate_hierarchy_options(kind, options, frame)
    if errors:
        raise ValueError(" ".join(errors))
    kwargs = hierarchy_kwargs(kind, options)
    frame = frame.copy()
    if kwargs.get("values"):
        frame[kwargs["values"]] = pd.to_numeric(frame[kwargs["values"]])
    # Plotly 6.5's hierarchy path calls .copy() on the documented identity mode.
    if kwargs.get("color_discrete_map") == "identity":
        color = kwargs.get("color")
        kwargs["color_discrete_map"] = {value: value for value in frame[color].dropna().unique()} if color else {}
    membership = {}

    def add(node, species):
        if pd.notna(species):
            membership.setdefault(node, {})[str(species)] = None

    if options.get("hierarchy_mode") == "nodes":
        ids, parents = node_keys(options, frame)
        if options.get("ids"):
            frame[options["ids"]] = ids
        else:
            frame[options["names"]] = ids
        frame[options["parents"]] = parents
        ancestors = dict(zip(ids, parents))
        for node, species in zip(ids, frame.get("Species", [None] * len(frame))):
            while node:
                add(node, species)
                node = ancestors.get(node, "")
    else:
        root = [options["root_label"]] if options.get("root_label") else []
        for _, row in frame.iterrows():
            levels = root + [str(row[col]) for col in options["path"] if pd.notna(row[col])]
            for depth in range(1, len(levels) + 1):
                add("/".join(levels[:depth]), row.get("Species"))
    # Membership comes from source rows: aggregated custom_data can contain '(?)'.
    figure = getattr(px, kind)(data_frame=frame, **kwargs)
    selected = {str(name).casefold() for name in (selected_species or [])}
    for trace in figure.data:
        node_ids = list(trace.ids) if trace.ids is not None else list(trace.labels)
        trace.meta = {"species_by_id": {str(node): list(membership.get(str(node), {})) for node in node_ids}}
        chosen = [any(name.casefold() in selected for name in membership.get(str(node), {})) for node in node_ids]
        trace.marker.line.color = [sel_color if value else "rgba(0,0,0,0)" for value in chosen]
        trace.marker.line.width = [3 if value else 0 for value in chosen]
    return figure.update_layout(clickmode="event", uirevision=kind)
