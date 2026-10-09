"""Pie option coverage, figure output, and dashboard callback integration."""

import inspect
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, no_update

from treedex.callbacks import register_callbacks
from treedex.components.pie import make_pie_plot
from treedex.layouts.main_layout import make_layout
from treedex.layouts.pie_options import pie_options_menu
from treedex.pie_options import (
    DEFAULT_PIE_OPTIONS, normalize_pie_options, pie_kwargs, validate_pie_options,
)


def components(component):
    if isinstance(component, (list, tuple)):
        for child in component:
            yield from components(child)
    elif hasattr(component, 'to_plotly_json'):
        yield component
        yield from components(getattr(component, 'children', []))


class PieFixture:
    def setUp(self):
        self.frame = pd.DataFrame({
            'Species': ['a', 'b', 'c', 'd'], 'Group': ['A', 'A', 'B', 'A'],
            'Value': [1., 2., 3., 4.], 'Facet': ['one', 'one', 'one', 'two'],
        })

    def options(self, **overrides):
        return normalize_pie_options(overrides, self.frame)


class PieTests(PieFixture, unittest.TestCase):
    def test_every_px_argument_has_controls(self):
        options = self.options()
        self.assertEqual(set(pie_kwargs(options)), set(inspect.signature(px.pie).parameters) - {'data_frame'})
        names = []
        for page in range(1, 4):
            menu = list(components(pie_options_menu(options, self.frame, page)))
            names.extend(c.id['name'] for c in menu if isinstance(getattr(c, 'id', None), dict) and c.id['type'] == 'pie-option')
            self.assertEqual(sum(getattr(c, 'id', None) == 'build-pie-plot' for c in menu), 1)
        self.assertEqual(set(names), set(DEFAULT_PIE_OPTIONS))
        self.assertEqual(len(names), len(set(names)))

    def test_count_rows_without_numeric_columns(self):
        frame = self.frame[['Species', 'Group']]
        options = normalize_pie_options({'names': 'Group'}, frame)
        self.assertEqual(validate_pie_options(options, frame), [])
        figure = make_pie_plot(frame, **options)
        self.assertIsNone(figure.data[0].values)
        self.assertEqual(list(figure.data[0].labels), ['A', 'A', 'B', 'A'])

    def test_full_figure_options_and_faceted_membership(self):
        options = self.options(
            names='Group', values='Value', color='Group', facet_col='Facet',
            facet_col_wrap=2, facet_col_spacing=0.1, facet_row_spacing=0.1,
            hole=0.45, opacity=0.7, title='Composition', subtitle='By group',
            width=900, height=500, custom_data=['Facet'], hover_name='Group',
            hover_data=['Value'], hover_data_format='{"Value": ":.2f"}',
            color_discrete_sequence='["red", "blue"]',
            color_discrete_map='{"A": "red", "B": "blue"}',
            labels='{"Value": "Abundance"}', category_orders='{"Group": ["B", "A"]}',
        )
        self.assertEqual(validate_pie_options(options, self.frame), [])
        figure = make_pie_plot(self.frame, selected_species=['b'], **options)
        self.assertEqual(len(figure.data), 2)
        self.assertEqual(figure.layout.title.text, 'Composition')
        self.assertEqual(figure.layout.title.subtitle.text, 'By group')
        self.assertEqual((figure.layout.width, figure.layout.height), (900, 500))
        first = figure.data[0]
        self.assertEqual(first.hole, 0.45)
        self.assertEqual(first.opacity, 0.7)
        self.assertEqual(first.meta['species_by_label']['A'], ['a', 'b'])
        self.assertEqual(figure.data[1].meta['species_by_label']['A'], ['d'])
        self.assertEqual(list(first.pull), [0, 0.08, 0.08])
        self.assertIn(':.2f', first.hovertemplate)
        self.assertEqual(list(first.customdata[0][:2]), ['one', 'c'])
        self.assertEqual(list(first.marker.colors), ['blue', 'red', 'red'])

    def test_row_facets_and_identity_colors(self):
        frame = self.frame.assign(Color=['red', 'red', 'blue', 'red'])
        options = normalize_pie_options({'names': 'Group', 'values': 'Value', 'color': 'Color',
                                         'color_discrete_map': 'identity', 'facet_row': 'Facet'}, frame)
        figure = make_pie_plot(frame, **options)
        self.assertEqual(len(figure.data), 2)
        self.assertEqual(set(figure.data[0].marker.colors), {'red', 'blue'})

    def test_invalid_options_report_errors(self):
        for overrides in (
            {'hole': 1.2}, {'opacity': -1}, {'width': 0}, {'height': 5.5},
            {'facet_col_wrap': 1.5}, {'facet_col_spacing': 2},
            {'facet_row': 'Group', 'facet_col_wrap': 2},
            {'color_discrete_map': '{broken'}, {'color_discrete_map': '["red"]'},
            {'color_discrete_sequence': '[]'}, {'color_discrete_sequence': '[1]'},
            {'category_orders': '{"Group": "A"}'}, {'labels': '{"missing": "Label"}'},
            {'hover_data_format': '{"Value": 12}'}, {'hover_data_format': '{"missing": true}'},
        ):
            with self.subTest(overrides=overrides):
                self.assertTrue(validate_pie_options(self.options(**overrides), self.frame))
        for values in ([-1, 1, 2, 3], [0, 0, 0, 0], [1, float('nan'), 2, 3], [1, float('inf'), 2, 3]):
            frame = self.frame.assign(Value=values)
            self.assertTrue(validate_pie_options(self.options(values='Value'), frame))

    def test_upload_normalizes_column_choices(self):
        options = normalize_pie_options(self.options(names='Group', values='Value', color='Group',
                                                     hover_data=['Group'], custom_data=['Value']),
                                        self.frame[['Species']])
        self.assertEqual(options['names'], 'Species')
        self.assertIsNone(options['values'])
        self.assertIsNone(options['color'])
        self.assertEqual(options['hover_data'], [])
        self.assertEqual(options['custom_data'], [])


