from dash import html, dcc

"""
Layout component for the phylogenetic tree panel.

This module defines the left-side layout that displays the phylogenetic
tree exported from ETE4. The tree is considered mandatory and is always
visible in the application.
"""


def tree_layout(f_tree):
    """Create the responsive tree panel layout."""

    return html.Div(
        children=[
            dcc.Graph(
                id="tree-graph",
                figure=f_tree,
                config={"responsive": True},
                responsive=True,
                className="tree-graph",
                style={"width": "100%", "height": "100%"},
            )
        ],
        id="tree-panel",
        className="tree-panel",
    )
