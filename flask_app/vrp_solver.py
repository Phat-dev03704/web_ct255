"""
VRP Solver using Google OR-Tools
Tìm tuyến đường tối ưu cho bài toán giao hàng có ràng buộc thời gian (VRPTW)
"""

import math
from datetime import datetime, timedelta
from decimal import Decimal
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from models import db, DonHang, TaiXe, NguoiDung, VanChuyen, CTVC, DonHangCTVC, OrderStatus, CTVCStatus, DHCTVCStatus
from sqlalchemy import func
import json


class VRPSolver:
    """Class để giải bài toán VRP với time windows"""
    
    def __init__(self, service_time=20, avg_speed=30, depot_id='DEPOT'):
        """
        Args:
            service_time: Thời gian phục vụ mỗi điểm (phút)
            avg_speed: Tốc độ trung bình (km/h)
            depot_id: ID của depot (kho xuất phát)
        """
        self.service_time_default = service_time
        self.avg_speed = avg_speed
        self.depot_id = depot_id
        self.depot_location = None
        self.locations = []
        self.demands = []
        self.time_windows = []
        self.service_times = []
        self.order_ids = []
        self.customer_names = []
        self.distance_matrix = []
        self.time_matrix = []
        
    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """Tính khoảng cách Haversine giữa 2 điểm (km)"""
        R = 6371  # Bán kính trái đất (km)
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c
        
        return distance
    
    def create_data_model(self, orders, drivers):
        """
        Tạo data model từ database
        Args:
            orders: List các đơn hàng (DonHang objects)
            drivers: List các tài xế (TaiXe objects)
        """
        # Lấy thông tin DEPOT từ database
        depot = NguoiDung.query.filter_by(MaND=self.depot_id).first()
        if not depot:
            raise ValueError(f"Không tìm thấy DEPOT '{self.depot_id}' trong database")
        
        self.depot_location = (float(depot.Lat), float(depot.Lon))
        
        # Khởi tạo với depot
        self.locations = [self.depot_location]
        self.demands = [0]  # Depot không có nhu cầu
        self.time_windows = [(0, 1440)]  # 0-1440 phút (24h)
        self.service_times = [0]  # Depot không có thời gian phục vụ
        self.order_ids = ['DEPOT']
        self.customer_names = ['DEPOT - DHCT']
        
        # Thêm thông tin từ các đơn hàng
        for order in orders:
            # Lấy thông tin khách hàng
            customer = order.nguoi_dung
            if not customer:
                continue
                
            # Location (convert Decimal to float)
            self.locations.append((float(order.Lat), float(order.Lon)))
            
            # Demand (tổng số lượng sản phẩm từ chi_tiets relationship)
            total_demand = sum(item.SoLuong for item in order.chi_tiets) if order.chi_tiets else 0
            self.demands.append(int(total_demand))
            
            # Time windows (chuyển đổi từ phút sang tuple)
            ready_time = order.READY_TIME or 0
            due_date = order.DUE_DATE or 1440
            self.time_windows.append((int(ready_time), int(due_date)))
            
            # Service time (sử dụng giá trị cấu hình)
            self.service_times.append(self.service_time_default)
            
            # Order ID và tên khách hàng
            self.order_ids.append(order.MaDH)
            self.customer_names.append(customer.TenND)
        
        # Tính ma trận khoảng cách
        num_locations = len(self.locations)
        self.distance_matrix = [[0] * num_locations for _ in range(num_locations)]
        self.time_matrix = [[0] * num_locations for _ in range(num_locations)]
        
        for i in range(num_locations):
            for j in range(num_locations):
                if i != j:
                    dist = self.calculate_distance(
                        self.locations[i][0], self.locations[i][1],
                        self.locations[j][0], self.locations[j][1]
                    )
                    # Distance in meters
                    self.distance_matrix[i][j] = int(dist * 1000)
                    # Time in minutes (sử dụng avg_speed cấu hình)
                    self.time_matrix[i][j] = int((dist / self.avg_speed) * 60)
        
        # Thông tin xe
        num_vehicles = len(drivers)
        vehicle_capacities = [driver.SucChua for driver in drivers]
        
        data = {
            'distance_matrix': self.distance_matrix,
            'time_matrix': self.time_matrix,
            'time_windows': self.time_windows,
            'service_times': self.service_times,
            'demands': self.demands,
            'vehicle_capacities': vehicle_capacities,
            'num_vehicles': num_vehicles,
            'depot': 0
        }
        
        return data
    
    def solve(self, orders, drivers, time_limit=30, search_strategy='PATH_CHEAPEST_ARC', metaheuristic='AUTOMATIC'):
        """
        Giải bài toán VRP
        Args:
            orders: List đơn hàng cần giao
            drivers: List tài xế khả dụng
            time_limit: Thời gian tối đa để tìm solution (giây)
            search_strategy: Chiến lược tìm kiếm ban đầu
            metaheuristic: Thuật toán metaheuristic cho local search
        Returns:
            dict chứa thông tin solution hoặc None nếu không tìm được
        """
        if not orders or not drivers:
            return None
        
        # Tạo data model
        data = self.create_data_model(orders, drivers)
        
        # Tạo routing index manager
        manager = pywrapcp.RoutingIndexManager(
            len(data['distance_matrix']),
            data['num_vehicles'],
            data['depot']
        )
        
        # Tạo routing model
        routing = pywrapcp.RoutingModel(manager)
        
        # Định nghĩa distance callback
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return data['distance_matrix'][from_node][to_node]
        
        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
        
        # Thêm ràng buộc capacity
        def demand_callback(from_index):
            from_node = manager.IndexToNode(from_index)
            return data['demands'][from_node]
        
        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,  # null capacity slack
            data['vehicle_capacities'],
            True,  # start cumul to zero
            'Capacity'
        )
        
        # Thêm ràng buộc time windows
        def time_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            travel_time = data['time_matrix'][from_node][to_node]
            service_time = data['service_times'][from_node]
            return travel_time + service_time
        
        time_callback_index = routing.RegisterTransitCallback(time_callback)
        routing.AddDimension(
            time_callback_index,
            60,  # allow waiting time
            1440,  # maximum time per vehicle (24h = 1440 minutes)
            False,  # Don't force start cumul to zero
            'Time'
        )
        
        time_dimension = routing.GetDimensionOrDie('Time')
        
        # Thêm time window constraints cho mỗi location
        for location_idx, time_window in enumerate(data['time_windows']):
            if location_idx == data['depot']:
                continue
            index = manager.NodeToIndex(location_idx)
            time_dimension.CumulVar(index).SetRange(time_window[0], time_window[1])
        
        # Thêm time window constraints cho depot
        depot_idx = data['depot']
        for vehicle_id in range(data['num_vehicles']):
            index = routing.Start(vehicle_id)
            time_dimension.CumulVar(index).SetRange(
                data['time_windows'][depot_idx][0],
                data['time_windows'][depot_idx][1]
            )
        
        # Setting first solution heuristic
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        
        # Map strategy name to enum
        strategy_map = {
            'PATH_CHEAPEST_ARC': routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC,
            'GLOBAL_CHEAPEST_ARC': routing_enums_pb2.FirstSolutionStrategy.GLOBAL_CHEAPEST_ARC,
            'LOCAL_CHEAPEST_ARC': routing_enums_pb2.FirstSolutionStrategy.LOCAL_CHEAPEST_ARC,
            'SAVINGS': routing_enums_pb2.FirstSolutionStrategy.SAVINGS,
            'CHRISTOFIDES': routing_enums_pb2.FirstSolutionStrategy.CHRISTOFIDES
        }
        search_parameters.first_solution_strategy = strategy_map.get(
            search_strategy, 
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        
        # Map metaheuristic name to enum
        metaheuristic_map = {
            'AUTOMATIC': routing_enums_pb2.LocalSearchMetaheuristic.AUTOMATIC,
            'GREEDY_DESCENT': routing_enums_pb2.LocalSearchMetaheuristic.GREEDY_DESCENT,
            'GUIDED_LOCAL_SEARCH': routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH,
            'SIMULATED_ANNEALING': routing_enums_pb2.LocalSearchMetaheuristic.SIMULATED_ANNEALING,
            'TABU_SEARCH': routing_enums_pb2.LocalSearchMetaheuristic.TABU_SEARCH
        }
        search_parameters.local_search_metaheuristic = metaheuristic_map.get(
            metaheuristic,
            routing_enums_pb2.LocalSearchMetaheuristic.AUTOMATIC
        )
        
        search_parameters.time_limit.FromSeconds(time_limit)
        
        # Giải bài toán
        solution = routing.SolveWithParameters(search_parameters)
        
        if solution:
            return self._extract_solution(data, manager, routing, solution, drivers)
        else:
            return None
    
    def _extract_solution(self, data, manager, routing, solution, drivers):
        """Trích xuất thông tin từ solution"""
        routes = []
        total_distance = 0
        total_load = 0
        total_orders = 0
        
        time_dimension = routing.GetDimensionOrDie('Time')
        
        for vehicle_id in range(data['num_vehicles']):
            index = routing.Start(vehicle_id)
            route = {
                'vehicle_id': vehicle_id,
                'driver': drivers[vehicle_id],
                'orders': [],
                'distance': 0,
                'load': 0,
                'sequence': []
            }
            
            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                time_var = time_dimension.CumulVar(index)
                
                if node_index != 0:  # Không phải depot
                    route['orders'].append({
                        'order_id': self.order_ids[node_index],
                        'customer_name': self.customer_names[node_index],
                        'location': self.locations[node_index],
                        'demand': self.demands[node_index],
                        'time_window': self.time_windows[node_index],
                        'arrival_time': solution.Min(time_var)
                    })
                    route['load'] += self.demands[node_index]
                    route['sequence'].append(node_index)
                
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                route['distance'] += routing.GetArcCostForVehicle(previous_index, index, vehicle_id)
            
            # Chỉ thêm route nếu có đơn hàng
            if route['orders']:
                routes.append(route)
                total_distance += route['distance']
                total_load += route['load']
                total_orders += len(route['orders'])
        
        return {
            'routes': routes,
            'total_distance': total_distance / 1000,  # Convert to km
            'total_load': total_load,
            'total_orders': total_orders,
            'num_vehicles_used': len(routes)
        }
    
    def save_to_database(self, solution):
        """
        Lưu solution vào database
        Args:
            solution: dict chứa thông tin solution từ solve()
        Returns:
            VanChuyen object đã tạo
        """
        if not solution or not solution['routes']:
            return None
        
        try:
            # Tạo MaVC tự động
            last_vc = VanChuyen.query.order_by(VanChuyen.MaVC.desc()).first()
            if last_vc and last_vc.MaVC.startswith('VC'):
                next_id = int(last_vc.MaVC[2:]) + 1
            else:
                next_id = 1
            ma_vc = f"VC{next_id:03d}"
            
            # Convert solution để serialize JSON (Decimal -> float)
            def decimal_to_float(obj):
                if isinstance(obj, dict):
                    return {k: decimal_to_float(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [decimal_to_float(item) for item in obj]
                elif isinstance(obj, Decimal):
                    return float(obj)
                else:
                    return obj
            
            solution_json = decimal_to_float(solution)
            
            # Tạo VAN_CHUYEN record
            van_chuyen = VanChuyen(
                MaVC=ma_vc,
                TenTuyen=f"Route_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                TrangThai='planned',
                NgayTao=datetime.now(),
                TongQuangDuong=solution['total_distance'],
                TongHang=solution['total_load'],
                TongDonHang=solution['total_orders'],
                RouteData=json.dumps(solution_json, default=str)
            )
            db.session.add(van_chuyen)
            db.session.commit()  # Commit để lấy MaVC
            
            # Tạo CTVC và DONHANG_CTVC cho mỗi route
            for route in solution['routes']:
                driver = route['driver']
                
                # Tạo CTVC
                ctvc = CTVC(
                    MaVC=van_chuyen.MaVC,
                    MaTX=driver.MaTX,
                    TrangThai=CTVCStatus.assigned,
                    NgayGiao=datetime.now().date()
                )
                db.session.add(ctvc)
                db.session.commit()  # Commit để lấy CTVC_id
                
                # Tạo DONHANG_CTVC cho mỗi đơn hàng trong route
                for idx, order_info in enumerate(route['orders'], start=1):
                    order_id = order_info['order_id']
                    
                    # Tạo DONHANG_CTVC
                    dh_ctvc = DonHangCTVC(
                        CTVC_id=ctvc.id,
                        MaDH=order_id,
                        ThuTu=idx,
                        TrangThai=DHCTVCStatus.pending
                    )
                    db.session.add(dh_ctvc)
                    
                    # Cập nhật trạng thái đơn hàng
                    order = DonHang.query.get(order_id)
                    if order:
                        order.TrangThai = OrderStatus.assigned
                
                db.session.commit()  # Commit sau mỗi route
            
            return van_chuyen
            
        except Exception as e:
            db.session.rollback()
            print(f"Error saving solution to database: {e}")
            raise
    
    def generate_map_html(self, solution):
        """
        Tạo HTML map với Leaflet.js để hiển thị routes
        Args:
            solution: dict chứa thông tin solution
        Returns:
            str: HTML content
        """
        if not solution or not solution['routes']:
            return None
        
        # Màu sắc cho các routes
        colors = ['#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#FF00FF', '#00FFFF', '#FFA500', '#800080']
        
        # Tạo markers và routes
        markers_js = []
        routes_js = []
        
        # Depot marker
        depot_lat, depot_lon = self.depot_location
        markers_js.append(f"""
            L.marker([{depot_lat}, {depot_lon}], {{
                icon: L.icon({{
                    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
                    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
                    iconSize: [25, 41],
                    iconAnchor: [12, 41],
                    popupAnchor: [1, -34],
                    shadowSize: [41, 41]
                }})
            }}).addTo(map)
                .bindPopup('<b>DEPOT - DHCT</b><br>Starting point');
        """)
        
        # Route markers và polylines
        for idx, route in enumerate(solution['routes']):
            color = colors[idx % len(colors)]
            driver = route['driver']
            
            # Tạo polyline cho route
            coords = [[depot_lat, depot_lon]]
            
            for order_info in route['orders']:
                lat, lon = order_info['location']
                coords.append([lat, lon])
                
                # Customer marker
                markers_js.append(f"""
                    L.marker([{lat}, {lon}]).addTo(map)
                        .bindPopup('<b>{order_info['customer_name']}</b><br>' +
                                   'Order: {order_info['order_id']}<br>' +
                                   'Demand: {order_info['demand']}<br>' +
                                   'Driver: {driver.TenTX}<br>' +
                                   'Arrival: {order_info['arrival_time']} min');
                """)
            
            # Quay về depot
            coords.append([depot_lat, depot_lon])
            
            # Tạo polyline
            coords_str = json.dumps(coords)
            routes_js.append(f"""
                L.polyline({coords_str}, {{
                    color: '{color}',
                    weight: 3,
                    opacity: 0.7
                }}).addTo(map)
                    .bindPopup('<b>Route {idx + 1}</b><br>' +
                               'Driver: {driver.TenTX}<br>' +
                               'Vehicle: {driver.BienSoXe}<br>' +
                               'Distance: {route['distance']/1000:.2f} km<br>' +
                               'Orders: {len(route['orders'])}<br>' +
                               'Load: {route['load']}');
            """)
        
        # HTML template
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VRP Routes - Optimized</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        body {{ margin: 0; padding: 0; }}
        #map {{ position: absolute; top: 0; bottom: 0; width: 100%; }}
        .info {{
            padding: 10px;
            background: white;
            border-radius: 5px;
            box-shadow: 0 0 15px rgba(0,0,0,0.2);
        }}
        .legend {{
            line-height: 24px;
            color: #555;
        }}
        .legend i {{
            width: 18px;
            height: 18px;
            float: left;
            margin-right: 8px;
            opacity: 0.7;
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        // Initialize map
        var map = L.map('map').setView([{depot_lat}, {depot_lon}], 13);
        
        // Add tile layer
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19
        }}).addTo(map);
        
        // Add markers
        {''.join(markers_js)}
        
        // Add routes
        {''.join(routes_js)}
        
        // Add legend
        var legend = L.control({{position: 'bottomright'}});
        legend.onAdd = function(map) {{
            var div = L.DomUtil.create('div', 'info legend');
            div.innerHTML = '<h4>VRP Solution</h4>' +
                           '<b>Total Distance:</b> {solution['total_distance']:.2f} km<br>' +
                           '<b>Total Orders:</b> {solution['total_orders']}<br>' +
                           '<b>Vehicles Used:</b> {solution['num_vehicles_used']}<br>' +
                           '<b>Total Load:</b> {solution['total_load']}';
            return div;
        }};
        legend.addTo(map);
    </script>
</body>
</html>
        """
        
        return html