class PieCallbackTests(PieFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.app = Dash(__name__, suppress_callback_exceptions=True)
        self.app.layout = make_layout(self.frame, go.Figure())
        register_callbacks(self.app, self.frame, self.frame)
        self.callbacks = {entry['callback'].__wrapped__.__name__: entry['callback'].__wrapped__
                          for entry in self.app.callback_map.values() if 'callback' in entry}

    def build(self, trigger, *, pie=None, scatter=None, built=None, selected=None, values=None, ids=None):
        with patch('treedex.callbacks.ctx', SimpleNamespace(triggered_id=trigger)):
            return self.callbacks['build_plot'](1, 1, 0, selected or [], scatter, pie,
                                                self.frame.to_dict('records'), built,
                                                values or [], ids or [], [], [], None, {}, [], [])

    def test_dash_layout_and_dependencies_serialize(self):
        client = self.app.server.test_client()
        self.assertEqual(client.get('/_dash-layout').status_code, 200)
        self.assertEqual(client.get('/_dash-dependencies').status_code, 200)

    def test_pages_and_plot_types_keep_independent_options(self):
        show = self.callbacks['show_plot_options']
        scatter = {'title': 'My scatter'}
        pie = self.options(hole=0.4)
        for page in range(1, 4):
            menu, scatter_result, pie_result = show('pie', self.frame.to_dict('records'), 1, page, {}, scatter, pie, {})
            self.assertIs(scatter_result, no_update)
            self.assertEqual(pie_result['hole'], 0.4)
        _, scatter_result, pie_result = show('scatter', self.frame.to_dict('records'), 1, 3, {}, scatter, pie, {})
        self.assertEqual(scatter_result['title'], 'My scatter')
        self.assertIs(pie_result, no_update)
        with patch('treedex.callbacks.ctx', SimpleNamespace(triggered_id={'page': 3})):
            self.assertIs(self.callbacks['change_pie_page']([0, 0, 0]), no_update)
            self.assertEqual(self.callbacks['change_pie_page']([0, 0, 1]), 3)

    def test_build_snapshot_and_live_fields(self):
        card, error, built = self.build('build-pie-plot', pie=self.options(),
                                      values=[0.5], ids=[{'type': 'pie-option', 'name': 'hole'}])
        self.assertEqual(error, '')
        self.assertEqual(card.children.id, 'pie-plot')
        self.assertTrue(card.children.responsive)
        self.assertEqual(card.children.figure.data[0].hole, 0.5)
        # Draft edits must not change the displayed plot on a tree/table click.
        card, _, _ = self.build('selected-species', pie=self.options(hole=0.9), built=built, selected=['a'])
        self.assertEqual(card.children.figure.data[0].hole, 0.5)
        self.assertEqual(card.children.figure.data[0].pull[0], 0.08)
        card, _, _ = self.build('build-pie-plot', pie=self.options(width=800))
        self.assertFalse(card.children.responsive)
        self.assertEqual(card.children.style['width'], 800)
        card, _, built = self.build('build-scatter-plot', scatter={'x': 'Value', 'y': 'Value'})
        self.assertEqual(card.children.id, 'scatter-plot')
        self.assertEqual(built['type'], 'scatter')

    def test_errors_preserve_previous_plot(self):
        for options in (self.options(hole=2), self.options(color_discrete_sequence='["not-a-color"]')):
            card, error, built = self.build('build-pie-plot', pie=options)
            self.assertIs(card, no_update)
            self.assertTrue(error)
            self.assertIs(built, no_update)

    def test_pie_click_selects_all_species_in_slice_and_facet(self):
        figure = make_pie_plot(self.frame, **self.options(names='Group', values='Value', facet_col='Facet'))
        with patch('treedex.callbacks.ctx', SimpleNamespace(triggered_id='pie-plot')):
            selected, rows = self.callbacks['synchronize_selection'](
                None, None, {'points': [{'curveNumber': 0, 'label': 'A'}]}, None, [], [],
                self.frame.to_dict('records'), figure.to_plotly_json())
        self.assertEqual(selected, ['a', 'b'])
        self.assertEqual(rows, [0, 1])


if __name__ == '__main__':
    unittest.main()
