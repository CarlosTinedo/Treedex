"""Plotly Express Basics figures with linked species selection."""

import plotly.express as px

from ..basic_options import basic_kwargs
from ..treedexcolors import sel_color


def make_basic_plot(kind, frame, selected_species=None, **options):
    kwargs = basic_kwargs(kind, options)
    # Keep Species first for the shared plot-click callback, even in wide mode.
    custom = list(kwargs.get("custom_data") or [])
    kwargs["custom_data"] = (["Species"] if "Species" in frame else []) + [col for col in custom if col != "Species"]
    if kind in ("line", "area") and options.get("sort_by"):
        frame = frame.sort_values(options["sort_by"], ascending=not options.get("sort_descending"), kind="stable")
    figure = getattr(px, kind)(data_frame=frame, **kwargs)
    selected = {str(name).casefold() for name in (selected_species or [])}
    traces = list(figure.data) + [trace for animation in figure.frames for trace in animation.data]
    for trace in traces:
        if not selected or trace.customdata is None or "Species" not in frame:
            continue
        chosen = [index for index, row in enumerate(trace.customdata) if str(row[0]).casefold() in selected]
        if trace.type in ("scatter", "scattergl", "bar"):
            if trace.type in ("scatter", "scattergl") and "markers" not in (trace.mode or ""):
                trace.mode = (trace.mode or "lines") + "+markers"
            trace.update(selectedpoints=chosen, selected={"marker": {"color": sel_color, "opacity": 1}},
                         unselected={"marker": {"opacity": 0.35}})
        elif trace.type == "funnel":
            count = len(trace.customdata)
            trace.marker.line.color = [sel_color if index in chosen else "rgba(0,0,0,0)" for index in range(count)]
            trace.marker.line.width = [3 if index in chosen else 0 for index in range(count)]
    return figure.update_layout(clickmode="event+select", uirevision=kind)
