from dash import dcc, html
from ete4.dashview import DEFAULT_SHAPE, make_tree_view_config
from .tree_layout import tree_layout
from .dashboard_layout import dashboard_layout
from .control_panel import top_control_panel

"""
Main application layout.

This module composes the full page layout by combining the tree panel
and the dashboard panel.
"""

def make_layout(df_table, f_tree, initial_shape=DEFAULT_SHAPE):
    """
    Build the main application layout.

    Parameters
    ----------
    df_table : pandas.DataFrame
        Table data used across the dashboard.
    f_tree : plotly.graph_objects.Figure
        Phylogenetic tree figure.

    Returns
    -------
    dash.html.Div
        The root layout container.
    """

    return html.Div(
        children=[
            dcc.Store(
                id="tree-view-config",
                data=make_tree_view_config(initial_shape),
            ),
            dcc.Store(id="selected-species", data=[]),
            top_control_panel(initial_shape=initial_shape),
            html.Main(
                [
                    tree_layout(f_tree),
                    html.Div(
                        id="workspace-divider",
                        className="workspace-divider",
                        role="separator",
                        tabIndex=0,
                        title="Drag to resize panels. Use arrow keys, or double-click to reset.",
                        **{
                            "aria-label": "Tree panel width",
                            "aria-orientation": "vertical",
                            "aria-controls": "tree-panel",
                            "aria-valuemin": "20",
                            "aria-valuemax": "80",
                            "aria-valuenow": "35",
                        },
                    ),
                    dashboard_layout(df_table),
                ],
                className="treedex-workspace",
            ),
        ],
        className="treedex-page",
    )
