# callbacks.py
import base64
import io

import pandas as pd
from dash import ALL, ClientsideFunction, Input, Output, State, ctx, dcc, html, no_update
from .components.plots import make_scatter_plot, scatter_config
from .scatter_options import normalize_scatter_options, validate_scatter_options
from .pie_options import normalize_pie_options, validate_pie_options
from .components.pie import make_pie_plot
from .layouts.pie_options import pie_options_menu
from .basic_options import BASIC_PLOT_TYPES, normalize_basic_options, validate_basic_options
from .components.basic import make_basic_plot
from .layouts.basic_options import basic_options_menu
from .hierarchy_options import HIERARCHY_PLOT_TYPES, normalize_hierarchy_options, validate_hierarchy_options
from .components.hierarchy import make_hierarchy_plot
from .layouts.hierarchy_options import hierarchy_options_menu
from .layouts.plot_picker import CATEGORIES, PLOT_LABELS, picker_items, plot_label
from .layouts.dashboard_layout import create_home_panel

def register_callbacks(app, df_table, df_scatter):

    @app.callback(
        Output("plot-picker-items", "children"),
        Output("plot-type-selector", "value"),
        Output("plot-picker-label", "children"),
        Output("plot-picker", "open"),
        Input({"type": "plot-picker-item", "value": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    def choose_plot_type(clicks):
        trigger = ctx.triggered_id
        if not isinstance(trigger, dict) or not any(clicks or []):
            return (no_update,) * 4
        value = trigger["value"]
        if value in CATEGORIES or value == "back":
            return picker_items(value), no_update, no_update, True
        if value in PLOT_LABELS:
            return picker_items(), value, plot_label(value), False
        return (no_update,) * 4

    app.clientside_callback(
        ClientsideFunction(namespace="treedex", function_name="updateBasicOptions"),
        Output("basic-options-page", "data"),
        Output("basic-options-store", "data"),
        Input({"type": "basic-page-button", "plot": ALL, "page": ALL}, "n_clicks"),
        Input({"type": "basic-option", "plot": ALL, "name": ALL}, "value"),
        State({"type": "basic-option", "plot": ALL, "name": ALL}, "id"),
        State("basic-options-page", "data"),
        State("basic-options-store", "data"),
        prevent_initial_call=True,
    )

    app.clientside_callback(
        ClientsideFunction(namespace="treedex", function_name="updateHierarchyOptions"),
        Output("hierarchy-options-page", "data"),
        Output("hierarchy-options-store", "data"),
        Input({"type": "hierarchy-page-button", "plot": ALL, "page": ALL}, "n_clicks"),
        Input({"type": "hierarchy-option", "plot": ALL, "name": ALL}, "value"),
        State({"type": "hierarchy-option", "plot": ALL, "name": ALL}, "id"),
        State("hierarchy-options-page", "data"),
        State("hierarchy-options-store", "data"),
        prevent_initial_call=True,
    )

    @app.callback(
        Output("species-table", "data"),
        Output("species-table", "columns"),
        Output("species-table", "selected_rows", allow_duplicate=True),
        Output("selected-species", "data", allow_duplicate=True),
        Output("upload-data-status", "children"),
        Input("upload-data", "contents"),
        State("upload-data", "filename"),
        prevent_initial_call=True,
    )
    def upload_data(contents, filename):
        """Parse an uploaded CSV/TSV/TXT file and replace the table contents."""
        if not contents:
            return no_update, no_update, no_update, no_update, no_update

        try:
            _, encoded = contents.split(",", 1)
            decoded = base64.b64decode(encoded)
            text = decoded.decode("utf-8-sig")

            lower_name = (filename or "").lower()
            if lower_name.endswith(".tsv"):
                uploaded_df = pd.read_csv(io.StringIO(text), sep="\\t")
            elif lower_name.endswith(".csv"):
                uploaded_df = pd.read_csv(io.StringIO(text))
            elif lower_name.endswith(".txt"):
                uploaded_df = pd.read_csv(io.StringIO(text), sep=None, engine="python")
            else:
                return (
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    "Unsupported file type. Please upload CSV, TSV or TXT.",
                )

            uploaded_df.columns = [str(col).strip() for col in uploaded_df.columns]

            if uploaded_df.empty:
                return (
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    "The uploaded file contains no rows.",
                )

            if "Species" not in uploaded_df.columns:
                return (
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    "The uploaded file must contain a 'Species' column.",
                )

            columns = [
                {"name": str(col), "id": str(col)}
                for col in uploaded_df.columns
            ]

            return (
                uploaded_df.to_dict("records"),
                columns,
                [],
                [],
                f"Loaded {filename}: {len(uploaded_df)} rows × {len(uploaded_df.columns)} columns.",
            )

        except UnicodeDecodeError:
            return (
                no_update,
                no_update,
                no_update,
                no_update,
                "Could not read the file as UTF-8 text.",
            )
        except Exception as exc:
            return (
                no_update,
                no_update,
                no_update,
                no_update,
                f"Could not load {filename or 'the file'}: {exc}",
            )


    def scatter_columns(table_data):
        """Return the current data frame and sensible numeric axis defaults."""
        current_df = pd.DataFrame(table_data) if table_data else df_scatter.copy()
        numeric_cols = current_df.select_dtypes(include="number").columns.tolist()
        default_x = "X" if "X" in numeric_cols else (numeric_cols[0] if numeric_cols else None)
        default_y = "Y" if "Y" in numeric_cols else (
            numeric_cols[1] if len(numeric_cols) > 1 else default_x
        )
        return current_df, numeric_cols, default_x, default_y

    def canonical_species(names, species):
        """Return valid table species, preserving table order."""
        requested = {
            str(name).casefold()
            for name in (names or [])
            if name is not None
        }
        return [
            name
            for name in species
            if name.casefold() in requested
        ]

    @app.callback(
        Output("selected-species", "data"),
        Output("species-table", "selected_rows"),
        Input("tree-graph", "clickData"),
        Input({"type": "managed-plot", "index": ALL}, "clickData"),
        Input("species-table", "selected_rows"),
        State("selected-species", "data"),
        State("species-table", "data"),
        State({"type": "managed-plot", "index": ALL}, "figure"),
        prevent_initial_call=True,
    )
    def synchronize_selection(tree_click, plot_clicks, selected_rows, current, table_data, plot_figures):
        """Keep tree, plots and table selections in one shared state."""
        trigger = ctx.triggered_id

        current_table = table_data or []
        species = [
            str(row.get("Species"))
            for row in current_table
            if row.get("Species") is not None
        ]

        if trigger == "species-table":
            selected = [
                species[index]
                for index in (selected_rows or [])
                if 0 <= index < len(species)
            ]
            selected = canonical_species(selected, species)
            if selected == canonical_species(current, species):
                return no_update, no_update
            return selected, no_update

        if isinstance(trigger, dict) and trigger.get("type") == "managed-plot":
            # Dash wildcard inputs and states use the same ordering.
            clicked_id = trigger.get("index")
            # Select the graph by its component ID, not by its position in the row.
            graph_ids = ctx.inputs_list[1]
            match = next((i for i, item in enumerate(graph_ids)
                          if item["id"].get("index") == clicked_id), None)
            if match is None or match >= len(plot_figures or []):
                return no_update, no_update
            point = ((plot_clicks or [])[match] or {}).get("points", [{}])[0]
            trace_list = ((plot_figures or [])[match] or {}).get("data", [])
            curve = point.get("curveNumber", 0)
            trace = trace_list[curve] if isinstance(curve, int) and 0 <= curve < len(trace_list) else {}
            metadata = trace.get("meta") or {}
            if "species_by_id" in metadata:
                node_id = point.get("id")
                if node_id is None:
                    index = point.get("pointNumber")
                    ids = trace.get("ids") or []
                    if isinstance(index, int) and 0 <= index < len(ids):
                        node_id = ids[index]
                selected = canonical_species(metadata["species_by_id"].get(str(node_id), []), species)
            elif "species_by_label" in metadata:
                selected = canonical_species(metadata["species_by_label"].get(str(point.get("label")), []), species)
            else:
                custom = point.get("customdata")
                clicked = custom[0] if isinstance(custom, (list, tuple)) and custom else point.get("hovertext") or point.get("text")
                selected = canonical_species([clicked], species)

        elif trigger == "tree-graph":
            point = (tree_click or {}).get("points", [{}])[0]
            node = point.get("customdata") or {}
            if not isinstance(node, dict):
                return no_update, no_update
            selected = canonical_species(
                node.get("leaf_names") or [node.get("name")],
                species,
            )
        else:
            return no_update, no_update

        if not selected:
            return no_update, no_update

        selected_lookup = {name.casefold() for name in selected}
        rows = [
            index
            for index, name in enumerate(species)
            if name.casefold() in selected_lookup
        ]
        return selected, rows

    @app.callback(
        Output("plot-options-content", "children"),
        Output("scatter-options-store", "data"),
        Output("pie-options-store", "data"),
        Input("plot-type-selector", "value"),
        Input("species-table", "data"),
        Input("scatter-options-page", "data"),
        Input("pie-options-page", "data"),
        Input("basic-options-page", "data"),
        State("scatter-options-store", "data"),
        State("pie-options-store", "data"),
        State("basic-options-store", "data"),
        Input("hierarchy-options-page", "data"),
        State("hierarchy-options-store", "data"),
    )
    def show_plot_options(plot_type, table_data, active_page, pie_page, basic_pages, stored_options, stored_pie_options, stored_basic_options,
                          hierarchy_pages=None, stored_hierarchy_options=None):
        """Render controls for the plot type selected by the user."""
        label = html.Span("Plot options", className="plot-control__label")

        if plot_type in HIERARCHY_PLOT_TYPES:
            current_df, _, _, _ = scatter_columns(table_data)
            options = normalize_hierarchy_options(plot_type, (stored_hierarchy_options or {}).get(plot_type), current_df)
            page = (hierarchy_pages or {}).get(plot_type, 1)
            return hierarchy_options_menu(plot_type, options, current_df, page), no_update, no_update

        if plot_type in BASIC_PLOT_TYPES:
            current_df, _, _, _ = scatter_columns(table_data)
            options = normalize_basic_options(plot_type, (stored_basic_options or {}).get(plot_type), current_df)
            page = (basic_pages or {}).get(plot_type, 1)
            return basic_options_menu(plot_type, options, current_df, page), no_update, no_update

        if plot_type == "pie":
            current_df, _, _, _ = scatter_columns(table_data)
            options = normalize_pie_options(stored_pie_options, current_df)
            return pie_options_menu(options, current_df, pie_page), no_update, options

        if plot_type != "scatter":
            message = (
                "Choose a plot type to configure it"
                if not plot_type
                else "Options for this plot type are coming soon"
            )
            return [
                label,
                html.Span(message, className="plot-options-placeholder"),
            ], stored_options, no_update

        current_df, numeric_cols, default_x, default_y = scatter_columns(table_data)
        if not numeric_cols:
            return [
                label,
                html.Span(
                    "The current data needs at least one numeric column.",
                    className="plot-options-placeholder",
                ),
            ], stored_options, no_update

        options = normalize_scatter_options(stored_options, current_df)
        active_page = active_page if active_page in (1, 2, 3, 4) else 1
        axis_options = [{"label": str(col), "value": col} for col in numeric_cols]
        column_options = [{"label": str(col), "value": col} for col in current_df.columns]
        size_columns = []
        for col in numeric_cols:
            values = pd.to_numeric(current_df[col], errors="coerce").dropna()
            if not values.empty and values.ge(0).all() and values.gt(0).any():
                size_columns.append(col)
        size_options = [{"label": col, "value": col} for col in size_columns]

        def control_id(name):
            return {"type": "scatter-option", "name": name}

        def dropdown(name, choices, clearable=True, multi=False, placeholder="None"):
            return dcc.Dropdown(
                id=control_id(name), options=choices, value=options.get(name),
                placeholder=placeholder, clearable=clearable, multi=multi,
                className="scatter-option__dropdown",
            )

        def number(name, placeholder=None, **kwargs):
            return dcc.Input(
                id=control_id(name), type="number", value=options.get(name),
                placeholder=placeholder, className="scatter-option__input", **kwargs,
            )

        def text_input(name, placeholder=None, input_type="text"):
            return dcc.Input(
                id=control_id(name), type=input_type, value=options.get(name),
                placeholder=placeholder, className="scatter-option__input",
            )

        def field(label_text, name, component):
            return html.Div(
                [html.Label(label_text, title=label_text), component],
                className="scatter-option",
            )

        none_choice = [{"label": "None", "value": ""}]
        marginal_choices = none_choice + [
            {"label": value.title(), "value": value}
            for value in ("rug", "box", "violin", "histogram")
        ]
        boolean_choices = [
            {"label": "Off", "value": False}, {"label": "On", "value": True}
        ]
        if active_page == 1:
            page_fields = [
                field("X axis", "x", dropdown("x", axis_options, clearable=False)),
                field("Y axis", "y", dropdown("y", axis_options, clearable=False)),
                field("Color by", "color", dropdown("color", column_options)),
                field("Symbol by", "symbol", dropdown("symbol", column_options)),
                field("Size by", "size", dropdown("size", size_options)),
                field("Text labels", "text", dropdown("text", column_options)),
                field("Hover title", "hover_name", dropdown("hover_name", column_options)),
                field("Extra hover data", "hover_data", dropdown(
                    "hover_data", column_options, multi=True, placeholder="Select columns"
                )),
                field("Title", "title", text_input("title", "Scatter plot")),
                field("Subtitle", "subtitle", text_input("subtitle", "Optional subtitle")),
                field("Template", "template", dropdown("template", [{"label": name, "value": name} for name in ("plotly_white", "plotly", "plotly_dark", "ggplot2", "seaborn", "simple_white", "none")], clearable=False)),
            ]
        elif active_page == 2:
            page_fields = [
                field("Facet rows", "facet_row", dropdown("facet_row", column_options)),
                field("Facet columns", "facet_col", dropdown("facet_col", column_options)),
                field("Facet column wrap", "facet_col_wrap", number("facet_col_wrap", min=0, step=1)),
                field("Row spacing", "facet_row_spacing", number("facet_row_spacing", min=0, max=1, step=0.01)),
                field("Column spacing", "facet_col_spacing", number("facet_col_spacing", min=0, max=1, step=0.01)),
                field("X error +", "error_x", dropdown("error_x", size_options)),
                field("X error −", "error_x_minus", dropdown("error_x_minus", size_options)),
                field("Y error +", "error_y", dropdown("error_y", size_options)),
                field("Y error −", "error_y_minus", dropdown("error_y_minus", size_options)),
                field("Animation frame", "animation_frame", dropdown("animation_frame", column_options)),
                field("Animation group", "animation_group", dropdown("animation_group", column_options)),
            ]
        elif active_page == 3:
            page_fields = [
                field("Opacity", "opacity", number("opacity", min=0, max=1, step=0.05)),
                field("Maximum size", "size_max", number("size_max", min=1, step=1)),
                field("Discrete palette", "color_discrete_palette", dropdown(
                    "color_discrete_palette",
                    [{"label": name, "value": name} for name in ("Plotly", "D3", "G10", "T10", "Alphabet", "Dark24", "Light24")],
                    clearable=False,
                )),
                field("Continuous scale", "color_continuous_scale", dropdown(
                    "color_continuous_scale",
                    [{"label": name, "value": name} for name in ("Viridis", "Plasma", "Inferno", "Magma", "Cividis", "Turbo", "RdBu", "Spectral")],
                    clearable=False,
                )),
                field("Color minimum", "range_color_min", number("range_color_min")),
                field("Color maximum", "range_color_max", number("range_color_max")),
                field("Color midpoint", "color_continuous_midpoint", number("color_continuous_midpoint")),
                field("X marginal", "marginal_x", dropdown("marginal_x", marginal_choices)),
                field("Y marginal", "marginal_y", dropdown("marginal_y", marginal_choices)),
                field("Render mode", "render_mode", dropdown(
                    "render_mode", [{"label": value.upper() if value != "auto" else "Auto", "value": value} for value in ("auto", "svg", "webgl")], clearable=False
                )),
            ]
        else:
            try:
                import statsmodels  # noqa: F401
                trendline_choices = none_choice + [
                    {"label": "OLS", "value": "ols"}, {"label": "LOWESS", "value": "lowess"}
                ]
            except ImportError:
                trendline_choices = none_choice
            page_fields = [
                field("Log X", "log_x", dropdown("log_x", boolean_choices, clearable=False)),
                field("Log Y", "log_y", dropdown("log_y", boolean_choices, clearable=False)),
                field("X minimum", "range_x_min", number("range_x_min")),
                field("X maximum", "range_x_max", number("range_x_max")),
                field("Y minimum", "range_y_min", number("range_y_min")),
                field("Y maximum", "range_y_max", number("range_y_max")),
                field("Orientation", "orientation", dropdown("orientation", none_choice + [{"label": "Vertical", "value": "v"}, {"label": "Horizontal", "value": "h"}])),
                field("Trendline", "trendline", dropdown("trendline", trendline_choices)),
                field("Trendline scope", "trendline_scope", dropdown("trendline_scope", [{"label": "Per trace", "value": "trace"}, {"label": "Overall", "value": "overall"}], clearable=False)),
                field("Trendline color", "trendline_color_override", text_input("trendline_color_override", "CSS color")),
            ]

        return [
            html.Div(
                [label, html.Div([
                    html.Div([
                        html.Button(
                            str(page), id={"type": "scatter-page-button", "page": page},
                            n_clicks=0, type="button",
                            className="scatter-page-button" + (" is-active" if page == active_page else ""),
                            **{"aria-label": f"Scatter options page {page}", "aria-pressed": str(page == active_page).lower()},
                        ) for page in range(1, 5)
                    ], className="scatter-pages", role="group", **{"aria-label": "Scatter option pages"}),
                ], className="scatter-options-actions")],
                className="scatter-options-header",
            ),
            html.Div(
                [
                    html.Div(
                        page_fields + [
                            html.Button(
                                "Build plot", id="build-scatter-plot", n_clicks=0,
                                type="button", className="build-plot-button",
                            ),
                        ],
                        className="scatter-options-page",
                    ),
                ],
                className="scatter-options",
            ),
        ], options, no_update

    @app.callback(
        Output("scatter-options-page", "data"),
        Input({"type": "scatter-page-button", "page": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    def change_scatter_page(_clicks):
        triggered = ctx.triggered_id
        return triggered["page"] if isinstance(triggered, dict) and any(_clicks or []) else no_update

    @app.callback(
        Output("pie-options-page", "data"),
        Input({"type": "pie-page-button", "page": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    def change_pie_page(clicks):
        triggered = ctx.triggered_id
        return triggered["page"] if isinstance(triggered, dict) and any(clicks or []) else no_update

    @app.callback(
        Output("pie-options-store", "data", allow_duplicate=True),
        Input({"type": "pie-option", "name": ALL}, "value"),
        State({"type": "pie-option", "name": ALL}, "id"),
        State("pie-options-store", "data"),
        prevent_initial_call=True,
    )
    def save_pie_options(values, ids, stored_options):
        updated = dict(stored_options or {})
        for component_id, value in zip(ids or [], values or []):
            if isinstance(component_id, dict):
                updated[component_id["name"]] = None if value == "" else value
        return updated

    @app.callback(
        Output("scatter-options-store", "data", allow_duplicate=True),
        Input({"type": "scatter-option", "name": ALL}, "value"),
        State({"type": "scatter-option", "name": ALL}, "id"),
        State("scatter-options-store", "data"),
        prevent_initial_call=True,
    )
    def save_scatter_options(values, ids, stored_options):
        updated = dict(stored_options or {})
        for component_id, value in zip(ids or [], values or []):
            if isinstance(component_id, dict):
                updated[component_id["name"]] = None if value == "" else value
        return updated

    @app.callback(
        Output("plot-instances", "data", allow_duplicate=True),
        Output("scatter-validation-message", "children"),
        Output("built-plot", "data"),
        Input("build-scatter-plot", "n_clicks", allow_optional=True),
        Input("build-pie-plot", "n_clicks", allow_optional=True),
        Input("build-basic-plot", "n_clicks", allow_optional=True),
        State("selected-species", "data"),
        State("scatter-options-store", "data"),
        State("pie-options-store", "data"),
        State("species-table", "data"),
        State("built-plot", "data"),
        State("plot-instances", "data"),
        State("current-plot-selector", "value"),
        State({"type": "pie-option", "name": ALL}, "value"),
        State({"type": "pie-option", "name": ALL}, "id"),
        State({"type": "scatter-option", "name": ALL}, "value"),
        State({"type": "scatter-option", "name": ALL}, "id"),
        State("plot-type-selector", "value"),
        State("basic-options-store", "data"),
        State({"type": "basic-option", "plot": ALL, "name": ALL}, "value"),
        State({"type": "basic-option", "plot": ALL, "name": ALL}, "id"),
        Input("build-hierarchy-plot", "n_clicks", allow_optional=True),
        State("hierarchy-options-store", "data"),
        State({"type": "hierarchy-option", "plot": ALL, "name": ALL}, "value"),
        State({"type": "hierarchy-option", "plot": ALL, "name": ALL}, "id"),
        prevent_initial_call=True,
    )
    def build_plot(
        scatter_clicks, pie_clicks, basic_clicks, selected_species, scatter_options,
        pie_options, table_data, built_plot, instances, active_id, pie_values, pie_ids,
        scatter_values, scatter_ids, selected_plot_type, basic_options, basic_values, basic_ids,
        hierarchy_clicks=None, hierarchy_options=None, hierarchy_values=None, hierarchy_ids=None,
    ):
        """Build on demand; selection updates use the last successfully built settings."""
        trigger = ctx.triggered_id
        if trigger == "build-hierarchy-plot":
            if not hierarchy_clicks or selected_plot_type not in HIERARCHY_PLOT_TYPES:
                return no_update, no_update, no_update
            plot_type = selected_plot_type
            stored_options = dict((hierarchy_options or {}).get(plot_type) or {})
            for component_id, value in zip(hierarchy_ids or [], hierarchy_values or []):
                if component_id["plot"] == plot_type:
                    stored_options[component_id["name"]] = None if value == "" else value
        elif trigger == "build-basic-plot":
            if not basic_clicks or selected_plot_type not in BASIC_PLOT_TYPES:
                return no_update, no_update, no_update
            plot_type = selected_plot_type
            stored_options = dict((basic_options or {}).get(plot_type) or {})
            for component_id, value in zip(basic_ids or [], basic_values or []):
                if component_id["plot"] == plot_type:
                    stored_options[component_id["name"]] = None if value == "" else value
        elif trigger in ("build-scatter-plot", "build-pie-plot"):
            plot_type = "pie" if trigger == "build-pie-plot" else "scatter"
            if not (pie_clicks if plot_type == "pie" else scatter_clicks):
                return no_update, no_update, no_update
            stored_options = dict((pie_options if plot_type == "pie" else scatter_options) or {})
            values, ids = (pie_values, pie_ids) if plot_type == "pie" else (scatter_values, scatter_ids)
            for component_id, value in zip(ids or [], values or []):
                stored_options[component_id["name"]] = None if value == "" else value
        else:
            return no_update, no_update, no_update

        current_df, _, _, _ = scatter_columns(table_data)
        if plot_type in HIERARCHY_PLOT_TYPES:
            options = normalize_hierarchy_options(plot_type, stored_options, current_df)
            errors = validate_hierarchy_options(plot_type, options, current_df)
        elif plot_type in BASIC_PLOT_TYPES:
            options = normalize_basic_options(plot_type, stored_options, current_df)
            errors = validate_basic_options(plot_type, options, current_df)
        else:
            normalize = normalize_pie_options if plot_type == "pie" else normalize_scatter_options
            validate = validate_pie_options if plot_type == "pie" else validate_scatter_options
            options = normalize(stored_options, current_df)
            errors = validate(options, current_df)
        if errors:
            return no_update, html.Ul([html.Li(error) for error in errors]), no_update

        try:
            if plot_type in HIERARCHY_PLOT_TYPES:
                figure = make_hierarchy_plot(plot_type, current_df, selected_species=selected_species, **options)
            elif plot_type in BASIC_PLOT_TYPES:
                figure = make_basic_plot(plot_type, current_df, selected_species=selected_species, **options)
            elif plot_type == "pie":
                figure = make_pie_plot(current_df, selected_species=selected_species, **options)
            else:
                selected_lookup = {str(name).casefold() for name in (selected_species or [])}
                selection_idx = [
                    index for index, name in enumerate(current_df["Species"])
                    if str(name).casefold() in selected_lookup
                ]
                figure = make_scatter_plot(current_df, selection=selection_idx, **options)
        except (ValueError, TypeError, KeyError) as exc:
            return no_update, f"Could not build {plot_type} plot: {exc}", no_update

        updated = [dict(item) for item in (instances or [])]
        target = next((item for item in updated if item["id"] == active_id), None)
        if target is None:
            return no_update, "Select a plot before building it.", no_update
        target.update(type=plot_type, options=options, visible=True)
        return updated, "", {"type": plot_type, "options": options}

    @app.callback(
        Output("plot-instances", "data"),
        Output("current-plot-selector", "value"),
        Input("sidebar-add-plot", "n_clicks"),
        Input({"type": "plot-action", "action": ALL, "index": ALL}, "n_clicks"),
        State("plot-instances", "data"),
        State("current-plot-selector", "value"),
        prevent_initial_call=True,
    )
    def manage_plots(add_clicks, action_clicks, instances, active_id):
        plots = [dict(item) for item in (instances or [])]
        trigger = ctx.triggered_id
        if trigger == "sidebar-add-plot":
            if not add_clicks:
                return no_update, no_update
            numbers = [int(item["id"].split("_")[-1]) for item in plots if item["id"].split("_")[-1].isdigit()]
            new_id = f"plot_{max(numbers, default=0) + 1}"
            plots.append({"id": new_id, "type": None, "options": {}, "visible": True, "pinned": False})
            return plots, new_id
        if not isinstance(trigger, dict) or not any(action_clicks or []):
            return no_update, no_update
        plot_id, action = trigger.get("index"), trigger.get("action")
        index = next((i for i, item in enumerate(plots) if item["id"] == plot_id), None)
        if index is None:
            return no_update, no_update
        if action == "select":
            return no_update, plot_id
        if action == "delete":
            plots.pop(index)
            if not plots:
                plots = [{"id": "plot_1", "type": None, "options": {}, "visible": True, "pinned": False}]
            return plots, plots[min(index, len(plots)-1)]["id"] if active_id == plot_id else no_update
        if action in ("visible", "pinned"):
            key = "visible" if action == "visible" else "pinned"
            plots[index][key] = not plots[index].get(key, key == "visible")
            if action == "pinned" and plots[index]["pinned"]:
                plots[index]["visible"] = True
            if action == "visible" and not plots[index]["visible"]:
                plots[index]["pinned"] = False
        elif action in ("left", "right"):
            destination = index + (-1 if action == "left" else 1)
            if 0 <= destination < len(plots):
                plots[index], plots[destination] = plots[destination], plots[index]
        return plots, no_update

    @app.callback(
        Output("current-plot-selector", "options"),
        Output("plots-sidebar-list", "children"),
        Input("plot-instances", "data"),
        Input("current-plot-selector", "value"),
    )
    def show_plot_manager(instances, active):
        plots = instances or []
        options = [{"label": p["id"], "value": p["id"]} for p in plots]
        rows = []
        for item in plots:
            pid = item["id"]
            def action(name, label, title):
                return html.Button(label, id={"type": "plot-action", "action": name, "index": pid},
                                   n_clicks=0, title=title, className="plots-sidebar-action")
            rows.append(html.Div([
                html.Button(pid + (" · " + item["type"] if item.get("type") else " · empty"),
                            id={"type": "plot-action", "action": "select", "index": pid},
                            n_clicks=0, className="plots-sidebar-select" + (" is-active" if pid == active else "")),
                html.Div([
                    action("visible", "◉" if item.get("visible", True) else "◯", "Show / hide"),
                    action("pinned", "📌" if item.get("pinned") else "♧", "Pin / unpin"),
                    action("left", "←", "Move left"), action("right", "→", "Move right"),
                    action("delete", "×", "Delete plot"),
                ], className="plots-sidebar-actions"),
            ], className="plots-sidebar-item", key=pid))
        return options, rows

    @app.callback(
        Output("plots-sidebar", "className"),
        Input("toggle-plots-sidebar", "n_clicks"),
        Input("close-plots-sidebar", "n_clicks"),
        State("plots-sidebar", "className"),
        prevent_initial_call=True,
    )
    def toggle_sidebar(toggle, close, current):
        return "plots-sidebar is-closed" if ctx.triggered_id == "close-plots-sidebar" or current == "plots-sidebar" else "plots-sidebar"

    @app.callback(
        Output("plot-type-selector", "value", allow_duplicate=True),
        Output("plot-picker-label", "children", allow_duplicate=True),
        Output("scatter-options-store", "data", allow_duplicate=True),
        Output("pie-options-store", "data", allow_duplicate=True),
        Output("basic-options-store", "data", allow_duplicate=True),
        Output("hierarchy-options-store", "data", allow_duplicate=True),
        Input("current-plot-selector", "value"),
        State("plot-instances", "data"),
        State("basic-options-store", "data"),
        State("hierarchy-options-store", "data"),
        prevent_initial_call=True,
    )
    def restore_plot_settings(active, instances, basics, hierarchies):
        item = next((p for p in (instances or []) if p["id"] == active), None)
        if item is None:
            return (no_update,) * 6
        kind, options = item.get("type"), item.get("options") or {}
        basic_store, hierarchy_store = dict(basics or {}), dict(hierarchies or {})
        if kind in BASIC_PLOT_TYPES:
            basic_store[kind] = options
        if kind in HIERARCHY_PLOT_TYPES:
            hierarchy_store[kind] = options
        return kind, plot_label(kind) if kind in PLOT_LABELS else "Select a plot type", options if kind == "scatter" else no_update, options if kind == "pie" else no_update, basic_store, hierarchy_store

    @app.callback(
        Output("main-plot-area", "children"),
        Input("plot-instances", "data"),
        Input("selected-species", "data"),
        Input("species-table", "data"),
    )
    def render_managed_plots(instances, selected_species, table_data):
        current_df, _, _, _ = scatter_columns(table_data)
        cards = []
        for item in (instances or []):
            if not item.get("visible", True) or not item.get("type"):
                continue
            kind = item["type"]
            stored = item.get("options") or {}
            try:
                if kind in HIERARCHY_PLOT_TYPES:
                    options = normalize_hierarchy_options(kind, stored, current_df)
                    figure = make_hierarchy_plot(kind, current_df, selected_species=selected_species, **options)
                elif kind in BASIC_PLOT_TYPES:
                    options = normalize_basic_options(kind, stored, current_df)
                    figure = make_basic_plot(kind, current_df, selected_species=selected_species, **options)
                elif kind == "pie":
                    options = normalize_pie_options(stored, current_df)
                    figure = make_pie_plot(current_df, selected_species=selected_species, **options)
                elif kind == "scatter":
                    options = normalize_scatter_options(stored, current_df)
                    lookup = {str(name).casefold() for name in (selected_species or [])}
                    selection_idx = [i for i, name in enumerate(current_df["Species"]) if str(name).casefold() in lookup]
                    figure = make_scatter_plot(current_df, selection=selection_idx, **options)
                else:
                    continue
                figure.update_layout(autosize=True, width=None, height=None)
                body = dcc.Graph(id={"type": "managed-plot", "index": item["id"]}, figure=figure,
                                 config={**scatter_config, "responsive": True}, responsive=True,
                                 className="dashboard-scatter-plot")
            except (ValueError, TypeError, KeyError) as exc:
                body = html.Div(f"Could not render {item['id']}: {exc}", className="scatter-validation-message")
            cards.append(html.Div([
                html.Div([html.Strong(item["id"]), html.Span(" 📌" if item.get("pinned") else "")], className="managed-plot-heading"),
                html.Div(body, className="managed-plot-body"),
            ], className="managed-plot-card", key=item["id"]))
        return cards if cards else [create_home_panel()]

    app.clientside_callback(
        """
        function(addClicks) {
            if (!addClicks) {
                return [dash_clientside.no_update, dash_clientside.no_update];
            }
            const panel = document.getElementById("top-control-panel");
            // Repeated clicks should still leave only one mouse-leave handler.
            panel.onmouseleave = function() {
                if (panel.contains(document.activeElement)) {
                    document.activeElement.blur();
                }
                dash_clientside.set_props("top-control-panel", {
                    className: "control-bar"
                });
                panel.onmouseleave = null;
            };
            return ["plots", "control-bar is-open"];
        }
        """,
        Output("control-panel-tabs", "value"),
        Output("top-control-panel", "className"),
        Input("add-plot-btn", "n_clicks", allow_optional=True),
        prevent_initial_call=True,
    )
