"""Controlli offline per il sistema di importazione progressiva di Cima Becco."""
import argparse
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent.parent / 'scripts'
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location('harvest_routes', SCRIPTS / 'harvest_routes.py')
harvest = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harvest)


def way(ref, points):
    return {'type': 'way', 'ref': ref, 'geometry': [
        {'lat': 46.51, 'lon': 11.60 + 0.002 * i} for i in points
    ]}


def sample():
    return {
        'type': 'relation', 'id': 891234,
        'tags': {'type': 'route', 'route': 'hiking', 'name': 'Sentiero di prova', 'ref': '666'},
        'members': [way(11, range(0, 5)), way(12, range(4, 11))],
    }


class HarvestRoutesTest(unittest.TestCase):
    def test_no_duplicate_grid_cells(self):
        cells = harvest.grid()
        ids = [cell['id'] for cell in cells]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreater(len(cells), 80)
        self.assertEqual(ids[0], 'it_46_11')
        self.assertEqual(cells[0]['bbox'], [46, 11, 47, 12])

    def test_checkpoint_resume(self):
        cells = harvest.grid()[:3]
        now = harvest.datetime(2026, 11, 27, tzinfo=harvest.timezone.utc)
        state = {'tiles': {cells[0]['id']: {'lastSuccess': '2026-11-27T00:00:00Z'}}}
        selected = harvest.due_cells(cells, state, now)
        self.assertEqual(selected[0]['id'], cells[1]['id'])

    def test_canonical_tile_assignment(self):
        route = {'coordinates': [[11.60, 46.51, 0], [11.62, 46.52, 0]]}
        self.assertTrue(harvest.in_own_cell(route, [46, 11, 47, 12]))
        self.assertFalse(harvest.in_own_cell(route, [46, 12, 47, 13]))

    def test_chunks_do_not_drop_routes(self):
        routes = [{'slug': 'r' + str(n)} for n in range(541)]
        parts = harvest.shard_files('it_46_11', routes)
        self.assertEqual(len(parts), 3)
        self.assertEqual(sum(len(part['routes']) for part in parts), 541)
        self.assertTrue(all(len(part['routes']) <= 200 for part in parts))

    def test_import_checkpoint_manifest_and_idempotency(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder)
            cell = harvest.grid()[0]
            status = {'version': 1, 'tiles': {}}
            with patch.object(harvest, 'DATA', data), patch.object(harvest, 'TILES_DIR', data / 'routes-tiles'):
                n = harvest.save_tile(cell, [sample()], status, '2026-11-27T10:00:00Z')
                self.assertEqual(n, 1)
                manifest = harvest.build_manifest(status, '2026-11-27T10:00:00Z')
                self.assertEqual(manifest['routeCount'], 1)
                self.assertEqual(manifest['lookup']['osm-hiking-891234'], cell['id'])
                paths = status['tiles'][cell['id']]['files']
                self.assertEqual(len(paths), 1)
                self.assertTrue((data / paths[0]).exists())
                # Una seconda importazione non introduce duplicati.
                n2 = harvest.save_tile(cell, [sample()], status, '2026-11-28T10:00:00Z')
                self.assertEqual(n2, 1)
                self.assertEqual(harvest.build_manifest(status, '2026-11-28')['routeCount'], 1)


if __name__ == '__main__':
    unittest.main()
