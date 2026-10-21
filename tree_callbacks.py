from dash import Input, Output, State, ctx, no_update

from ete4.dashview import make_tree_view_config, normalize_shape, tree_to_plotly


SHAPE_BUTTON_CLASS = "tree-shape-button"
SELECTED_SHAPE_BUTTON_CLASS = "tree-shape-button is-selected"


def register_tree_callbacks(app, tree):
    """Connect Treedex's tree controls to ETE's view configuration."""

    @app.callback(
        Output("tree-view-config", "data"),
        Input("tree-shape-rectangular", "n_clicks"),
        Input("tree-shape-circular", "n_clicks"),
        State("tree-view-config", "data"),
        prevent_initial_call=True,
    )
    def select_tree_shape(rectangular_clicks, circular_clicks, config):
        shape_by_button = {
            "tree-shape-rectangular": "rectangular",
            "tree-shape-circular": "circular",
        }
        shape = shape_by_button.get(ctx.triggered_id)
        if shape is None:
            return no_update

        updated_config = dict(config or {})
        updated_config.update(make_tree_view_config(shape))
        return updated_config

    @app.callback(
        Output("tree-graph", "figure"),
        Output("tree-shape-rectangular", "className"),
        Output("tree-shape-circular", "className"),
        Output("tree-shape-rectangular", "aria-pressed"),
        Output("tree-shape-circular", "aria-pressed"),
        Input("tree-view-config", "data"),
        Input("selected-species", "data"),
    )
    def render_tree_shape(config, selected_species):
        shape = normalize_shape((config or {}).get("shape"))
        rectangular_selected = shape == "rectangular"
        circular_selected = shape == "circular"

        figure = tree_to_plotly(tree, shape=shape)
        selected = {
            str(name).casefold()
            for name in (selected_species or [])
        }

        # ETE's leaf trace carries one customdata dictionary per terminal node.
        # Styling it here keeps selection independent of tree shape.
        for trace in figure.data:
            nodes = getattr(trace, "customdata", None)
            if not nodes or "markers" not in (getattr(trace, "mode", "") or ""):
                continue
            names = [
                node.get("name", "") if isinstance(node, dict) else ""
                for node in nodes
            ]
            if not any(names):
                continue
            is_selected = [name.casefold() in selected for name in names]
            trace.marker.color = [
                "#b3004b" if chosen else "#1f77b4"
                for chosen in is_selected
            ]
            trace.marker.size = [14 if chosen else 10 for chosen in is_selected]
            trace.marker.line = {
                "color": ["#7f0035" if chosen else "#ffffff" for chosen in is_selected],
                "width": [2 if chosen else 0 for chosen in is_selected],
            }

        return (
            figure,
            SELECTED_SHAPE_BUTTON_CLASS
            if rectangular_selected
            else SHAPE_BUTTON_CLASS,
            SELECTED_SHAPE_BUTTON_CLASS
            if circular_selected
            else SHAPE_BUTTON_CLASS,
            str(rectangular_selected).lower(),
            str(circular_selected).lower(),
        )
