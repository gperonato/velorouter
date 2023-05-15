#!/usr/bin/env python3

import unittest
import os
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
        self.assertAlmostEqual(height_gain, 120 + 180, delta=height_gain * TOLERANCE)
        self.assertAlmostEqual(height_loss, 180 + 260, delta=height_loss * TOLERANCE)
        self.assertAlmostEqual(length_unpaved, 3 + 1, delta=length_unpaved * TOLERANCE)


if __name__ == "__main__":
    unittest.main()
