"""
Run OR-Tools VRPTW solver on a CSV in `data/input/` and visualize the resulting routes as a Folium HTML map.

This script:
- Normalizes a simple input CSV (id,lat,lon,...) to the OR-Tools expected CSV format.
- Runs the OR-Tools solver implementation in algorithm/OR-Tools/ortools_vrptw_solver.py by loading it from file.
- Visualizes the solution with Folium. Use --use-osrm to draw realistic road polylines (OSRM or OpenRouteService) with caching.

Example:
  python scripts/run_and_visualize.py --input data/input/khach_hang_mau.csv --use-osrm
"""

from pathlib import Path
import argparse
import pandas as pd
import importlib.util
import tempfile
import folium
import json
from typing import Tuple, List
import math
from folium.features import DivIcon
from folium.plugins import PolyLineTextPath
import sys

# allow imports from repo root (so we can import src.osm_routing_client)
sys.path.insert(0, str(Path(__file__).parent.parent))


def normalize_to_ortools(input_csv: Path, output_csv: Path):
    df = pd.read_csv(input_csv)
    # Support both (lat,lon) or (YCOORD.,XCOORD.) input
    if 'lat' in df.columns and 'lon' in df.columns:
        lat_col, lon_col = 'lat', 'lon'
    elif 'YCOORD.' in df.columns and 'XCOORD.' in df.columns:
        lat_col, lon_col = 'YCOORD.', 'XCOORD.'
    else:
        raise ValueError('Input CSV must contain lat/lon or YCOORD./XCOORD. columns')

    ortools_df = pd.DataFrame()
    ortools_df['ID'] = df.get('id', df.index)
    ortools_df['NAME'] = df.get('name', ortools_df['ID'])
    ortools_df['XCOORD.'] = df[lon_col]
    ortools_df['YCOORD.'] = df[lat_col]
    ortools_df['DEMAND'] = df.get('demand', 1)
    ortools_df['READY TIME'] = df.get('ready_time', 0)
    ortools_df['DUE DATE'] = df.get('due_date', 1000)
    ortools_df['SERVICE TIME'] = df.get('service_time', 0)
    ortools_df.to_csv(output_csv, index=False)


