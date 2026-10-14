"""Part-of-Whole API, hierarchy aggregation, and dashboard integration coverage."""

import base64
import inspect
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from dash import Dash, no_update
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from treedex.callbacks import register_callbacks
from treedex.components.hierarchy import make_hierarchy_plot
from treedex.hierarchy_options import (
    HIERARCHY_PLOT_TYPES, default_hierarchy_options, hierarchy_kwargs,
    normalize_hierarchy_options, option_pages, validate_hierarchy_options,
)
from treedex.layouts.hierarchy_options import hierarchy_options_menu
from treedex.layouts.main_layout import make_layout
from treedex.layouts.plot_picker import CATEGORIES, picker_items


def walk(component):
    if isinstance(component, (list, tuple)):
        for child in component:
            yield from walk(child)
    elif hasattr(component, 'to_plotly_json'):
        yield component
        yield from walk(getattr(component, 'children', []))


class HierarchyFixture:
    def setUp(self):
        self.frame = pd.DataFrame({
            'Species': ['a', 'b', 'c', 'd'], 'Order': ['M', 'M', 'N', 'N'],
            'Family': ['Same', 'Same', 'Same', 'Other'], 'Weight': [1, 3, 2, 4],
            'Metric': [10, 20, 30, 40],
        })

    def options(self, kind='sunburst', frame=None, **values):
        return normalize_hierarchy_options(kind, values, self.frame if frame is None else frame)


