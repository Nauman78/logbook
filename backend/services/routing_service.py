import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

ORS_BASE = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"
METERS_PER_MILE = 1609.344
SECONDS_PER_HOUR = 3600


def get_route(
    origin: tuple[float, float],
    pickup: tuple[float, float],
    dropoff: tuple[float, float],
    waypoints: list[tuple[float, float]] | None = None,
) -> dict[str, Any]:
    api_key = (os.environ.get("OPENROUTE_SERVICE_API_KEY") or "").strip()
    if not api_key:
        raise ValueError(
            "OPENROUTE_SERVICE_API_KEY is not set. "
            "Add it to your .env or get a free key at https://openrouteservice.org/dev/#/signup"
        )

    waypoints = waypoints or []
    coordinates = [
        [float(origin[0]), float(origin[1])],
        [float(pickup[0]), float(pickup[1])],
    ]
    for w in waypoints:
        coordinates.append([float(w[0]), float(w[1])])
    coordinates.append([float(dropoff[0]), float(dropoff[1])])

    url = f"{ORS_BASE}?api_key={api_key}"
    try:
        resp = requests.post(
            url,
            json={"coordinates": coordinates},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
    except requests.HTTPError as e:
        if e.response is not None:
            if e.response.status_code == 403:
                raise ValueError(
                    "OpenRouteService returned 403 Forbidden. "
                    "Check that OPENROUTE_SERVICE_API_KEY in .env is correct and has access to the Directions API."
                ) from e
            if e.response.status_code == 404:
                raise ValueError(
                    "OpenRouteService returned 404 Not Found. Check the API key and endpoint at https://openrouteservice.org/dev/#/api-docs"
                ) from e
        raise
    data = resp.json()
    if not isinstance(data, dict):
        raise ValueError(f"OpenRouteService returned unexpected response: {type(data).__name__}")

    coords = []
    summary = {}

    features = data.get("features")
    if features and isinstance(features, list) and len(features) > 0:
        feat = features[0]
        if isinstance(feat, dict):
            geom = feat.get("geometry")
            if isinstance(geom, dict):
                coords = geom.get("coordinates") or []
            props = feat.get("properties") or {}
            if isinstance(props.get("summary"), dict):
                summary = props["summary"]
    else:
        routes = data.get("routes") or []
        if not routes:
            raise ValueError("No route returned from OpenRouteService")
        route = routes[0]
        if not isinstance(route, dict):
            raise ValueError(f"OpenRouteService route entry unexpected type: {type(route).__name__}")
        geometry = route.get("geometry")
        if isinstance(geometry, dict):
            coords = geometry.get("coordinates") or []
        elif isinstance(geometry, list):
            coords = geometry
        if isinstance(route.get("summary"), dict):
            summary = route["summary"]

    if not coords:
        raise ValueError("No route geometry returned from OpenRouteService")

    distance_m = float(summary.get("distance") or 0)
    duration_s = float(summary.get("duration") or 0)

    return {
        "polyline": coords,
        "distance_miles": round(distance_m / METERS_PER_MILE, 4),
        "duration_hours": round(duration_s / SECONDS_PER_HOUR, 4),
    }
