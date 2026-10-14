"""Category-first plot picker, shared by layout and callbacks."""

from dash import dcc, html

CATEGORIES = {
    "basics": ("Basics", ("scatter", "line", "area", "bar", "funnel")),
    "part-of-whole": ("Part-of-Whole", ("pie", "sunburst", "treemap", "icicle")),
    "1d": ("1D Distributions", ("violin",)),
    "2d": ("2D Distributions", ()),
}
PLOT_LABELS = {
    "scatter": "Scatter plot", "line": "Line plot", "area": "Area plot",
    "bar": "Bar plot", "funnel": "Funnel plot", "pie": "Pie chart", "violin": "Violin plot",
    "sunburst": "Sunburst chart", "treemap": "Treemap", "icicle": "Icicle chart",
}
PLOT_IMAGES = {
    "scatter": "scatter.svg", "pie": "piechart.svg", "line": "line.svg",
    "area": "area.svg", "bar": "barplot.svg",
}
SYMBOLS = {"funnel": "▽", "violin": "⌁", "sunburst": "◉", "treemap": "▦", "icicle": "▤"}


def plot_label(name):
    visual = html.Img(src=f"/assets/{PLOT_IMAGES[name]}",
                      alt="", className="plot-type-option__image") if name in PLOT_IMAGES else html.Span(
                          SYMBOLS[name], className="plot-type-option__symbol", **{"aria-hidden": "true"})
    return html.Div([visual, html.Span(PLOT_LABELS[name], className="plot-type-option__name")],
                    className="plot-type-option")


def picker_items(category=None):
    def button(value, children, **kwargs):
        return html.Button(children, id={"type": "plot-picker-item", "value": value},
                           type="button", n_clicks=0, className="plot-picker__item", **kwargs)

    if category not in CATEGORIES:
        return [button(key, [html.Span(label), html.Span("›", **{"aria-hidden": "true"})])
                for key, (label, _) in CATEGORIES.items()]
    title, plots = CATEGORIES[category]
    return [button("back", "‹ All categories"), html.Div(title, className="plot-picker__heading")] + (
        [button(name, plot_label(name)) for name in plots] if plots else
        [html.Div("More plot types coming soon", className="plot-picker__empty")]
    )


def plot_picker():
    return html.Div([
        dcc.Input(id="plot-type-selector", type="hidden", value=None),
        html.Details([
            html.Summary("Select a plot type", id="plot-picker-label", className="plot-picker__summary"),
            html.Div(picker_items(), id="plot-picker-items", className="plot-picker__menu",
                     role="group", **{"aria-label": "Plot categories and types"}),
        ], id="plot-picker", className="plot-picker"),
    ])
