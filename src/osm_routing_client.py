"""OSM routing client with caching.

Provides a simple wrapper to call OSRM (public demo) or OpenRouteService (if ORS key
is provided via ORS_API_KEY env var) and returns a list of (lat, lon) coordinates for the route.

Caching: saves each segment response to data/cache as JSON keyed by rounded coordinates.
"""
from pathlib import Path
import requests
import os
import json
from typing import Tuple, List


def _cache_path(cache_dir: Path, a: Tuple[float, float], b: Tuple[float, float]) -> Path:
    a_lat, a_lon = a
    b_lat, b_lon = b
    fname = f"{round(a_lat,5)}_{round(a_lon,5)}__{round(b_lat,5)}_{round(b_lon,5)}.json"
    return cache_dir / fname


def get_route_osrm(a: Tuple[float, float], b: Tuple[float, float]) -> List[Tuple[float, float]]:
    """Call OSRM public demo to get route geometry and step-by-step instructions.

    Returns a dict: {'coords': [(lat,lon), ...], 'steps': [{'instruction': str, 'distance': meters}, ...]}
    """
    coords = f"{a[1]},{a[0]};{b[1]},{b[0]}"
    url = f"http://router.project-osrm.org/route/v1/driving/{coords}?overview=full&geometries=geojson&steps=true"
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    route = data['routes'][0]
    coords_list = route['geometry']['coordinates']
    coords_latlon = [(c[1], c[0]) for c in coords_list]

    # collect steps from legs -> steps
    steps = []
    for leg in route.get('legs', []):
        for step in leg.get('steps', []):
            # build a human readable instruction
            instr_parts = []
            man = step.get('maneuver', {})
            mtype = man.get('type')
            mod = man.get('modifier')
            if mtype:
                instr_parts.append(mtype.replace('_', ' ').capitalize())
            if mod:
                instr_parts.append(mod)
            name = step.get('name')
            if name:
                instr_parts.append(f"vào {name}")
            instruction = ' '.join(instr_parts).strip()
            if not instruction:
                instruction = step.get('name') or ''
            steps.append({'instruction': instruction, 'distance': float(step.get('distance', 0))})

    return {'coords': coords_latlon, 'steps': steps}


def get_route_ors(a: Tuple[float, float], b: Tuple[float, float], api_key: str) -> List[Tuple[float, float]]:
    """Call OpenRouteService directions API (if api_key provided).

    a and b are (lat, lon)
    """
    url = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"
    headers = {"Authorization": api_key, "Content-Type": "application/json"}
    body = {
        "coordinates": [[a[1], a[0]], [b[1], b[0]]]
    }
    resp = requests.post(url, headers=headers, json=body, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    coords_list = data['features'][0]['geometry']['coordinates']
    coords_latlon = [(c[1], c[0]) for c in coords_list]

    # parse steps if available
    steps = []
    props = data['features'][0].get('properties', {})
    for segment in props.get('segments', []):
        for step in segment.get('steps', []):
            instr = step.get('instruction') or step.get('name') or ''
            steps.append({'instruction': instr, 'distance': float(step.get('distance', 0))})

    return {'coords': coords_latlon, 'steps': steps}


def get_route_cached(a: Tuple[float, float], b: Tuple[float, float], cache_dir: Path = None) -> List[Tuple[float, float]]:
    """Get route between a and b using cache if available. Uses ORS if ORS_API_KEY is present, otherwise OSRM."""
    if cache_dir is None:
        cache_dir = Path(__file__).parent.parent / 'data' / 'cache'
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    p = _cache_path(cache_dir, a, b)
    if p.exists():
        try:
            j = json.loads(p.read_text(encoding='utf-8'))
            return [(pt[0], pt[1]) for pt in j['coords']]
        except Exception:
            # fallthrough to re-fetch
            pass

    # Decide service
    ors_key = os.environ.get('ORS_API_KEY')
    try:
        if ors_key:
            res = get_route_ors(a, b, ors_key)
        else:
            res = get_route_osrm(a, b)
    except Exception:
        # As fallback return straight line
        res = {'coords': [a, b], 'steps': []}

    # Save cache (coords + steps)
    try:
        p.write_text(json.dumps({'coords': [[lat, lon] for lat, lon in res['coords']], 'steps': res.get('steps', [])}, ensure_ascii=False), encoding='utf-8')
    except Exception:
        pass

    return res
