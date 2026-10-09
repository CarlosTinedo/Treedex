from dash import dcc, html

from ete4.dashview import DEFAULT_SHAPE, normalize_shape
from .plot_picker import plot_picker


def _shape_button(shape, selected_shape):
    selected = shape == selected_shape
    class_name = "tree-shape-button"
    if selected:
        class_name += " is-selected"

    return html.Button(
        shape.capitalize(),
        id=f"tree-shape-{shape}",
        className=class_name,
        type="button",
        **{"aria-pressed": str(selected).lower()},
    )


def _brand():
    """Compact TreeDEx wordmark built from accessible HTML and CSS."""
    return html.Div(
        [
            html.Span(
                [
                    html.Span(className="treedex-logo__branch treedex-logo__branch--left"),
                    html.Span(className="treedex-logo__branch treedex-logo__branch--right"),
                    html.Span(className="treedex-logo__trunk"),
                ],
                className="treedex-logo__mark",
                **{"aria-hidden": "true"},
            ),
            html.Span(
                [html.Span("Tree", className="treedex-logo__accent"), "DEx"],
                className="treedex-logo__name",
            ),
        ],
        className="treedex-logo",
        **{"aria-label": "TreeDEx"},
    )


def _tree_panel(initial_shape):
    return html.Div(
        [
            html.Div(
                [
                    html.Span("Tree layout", className="control-panel__title"),
                    html.Span(
                        "Choose how the phylogeny is displayed",
                        className="control-panel__description",
                    ),
                ],
                className="control-panel__heading",
            ),
            html.Div(
                [
                    html.Span("Shape", className="tree-control__label"),
                    html.Div(
                        [
                            _shape_button("rectangular", initial_shape),
                            _shape_button("circular", initial_shape),
                        ],
                        className="tree-shape-options",
                        role="group",
                        **{"aria-label": "Tree shape"},
                    ),
                ],
                className="tree-control",
            ),
        ],
        className="control-panel__content",
    )


def _plots_panel():
    """Plot selection controls and saved settings for each plot type."""
    return html.Div(
        [
            dcc.Store(id="scatter-options-store", storage_type="memory"),
            dcc.Store(id="scatter-options-page", data=1, storage_type="memory"),
            dcc.Store(id="pie-options-store", storage_type="memory"),
            dcc.Store(id="pie-options-page", data=1, storage_type="memory"),
            dcc.Store(id="built-plot", storage_type="memory"),
            dcc.Store(id="basic-options-store", data={}, storage_type="memory"),
            dcc.Store(id="basic-options-page", data={}, storage_type="memory"),
            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Current plot", htmlFor="current-plot-selector", className="plot-control__label"),
                            dcc.Dropdown(
                                id="current-plot-selector",
                                options=[{"label": "plot_1", "value": "plot_1"}],
                                value="plot_1",
                                clearable=False,
                                searchable=False,
                                className="plot-control__dropdown",
                            ),
                        ],
                        className="plot-control",
                    ),
                    html.Div(
                        [
                            html.Label("Plot type", htmlFor="plot-picker-label", className="plot-control__label"),
                            plot_picker(),
                        ],
                        className="plot-control",
                    ),
                ],
                className="plot-controls-column",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Span("Plot options", className="plot-control__label"),
                            html.Span(
                                "Choose a plot type to configure it",
                                className="plot-options-placeholder",
                            ),
                        ],
                        id="plot-options-content",
                        className="plot-options-content",
                    ),
                    html.Div(
                        id="scatter-validation-message",
                        className="scatter-validation-message",
                        role="alert",
                    ),
                ],
                className="plot-control plot-control--options",
            ),
        ],
        className="control-panel__content plots-panel plots-panel--dropdown-overflow",
    )


def _coming_soon_panel(title, description, action_label=None):
    children = [
        html.Div(
            [
                html.Span(title, className="control-panel__title"),
                html.Span(description, className="control-panel__description"),
            ],
            className="control-panel__heading",
        )
    ]
    if action_label:
        children.append(
            html.Button(
                [html.Span("+", **{"aria-hidden": "true"}), action_label],
                className="control-panel__placeholder-action",
                type="button",
                disabled=True,
                title="Coming soon",
            )
        )
    children.append(html.Span("Coming soon", className="control-panel__badge"))
    return html.Div(children, className="control-panel__content")



def _data_panel():
    """Controls for uploading a replacement data table."""
    return html.Div(
        [
            html.Div(
                [
                    html.Span("Data", className="control-panel__title"),
                    html.Span(
                        "Manage the data connected to this dashboard",
                        className="control-panel__description",
                    ),
                ],
                className="control-panel__heading",
            ),
            dcc.Upload(
                id="upload-data",
                children=html.Button(
                    "Upload data",
                    type="button",
                    className="upload-data-button",
                ),
                multiple=False,
                accept=".csv,.tsv,.txt",
            ),
            html.Div(
                "Accepted formats: CSV, TSV and TXT",
                id="upload-data-status",
                className="control-panel__description",
            ),
        ],
        className="control-panel__content",
    )

def top_control_panel(initial_shape=DEFAULT_SHAPE):
    """Return the main TreeDEx navigation and contextual controls."""
    initial_shape = normalize_shape(initial_shape)
    return html.Header(
        html.Div(
            [
                _brand(),
                dcc.Tabs(
                    id="control-panel-tabs",
                    value="tree",
                    mobile_breakpoint=0,
                    className="control-tabs",
                    parent_className="control-tabs-container",
                    content_className="control-tabs__content",
                    children=[
                        dcc.Tab(
                            _tree_panel(initial_shape),
                            label="Tree",
                            value="tree",
                            className="control-tab",
                            selected_className="control-tab--selected",
                        ),
                        dcc.Tab(
                            _plots_panel(),
                            label="Plots",
                            value="plots",
                            className="control-tab",
                            selected_className="control-tab--selected",
                        ),
                        dcc.Tab(
                            _data_panel(),
                            label="Data",
                            value="data",
                            className="control-tab",
                            selected_className="control-tab--selected",
                        ),
                    ],
                ),
            ],
            className="control-bar__inner",
        ),
        id="top-control-panel",
        className="control-bar",
    )
