"""Paginated pie controls sharing the scatter menu's styles."""

from dash import dcc, html
import plotly.express as px
import plotly.io as pio


PAGE_TITLES = {1: "Data and titles", 2: "Facets and size", 3: "Appearance"}


def pie_options_menu(options, frame, active_page):
    active_page = active_page if active_page in PAGE_TITLES else 1
    columns = [{"label": str(col), "value": col} for col in frame.columns]
    numeric = [{"label": str(col), "value": col} for col in frame.select_dtypes(include="number").columns]

    def control_id(name):
        return {"type": "pie-option", "name": name}

    def dropdown(name, choices, **kwargs):
        return dcc.Dropdown(id=control_id(name), options=choices, value=options[name],
                            className="scatter-option__dropdown", **kwargs)

    def number(name, **kwargs):
        return dcc.Input(id=control_id(name), value=options[name], type="number",
                         className="scatter-option__input", **kwargs)

    def text(name, placeholder=None):
        return dcc.Input(id=control_id(name), value=options[name], type="text",
                         placeholder=placeholder, className="scatter-option__input")

    def field(label, name, component, hint=None):
        return html.Div([html.Label(label, title=label), component], className="scatter-option", title=hint or label)

    if active_page == 1:
        fields = [
            field("Slice names", "names", dropdown("names", columns, clearable=False)),
            field("Slice values", "values", dropdown("values", numeric, placeholder="Count rows"), "Leave empty to count rows for each slice name."),
            field("Color by", "color", dropdown("color", columns)),
            field("Hover title", "hover_name", dropdown("hover_name", columns)),
            field("Extra hover data", "hover_data", dropdown("hover_data", columns, multi=True)),
            field("Custom data", "custom_data", dropdown("custom_data", columns, multi=True)),
            field("Hover formats (JSON)", "hover_data_format", text("hover_data_format", '{"Value": ":.2f"}'), "Column names mapped to true, false, or a Plotly format string."),
            field("Title", "title", text("title", "Pie chart")),
            field("Subtitle", "subtitle", text("subtitle", "Optional subtitle")),
        ]
    elif active_page == 2:
        fields = [
            field("Facet rows", "facet_row", dropdown("facet_row", columns)),
            field("Facet columns", "facet_col", dropdown("facet_col", columns)),
            field("Facet column wrap", "facet_col_wrap", number("facet_col_wrap", min=0, step=1)),
            field("Row spacing", "facet_row_spacing", number("facet_row_spacing", min=0, max=1, step=0.01)),
            field("Column spacing", "facet_col_spacing", number("facet_col_spacing", min=0, max=1, step=0.01)),
            field("Category order (JSON)", "category_orders", text("category_orders", '{"Group": ["A", "B"]}')),
            field("Width (px)", "width", number("width", min=10, step=1, placeholder="Fit panel")),
            field("Height (px)", "height", number("height", min=10, step=1, placeholder="Fit panel")),
        ]
    else:
        palettes = [{"label": name, "value": name} for name in dir(px.colors.qualitative)
                    if isinstance(getattr(px.colors.qualitative, name), list)]
        fields = [
            field("Discrete palette", "color_discrete_palette", dropdown("color_discrete_palette", palettes, clearable=False)),
            field("Custom colors (JSON)", "color_discrete_sequence", text("color_discrete_sequence", '["#198754", "#3366cc"]'), "Overrides the selected palette."),
            field("Color map (JSON)", "color_discrete_map", text("color_discrete_map", '{"A": "red"}'), 'A JSON object mapping categories to CSS colors, or identity to use the Color by column as CSS colors.'),
            field("Opacity", "opacity", number("opacity", min=0, max=1, step=0.05)),
            field("Donut hole", "hole", number("hole", min=0, max=1, step=0.05)),
            field("Template", "template", dropdown("template", [{"label": name, "value": name} for name in pio.templates], clearable=False)),
            field("Labels (JSON)", "labels", text("labels", '{"Value": "Abundance"}')),
        ]
    return [
        html.Div([
            html.Span("Plot options", className="plot-control__label"),
            html.Div(html.Div([
                html.Button(str(page), id={"type": "pie-page-button", "page": page},
                            n_clicks=0, type="button", title=title,
                            className="scatter-page-button" + (" is-active" if page == active_page else ""),
                            **{"aria-label": f"Pie options page {page}: {title}", "aria-pressed": str(page == active_page).lower()})
                for page, title in PAGE_TITLES.items()
            ], className="scatter-pages", role="group", **{"aria-label": "Pie option pages"}), className="scatter-options-actions"),
        ], className="scatter-options-header"),
        html.Div(html.Div(fields + [
            html.Button("Build plot", id="build-pie-plot", n_clicks=0, type="button", className="build-plot-button"),
        ], className="scatter-options-page"), className="scatter-options"),
    ]