def load_ortools_solver_module() -> object:
    """Dynamically load the OR-Tools solver module from algorithm/OR-Tools/ortools_vrptw_solver.py

    Returns the loaded module object.
    """
    repo_root = Path(__file__).parent.parent
    solver_path = repo_root / 'algorithm' / 'OR-Tools' / 'ortools_vrptw_solver.py'
    if not solver_path.exists():
        raise FileNotFoundError(f'ORTools solver not found at {solver_path}')

    spec = importlib.util.spec_from_file_location('ortools_vrptw_solver', str(solver_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def draw_solution(solution: dict, temp_csv: Path, out_html: Path, use_osrm: bool = False):
    df = pd.read_csv(temp_csv)

    # Prepare map
    center = [df['YCOORD.'].mean(), df['XCOORD.'].mean()]
    m = folium.Map(location=center, zoom_start=14)

    # Depot marker (always visible, not in any vehicle layer)
    depot_row = df.iloc[0]
    depot_name = str(depot_row.get('NAME', ''))
    depot_id = str(depot_row.get('ID', 0))
    depot_tooltip = f"{depot_id} - {depot_name}" if depot_name else depot_id
    folium.Marker(
        [depot_row['YCOORD.'], depot_row['XCOORD.']],
        popup=folium.Popup(html=f"<b>Depot</b><br/>{depot_tooltip}", max_width=300),
        tooltip=depot_tooltip,
        icon=folium.Icon(color='black', icon='home')
    ).add_to(m)

    routes = solution.get('routes', [])

    # color palette for vehicles
    colors = ['blue', 'red', 'green', 'purple', 'orange', 'darkred', 'cadetblue', 'darkgreen', 'brown', 'pink']

    def haversine_km(a: Tuple[float, float], b: Tuple[float, float]) -> float:
        # a, b are (lat, lon)
        lat1, lon1 = a
        lat2, lon2 = b
        R = 6371.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        x = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        return 2 * R * math.asin(math.sqrt(x))

    # store legend entries
    legend_entries = []

    for r_idx, route in enumerate(routes):
        # Create a FeatureGroup for this vehicle (allows layer control)
        vehicle_group = folium.FeatureGroup(name=f'Xe {r_idx+1}', show=True)
        
        # build full route (depot -> customers -> depot)
        coords: List[Tuple[float, float]] = []
        coords.append((df.iloc[0]['YCOORD.'], df.iloc[0]['XCOORD.']))
        for node in route:
            coords.append((df.iloc[node]['YCOORD.'], df.iloc[node]['XCOORD.']))
        coords.append((df.iloc[0]['YCOORD.'], df.iloc[0]['XCOORD.']))

        # ensure steps_acc is always defined (used later when building popups)
        steps_acc: List[dict] = []

        if use_osrm:
            from src.osm_routing_client import get_route_cached
            poly: List[Tuple[float, float]] = []
            steps_acc: List[dict] = []
            for i in range(len(coords) - 1):
                a = coords[i]
                b = coords[i + 1]
                seg_res = get_route_cached(a, b)
                # seg_res: {'coords': [(lat,lon)...], 'steps': [...]}
                seg = seg_res.get('coords') if isinstance(seg_res, dict) else seg_res
                seg_steps = seg_res.get('steps') if isinstance(seg_res, dict) else []
                # append segment geometry
                if poly and seg and poly[-1] == seg[0]:
                    poly.extend(seg[1:])
                else:
                    poly.extend(seg)
                # accumulate steps
                if seg_steps:
                    steps_acc.extend(seg_steps)
        else:
            poly = [[lat, lon] for lat, lon in coords]

        # compute polyline length (km)
        route_dist = 0.0
        for i in range(len(poly) - 1):
            a = poly[i]
            b = poly[i + 1]
            latlon_a = (float(a[0]), float(a[1]))
            latlon_b = (float(b[0]), float(b[1]))
            route_dist += haversine_km(latlon_a, latlon_b)

        color = colors[r_idx % len(colors)]
        tooltip = f"Xe {r_idx+1} — {route_dist:.2f} km — {len(route)} KH"
        # build html for step-by-step (collapsible)
        steps_html = ""
        if steps_acc:
            steps_html = '<details><summary>Hướng dẫn chi tiết</summary><ol style="margin-left:14px;">'
            for s in steps_acc:
                instr = s.get('instruction', '')
                distm = s.get('distance', 0.0)
                steps_html += f"<li>{instr} <small>({distm:.0f} m)</small></li>"
            steps_html += '</ol></details>'

        popup_html = f"<b>Xe {r_idx+1}</b><br/>Quãng đường: {route_dist:.2f} km<br/>Số khách: {len(route)}<br/>{steps_html}"

        # create an invisible/non-interactive base polyline so arrows can be drawn but it won't block markers
        pl = folium.PolyLine(poly, color='transparent', weight=0, opacity=0.0, interactive=False, tooltip=tooltip, popup=folium.Popup(popup_html, max_width=300)).add_to(vehicle_group)
        # add directional arrows along the line
        try:
            PolyLineTextPath(pl, ' ➤ ', repeat=True, offset=12, attributes={'fill': color, 'font-weight': 'bold', 'font-size': '14'}).add_to(vehicle_group)
        except Exception:
            # fallback: AntPath (animated) as a visual cue
            try:
                from folium.plugins import AntPath
                AntPath(poly, color=color, weight=3, delay=1000).add_to(vehicle_group)
            except Exception:
                pass

        # add mid-label
        try:
            mid = poly[len(poly)//2]
            folium.map.Marker(
                location=mid,
                icon=DivIcon(icon_size=(150,36), icon_anchor=(0,0), html=f"<div style='font-size:12px; color:{color}; font-weight:bold; background: rgba(255,255,255,0.7); padding:2px 6px; border-radius:4px;'>Xe {r_idx+1}</div>" )
            ).add_to(vehicle_group)
        except Exception:
            pass

        # Add numbered customer markers for this route (order 1, 2, 3...)
        for order_idx, node in enumerate(route, start=1):
            cust_row = df.iloc[node]
            cust_name = str(cust_row.get('NAME', ''))
            cust_id = str(cust_row.get('ID', node))
            cust_demand = cust_row.get('DEMAND', 0)
            cust_tooltip = f"{cust_id} - {cust_name}<br/>Thứ tự: {order_idx}<br/>Demand: {cust_demand}"
            
            # Create a circle marker with order number inside
            folium.CircleMarker(
                location=[cust_row['YCOORD.'], cust_row['XCOORD.']],
                radius=10,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.8,
                tooltip=cust_tooltip,
                popup=folium.Popup(html=f"<b>Xe {r_idx+1} - Điểm {order_idx}</b><br/>{cust_id} - {cust_name}<br/>Demand: {cust_demand}", max_width=300)
            ).add_to(vehicle_group)
            
            # Add order number label
            folium.map.Marker(
                location=[cust_row['YCOORD.'], cust_row['XCOORD.']],
                icon=DivIcon(icon_size=(20,20), icon_anchor=(10,10), html=f"<div style='font-size:11px; color:white; font-weight:bold; text-align:center;'>{order_idx}</div>")
            ).add_to(vehicle_group)

        # Add the vehicle group to map
        vehicle_group.add_to(m)

        legend_entries.append((color, f'Xe {r_idx+1}'))

    # Add LayerControl to toggle vehicles on/off
    folium.LayerControl(collapsed=False).add_to(m)

    # add legend box (moved to bottom-right to avoid overlap with LayerControl)
    legend_html = '<div style="position: fixed; bottom: 80px; right: 10px; z-index:9999; background: rgba(255,255,255,0.95); padding:8px; border-radius:6px; box-shadow:0 2px 6px rgba(0,0,0,0.3); font-family: Arial, Helvetica, sans-serif; font-size:13px;">'
    legend_html += '<b>Tên tuyến</b><br/>'
    for c, label in legend_entries:
        legend_html += f"<div style='display:flex;align-items:center;margin:4px 0;'><div style='width:16px;height:10px;background:{c};margin-right:8px;border:1px solid #222'></div>{label}</div>"
    legend_html += '</div>'
    try:
        from folium import Element
        m.get_root().html.add_child(Element(legend_html))
    except Exception:
        pass

    # Add a small summary panel (number of vehicles, total distance)
    try:
        num_v = int(solution.get('num_vehicles', 0))
        total_d = float(solution.get('total_distance', 0.0))
    except Exception:
        num_v = 0
        total_d = 0.0

    summary_html = f"""
    <div style="position: fixed; bottom: 20px; left: 10px; z-index:9999; background: rgba(255,255,255,0.95);
        padding:10px; border-radius:6px; box-shadow: 0 2px 6px rgba(0,0,0,0.3); font-family: Arial, Helvetica, sans-serif;">
      <b>OR-Tools Summary</b><br/>
      Số xe sử dụng: <b>{num_v}</b><br/>
      Tổng quãng đường: <b>{total_d:.2f}</b>
    </div>
    """
    try:
        from folium import Element
        m.get_root().html.add_child(Element(summary_html))
    except Exception:
        # best-effort; ignore if add fails
        pass

    out_html.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(out_html))
    return out_html


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=False, default=str(Path(__file__).parent.parent / 'data' / 'input' / 'khach_hang.csv'))
    parser.add_argument('--time_limit', type=int, default=10000)
    parser.add_argument('--vehicle_capacity', type=int, default=100000)
    parser.add_argument('--max_vehicles', type=int, default=1)
    parser.add_argument('--use-osrm', action='store_true')
    parser.add_argument('--depot-name', type=str, default=None, help='Optional override name for depot (will set popup/tooltip)')
    parser.add_argument('--depot-lat', type=float, default=None, help='Optional override latitude for depot')
    parser.add_argument('--depot-lon', type=float, default=None, help='Optional override longitude for depot')
    parser.add_argument('--out', default=str(Path(__file__).parent.parent / 'maps' / 'ortools_ninh_kieu.html'))
    args = parser.parse_args()

    input_csv = Path(args.input)
    if not input_csv.exists():
        print(f'Input CSV not found: {input_csv}')
        return

    # create temp csv in OR-Tools format
    temp_dir = Path(tempfile.gettempdir()) / 'vrptw_tmp'
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_csv = temp_dir / 'temp_input_for_ortools.csv'
    normalize_to_ortools(input_csv, temp_csv)

    # If user provided a custom depot, patch the temp CSV so visualization (and solver) see it as depot (row 0)
    if args.depot_lat is not None and args.depot_lon is not None:
        tdf = pd.read_csv(temp_csv)
        # override first row (depot)
        tdf.at[0, 'YCOORD.'] = args.depot_lat
        tdf.at[0, 'XCOORD.'] = args.depot_lon
        if args.depot_name:
            tdf.at[0, 'NAME'] = args.depot_name
            tdf.at[0, 'ID'] = args.depot_name
        tdf.to_csv(temp_csv, index=False)
    elif args.depot_name:
        # only override name
        tdf = pd.read_csv(temp_csv)
        tdf.at[0, 'NAME'] = args.depot_name
        tdf.at[0, 'ID'] = args.depot_name
        tdf.to_csv(temp_csv, index=False)

    # load solver
    ortools_mod = load_ortools_solver_module()
    SolverClass = getattr(ortools_mod, 'ORToolsVRPTWSolver')
    solver = SolverClass(dataset_path=str(temp_csv), vehicle_capacity=args.vehicle_capacity, max_vehicles=args.max_vehicles)

    print('Running OR-Tools solver...')
    solution = solver.solve(time_limit=args.time_limit)
    if not solution:
        print('No solution found')
        return

    out_html = Path(args.out)
    draw_solution(solution, temp_csv, out_html, use_osrm=args.use_osrm)
    print(f'✅ Visualization saved to: {out_html}')


if __name__ == '__main__':
    main()