class HierarchyTests(HierarchyFixture, unittest.TestCase):
    def test_api_coverage_and_paginated_controls_for_all_types(self):
        self.assertEqual(CATEGORIES['part-of-whole'][1], ('pie', *HIERARCHY_PLOT_TYPES))
        buttons = [c.id['value'] for c in walk(picker_items('part-of-whole'))
                   if isinstance(getattr(c, 'id', None), dict)]
        self.assertEqual(buttons, ['back', 'pie', *HIERARCHY_PLOT_TYPES])
        for kind in HIERARCHY_PLOT_TYPES:
            with self.subTest(kind=kind):
                options = self.options(kind)
                self.assertEqual(set(hierarchy_kwargs(kind, options)),
                                 set(inspect.signature(getattr(px, kind)).parameters) - {'data_frame'})
                controls = []
                for page in range(1, len(option_pages(kind)) + 1):
                    menu = list(walk(hierarchy_options_menu(kind, options, self.frame, page)))
                    controls.extend(c.id['name'] for c in menu if isinstance(getattr(c, 'id', None), dict)
                                    and c.id['type'] == 'hierarchy-option')
                    self.assertEqual(sum(getattr(c, 'id', None) == 'build-hierarchy-plot' for c in menu), 1)
                self.assertEqual(set(controls), set(default_hierarchy_options(kind)))
                self.assertEqual(len(controls), len(set(controls)))
                self.assertTrue(all(len(page) <= 11 for page in option_pages(kind)))
                self.assertEqual(validate_hierarchy_options(kind, options, self.frame), [])
                nodes = list(walk(hierarchy_options_menu(kind, self.options(kind, hierarchy_mode='nodes'), self.frame)))
                states = {c.id['name']: c.disabled for c in nodes if isinstance(getattr(c, 'id', None), dict)
                          and c.id['type'] == 'hierarchy-option'}
                self.assertTrue(states['path'])
                self.assertFalse(states['parents'])

    def test_column_hierarchies_aggregate_values_and_membership_by_id(self):
        for kind in HIERARCHY_PLOT_TYPES:
            with self.subTest(kind=kind):
                options = self.options(kind, path=['Order', 'Family', 'Species'], values='Weight')
                figure = make_hierarchy_plot(kind, self.frame, selected_species=['B'], **options)
                trace = figure.data[0]
                self.assertEqual(trace.type, kind)
                values = dict(zip(trace.ids, trace.values))
                self.assertEqual(values['All species'], 10)
                self.assertEqual(values['All species/M/Same'], 4)
                self.assertEqual(values['All species/N/Same'], 2)
                membership = trace.meta['species_by_id']
                self.assertEqual(membership['All species'], ['a', 'b', 'c', 'd'])
                self.assertEqual(membership['All species/M/Same'], ['a', 'b'])
                self.assertEqual(membership['All species/N/Same'], ['c'])
                widths = dict(zip(trace.ids, trace.marker.line.width))
                self.assertEqual(widths['All species/M/Same/b'], 3)
                self.assertEqual(widths['All species/M/Same'], 3)
                self.assertEqual(widths['All species/N/Same'], 0)
                self.assertEqual(trace.branchvalues, 'total')

    def test_row_counts_flat_default_and_supplied_dashboard_data(self):
        sample = pd.read_csv(Path(__file__).resolve().parents[1] / 'species_information.csv')
        for kind in HIERARCHY_PLOT_TYPES:
            with self.subTest(kind=kind):
                grouped = make_hierarchy_plot(kind, self.frame, **self.options(kind, path=['Order']))
                self.assertEqual(dict(zip(grouped.data[0].ids, grouped.data[0].values)),
                                 {'All species/M': 2, 'All species/N': 2, 'All species': 4})
                default = make_hierarchy_plot(kind, sample, **self.options(kind, frame=sample))
                self.assertEqual(default.data[0].meta['species_by_id']['All species'], sample.Species.tolist())
                no_root = make_hierarchy_plot(kind, self.frame, **self.options(kind, path=['Order', 'Species'], root_label=None))
                self.assertNotIn('All species', no_root.data[0].ids)

    def test_color_hover_labels_depth_and_size_are_forwarded(self):
        for kind in HIERARCHY_PLOT_TYPES:
            with self.subTest(kind=kind):
                options = self.options(kind, path=['Order', 'Species'], values='Weight', color='Metric',
                                       hover_name='Species', hover_data=['Weight'], custom_data=['Family'],
                                       hover_data_format='{"Weight": ":.2f"}', color_continuous_scale='viridis',
                                       range_color='[0, 100]', color_continuous_midpoint=25, maxdepth=2,
                                       title='Taxonomy', subtitle='Measured weights', labels='{"Weight": "Abundance"}',
                                       width=850, height=600)
                figure = make_hierarchy_plot(kind, self.frame, **options)
                self.assertEqual(figure.data[0].maxdepth, 2)
                self.assertIn('Abundance', figure.data[0].hovertemplate)
                self.assertIn(':.2f', figure.data[0].hovertemplate)
                self.assertIsNotNone(figure.data[0].customdata)
                self.assertEqual(figure.layout.coloraxis.cmid, 25)
                self.assertEqual((figure.layout.coloraxis.cmin, figure.layout.coloraxis.cmax), (0, 100))
                self.assertEqual(figure.layout.title.text, 'Taxonomy')
                self.assertEqual(figure.layout.title.subtitle.text, 'Measured weights')
                self.assertEqual((figure.layout.width, figure.layout.height), (850, 600))
                discrete = make_hierarchy_plot(kind, self.frame, **self.options(
                    kind, path=['Order', 'Species'], color='Order', color_discrete_map='{"M": "red", "N": "blue"}'))
                self.assertIn('red', discrete.data[0].marker.colors)
                self.assertIn('blue', discrete.data[0].marker.colors)
                css_frame = self.frame.assign(CSS=['red', 'red', 'blue', 'blue'])
                identity = make_hierarchy_plot(kind, css_frame, **self.options(
                    kind, frame=css_frame, path=['Order', 'Species'], color='CSS', color_discrete_map='identity'))
                self.assertIn('red', identity.data[0].marker.colors)
                self.assertIn('blue', identity.data[0].marker.colors)

    def test_explicit_node_ids_duplicate_labels_and_descendant_membership(self):
        frame = pd.DataFrame({'Species': ['root', 'a', 'b'], 'Node': ['Life', 'Same', 'Same'],
                              'ID': [1, 2, 3], 'Parent': [None, 1, 1], 'Weight': [5, 2, 3]})
        for kind in HIERARCHY_PLOT_TYPES:
            with self.subTest(kind=kind):
                options = self.options(kind, frame=frame, hierarchy_mode='nodes', names='Node', ids='ID',
                                       parents='Parent', values='Weight')
                figure = make_hierarchy_plot(kind, frame, selected_species=['a'], **options)
                trace = figure.data[0]
                self.assertEqual(list(trace.parents), ['', '1', '1'])
                self.assertEqual(list(trace.labels), ['Life', 'Same', 'Same'])
                self.assertEqual(trace.meta['species_by_id']['1'], ['root', 'a', 'b'])
                self.assertEqual(list(trace.marker.line.width), [3, 3, 0])
                remainder = make_hierarchy_plot(kind, frame, **{**options, 'branchvalues': 'remainder'})
                self.assertEqual(remainder.data[0].branchvalues, 'remainder')

    def test_invalid_options_and_invalid_tree_structures(self):
        bad = [
            {'path': []}, {'path': ['missing']}, {'branchvalues': 'remainder'}, {'maxdepth': 0},
            {'maxdepth': -2}, {'maxdepth': 1.5}, {'width': 9}, {'height': 10.5},
            {'color_continuous_midpoint': float('inf')}, {'range_color': '[5, 1]'},
            {'range_color': '[1]'}, {'range_color': '[0, "x"]'}, {'labels': '{bad'},
            {'labels': '{"missing": "A"}'}, {'labels': '{"Weight": 2}'},
            {'color_discrete_sequence': '[]'}, {'color_discrete_sequence': '[2]'},
            {'color_discrete_map': '{"A": 2}'}, {'hover_data_format': '{"Weight": 2}'},
            {'hover_data_format': '{"missing": true}'}, {'hierarchy_mode': 'unknown'},
            {'hierarchy_mode': 'nodes'}, {'root_label': 'A/B'},
        ]
        for kind in HIERARCHY_PLOT_TYPES:
            for overrides in bad:
                with self.subTest(kind=kind, overrides=overrides):
                    self.assertTrue(validate_hierarchy_options(kind, self.options(kind, **overrides), self.frame))
            for weights in ([-1, 1, 2, 3], [0, 0, 0, 0], [1, float('nan'), 2, 3], [1, float('inf'), 2, 3]):
                self.assertTrue(validate_hierarchy_options(kind, self.options(kind, values='Weight'), self.frame.assign(Weight=weights)))
        for ids, parents in ((['a', 'a', 'c'], ['', 'a', 'a']), (['a', 'b', 'c'], ['', 'missing', 'a']),
                             (['a', 'b', 'c'], ['b', 'c', 'a']), (['a', 'b', 'c'], ['', 'b', 'a']),
                             (['', 'b', 'c'], ['', '', 'b'])):
            frame = pd.DataFrame({'Species': ['a', 'b', 'c'], 'ID': ids, 'Parent': parents})
            options = self.options(frame=frame, hierarchy_mode='nodes', names='Species', ids='ID', parents='Parent')
            self.assertTrue(validate_hierarchy_options('sunburst', options, frame))
        frame = pd.DataFrame({'Species': ['a', 'b', 'c'], 'Parent': ['', 'a', 'a'], 'Value': [1, 2, 3]})
        options = self.options(frame=frame, hierarchy_mode='nodes', names='Species', parents='Parent', values='Value')
        self.assertTrue(validate_hierarchy_options('sunburst', options, frame))
        self.assertEqual(validate_hierarchy_options('sunburst', {**options, 'branchvalues': 'remainder'}, frame), [])

    def test_missing_leaf_levels_and_column_changes(self):
        frame = pd.DataFrame({'Species': ['a', 'b'], 'Group': ['M', 'N'], 'Leaf': ['a', None], 'Value': [2, 3]})
        for kind in HIERARCHY_PLOT_TYPES:
            options = self.options(kind, frame=frame, path=['Group', 'Leaf'], values='Value')
            trace = make_hierarchy_plot(kind, frame, **options).data[0]
            self.assertEqual(trace.meta['species_by_id']['All species/N'], ['b'])
            with self.assertRaises(ValueError):
                make_hierarchy_plot(kind, frame.assign(Group=['M', 'M']), **options)
            updated = normalize_hierarchy_options(kind, self.options(kind, path=['Order', 'Species'], values='Weight',
                                                  color='Order', hover_data=['Weight']), self.frame[['Species']])
            self.assertEqual(updated['path'], ['Species'])
            self.assertIsNone(updated['values'])
            self.assertIsNone(updated['color'])
            self.assertEqual(updated['hover_data'], [])
            self.assertTrue(validate_hierarchy_options(kind, normalize_hierarchy_options(kind, options, frame.iloc[:0]), frame.iloc[:0]))


