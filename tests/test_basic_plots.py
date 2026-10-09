"""API coverage and integration for the category picker and Basics plots."""

import inspect
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from dash import Dash, no_update
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from treedex.basic_options import (
    BASIC_PLOT_TYPES, basic_kwargs, default_basic_options, normalize_basic_options,
    option_pages, validate_basic_options,
)
from treedex.components.basic import make_basic_plot
from treedex.callbacks import register_callbacks
from treedex.layouts.basic_options import basic_options_menu
from treedex.layouts.main_layout import make_layout
from treedex.layouts.plot_picker import CATEGORIES, picker_items


def walk(component):
    if isinstance(component, (list, tuple)):
        for child in component:
            yield from walk(child)
    elif hasattr(component, 'to_plotly_json'):
        yield component
        yield from walk(getattr(component, 'children', []))


class BasicsTests(unittest.TestCase):
    def setUp(self):
        self.frame = pd.DataFrame({
            'Species': ['a', 'b', 'c', 'd'], 'X': [3, 1, 2, 4], 'Y': [2, 4, 1, 3],
            'Other': [5, 6, 7, 8], 'Group': ['A', 'A', 'B', 'B'],
            'Error': [0.1, 0.2, 0.1, 0.2], 'Date': ['2026-01-03', '2026-01-01', '2026-01-02', '2026-01-04'],
        })
        self.app = Dash(__name__, suppress_callback_exceptions=True)
        self.app.layout = make_layout(self.frame, go.Figure())
        register_callbacks(self.app, self.frame, self.frame)
        self.callbacks = {entry['callback'].__wrapped__.__name__: entry['callback'].__wrapped__
                          for entry in self.app.callback_map.values() if 'callback' in entry}

    def options(self, kind, **values):
        return normalize_basic_options(kind, values, self.frame)

    def build(self, kind, options=None, built=None, trigger='build-basic-plot', selected=None):
        with patch('treedex.callbacks.ctx', SimpleNamespace(triggered_id=trigger)):
            return self.callbacks['build_plot'](
                0, 0, 1, selected or [], {}, {}, self.frame.to_dict('records'), built,
                [], [], [], [], kind, {kind: options or {}}, [], [],
            )

    def test_category_structure_and_drilldown(self):
        self.assertEqual([label for label, _ in CATEGORIES.values()],
                         ['Basics', 'Part-of-Whole', '1D Distributions', '2D Distributions'])
        self.assertEqual(CATEGORIES['basics'][1], ('scatter', 'line', 'area', 'bar', 'funnel'))
        for category in CATEGORIES:
            with patch('treedex.callbacks.ctx', SimpleNamespace(triggered_id={'value': category})):
                menu, value, label, opened = self.callbacks['choose_plot_type']([1])
            self.assertTrue(opened)
            self.assertIs(value, no_update)
            self.assertIn('back', [c.id['value'] for c in walk(menu) if isinstance(getattr(c, 'id', None), dict)])
        for kind in ('scatter', 'pie', *BASIC_PLOT_TYPES):
            with patch('treedex.callbacks.ctx', SimpleNamespace(triggered_id={'value': kind})):
                menu, value, label, opened = self.callbacks['choose_plot_type']([1])
            self.assertEqual(value, kind)
            self.assertFalse(opened)
            self.assertEqual(len(menu), 4)
        with patch('treedex.callbacks.ctx', SimpleNamespace(triggered_id={'value': 'line'})):
            self.assertEqual(self.callbacks['choose_plot_type']([0]), (no_update,) * 4)

    def test_all_api_parameters_have_controls_and_are_forwarded(self):
        for kind in BASIC_PLOT_TYPES:
            with self.subTest(kind=kind):
                options = self.options(kind)
                self.assertEqual(set(basic_kwargs(kind, options)), set(inspect.signature(getattr(px, kind)).parameters) - {'data_frame'})
                controls = []
                for page in range(1, len(option_pages(kind)) + 1):
                    menu = list(walk(basic_options_menu(kind, options, self.frame, page)))
                    controls.extend(c.id['name'] for c in menu if isinstance(getattr(c, 'id', None), dict) and c.id['type'] == 'basic-option')
                    self.assertEqual(sum(getattr(c, 'id', None) == 'build-basic-plot' for c in menu), 1)
                self.assertEqual(set(controls), set(default_basic_options(kind)))
                self.assertEqual(len(set(controls)), len(controls))
                self.assertTrue(all(len(page) <= 11 for page in option_pages(kind)))
                self.assertEqual(validate_basic_options(kind, options, self.frame), [])

    def test_line_order_sorting_date_axis_and_line_style(self):
        options = self.options('line', x=['Date'], y=['Y'], markers=True, line_shape='spline',
                               color='Group', line_dash='Group', symbol='Group',
                               color_discrete_map='{"A": "red", "B": "blue"}',
                               line_dash_map='{"A": "dash"}', symbol_map='{"A": "square"}')
        original = make_basic_plot('line', self.frame, **options)
        self.assertEqual(list(original.data[0].x), ['2026-01-03', '2026-01-01'])
        sorted_figure = make_basic_plot('line', self.frame, **{**options, 'sort_by': 'Date'})
        self.assertEqual(list(sorted_figure.data[0].x), ['2026-01-01', '2026-01-03'])
        self.assertEqual(sorted_figure.data[0].line.shape, 'spline')
        self.assertEqual(sorted_figure.data[0].line.dash, 'dash')
        self.assertEqual(sorted_figure.data[0].marker.symbol, 'square')
        self.assertEqual(list(self.frame.X), [3, 1, 2, 4])

    def test_area_stacking_patterns_and_wide_data(self):
        figure = make_basic_plot('area', self.frame, **self.options(
            'area', y=['Y', 'Other'], groupnorm='percent', pattern_shape='Group',
            pattern_shape_map='{"A": "/", "B": "x"}', markers=True))
        self.assertTrue(all(trace.stackgroup == '1' for trace in figure.data))
        self.assertTrue(all(trace.groupnorm == 'percent' for trace in figure.data))
        self.assertEqual({trace.fillpattern.shape for trace in figure.data}, {'/', 'x'})
        self.assertTrue(all(trace.customdata is not None for trace in figure.data))

    def test_bar_errors_base_continuous_color_text_and_layout(self):
        figure = make_basic_plot('bar', self.frame, **self.options(
            'bar', x=['Species'], y=['Y'], color='Other', color_continuous_scale='viridis',
            range_color='[0, 10]', color_continuous_midpoint=5, error_y='Error', base='X',
            text_auto='.2f', barmode='group', opacity=0.6, range_y='[0, 20]',
            labels='{"Y": "Quantity"}', title='Bars', subtitle='Subtitle', width=850, height=550))
        self.assertEqual(figure.layout.barmode, 'group')
        self.assertEqual(figure.layout.yaxis.title.text, 'Quantity')
        self.assertEqual(tuple(figure.layout.yaxis.range), (0, 20))
        self.assertEqual(figure.layout.title.subtitle.text, 'Subtitle')
        self.assertEqual(tuple(figure.data[0].error_y.array), tuple(self.frame.Error))
        self.assertEqual(figure.data[0].texttemplate, '%{y:.2f}')
        self.assertEqual(figure.layout.coloraxis.cmid, 5)
        self.assertEqual(figure.data[0].marker.opacity, 0.6)
        self.assertEqual((figure.layout.width, figure.layout.height), (850, 550))

    def test_funnel_orientation_hover_and_selection(self):
        figure = make_basic_plot('funnel', self.frame, selected_species=['b'], **self.options(
            'funnel', x=['Y'], y=['Species'], orientation='h', opacity=0.8,
            hover_data=['Other'], hover_data_format='{"Other": ":.2f"}', custom_data=['Group']))
        self.assertEqual(figure.data[0].type, 'funnel')
        self.assertEqual(figure.data[0].orientation, 'h')
        self.assertIn(':.2f', figure.data[0].hovertemplate)
        self.assertEqual(list(figure.data[0].marker.line.width), [0, 3, 0, 0])
        self.assertEqual(list(figure.data[0].customdata[1][:2]), ['b', 'A'])

    def test_facets_and_animation_for_all_four_types(self):
        for kind in BASIC_PLOT_TYPES:
            with self.subTest(kind=kind):
                figure = make_basic_plot(kind, self.frame, selected_species=['b'], **self.options(
                    kind, x=['X'], y=['Y'], facet_col='Group', facet_col_wrap=2,
                    facet_col_spacing=0.05, category_orders='{"Group": ["B", "A"]}'))
                self.assertEqual(len(figure.data), 2)
                self.assertEqual(figure.layout.annotations[0].text, 'Group=B')
                animated = make_basic_plot(kind, self.frame, selected_species=['b'], **self.options(
                    kind, x=['X'], y=['Y'], animation_frame='Group', animation_group='Species'))
                self.assertEqual(len(animated.frames), 2)
                self.assertTrue(all(frame.data[0].customdata is not None for frame in animated.frames))

    def test_validation_upload_and_invalid_json(self):
        for overrides in (
            {'x': []}, {'x': ['X', 'Other'], 'y': ['Y', 'Other']},
            {'width': -2}, {'height': 10.5}, {'facet_col_wrap': 1.5},
            {'facet_row': 'Group', 'facet_col_wrap': 2}, {'animation_group': 'Species'},
            {'error_y_minus': 'Error'}, {'range_x': '[1]'}, {'range_y': '[10, 0]'},
            {'labels': '{bad'}, {'labels': '{"missing": "A"}'},
            {'category_orders': '{"Group": "A"}'}, {'hover_data_format': '{"Y": 2}'},
        ):
            with self.subTest(overrides=overrides):
                self.assertTrue(validate_basic_options('line', self.options('line', **overrides), self.frame))
        options = normalize_basic_options('bar', {'x': ['missing'], 'y': ['Y'], 'color': 'Group'}, self.frame[['Species', 'X']])
        self.assertEqual(options['x'], ['X'])
        self.assertEqual(options['y'], ['X'])
        self.assertIsNone(options['color'])

    def test_options_and_pages_are_independent_and_survive_switches(self):
        store = {'line': {'title': 'First'}, 'bar': {'title': 'Second'}}
        pages = {'bar': 2, 'line': 3}
        for kind in BASIC_PLOT_TYPES:
            menu, scatter, pie = self.callbacks['show_plot_options'](
                kind, self.frame.to_dict('records'), 1, 1, pages, {}, {}, store)
            self.assertIs(scatter, no_update)
            self.assertIs(pie, no_update)
            self.assertTrue(any(getattr(c, 'id', None) == 'build-basic-plot' for c in walk(menu)))

    def test_build_snapshot_errors_selection_and_resizing(self):
        for kind in BASIC_PLOT_TYPES:
            with self.subTest(kind=kind):
                card, errors, built = self.build(kind, {'title': 'Built'})
                self.assertEqual(errors, '')
                self.assertEqual(card.children.id, 'basic-plot')
                self.assertTrue(card.children.responsive)
                self.assertEqual(built['type'], kind)
                card, _, _ = self.build(kind, {'title': 'Draft'}, built, 'selected-species', ['b'])
                self.assertEqual(card.children.figure.layout.title.text, 'Built')
                card, errors, state = self.build(kind, {'labels': '{broken'})
                self.assertIs(card, no_update)
                self.assertIs(state, no_update)
                self.assertTrue(errors)
                card, _, _ = self.build(kind, {'width': 900})
                self.assertFalse(card.children.responsive)
                self.assertEqual(card.children.style['width'], 900)
        with patch('treedex.callbacks.ctx', SimpleNamespace(triggered_id='basic-plot')):
            selected, rows = self.callbacks['synchronize_selection'](
                None, None, None, {'points': [{'customdata': ['b']}]}, [], [], self.frame.to_dict('records'), None)
        self.assertEqual(selected, ['b'])
        self.assertEqual(rows, [1])


if __name__ == '__main__':
    unittest.main()
