#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2023 Giuseppe Peronato
#
# SPDX-License-Identifier: AGPL-3.0-only

"""
Create and query the path network

@author: gperonato
"""

import os

os.environ["USE_PYGEOS"] = "0"
import pickle
import geopandas as gpd
import pandas as pd
import networkx as nx
import dash_leaflet as dl
import momepy
import numpy as np
from shapely import ops
from shapely.geometry import Point, MultiLineString, LineString
from shapely.geometry.base import BaseGeometry
from shapely import wkt
from pyproj import crs
import ast


def calc_height_diff(line, start):
    """Calculate height difference and losses of each segment"""

    height_gain = 0
    height_loss = 0
    coords = line.coords
    for c in range(len(coords) - 1):
        diff = coords[c + 1][-1] - coords[c][-1]
        if diff > 0:
            height_gain += diff
        else:
            height_loss += -diff
    return pd.Series([height_gain, height_loss])


def load_graph():
    """Prepare the NetworkX graph or load local file"""
    if os.path.exists("graph.p"):
        with open("graph.p", "rb") as f:
            G = pickle.load(f)
    elif os.path.exists("graph.gml"):
        G = nx.read_gml("graph.gml")
        for u, v, data in G.edges(data=True):
            G[u][v]["geometry"] = wkt.loads(G[u][v]["geometry"])
        nx.relabel_nodes(G, {x: ast.literal_eval(x) for x in G.nodes}, False)
        G.graph["crs"] = crs.CRS(G.graph["crs"])
    else:
        paths = gpd.read_file("data/veloland.gdb", layer="weg")

        locations = gpd.read_file(
            os.path.join(
                "data", "swisstlmregio_2022_2056.gdb", "swissTLMRegio_Produkt_LV95.gdb"
            ),
            layer="TLMRegio_NamedLocation",
        )

        paths = paths.explode(index_parts=False)

        # Keep only relevant attributes
        paths = paths[["BelagTLM", "geometry"]]

        G = momepy.gdf_to_nx(paths, approach="primal", multigraph=False)

        nodes = pd.DataFrame(G.nodes(data=True), columns=["node", "attributes"])
        nodes["geometry"] = nodes.apply(lambda x: Point(x["node"]), axis=1)
        nodes = gpd.GeoDataFrame(nodes,)
        nodes = nodes.set_crs(G.graph["crs"])

        closest_nodes = nodes.sjoin_nearest(
            locations, how="left", distance_col="distances"
        )

        # Create a dict {node: closest_location_name}
        closest_locations = (
            closest_nodes[["node", "NAMN1", "distances"]]
            .sort_values("distances")
            .groupby("NAMN1")
            .first()
            .reset_index()
            .set_index("node")["NAMN1"]
            .to_dict()
        )
        nx.set_node_attributes(G, closest_locations, "location")

        # Save pickle
        with open("graph.p", "wb") as f:
            pickle.dump(G, f)

        # Save in GML (Graph Modelling Language)
        def stringify(s):
            if isinstance(s, tuple):
                return str(s)
            elif isinstance(s, crs.CRS):
                return s.to_wkt()
            elif isinstance(s, BaseGeometry):
                return wkt.dumps(s)
            else:
                return s

        nx.write_gml(G, "graph.gml", stringify)

    return G


def reverse_geom(geom):
    """Reverse Shapely geometry"""
    # mikewatt CC BY SA 4.0 https://gis.stackexchange.com/a/415879

    def _reverse(x, y, z=None):
        if z:
            return x[::-1], y[::-1], z[::-1]
        return x[::-1], y[::-1]

    return ops.transform(_reverse, geom)


def get_path(G, origin, destination, via=[]) -> gpd.GeoDataFrame:
    """Get shortest path using Dijkstra algorithm"""

    stops = [origin] + via + [destination]

    segments = []
    count = 0
    for s in range(len(stops) - 1):
        start = stops[s]
        end = stops[s + 1]
        n1 = [x for x in G.nodes if G.nodes[x].get("location") == start][0]
        n2 = [x for x in G.nodes if G.nodes[x].get("location") == end][0]

        shortest_paths = nx.all_shortest_paths(G, n1, n2, weight="mm_len")

        shortest_path = [p for p in shortest_paths][0]

        segment = {}
        for p in range(len(shortest_path) - 1):
            segment = G[shortest_path[p]][shortest_path[p + 1]]
            segment["start"] = shortest_path[p]
            segment["end"] = shortest_path[p + 1]
            segment["leg"] = s
            segment["i"] = count
            segment["is_paved"] = True if segment["BelagTLM"] == "hart" else False

            # Make sure the direction of the coordinates is correct
            if segment["geometry"].coords[0] != segment["start"]:
                segment["geometry"] = reverse_geom(segment["geometry"])

            segments.append(segment)

            count += 1

    segments = gpd.GeoDataFrame(pd.DataFrame(segments), crs=G.graph["crs"])
    segments["length_unpaved_km"] = 0.0

    segments["length_km"] = segments.length / 1000
    segments.loc[~segments.is_paved, "length_unpaved_km"] = (
        segments.loc[~segments.is_paved].length / 1000
    )
    segments[["height_gain_m", "height_loss_m"]] = segments.apply(
        lambda x: calc_height_diff(x.geometry, x.start), axis=1
    )

    return segments


def get_dl(segments):
    """Get Dash leaflet geometry"""

    polylines = []
    stops = []
    segments = segments.to_crs("EPSG:4326")
    segments = segments.sort_values("i")
    for s, segment in segments.iterrows():
        points = []
        for pt in segment["geometry"].coords:
            point = (pt[1], pt[0])
            if point not in points:
                points.append(point)
        polylines.append(dl.Polyline(positions=points))

    stops = list(
        segments.groupby("leg")
        .first()
        .apply(lambda x: (x.geometry.coords[0][1], x.geometry.coords[0][0]), axis=1)
    )
    stops.append(
        list(
            segments.groupby("leg")
            .last()
            .apply(
                lambda x: (x.geometry.coords[-1][1], x.geometry.coords[-1][0]), axis=1
            )
        )[-1]
    )

    markers = [dl.Marker(position=x) for x in stops]

    return polylines, markers


def get_height_profile(segments):
    """Get horizontal and vertical distance for plotting"""
    profile = pd.DataFrame()
    profile["vert"] = segments.apply(
        lambda x: np.array(x.geometry.coords)[:, 2].mean(), axis=1
    )
    profile["hor"] = segments.length.cumsum() / 1000
    return profile


if __name__ == "__main__":
    # Test
    G = load_graph()
    origin = "Interlaken"
    destination = "Lausanne"
    # via = ["Bern", "Murten", "Romont FR", "Châtel-St-Denis", "Vevey"]
    via = []
    segments = get_path(G, origin, destination, via)
    points, stops = get_dl(segments)
