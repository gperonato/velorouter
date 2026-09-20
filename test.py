#!/usr/bin/env python3

import unittest
import os
import base64
import shutil
import tempfile
import networkx as nx
from shapely.geometry import LineString
import router
from router import *


TOLERANCE = 0.1  # 10%
G = load_graph()


def get_kpis(segments):
    """Calculate cumulated values"""

    length = segments["length_km"].sum().round()
    height_gain = segments["height_gain_m"].sum().round()
    height_loss = segments["height_loss_m"].sum().round()
    length_unpaved = segments["length_unpaved_km"].sum().round()

    return length, height_gain, height_loss, length_unpaved


class DESTEST(unittest.TestCase):
    def test_figures_1(self):
        """
        Test Berner Oberland-Route Stage 1
        https://schweizmobil.ch/en/cycling-in-switzerland/route-61/stage-1
        """
        origin = "Steffisburg"
        destination = "Interlaken"
        via = ["Sigriswil"]
        segments = get_path(G, origin, destination, via)

        length, height_gain, height_loss, length_unpaved = get_kpis(segments)

        self.assertAlmostEqual(length, 45, delta=length * TOLERANCE)
        self.assertAlmostEqual(height_gain, 1200, delta=height_gain * TOLERANCE)
        self.assertAlmostEqual(height_loss, 1150, delta=height_loss * TOLERANCE)
        self.assertAlmostEqual(length_unpaved, 0, delta=length_unpaved * TOLERANCE)

    def test_figures_2(self):
        """
        Test Rhone Route Stage 4 and 5
        https://schweizmobil.ch/en/cycling-in-switzerland/route-1/stage-4
        https://schweizmobil.ch/en/cycling-in-switzerland/route-1/stage-5
        """
        origin = "Sierre"
        destination = "Montreux"
        via = []
        segments = get_path(G, origin, destination, via)

        length, height_gain, height_loss, length_unpaved = get_kpis(segments)

        self.assertAlmostEqual(length, 44 + 48, delta=length * TOLERANCE)
        self.assertAlmostEqual(height_gain, 90 + 160, delta=height_gain * TOLERANCE)
        self.assertAlmostEqual(height_loss, 150 + 240, delta=height_loss * TOLERANCE)
        self.assertAlmostEqual(length_unpaved, 3 + 0, delta=length_unpaved * TOLERANCE)

    def test_cross_border_reachability(self):
        """Belfort (FR) became reachable from Basel with the 2026 Veloland update"""
        segments = get_path(G, "Basel", "Belfort")
        self.assertGreater(len(segments), 0)


# The tests below build a small synthetic network instead of using the real
# graph, so they need neither the source datasets nor graph.p / graph.gml.

CRS = "EPSG:2056"  # Swiss LV95, metres

# Nodes are (x, y, z) tuples, as produced by momepy.gdf_to_nx on 3D input.
A = (0.0, 0.0, 0.0)  # origin
B = (1000.0, 0.0, 0.0)  # junction
C = (2000.0, 0.0, 0.0)  # destination
D = (1000.0, 1000.0, 100.0)  # via: a spur 100 m above the junction


def build_graph():
    """Build a T-shaped network whose "via" leg is a dead end

        D  (via, +100 m)
        |
    A---B---C

    Routing Alpha -> Delta -> Charlie has to use edge B-D twice: uphill on
    leg 0, downhill on leg 1. That is the ordinary case of a via location
    that does not sit on the through route.
    """
    G = nx.Graph(crs=CRS)
    for start, end in ((A, B), (B, D), (B, C)):
        line = LineString([start, end])
        G.add_edge(start, end, geometry=line, mm_len=line.length, BelagTLM="hart")
    for node, name in ((A, "Alpha"), (C, "Charlie"), (D, "Delta")):
        G.nodes[node]["location"] = name
    return G


def edge_state(G):
    """Snapshot the attribute names and geometry of every edge"""

    return {
        frozenset((u, v)): (frozenset(data), tuple(data["geometry"].coords))
        for u, v, data in G.edges(data=True)
    }


class SharedGraphTest(unittest.TestCase):
    """get_path() must not write into the graph it is given"""

    def setUp(self):
        self.G = build_graph()

    def test_graph_is_left_untouched(self):
        """The graph is a process-wide singleton, so routing must not write to it"""

        before = edge_state(self.G)

        get_path(self.G, "Alpha", "Charlie", ["Delta"])

        self.assertEqual(
            before,
            edge_state(self.G),
            "get_path() wrote routing attributes and/or a reversed geometry "
            "back into the shared graph",
        )

    def test_backtracked_segment_keeps_its_own_direction(self):
        """Climbing B->D then descending D->B is +100 m and -100 m, not -200 m"""

        segments = get_path(self.G, "Alpha", "Charlie", ["Delta"])

        self.assertAlmostEqual(100.0, segments["height_gain_m"].sum(), places=6)
        self.assertAlmostEqual(100.0, segments["height_loss_m"].sum(), places=6)


SENTINEL = b"PRIVATE-FILE-OUTSIDE-THE-GPX-DIRECTORY"


class DownloadTraversalTest(unittest.TestCase):
    """The download callback must not read outside ./gpx"""

    @classmethod
    def setUpClass(cls):
        # app.py calls load_graph() at import time; swap in the synthetic one
        # before "from router import *" binds the name.
        cls.real_load_graph = router.load_graph
        router.load_graph = build_graph
        import app

        cls.app = app

    @classmethod
    def tearDownClass(cls):
        router.load_graph = cls.real_load_graph

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="velorouter_traversal_")
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)
        # Reach the directory the way a remote caller would have to: relative
        # to the working directory, since the callback prefixes "./gpx/".
        self.escape = os.path.relpath(self.tmpdir, os.getcwd())
        self.assertNotIn(" ", self.escape, "callback rewrites spaces to underscores")

    def plant(self, stem):
        """Create <stem>.gpx in the directory that self.escape reaches"""

        with open(os.path.join(self.tmpdir, stem + ".gpx"), "wb") as f:
            f.write(SENTINEL)

    def served(self, *args):
        """Return whatever bytes the callback handed back, if it returned at all"""

        try:
            result = self.app.download(*args)
        except Exception:
            # Refusing the request is a valid fix; what matters is the bytes.
            return b""
        if not result:
            return b""
        content = result.get("content", b"")
        if result.get("base64"):
            return base64.b64decode(content)
        return content.encode() if isinstance(content, str) else content

    def test_origin_cannot_escape_the_gpx_directory(self):
        # "./gpx/" + "../<tmpdir>/leak" + "-" + "target" + ".gpx"
        self.plant("leak-target")
        origin = "../{}/leak".format(self.escape)

        self.assertNotIn(
            SENTINEL,
            self.served(1, origin, "target", None),
            "download() served a file from outside ./gpx",
        )

    def test_slash_in_location_name_stays_in_the_gpx_directory(self):
        """Bilingual names such as "Biel/Bienne" are valid locations"""

        file_path = self.app.get_gpx_path("Biel/Bienne", "Interlaken")

        self.assertEqual(
            os.path.realpath(self.app.GPX_DIR),
            os.path.dirname(os.path.realpath(file_path)),
            "a location name containing a separator escaped the gpx directory",
        )


if __name__ == "__main__":
    unittest.main()
