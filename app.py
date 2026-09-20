#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2023 Giuseppe Peronato
#
# SPDX-License-Identifier: AGPL-3.0-only

"""
Dash app to query the path network

@author: gperonato
"""

from flask import Flask
from dash import Dash, html, dcc
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import dash_leaflet as dl
import plotly.graph_objs as go
import os
import json
import getpass
from router import *

DEFAULT_ZOOM = 8
GPX_DIR = "./gpx"
LOCATION_NOT_FOUND = "Location not found. Only locations within the supported network are allowed."
DESTINATION_EQUALS_ORIGIN = "Must be different from the origin."


def get_gpx_path(origin, destination, via=None):
    """Build the path of the GPX file of a route

    Location names can contain a path separator (e.g. "Biel/Bienne"), and the
    values reaching the callbacks are not necessarily validated, so the file
    name is sanitised and the result is checked to stay directly inside GPX_DIR.
    """
    stops = [origin, destination] if not via else [origin, via, destination]
    name = "-".join(stops).replace(" ", "_").replace(os.sep, "_")
    if os.altsep:
        name = name.replace(os.altsep, "_")

    file_path = os.path.join(GPX_DIR, name + ".gpx")
    if os.path.dirname(os.path.realpath(file_path)) != os.path.realpath(GPX_DIR):
        raise PreventUpdate()

    return file_path


def make_graph(segments):
    """Make Plotly Height profile plot"""
    profile = get_height_profile(segments)
    layout = go.Layout(
        height=150,
        xaxis_title="km",
        yaxis_title="m asl",
        margin=go.layout.Margin(l=0, r=0, b=0, t=0,),
    )

    fig = go.Figure(layout=layout)
    fig.add_trace(go.Scatter(x=profile.hor, y=profile.vert, mode="lines"))

    return fig


# Load settings
PARAMS = {}
if os.path.exists("params.json"):
    with open("params.json") as f:
        PARAMS = json.load(f)
else:
    print("The params.json file is missing: using default settings.")
# SET DEFAULTS HERE
PARAMS["deployment_user"] = PARAMS.get("deployment_user", getpass.getuser())
PARAMS["port"] = PARAMS.get("port", 8050)


# Load graph
G = load_graph()
locations = [
    v.get("location") for k, v in G.nodes(data=True) if v.get("location") != None
]
locations.sort()
locations_options = [html.Option(value=v) for v in locations]

# Prepare UI
server = Flask(__name__)
app = Dash(server=server, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "VeloRouter"

origin = dbc.Row(
    [
        dbc.Label("From", html_for="origin", width=2),
        dbc.Col(
            [
                dbc.Input(
                    type="search",
                    list="locations",
                    id="origin",
                    autoComplete="True",
                    autoFocus=True,
                    debounce=True,
                ),
                dbc.FormFeedback(
                    LOCATION_NOT_FOUND, type="invalid", id="origin-feedback"
                ),
            ],
            width=5,
        ),
    ],
    className="mb-3",
)

destination = dbc.Row(
    [
        dbc.Label("To", html_for="destination", width=2),
        dbc.Col(
            [
                dbc.Input(
                    type="search",
                    list="locations",
                    id="destination",
                    autoComplete="True",
                    autoFocus=True,
                    debounce=True,
                ),
                dbc.FormFeedback(
                    LOCATION_NOT_FOUND, type="invalid", id="destination-feedback"
                ),
            ],
            width=5,
        ),
    ],
    className="mb-3",
)

via = dbc.Row(
    [
        dbc.Label("Via", html_for="via", width=2),
        dbc.Col(
            [
                dbc.Input(
                    type="search",
                    list="locations",
                    id="via",
                    autoComplete="True",
                    autoFocus=True,
                    debounce=True,
                ),
                dbc.FormFeedback(
                    LOCATION_NOT_FOUND, type="invalid", id="via-feedback"
                ),
            ],
            width=5,
        ),
    ],
    className="mb-3",
)

button = dbc.Row(
    [
        dbc.Col(
            dbc.Button(
                dbc.Spinner(["Submit", html.Div(id="loading-output")]),
                id="submit",
                disabled=True,
            ),
            width=2,
        ),
    ],
    className="mb-3",
)

app.layout = dbc.Container(
    [
        html.H1("VeloRouter"),
        html.Datalist(id="locations", children=locations_options,),
        dbc.Form([origin, destination, via, button]),
        dbc.Row(
            dbc.Col(
                [
                    dl.Map(
                        [
                            dl.TileLayer(
                                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                            ),
                            dl.LayerGroup(id="layer"),
                        ],
                        style={"width": "100%", "height": "500px"},
                        center=(47, 8),
                        zoom=DEFAULT_ZOOM,
                        id="map",
                    ),
                ]
            ),
            className="mb-3",
        ),
        html.Div(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            dbc.Table(
                                [
                                    html.Tr(
                                        [
                                            html.Td("Distance"),
                                            html.Td(
                                                "", id="distance", className="text-end"
                                            ),
                                        ]
                                    ),
                                    html.Tr(
                                        [
                                            html.Td("of which unpaved"),
                                            html.Td(
                                                "",
                                                id="distance_unpaved",
                                                className="text-end",
                                            ),
                                        ]
                                    ),
                                    html.Tr(
                                        [
                                            html.Td("Height gain"),
                                            html.Td(
                                                "",
                                                id="height_gain",
                                                className="text-end",
                                            ),
                                        ]
                                    ),
                                    html.Tr(
                                        [
                                            html.Td("Height loss"),
                                            html.Td(
                                                "",
                                                id="height_loss",
                                                className="text-end",
                                            ),
                                        ]
                                    ),
                                ],
                                bordered=False,
                            ),
                            md=3,
                        ),
                        dbc.Col(dcc.Graph(id="graph")),
                    ]
                ),
                dbc.Row(dbc.Col(dbc.Button("Download GPX", id="download_clicks"),)),
                dbc.Row(dcc.Download(id="download"), className="mb-3"),
            ],
            style={"display": "none"},
            id="results-div",
        ),
        dbc.Row(
            [
                html.Div(
                    [
                        "Data sources: ",
                        dcc.Link(
                            "Veloland Schweiz",
                            href="https://opendata.swiss/en/perma/16d16fa3-a416-4e8b-99fc-69c7267f134d@bundesamt-fur-strassen-astra",
                            id="link",
                            target="_blank",
                        ),
                        " from the Federal Roads Office (FEDRO) and ",
                        dcc.Link(
                            "swissTLMRegio",
                            href="https://opendata.swiss/en/perma/2a190233-498a-46c4-91ca-509a97d797a2@bundesamt-fur-landestopografie-swisstopo",
                            id="link2",
                            target="_blank",
                        ),
                        " from the Federal Office of Topography (swisstopo).",
                    ],
                ),
                html.Div(
                    [
                        "Released under the AGPLv3 license. ",
                        dcc.Link(
                            "Source code",
                            href="https://github.com/gperonato/velorouter",
                            id="link3",
                            target="_blank",
                        ),
                        ".",
                    ],
                ),
            ],
            className="mb-3",
        ),
    ],
    fluid=True,
)


