"""
VRPTW Solver using Tabu Search
Giải bài toán VRP với cửa sổ thời gian bằng Tìm kiếm Tabu

Thuật toán Metaheuristic với cơ chế memory (Tabu List) để tránh lặp lại
và thoát khỏi local optimum
"""

import pandas as pd
import numpy as np
import time
from pathlib import Path
import matplotlib.pyplot as plt
import random
from copy import deepcopy
from collections import deque


class TabuSearchVRPTWSolver:
    """
    Class giải bài toán VRPTW bằng Tabu Search
    """
    
    def __init__(self, dataset_path, vehicle_capacity=200, max_vehicles=25):
        """
        Khởi tạo solver
        
        Args:
            dataset_path: Đường dẫn đến file CSV dataset
            vehicle_capacity: Sức chứa của mỗi xe
            max_vehicles: Số lượng xe tối đa
        """
        self.dataset_path = dataset_path
        self.dataset_name = Path(dataset_path).stem
        self.vehicle_capacity = vehicle_capacity
        self.max_vehicles = max_vehicles
        
        # Đọc dữ liệu
        self.data = pd.read_csv(dataset_path)
        self.depot = self.data.iloc[0]
        self.customers = self.data.iloc[1:].reset_index(drop=True)
        
        # Số lượng khách hàng (không tính depot)
        self.n_customers = len(self.customers)
        
        # Tính ma trận khoảng cách
        self.distance_matrix = self._calculate_distance_matrix()
        
        # Tính ma trận thời gian di chuyển (giả sử vận tốc = 1)
        self.time_matrix = self.distance_matrix.copy()
        
        # Solution
        self.solution = None
        self.best_objective = float('inf')
        
        # Tabu list - lưu các move đã thực hiện gần đây
        self.tabu_list = deque(maxlen=20)  # Độ dài tabu list
        
    def _calculate_distance_matrix(self):
        """Tính ma trận khoảng cách Euclid"""
        n = self.n_customers + 1  # +1 cho depot
        dist_matrix = np.zeros((n, n))
        
        # Tạo danh sách tất cả các điểm (depot + customers)
        all_points = pd.concat([self.depot.to_frame().T, self.customers]).reset_index(drop=True)
        
        for i in range(n):
            for j in range(n):
                if i != j:
                    x1, y1 = all_points.loc[i, 'XCOORD.'], all_points.loc[i, 'YCOORD.']
                    x2, y2 = all_points.loc[j, 'XCOORD.'], all_points.loc[j, 'YCOORD.']
                    dist_matrix[i][j] = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        
        return dist_matrix
    
    def _check_time_window_feasibility(self, route):
        """
        Kiểm tra xem route có thỏa mãn time window không
        """
        if not route:
            return True
            
        current_time = 0
        current_location = 0  # Bắt đầu từ depot
        
        for customer_id in route:
            # Thời gian di chuyển đến khách hàng
            travel_time = self.time_matrix[current_location][customer_id]
            arrival_time = current_time + travel_time
            
            # Lấy thông tin time window
            ready_time = self.customers.loc[customer_id - 1, 'READY TIME']
            due_date = self.customers.loc[customer_id - 1, 'DUE DATE']
            service_time = self.customers.loc[customer_id - 1, 'SERVICE TIME']
            
            # Nếu đến sớm, phải đợi
            start_service = max(arrival_time, ready_time)
            
            # Kiểm tra có quá muộn không
            if start_service > due_date:
                return False
            
            # Cập nhật thời gian hiện tại
            current_time = start_service + service_time
            current_location = customer_id
        
        # Kiểm tra có về depot kịp không
        travel_time_back = self.time_matrix[current_location][0]
        return_time = current_time + travel_time_back
        depot_due_date = self.depot['DUE DATE']
        
        return return_time <= depot_due_date
    
    def _calculate_route_distance(self, route):
        """Tính quãng đường của một route"""
        if not route:
            return 0
            
        distance = 0
        
        # Từ depot đến khách hàng đầu tiên
        distance += self.distance_matrix[0][route[0]]
        
        # Giữa các khách hàng
        for i in range(len(route) - 1):
            distance += self.distance_matrix[route[i]][route[i+1]]
        
        # Từ khách hàng cuối về depot
        distance += self.distance_matrix[route[-1]][0]
        
        return distance
    
    def _calculate_route_load(self, route):
        """Tính tải trọng của một route"""
        return sum([self.customers.loc[customer_id - 1, 'DEMAND'] for customer_id in route])
    
    def _calculate_total_distance(self, routes):
        """Tính tổng quãng đường của tất cả routes"""
        return sum([self._calculate_route_distance(route) for route in routes if route])
    
    def _create_initial_solution_nearest_neighbor(self):
        """
        Tạo solution ban đầu bằng Nearest Neighbor
        """
        print("Tạo solution ban đầu bằng Nearest Neighbor...")
        
        routes = []
        unvisited = set(range(1, self.n_customers + 1))
        
        while unvisited and len(routes) < self.max_vehicles:
            # Bắt đầu route mới
            current_route = []
            current_load = 0
            current_location = 0  # depot
            
            while unvisited:
                # Tìm khách hàng gần nhất chưa thăm
                nearest = None
                min_distance = float('inf')
                
                for customer_id in unvisited:
                    demand = self.customers.loc[customer_id - 1, 'DEMAND']
                    
                    # Kiểm tra capacity
                    if current_load + demand > self.vehicle_capacity:
                        continue
                    
                    # Kiểm tra time window
                    test_route = current_route + [customer_id]
                    if not self._check_time_window_feasibility(test_route):
                        continue
                    
                    # Tính khoảng cách
                    dist = self.distance_matrix[current_location][customer_id]
                    if dist < min_distance:
                        min_distance = dist
                        nearest = customer_id
                
                if nearest is None:
                    break
                
                # Thêm khách hàng vào route
                current_route.append(nearest)
                current_load += self.customers.loc[nearest - 1, 'DEMAND']
                current_location = nearest
                unvisited.remove(nearest)
            
            if current_route:
                routes.append(current_route)
        
        # Nếu còn khách hàng chưa thăm, tạo thêm routes đơn giản
        while unvisited:
            customer_id = unvisited.pop()
            routes.append([customer_id])
        
        print(f"✓ Tạo được {len(routes)} routes ban đầu")
        print(f"  - Tổng quãng đường ban đầu: {self._calculate_total_distance(routes):.2f}")
        
        return routes
    
    def _get_move_hash(self, move_type, params):
        """
        Tạo hash cho một move để lưu vào tabu list
        """
        return (move_type, tuple(sorted(params)))
    
    def get_recommended_hyperparameters(self):
        """
        Tự động đề xuất siêu tham số dựa trên kích thước bài toán
        
        Returns:
            dict: Dictionary chứa các siêu tham số được đề xuất
        """
        n = self.n_customers
        
        # Tabu tenure: từ sqrt(n) đến 2*sqrt(n)
        min_tabu = max(10, int(np.sqrt(n)))
        max_tabu = max(15, int(2 * np.sqrt(n)))
        recommended_tabu = int(1.5 * np.sqrt(n))
        
        # Max iterations: tăng theo kích thước bài toán
        if n <= 50:
            max_iterations = 300
        elif n <= 100:
            max_iterations = 500
        else:
            max_iterations = 800
        
        # Diversification threshold: khoảng 10-20% của max_iterations
        diversification_threshold = max(30, int(0.15 * max_iterations))
        
        # Neighborhood size limit: để cân bằng giữa tốc độ và chất lượng
        if n <= 50:
            neighborhood_limit = None  # Không giới hạn
        elif n <= 100:
            neighborhood_limit = 500
        else:
            neighborhood_limit = 800
        
        recommendations = {
            'tabu_tenure': recommended_tabu,
            'tabu_tenure_range': (min_tabu, max_tabu),
            'max_iterations': max_iterations,
            'diversification_threshold': diversification_threshold,
            'neighborhood_size_limit': neighborhood_limit,
            'adaptive_tabu_tenure': n > 50,  # Bật adaptive cho bài toán lớn
            'aspiration_plus': True,  # Luôn bật
            'time_limit': 60  # Mặc định
        }
        
        return recommendations
    
    def print_hyperparameter_guide(self):
        """
        In hướng dẫn chi tiết về các siêu tham số
        """
        print("\n" + "="*80)
        print("📚 HƯỚNG DẪN ĐIỀU CHỈNH SIÊU THAM SỐ TABU SEARCH")
        print("="*80)
        
        print("\n1. TABU TENURE (Độ dài Tabu List):")
        print("   Công thức: sqrt(n) đến 2*sqrt(n), với n = số khách hàng")
        print(f"   Cho dataset này (n={self.n_customers}): {int(np.sqrt(self.n_customers))}-{int(2*np.sqrt(self.n_customers))}")
        print("   - Nhỏ (10-15): Intensification - khai thác sâu vùng tốt")
        print("   - Trung bình (15-25): Cân bằng")
        print("   - Lớn (25-40): Diversification - khám phá rộng")
        print("   ⚠️ Quá nhỏ: dễ bị kẹt local optimum")
        print("   ⚠️ Quá lớn: mất khả năng khai thác, chậm hội tụ")
        
        print("\n2. MAX ITERATIONS (Số vòng lặp tối đa):")
        print("   - Dataset nhỏ (<50 KH): 200-300 vòng")
        print("   - Dataset trung bình (50-100 KH): 400-600 vòng")
        print("   - Dataset lớn (>100 KH): 600-1000 vòng")
        print("   💡 Tăng nếu có đủ thời gian và muốn chất lượng cao hơn")
        
        print("\n3. DIVERSIFICATION THRESHOLD:")
        print("   Số vòng không cải thiện trước khi reset tabu list")
        print("   Công thức: 10-20% của max_iterations")
        print("   - Nhỏ (20-30): Diversify sớm, explore nhiều")
        print("   - Lớn (50-100): Exploit lâu hơn trước khi diversify")
        
        print("\n4. ASPIRATION CRITERION:")
        print("   - True (khuyến nghị): Chấp nhận tabu move nếu cải thiện best")
        print("   - False: Nghiêm ngặt, không bao giờ chấp nhận tabu move")
        
        print("\n5. ADAPTIVE TABU TENURE:")
        print("   - True: Tự động điều chỉnh tabu tenure trong quá trình tìm kiếm")
        print("     * Giảm khi tìm thấy improvement (intensification)")
        print("     * Tăng khi không cải thiện (diversification)")
        print("   - False: Giữ tabu tenure cố định")
        print("   💡 Khuyến nghị: Bật cho bài toán lớn (>50 KH)")
        
        print("\n6. NEIGHBORHOOD SIZE LIMIT:")
        print("   Giới hạn số neighbors đánh giá mỗi vòng (để tăng tốc)")
        print("   - None: Không giới hạn (chậm nhưng chất lượng cao)")
        print("   - 300-500: Cân bằng tốc độ và chất lượng")
        print("   - 100-200: Ưu tiên tốc độ")
        
        print("\n7. TIME LIMIT:")
        print("   - 30s: Test nhanh")
        print("   - 60s: Standard (khuyến nghị)")
        print("   - 120s+: Tìm kiếm chất lượng cao")
        
        print("\n" + "="*80)
        print("🎯 KHUYẾN NGHỊ CHO DATASET NÀY:")
        print("="*80)
        
        rec = self.get_recommended_hyperparameters()
        print(f"tabu_tenure = {rec['tabu_tenure']} (range: {rec['tabu_tenure_range']})")
        print(f"max_iterations = {rec['max_iterations']}")
        print(f"diversification_threshold = {rec['diversification_threshold']}")
        print(f"aspiration_plus = {rec['aspiration_plus']}")
        print(f"adaptive_tabu_tenure = {rec['adaptive_tabu_tenure']}")
        print(f"neighborhood_size_limit = {rec['neighborhood_size_limit']}")
        print(f"time_limit = {rec['time_limit']}")
        
        print("\n📝 VÍ DỤ SỬ DỤNG:")
        print("solver.solve(")
        print(f"    time_limit={rec['time_limit']},")
        print(f"    max_iterations={rec['max_iterations']},")
        print(f"    tabu_tenure={rec['tabu_tenure']},")
        print(f"    diversification_threshold={rec['diversification_threshold']},")
        print(f"    aspiration_plus={rec['aspiration_plus']},")
        print(f"    adaptive_tabu_tenure={rec['adaptive_tabu_tenure']},")
        print(f"    neighborhood_size_limit={rec['neighborhood_size_limit']}")
        print(")")
        print("="*80 + "\n")
    
    def _get_move_hash(self, move_type, params):
        """
        Tạo hash cho một move để lưu vào tabu list
        """
        return (move_type, tuple(sorted(params)))
    
    def _is_tabu(self, move_type, params):
        """
        Kiểm tra xem move có trong tabu list không
        """
        move_hash = self._get_move_hash(move_type, params)
        return move_hash in self.tabu_list
    
    def _add_to_tabu(self, move_type, params):
        """
        Thêm move vào tabu list
        """
        move_hash = self._get_move_hash(move_type, params)
        self.tabu_list.append(move_hash)
    
    def _get_neighborhood_relocate(self, routes, current_distance):
        """
        Tạo neighborhood bằng Relocate move
        Trả về list các (new_routes, distance, move_info)
        """
        neighbors = []
        
        for i, route_i in enumerate(routes):
            if not route_i:
                continue
                
            for pos_i, customer in enumerate(route_i):
                demand = self.customers.loc[customer - 1, 'DEMAND']
                
                # Thử chèn vào các route khác
                for j, route_j in enumerate(routes):
                    if i == j:
                        continue
                    
                    # Kiểm tra capacity
                    load_j = self._calculate_route_load(route_j)
                    if load_j + demand > self.vehicle_capacity:
                        continue
                    
                    # Thử tất cả vị trí chèn trong route_j
                    for pos_j in range(len(route_j) + 1):
                        # Tạo routes mới
                        new_route_i = route_i[:pos_i] + route_i[pos_i+1:]
                        new_route_j = route_j[:pos_j] + [customer] + route_j[pos_j:]
                        
                        # Kiểm tra time window
                        if not self._check_time_window_feasibility(new_route_i):
                            continue
                        if not self._check_time_window_feasibility(new_route_j):
                            continue
                        
                        # Tính khoảng cách mới
                        new_routes = routes[:]
                        new_routes[i] = new_route_i
                        new_routes[j] = new_route_j
                        new_distance = self._calculate_total_distance(new_routes)
                        
                        # Lưu neighbor
                        move_info = {
                            'type': 'relocate',
                            'customer': customer,
                            'from_route': i,
                            'to_route': j,
                            'from_pos': pos_i,
                            'to_pos': pos_j
                        }
                        
                        neighbors.append((new_routes, new_distance, move_info))
        
        return neighbors
    
    def _get_neighborhood_exchange(self, routes, current_distance):
        """
        Tạo neighborhood bằng Exchange move
        """
        neighbors = []
        
        for i, route_i in enumerate(routes):
            if not route_i:
                continue
                
            for j, route_j in enumerate(routes):
                if i >= j or not route_j:
                    continue
                
                for pos_i, customer_i in enumerate(route_i):
                    for pos_j, customer_j in enumerate(route_j):
                        demand_i = self.customers.loc[customer_i - 1, 'DEMAND']
                        demand_j = self.customers.loc[customer_j - 1, 'DEMAND']
                        
                        # Kiểm tra capacity
                        load_i = self._calculate_route_load(route_i)
                        load_j = self._calculate_route_load(route_j)
                        
                        new_load_i = load_i - demand_i + demand_j
                        new_load_j = load_j - demand_j + demand_i
                        
                        if new_load_i > self.vehicle_capacity or new_load_j > self.vehicle_capacity:
                            continue
                        
                        # Tạo routes mới
                        new_route_i = route_i[:]
                        new_route_j = route_j[:]
                        new_route_i[pos_i] = customer_j
                        new_route_j[pos_j] = customer_i
                        
                        # Kiểm tra time window
                        if not self._check_time_window_feasibility(new_route_i):
                            continue
                        if not self._check_time_window_feasibility(new_route_j):
                            continue
                        
                        # Tính khoảng cách mới
                        new_routes = routes[:]
                        new_routes[i] = new_route_i
                        new_routes[j] = new_route_j
                        new_distance = self._calculate_total_distance(new_routes)
                        
                        # Lưu neighbor
                        move_info = {
                            'type': 'exchange',
                            'customer_i': customer_i,
                            'customer_j': customer_j,
                            'route_i': i,
                            'route_j': j
                        }
                        
                        neighbors.append((new_routes, new_distance, move_info))
        
        return neighbors
    
    def _get_neighborhood_2opt(self, routes, current_distance):
        """
        Tạo neighborhood bằng 2-opt within route
        """
        neighbors = []
        
        for route_idx, route in enumerate(routes):
            if len(route) < 4:
                continue
            
            for i in range(len(route) - 2):
                for j in range(i + 2, len(route)):
                    # Tạo route mới bằng cách đảo ngược đoạn [i+1, j]
                    new_route = route[:i+1] + route[i+1:j+1][::-1] + route[j+1:]
                    
                    # Kiểm tra time window
                    if not self._check_time_window_feasibility(new_route):
                        continue
                    
                    # Tính khoảng cách mới
                    new_routes = routes[:]
                    new_routes[route_idx] = new_route
                    new_distance = self._calculate_total_distance(new_routes)
                    
                    # Lưu neighbor
                    move_info = {
                        'type': '2opt',
                        'route': route_idx,
                        'i': i,
                        'j': j
                    }
                    
                    neighbors.append((new_routes, new_distance, move_info))
        
        return neighbors
    
    def solve(self, 
              time_limit=60, 
              max_iterations=500, 
              tabu_tenure=20,
              diversification_threshold=50,
              aspiration_plus=True,
              neighborhood_size_limit=None,
              adaptive_tabu_tenure=False):
        """
        Giải bài toán bằng Tabu Search
        
        Args:
            time_limit: Giới hạn thời gian (giây) - default 60
            max_iterations: Số vòng lặp tối đa - default 500
            tabu_tenure: Độ dài tabu list - default 20
                        Nhỏ (10-15): Intensification (tập trung khai thác)
                        Lớn (20-30): Diversification (khám phá rộng)
                        Khuyến nghị: sqrt(n_customers) đến 2*sqrt(n_customers)
            diversification_threshold: Số vòng không cải thiện trước khi reset tabu - default 50
            aspiration_plus: Sử dụng aspiration criterion - default True
            neighborhood_size_limit: Giới hạn số neighbors đánh giá (None = không giới hạn)
            adaptive_tabu_tenure: Tự động điều chỉnh tabu tenure - default False
        """
        print(f"\n{'='*80}")
        print(f"XÂY DỰNG GIẢI PHÁP BẰNG TABU SEARCH")
        print(f"{'='*80}")
        print(f"Dataset: {self.dataset_name}")
        print(f"Số khách hàng: {self.n_customers}")
        print(f"Sức chứa xe: {self.vehicle_capacity}")
        print(f"Số xe tối đa: {self.max_vehicles}")
        print(f"\n📊 SIÊU THAM SỐ:")
        print(f"  - Thời gian giới hạn: {time_limit}s")
        print(f"  - Số vòng lặp tối đa: {max_iterations}")
        print(f"  - Tabu tenure: {tabu_tenure}")
        print(f"  - Diversification threshold: {diversification_threshold}")
        print(f"  - Aspiration criterion: {'✅ Bật' if aspiration_plus else '❌ Tắt'}")
        print(f"  - Adaptive tabu tenure: {'✅ Bật' if adaptive_tabu_tenure else '❌ Tắt'}")
        if neighborhood_size_limit:
            print(f"  - Neighborhood size limit: {neighborhood_size_limit}")
        print(f"{'='*80}\n")
        
        start_time = time.time()
        
        # Cập nhật tabu list size
        initial_tabu_tenure = tabu_tenure
        self.tabu_list = deque(maxlen=tabu_tenure)
        
        # Adaptive tabu tenure parameters
        if adaptive_tabu_tenure:
            min_tenure = max(5, int(tabu_tenure * 0.5))
            max_tenure = int(tabu_tenure * 1.5)
            print(f"🔧 Adaptive tabu tenure: [{min_tenure}, {max_tenure}]")
        
        # Tạo solution ban đầu
        current_routes = self._create_initial_solution_nearest_neighbor()
        current_distance = self._calculate_total_distance(current_routes)
        
        best_routes = deepcopy(current_routes)
        best_distance = current_distance
        
        print(f"\nBắt đầu Tabu Search...")
        print(f"Solution ban đầu: {best_distance:.2f}")
        
        iterations = 0
        improvements_log = []
        no_improvement_count = 0
        
        while iterations < max_iterations:
            elapsed_time = time.time() - start_time
            if elapsed_time > time_limit:
                print(f"\n⏱ Đạt giới hạn thời gian ({time_limit}s)")
                break
            
            iterations += 1
            
            # Tạo neighborhood
            neighbors = []
            
            # Thêm relocate moves
            neighbors.extend(self._get_neighborhood_relocate(current_routes, current_distance))
            
            # Thêm exchange moves (giới hạn để tăng tốc)
            if iterations % 2 == 0:  # Chỉ thực hiện mỗi 2 vòng
                neighbors.extend(self._get_neighborhood_exchange(current_routes, current_distance))
            
            # Thêm 2-opt moves
            neighbors.extend(self._get_neighborhood_2opt(current_routes, current_distance))
            
            # Giới hạn neighborhood size nếu cần (để tăng tốc)
            if neighborhood_size_limit and len(neighbors) > neighborhood_size_limit:
                # Random sampling để đảm bảo diversity
                import random
                neighbors = random.sample(neighbors, neighborhood_size_limit)
            
            if not neighbors:
                print(f"\n⚠ Không tìm thấy neighbor nào ở vòng {iterations}")
                break
            
            # Sắp xếp neighbors theo distance
            neighbors.sort(key=lambda x: x[1])
            
            # Chọn best non-tabu move hoặc aspiration criterion
            best_neighbor = None
            for new_routes, new_distance, move_info in neighbors:
                move_type = move_info['type']
                
                # Tạo params cho move
                if move_type == 'relocate':
                    params = (move_info['customer'], move_info['from_route'], move_info['to_route'])
                elif move_type == 'exchange':
                    params = (move_info['customer_i'], move_info['customer_j'])
                elif move_type == '2opt':
                    params = (move_info['route'], move_info['i'], move_info['j'])
                else:
                    params = ()
                
                # Kiểm tra tabu
                is_tabu = self._is_tabu(move_type, params)
                
                # Aspiration criterion: chấp nhận move tabu nếu cải thiện best solution
                if is_tabu:
                    if aspiration_plus and new_distance < best_distance:
                        # Aspiration: chấp nhận tabu move nếu cải thiện best
                        pass
                    else:
                        # Bỏ qua move tabu
                        continue
                
                # Chọn move này
                best_neighbor = (new_routes, new_distance, move_info, move_type, params)
                break
            
            if best_neighbor is None:
                print(f"\n⚠ Tất cả moves đều bị tabu ở vòng {iterations}")
                break
            
            new_routes, new_distance, move_info, move_type, params = best_neighbor
            
            # Cập nhật current solution
            current_routes = new_routes
            current_distance = new_distance
            
            # Thêm move vào tabu list
            self._add_to_tabu(move_type, params)
            
            # Cập nhật best solution
            if current_distance < best_distance:
                best_routes = deepcopy(current_routes)
                best_distance = current_distance
                improvements_log.append({
                    'iteration': iterations,
                    'distance': best_distance,
                    'time': time.time() - start_time,
                    'move': move_type
                })
                print(f"  Vòng {iterations}: Cải thiện! Distance = {best_distance:.2f} (Move: {move_type})")
                no_improvement_count = 0
                
                # Adaptive tabu tenure: giảm khi tìm thấy improvement (intensification)
                if adaptive_tabu_tenure and tabu_tenure > min_tenure:
                    tabu_tenure = max(min_tenure, tabu_tenure - 1)
                    self.tabu_list = deque(self.tabu_list, maxlen=tabu_tenure)
            else:
                no_improvement_count += 1
                
                # Adaptive tabu tenure: tăng khi không cải thiện (diversification)
                if adaptive_tabu_tenure and no_improvement_count % 10 == 0 and tabu_tenure < max_tenure:
                    tabu_tenure = min(max_tenure, tabu_tenure + 1)
                    self.tabu_list = deque(self.tabu_list, maxlen=tabu_tenure)
            
            # Diversification: Reset tabu list nếu stuck quá lâu
            if no_improvement_count >= diversification_threshold:
                print(f"  Vòng {iterations}: 🔄 Diversification - Reset tabu list")
                self.tabu_list.clear()
                no_improvement_count = 0
                
                # Reset tabu tenure về giá trị ban đầu
                if adaptive_tabu_tenure:
                    tabu_tenure = initial_tabu_tenure
                    self.tabu_list = deque(maxlen=tabu_tenure)
            
            # In tiến độ mỗi 50 vòng
            if iterations % 50 == 0:
                tabu_info = f", Tabu={len(self.tabu_list)}/{tabu_tenure}" if adaptive_tabu_tenure else f", Tabu={len(self.tabu_list)}"
                print(f"  Vòng {iterations}: Current = {current_distance:.2f}, Best = {best_distance:.2f}{tabu_info}")
        
        solve_time = time.time() - start_time
        
        # Loại bỏ routes rỗng
        best_routes = [route for route in best_routes if route]
        
        # Chuyển đổi sang format solution
        self.solution = {}
        route_id = 0
        
        for customers_list in best_routes:
            distance = self._calculate_route_distance(customers_list)
            load = self._calculate_route_load(customers_list)
            
            self.solution[route_id] = {
                'route': customers_list,
                'distance': distance,
                'load': load,
                'num_customers': len(customers_list)
            }
            route_id += 1
        
        # In kết quả
        print(f"\n{'='*80}")
        print(f"KẾT QUẢ GIẢI")
        print(f"{'='*80}")
        print(f"Trạng thái: Feasible (Tabu Search)")
        print(f"Thời gian giải: {solve_time:.2f} giây")
        print(f"Số vòng lặp: {iterations}")
        print(f"Số lần cải thiện: {len(improvements_log)}")
        print(f"Số xe sử dụng: {len(self.solution)}")
        print(f"Tổng quãng đường: {best_distance:.2f}")
        
        if improvements_log:
            initial_distance = self._calculate_total_distance(
                self._create_initial_solution_nearest_neighbor()
            )
            improvement_pct = ((initial_distance - best_distance) / initial_distance * 100)
            print(f"Cải thiện so với initial: {improvement_pct:.2f}%")
        
        # In chi tiết routes
        print(f"\n{'='*80}")
        print(f"CHI TIẾT CÁC TUYẾN ĐƯỜNG")
        print(f"{'='*80}")
        
        for route_id, info in self.solution.items():
            print(f"\nXe {route_id + 1}:")
            print(f"  Tuyến đường: 0 → {' → '.join(map(str, info['route']))} → 0")
            print(f"  Số khách hàng: {info['num_customers']}")
            print(f"  Tổng nhu cầu: {info['load']}/{self.vehicle_capacity}")
            print(f"  Quãng đường: {info['distance']:.2f}")
        
        return {
            'status': 'Feasible (Tabu Search)',
            'objective': best_distance,
            'time': solve_time,
            'routes': self.solution,
            'iterations': iterations,
            'improvements': len(improvements_log),
            'improvements_log': improvements_log
        }
    
    def visualize_solution_comprehensive(self, save=False):
        """
        Vẽ biểu đồ tổng hợp với nhiều sub-plots
        Bao gồm: Routes, Thống kê xe, Phân bố customers
        """
        if self.solution is None:
            print("❌ Chưa có solution để vẽ!")
            return
        
        # Tắt chế độ interactive để không hiển thị cửa sổ
        plt.ioff()
        
        fig = plt.figure(figsize=(20, 12))
        gs = fig.add_gridspec(2, 3, hspace=0.3, wspace=0.3)
        
        # ============= 1. VẼ CÁC TUYẾN ĐƯỜNG (CHÍNH - LỚN) =============
        ax1 = fig.add_subplot(gs[0:2, 0:2])
        
        # Vẽ depot
        depot_x = self.depot['XCOORD.']
        depot_y = self.depot['YCOORD.']
        ax1.scatter(depot_x, depot_y,
                   c='red', s=600, marker='s', edgecolors='black',
                   linewidth=3, label='Kho', zorder=5)
        
        # Vẽ customers
        ax1.scatter(self.customers['XCOORD.'], self.customers['YCOORD.'],
                   c='lightblue', s=200, edgecolors='black',
                   linewidth=1.5, label='Khách hàng', zorder=3)
        
        # Vẽ các routes với màu khác nhau
        colors = plt.cm.tab20(np.linspace(0, 1, len(self.solution)))
        
        for idx, (route_id, info) in enumerate(self.solution.items()):
            route = [0] + info['route'] + [0]
            color = colors[idx]
            
            # Vẽ đường đi
            for i in range(len(route) - 1):
                node1, node2 = route[i], route[i+1]
                
                if node1 == 0:
                    x1, y1 = depot_x, depot_y
                else:
                    x1, y1 = self.customers.loc[node1-1, 'XCOORD.'], self.customers.loc[node1-1, 'YCOORD.']
                
                if node2 == 0:
                    x2, y2 = depot_x, depot_y
                else:
                    x2, y2 = self.customers.loc[node2-1, 'XCOORD.'], self.customers.loc[node2-1, 'YCOORD.']
                
                ax1.plot([x1, x2], [y1, y2], color=color, linewidth=2.5, alpha=0.7, zorder=2)
                
                # Vẽ mũi tên
                dx, dy = x2 - x1, y2 - y1
                ax1.annotate('', xy=(x2, y2), xytext=(x1, y1),
                            arrowprops=dict(arrowstyle='->', color=color, lw=2, alpha=0.7))
            
            # Label cho route
            if len(info['route']) > 0:
                mid_idx = len(info['route']) // 2
                mid_customer = info['route'][mid_idx]
                mid_x = self.customers.loc[mid_customer-1, 'XCOORD.']
                mid_y = self.customers.loc[mid_customer-1, 'YCOORD.']
                
                ax1.text(mid_x, mid_y + 5, f"Xe {route_id+1}", 
                        fontsize=10, fontweight='bold',
                        ha='center', bbox=dict(boxstyle='round,pad=0.4', facecolor=color, alpha=0.8))
        
        # Thêm số thứ tự khách hàng
        for idx, row in self.customers.iterrows():
            ax1.annotate(str(idx + 1), (row['XCOORD.'], row['YCOORD.']),
                        fontsize=9, ha='center', va='center', fontweight='bold')
        
        ax1.set_xlabel('Tọa độ X', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Tọa độ Y', fontsize=12, fontweight='bold')
        ax1.set_title('① Các tuyến đường (Tabu Search - Metaheuristic)',
                     fontsize=14, fontweight='bold', pad=12)
        ax1.legend(fontsize=11, loc='best')
        ax1.grid(True, alpha=0.3, linestyle='--')
        
        # ============= 2. THỐNG KÊ CÁC XE =============
        ax2 = fig.add_subplot(gs[0, 2])
        
        vehicles = list(self.solution.keys())
        distances = [info['distance'] for info in self.solution.values()]
        loads = [info['load'] for info in self.solution.values()]
        
        x = np.arange(len(vehicles))
        width = 0.35
        
        bars1 = ax2.bar(x - width/2, distances, width, label='Quãng đường',
                       color='steelblue', alpha=0.8, edgecolor='black', linewidth=1.5)
        ax2_twin = ax2.twinx()
        bars2 = ax2_twin.bar(x + width/2, loads, width, label='Tải trọng',
                            color='coral', alpha=0.8, edgecolor='black', linewidth=1.5)
        
        ax2.set_xlabel('Xe', fontsize=11, fontweight='bold')
        ax2.set_ylabel('Quãng đường', fontsize=11, fontweight='bold', color='steelblue')
        ax2_twin.set_ylabel('Tải trọng', fontsize=11, fontweight='bold', color='coral')
        ax2.set_title('② Thống kê các xe', fontsize=13, fontweight='bold', pad=10)
        ax2.set_xticks(x)
        ax2.set_xticklabels([f'Xe {v+1}' for v in vehicles], fontsize=9)
        ax2.tick_params(axis='y', labelcolor='steelblue')
        ax2_twin.tick_params(axis='y', labelcolor='coral')
        ax2.grid(True, alpha=0.3, axis='y', linestyle='--')
        
        # Thêm giá trị trên các cột
        for bar in bars1:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}', ha='center', va='bottom', fontsize=8)
        
        for bar in bars2:
            height = bar.get_height()
            ax2_twin.text(bar.get_x() + bar.get_width()/2., height,
                         f'{int(height)}', ha='center', va='bottom', fontsize=8)
        
        # ============= 3. PHÂN BỐ KHÁCH HÀNG =============
        ax3 = fig.add_subplot(gs[1, 2])
        
        num_customers_per_vehicle = [info['num_customers'] for info in self.solution.values()]
        
        # Pie chart
        colors_pie = plt.cm.Set3(np.linspace(0, 1, len(vehicles)))
        wedges, texts, autotexts = ax3.pie(num_customers_per_vehicle, 
                                            labels=[f'Xe {v+1}' for v in vehicles],
                                            autopct='%1.1f%%',
                                            startangle=90,
                                            colors=colors_pie,
                                            textprops={'fontsize': 10, 'fontweight': 'bold'})
        
        ax3.set_title('③ Phân bố số khách hàng', fontsize=13, fontweight='bold', pad=10)
        
        # Thêm legend với thông tin chi tiết
        legend_labels = [f'Xe {v+1}: {num_customers_per_vehicle[i]} KH' 
                        for i, v in enumerate(vehicles)]
        ax3.legend(legend_labels, loc='upper left', bbox_to_anchor=(1, 1), fontsize=9)
        
        # ============= TIÊU ĐỀ CHÍNH =============
        total_distance = sum([info['distance'] for info in self.solution.values()])
        total_customers = sum(num_customers_per_vehicle)
        
        fig.suptitle(
            f'KẾT QUẢ TABU SEARCH ALGORITHM - {self.dataset_name}\n'
            f'Số xe: {len(self.solution)} | Tổng quãng đường: {total_distance:.2f} | '
            f'Khách hàng phục vụ: {total_customers}/{self.n_customers}',
            fontsize=16, fontweight='bold', y=0.98
        )
        
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        
        if save:
            output_dir = Path(__file__).parent / 'result' / 'images'
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f'{self.dataset_name}_tabu_solution.png'
            plt.savefig(str(output_path), dpi=300, bbox_inches='tight')
            print(f"✓ Đã lưu hình ảnh: {output_path}")
        
        plt.close(fig)  # Đóng figure để giải phóng bộ nhớ
    
    def visualize_solution(self, save=False):
        """Wrapper để tương thích - gọi comprehensive visualization"""
        self.visualize_solution_comprehensive(save)
    
    def save_solution(self, solve_time=None, status=None, iterations=None, improvements=None):
        """Lưu solution ra file TXT chi tiết"""
        if self.solution is None:
            print("❌ Chưa có solution để lưu!")
            return
        
        output_dir = Path(__file__).parent / 'result' / 'text'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f'{self.dataset_name}_tabu_solution.txt'
        
        total_distance = sum([r['distance'] for r in self.solution.values()])
        total_load = sum([r['load'] for r in self.solution.values()])
        total_customers_served = sum([r['num_customers'] for r in self.solution.values()])
        
        with open(str(output_path), 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write(f"BÁO CÁO KẾT QUẢ TABU SEARCH ALGORITHM\n")
            f.write(f"Metaheuristic with Memory for VRPTW\n")
            f.write("="*80 + "\n\n")
            
            f.write(f"Dataset: {self.dataset_name}\n")
            f.write(f"Ngày giờ: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("\n")
            
            # THÔNG SỐ BÀI TOÁN
            f.write("="*80 + "\n")
            f.write("THÔNG SỐ BÀI TOÁN\n")
            f.write("="*80 + "\n")
            f.write(f"Số khách hàng: {self.n_customers}\n")
            f.write(f"Sức chứa xe: {self.vehicle_capacity}\n")
            f.write(f"Số xe tối đa: {self.max_vehicles}\n")
            if solve_time:
                f.write(f"Thời gian giải: {solve_time:.2f} giây\n")
            if status:
                f.write(f"Trạng thái: {status}\n")
            if iterations:
                f.write(f"Số vòng lặp: {iterations}\n")
            if improvements:
                f.write(f"Số lần cải thiện: {improvements}\n")
            f.write(f"Tabu list size: {self.tabu_list.maxlen}\n")
            f.write("\n")
            
            # PHƯƠNG PHÁP TABU SEARCH
            f.write("="*80 + "\n")
            f.write("PHƯƠNG PHÁP TABU SEARCH\n")
            f.write("="*80 + "\n")
            f.write("Đặc điểm:\n")
            f.write("  - Metaheuristic với cơ chế memory (Tabu List)\n")
            f.write("  - Tránh lặp lại các move đã thực hiện gần đây\n")
            f.write("  - Có thể thoát khỏi local optimum\n")
            f.write("  - Aspiration criterion: chấp nhận tabu move nếu cải thiện best\n")
            f.write("\nCác phép biến đổi:\n")
            f.write("  1. Relocate: Di chuyển khách hàng giữa routes\n")
            f.write("  2. Exchange: Hoán đổi khách hàng giữa routes\n")
            f.write("  3. 2-opt: Đảo ngược đoạn trong route\n")
            f.write("\n")
            
            # KẾT QUẢ TỔNG HỢP
            f.write("="*80 + "\n")
            f.write("KẾT QUẢ TỔNG HỢP\n")
            f.write("="*80 + "\n")
            f.write(f"Số xe sử dụng: {len(self.solution)}\n")
            f.write(f"Tổng quãng đường: {total_distance:.2f}\n")
            f.write(f"Quãng đường trung bình/xe: {total_distance/len(self.solution):.2f}\n")
            f.write(f"Tổng tải trọng: {total_load}\n")
            f.write(f"Tải trọng trung bình/xe: {total_load/len(self.solution):.2f}\n")
            f.write(f"Khách hàng được phục vụ: {total_customers_served}/{self.n_customers}\n")
            f.write(f"Tỷ lệ phục vụ: {(total_customers_served/self.n_customers)*100:.1f}%\n")
            f.write("\n")
            
            # THỐNG KÊ THEO XE
            f.write("="*80 + "\n")
            f.write("THỐNG KÊ THEO XE\n")
            f.write("="*80 + "\n")
            f.write(f"{'Xe':<8} {'Số KH':<10} {'Quãng đường':<15} {'Tải trọng':<15} {'% Capacity':<12}\n")
            f.write("-"*80 + "\n")
            
            for route_id, info in self.solution.items():
                capacity_pct = (info['load'] / self.vehicle_capacity) * 100
                f.write(f"{route_id+1:<8} {info['num_customers']:<10} {info['distance']:<15.2f} "
                       f"{info['load']:<15} {capacity_pct:<12.1f}\n")
            f.write("\n")
            
            # CHI TIẾT CÁC TUYẾN ĐƯỜNG
            f.write("="*80 + "\n")
            f.write("CHI TIẾT CÁC TUYẾN ĐƯỜNG\n")
            f.write("="*80 + "\n\n")
            
            for route_id, info in self.solution.items():
                f.write(f"{'─'*80}\n")
                f.write(f"XE {route_id + 1}\n")
                f.write(f"{'─'*80}\n")
                f.write(f"Tuyến đường: 0 (Kho) → {' → '.join(map(str, info['route']))} → 0 (Kho)\n")
                f.write(f"Số khách hàng: {info['num_customers']}\n")
                f.write(f"Tổng nhu cầu: {info['load']}/{self.vehicle_capacity} "
                       f"({(info['load']/self.vehicle_capacity)*100:.1f}%)\n")
                f.write(f"Quãng đường: {info['distance']:.2f}\n")
                
                # Chi tiết từng khách hàng trong route
                f.write(f"\nChi tiết khách hàng:\n")
                f.write(f"  {'STT':<6} {'KH':<6} {'Nhu cầu':<10} {'Ready Time':<12} {'Due Date':<12} {'Service Time':<12}\n")
                f.write(f"  {'-'*80}\n")
                
                for idx, customer_id in enumerate(info['route'], 1):
                    cust = self.customers.loc[customer_id-1]
                    f.write(f"  {idx:<6} {customer_id:<6} {cust['DEMAND']:<10} "
                           f"{cust['READY TIME']:<12.0f} {cust['DUE DATE']:<12.0f} "
                           f"{cust['SERVICE TIME']:<12.0f}\n")
                f.write("\n")
            
            f.write("="*80 + "\n")
            f.write("KẾT THÚC BÁO CÁO\n")
            f.write("="*80 + "\n")
        
        print(f"✓ Đã lưu báo cáo chi tiết: {output_path}")


def main():
    """Hàm chính để chạy Tabu Search solver"""
    
    # Đường dẫn đến dataset
    current_dir = Path(__file__).parent
    code_dir = current_dir.parent.parent
    dataset_path = code_dir / "dataset" / "C1" / "C101.csv"
    
    print("="*80)
    print("TABU SEARCH FOR VRPTW")
    print("="*80)
    print("✓ Thuật toán Metaheuristic với cơ chế memory (Tabu List)")
    print("✓ Tránh lặp lại và thoát khỏi local optimum")
    print("✓ Có thể giải toàn bộ dataset (100+ khách hàng)")
    print("✓ Chất lượng solution rất tốt, tốt hơn Local Search")
    print("="*80)
    
    # Tạo solver
    solver = TabuSearchVRPTWSolver(
        dataset_path=str(dataset_path),
        vehicle_capacity=200,
        max_vehicles=25
    )
    
    # Hiển thị hướng dẫn siêu tham số
    solver.print_hyperparameter_guide()
    
    # Lấy siêu tham số được đề xuất
    hyperparams = solver.get_recommended_hyperparameters()
    
    print("🚀 Bắt đầu giải với siêu tham số được đề xuất...")
    
    # Giải bài toán với siêu tham số tự động
    result = solver.solve(
        time_limit=hyperparams['time_limit'],
        max_iterations=hyperparams['max_iterations'],
        tabu_tenure=hyperparams['tabu_tenure'],
        diversification_threshold=hyperparams['diversification_threshold'],
        aspiration_plus=hyperparams['aspiration_plus'],
        adaptive_tabu_tenure=hyperparams['adaptive_tabu_tenure'],
        neighborhood_size_limit=hyperparams['neighborhood_size_limit']
    )
    
    if result:
        # Vẽ và lưu solution
        print("\n" + "="*80)
        print("TẠO TRỰC QUAN HÓA VÀ BÁO CÁO")
        print("="*80)
        solver.visualize_solution(save=True)
        solver.save_solution(
            solve_time=result['time'],
            status=result['status'],
            iterations=result['iterations'],
            improvements=result['improvements']
        )
        print("✓ Đã tạo file PNG và TXT trong thư mục 'result/'")
    else:
        print("\n❌ Không thể tạo solution!")
    
    print("\n" + "="*80)
    print("HOÀN THÀNH!")
    print("="*80)


if __name__ == "__main__":
    main()
