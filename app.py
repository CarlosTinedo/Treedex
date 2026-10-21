import dash
import dash_bootstrap_components as dbc
from ete4.dashview import DEFAULT_SHAPE, normalize_shape, tree_to_plotly

from .layouts.main_layout import make_layout
from .callbacks import register_callbacks
from .tree_callbacks import register_tree_callbacks

"""
Dash application factory for Treedex.

This module is responsible for creating and configuring the Dash app.
It wires together the layout and the callbacks, but does not deal with
data loading or command-line argument parsing.

This separation allows:
- Easier testing
- Cleaner main entry point
- Future support for multi-page or modular dashboards
"""

def create_app(df_table, tree, initial_shape=DEFAULT_SHAPE):
    """
    Create and configure the Dash application.

    Parameters
    ----------
    df_table : pandas.DataFrame
        DataFrame containing species or metadata used across the dashboard
        (tables, plots, filters, etc.).

    tree : ete4.PhyloTree
        Tree rendered and manipulated by the ETE Dash backend.
    initial_shape : str
        Initial tree shape: "rectangular" or "circular".

    Returns
    -------
    dash.Dash
        A fully configured Dash application instance ready to be run.
    """
    initial_shape = normalize_shape(initial_shape)
    f_tree = tree_to_plotly(tree, shape=initial_shape)

    # Initialize Dash application
    app = dash.Dash(
        __name__,
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        suppress_callback_exceptions=True
    )
    # Build and assign the main layout
    app.layout = make_layout(df_table, f_tree, initial_shape=initial_shape)
    # Register all Dash callbacks (interactivity logic)
    register_callbacks(app, df_table, df_table)
    register_tree_callbacks(app, tree)

    return app