@app.callback(
    [
        Output("origin", "invalid"),
        Output("destination", "invalid"),
        Output("via", "invalid"),
        Output("destination-feedback", "children"),
        Output("submit", "disabled"),
    ],
    Input("origin", "value"),
    Input("destination", "value"),
    Input("via", "value"),
)
def validate_locations(origin, destination, via):
    origin_invalid = bool(origin) and origin not in locations
    via_invalid = bool(via) and via not in locations

    destination_invalid = False
    destination_feedback = LOCATION_NOT_FOUND
    if destination:
        if destination not in locations:
            destination_invalid = True
        elif destination == origin:
            destination_invalid = True
            destination_feedback = DESTINATION_EQUALS_ORIGIN

    submit_disabled = (
        not origin
        or not destination
        or origin_invalid
        or destination_invalid
        or via_invalid
    )

    return (
        origin_invalid,
        destination_invalid,
        via_invalid,
        destination_feedback,
        submit_disabled,
    )


@app.callback(
    [
        Output("map", "viewport"),
        Output("layer", "children"),
        Output("distance", "children"),
        Output("distance_unpaved", "children"),
        Output("height_gain", "children"),
        Output("height_loss", "children"),
        Output("results-div", "style"),
        Output("graph", "figure"),
        Output("loading-output", "children"),
    ],
    [Input("submit", "n_clicks")],
    State("origin", "value"),
    State("destination", "value"),
    State("via", "value"),
    prevent_initial_call=True,
)
def update_output(n_clicks, origin, destination, via):
    if n_clicks is not None:
        if (
            origin != destination
            and origin in locations
            and destination in locations
            and (via in locations or (via == None or via == ""))
        ):
            file_path = get_gpx_path(origin, destination, via)
            via = [via] if via else []

            segments = get_path(G, origin, destination, via)

            segments[["geometry"]].to_crs("EPSG:4326").to_file(file_path)

            polylines, markers = get_dl(segments)

            geometry = [*polylines, *markers]

            results = (
                segments[segments.columns[segments.dtypes == "float64"]].sum().round(0)
            )
            results_string = [
                f"{str(round(results['length_km']))} km",
                f"{str(round(results['length_unpaved_km']))} km",
                f"{str(round(results['height_gain_m']))} m",
                f"{str(round(results['height_loss_m']))} m",
            ]

            fig = make_graph(segments)

            minx, miny, maxx, maxy = segments.to_crs("EPSG:4326").total_bounds
            viewport = {
                "bounds": [[miny, minx], [maxy, maxx]],
                # Padding accounts for the default marker icon (25x41px),
                # which is anchored at its bottom tip and can otherwise get
                # clipped when a stop sits right on the edge of the bounds.
                "options": {"padding": [30, 50]},
            }

            return (
                viewport,
                geometry,
                *results_string,
                {"display": "block"},
                fig,
                None,  # for the spinner
            )
        else:
            raise PreventUpdate()


@app.callback(
    Output("download", "data"),
    Input("download_clicks", "n_clicks"),
    State("origin", "value"),
    State("destination", "value"),
    State("via", "value"),
    prevent_initial_call=True,
)
def download(n_clicks, origin, destination, via):
    if n_clicks is not None:
        return dcc.send_file(get_gpx_path(origin, destination, via))


if __name__ == "__main__":
    app.run_server(debug=os.environ.get("DEBUG") == "1", port=PARAMS["port"])