class HierarchyCallbackTests(HierarchyFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.app = Dash(__name__, suppress_callback_exceptions=True,
                        assets_folder=str(Path(__file__).resolve().parents[1] / 'src/treedex/assets'))
        self.app.layout = make_layout(self.frame, go.Figure())
        register_callbacks(self.app, self.frame, self.frame)
        self.callbacks = {entry['callback'].__wrapped__.__name__: entry['callback'].__wrapped__
                          for entry in self.app.callback_map.values() if 'callback' in entry}

    def build(self, kind, options=None, built=None, trigger='build-hierarchy-plot', selected=None, values=None, ids=None):
        with patch('treedex.callbacks.ctx', SimpleNamespace(triggered_id=trigger)):
            return self.callbacks['build_plot'](
                0, 0, 0, selected or [], {}, {}, self.frame.to_dict('records'), built,
                [], [], [], [], kind, {}, [], [], 1, {kind: options or {}}, values or [], ids or [],
            )

    def test_independent_drafts_pages_live_values_snapshots_and_resizing(self):
        store = {'sunburst': {'title': 'First'}, 'treemap': {'title': 'Second'}, 'icicle': {'title': 'Third'}}
        pages = {'sunburst': 3, 'treemap': 2, 'icicle': 1}
        for kind in HIERARCHY_PLOT_TYPES:
            with self.subTest(kind=kind):
                menu, scatter, pie = self.callbacks['show_plot_options'](
                    kind, self.frame.to_dict('records'), 1, 1, {}, {}, {}, {}, pages, store)
                self.assertIs(scatter, no_update)
                self.assertIs(pie, no_update)
                active = [c for c in walk(menu) if 'is-active' in getattr(c, 'className', '')]
                self.assertEqual(active[0].id['page'], pages[kind])
                card, error, built = self.build(kind, {'path': ['Order', 'Species']}, values=['Built title'],
                                              ids=[{'type': 'hierarchy-option', 'plot': kind, 'name': 'title'}])
                self.assertEqual(error, '')
                self.assertEqual(card.children.id, 'hierarchy-plot')
                self.assertTrue(card.children.responsive)
                self.assertEqual(card.children.figure.data[0].type, kind)
                self.assertEqual(built['type'], kind)
                card, error, _ = self.build('bar', {'title': 'Draft title'}, built, 'selected-species', ['b'])
                self.assertEqual(card.children.figure.layout.title.text, 'Built title')
                self.assertIn(3, card.children.figure.data[0].marker.line.width)
                card, error, _ = self.build(kind, {'width': 900})
                self.assertFalse(card.children.responsive)
                self.assertEqual(card.children.style['width'], 900)
                for bad in ({'path': []}, {'labels': '{broken'}, {'color_discrete_sequence': '["not-a-color"]'}):
                    card, error, state = self.build(kind, bad, built)
                    self.assertIs(card, no_update)
                    self.assertIs(state, no_update)
                    self.assertTrue(error)

    def test_hierarchy_click_selects_parent_descendants_and_distinguishes_same_labels(self):
        for kind in HIERARCHY_PLOT_TYPES:
            figure = make_hierarchy_plot(kind, self.frame, **self.options(kind, path=['Order', 'Family', 'Species']))
            with patch('treedex.callbacks.ctx', SimpleNamespace(triggered_id='hierarchy-plot')):
                for node, expected in (('All species/M/Same', ['a', 'b']), ('All species/N/Same', ['c']),
                                       ('All species', ['a', 'b', 'c', 'd'])):
                    selected, rows = self.callbacks['synchronize_selection'](
                        None, None, None, None, [], [], self.frame.to_dict('records'), None,
                        {'points': [{'curveNumber': 0, 'id': node}]}, figure.to_plotly_json())
                    self.assertEqual(selected, expected)
                    self.assertEqual(rows, [i for i, value in enumerate(self.frame.Species) if value in expected])
                index = list(figure.data[0].ids).index('All species/M/Same')
                selected, _ = self.callbacks['synchronize_selection'](
                    None, None, None, None, [], [], self.frame.to_dict('records'), None,
                    {'points': [{'pointNumber': index}]}, figure.to_plotly_json())
                self.assertEqual(selected, ['a', 'b'])

    def test_dash_http_dispatch_layout_dependencies_assets_and_build(self):
        client = self.app.server.test_client()
        for url in ('/_dash-layout', '/_dash-dependencies', '/assets/hierarchy_options.js'):
            self.assertEqual(client.get(url).status_code, 200)
        key, entry = next((key, entry) for key, entry in self.app.callback_map.items()
                          if 'callback' in entry and entry['callback'].__wrapped__.__name__ == 'build_plot')
        for kind in HIERARCHY_PLOT_TYPES:
            props = {
                ('build-hierarchy-plot', 'n_clicks'): 1, ('selected-species', 'data'): [],
                ('plot-type-selector', 'value'): kind, ('species-table', 'data'): self.frame.to_dict('records'),
                ('hierarchy-options-store', 'data'): {kind: {'path': ['Order', 'Species']}},
            }
            response = client.post('/_dash-update-component', json={
                'output': key,
                'outputs': [{'id': output.component_id, 'property': output.component_property} for output in entry['output']],
                'inputs': [{**item, 'value': props.get((item['id'], item['property']), [] if item['id'].startswith('{') else None)} for item in entry['inputs']],
                'state': [{**item, 'value': props.get((item['id'], item['property']), [] if item['id'].startswith('{') else None)} for item in entry['state']],
                'changedPropIds': ['build-hierarchy-plot.n_clicks'],
            })
            self.assertEqual(response.status_code, 200)
            result = response.get_json()['response']
            self.assertEqual(result['scatter-validation-message']['children'], '')
            self.assertEqual(result['built-plot']['data']['type'], kind)
            self.assertEqual(result['main-plot-area']['children']['props']['children']['props']['figure']['data'][0]['type'], kind)

    def test_uploaded_taxonomy_columns_feed_menus_and_builders(self):
        csv = 'Species,Taxon,Abundance\na,Mammals,2\nb,Mammals,3\nc,Birds,5\n'
        contents = 'data:text/csv;base64,' + base64.b64encode(csv.encode()).decode()
        data, columns, rows, selected, status = self.callbacks['upload_data'](contents, 'taxonomy.csv')
        self.assertEqual(rows, [])
        self.assertEqual(selected, [])
        self.assertEqual([col['id'] for col in columns], ['Species', 'Taxon', 'Abundance'])
        self.frame = pd.DataFrame(data)
        for kind in HIERARCHY_PLOT_TYPES:
            menu, _, _ = self.callbacks['show_plot_options'](kind, data, 1, 1, {}, {}, {}, {}, {}, {
                kind: {'path': ['Order', 'Species'], 'values': 'Weight'},
            })
            path_control = next(c for c in walk(menu) if isinstance(getattr(c, 'id', None), dict)
                                and c.id.get('name') == 'path')
            self.assertEqual(path_control.value, ['Species'])
            self.assertEqual([choice['value'] for choice in path_control.options], ['Species', 'Taxon', 'Abundance'])
            card, error, _ = self.build(kind, {'path': ['Taxon', 'Species'], 'values': 'Abundance'})
            self.assertEqual(error, '')
            trace = card.children.figure.data[0]
            self.assertEqual(dict(zip(trace.ids, trace.values))['All species/Mammals'], 5)


if __name__ == '__main__':
    unittest.main()
