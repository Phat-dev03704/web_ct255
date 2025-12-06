"""
VRPTW Solver using Simulated Annealing
Giải bài toán VRP với cửa sổ thời gian bằng Thuật toán luyện kim

Thuật toán Metaheuristic mô phỏng quá trình luyện kim trong vật lý
Có thể chấp nhận giải pháp tệ hơn với xác suất giảm dần theo nhiệt độ
"""

import pandas as pd
import numpy as np
import time
from pathlib import Path
import matplotlib.pyplot as plt
import random
import math
from copy import deepcopy


class SimulatedAnnealingVRPTWSolver:
    """
    Class giải bài toán VRPTW bằng Simulated Annealing
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
    
    def _get_neighbor_relocate(self, routes):
        """
        Tạo neighbor bằng Relocate: di chuyển một khách hàng sang route khác
        """
        new_routes = deepcopy(routes)
        
        # Chọn ngẫu nhiên route nguồn có ít nhất 1 khách hàng
        non_empty = [i for i, r in enumerate(new_routes) if len(r) > 0]
        if not non_empty:
            return None
        
        from_route_idx = random.choice(non_empty)
        from_route = new_routes[from_route_idx]
        
        # Chọn ngẫu nhiên khách hàng
        if not from_route:
            return None
        customer_pos = random.randint(0, len(from_route) - 1)
        customer = from_route[customer_pos]
        
        # Chọn ngẫu nhiên route đích
        to_route_idx = random.randint(0, len(new_routes) - 1)
        if to_route_idx == from_route_idx and len(from_route) == 1:
            return None
        
        # Chọn vị trí chèn
        to_route = new_routes[to_route_idx]
        insert_pos = random.randint(0, len(to_route))
        
        # Thực hiện move
        demand = self.customers.loc[customer - 1, 'DEMAND']
        
        # Kiểm tra capacity
        if to_route_idx != from_route_idx:
            to_load = self._calculate_route_load(to_route)
            if to_load + demand > self.vehicle_capacity:
                return None
        
        # Tạo routes mới
        new_from_route = from_route[:customer_pos] + from_route[customer_pos+1:]
        new_to_route = to_route[:insert_pos] + [customer] + to_route[insert_pos:]
        
        # Kiểm tra time window
        if not self._check_time_window_feasibility(new_from_route):
            return None
        if not self._check_time_window_feasibility(new_to_route):
            return None
        
        new_routes[from_route_idx] = new_from_route
        new_routes[to_route_idx] = new_to_route
        
        return new_routes
    
    def _get_neighbor_exchange(self, routes):
        """
        Tạo neighbor bằng Exchange: hoán đổi hai khách hàng giữa hai routes
        """
        new_routes = deepcopy(routes)
        
        # Chọn ngẫu nhiên 2 routes có khách hàng
        non_empty = [i for i, r in enumerate(new_routes) if len(r) > 0]
        if len(non_empty) < 2:
            return None
        
        route1_idx, route2_idx = random.sample(non_empty, 2)
        route1 = new_routes[route1_idx]
        route2 = new_routes[route2_idx]
        
        # Chọn ngẫu nhiên khách hàng từ mỗi route
        pos1 = random.randint(0, len(route1) - 1)
        pos2 = random.randint(0, len(route2) - 1)
        
        customer1 = route1[pos1]
        customer2 = route2[pos2]
        
        demand1 = self.customers.loc[customer1 - 1, 'DEMAND']
        demand2 = self.customers.loc[customer2 - 1, 'DEMAND']
        
        # Kiểm tra capacity
        load1 = self._calculate_route_load(route1)
        load2 = self._calculate_route_load(route2)
        
        new_load1 = load1 - demand1 + demand2
        new_load2 = load2 - demand2 + demand1
        
        if new_load1 > self.vehicle_capacity or new_load2 > self.vehicle_capacity:
            return None
        
        # Tạo routes mới
        new_route1 = route1[:]
        new_route2 = route2[:]
        new_route1[pos1] = customer2
        new_route2[pos2] = customer1
        
        # Kiểm tra time window
        if not self._check_time_window_feasibility(new_route1):
            return None
        if not self._check_time_window_feasibility(new_route2):
            return None
        
        new_routes[route1_idx] = new_route1
        new_routes[route2_idx] = new_route2
        
        return new_routes
    
    def _get_neighbor_2opt(self, routes):
        """
        Tạo neighbor bằng 2-opt: đảo ngược một đoạn trong route
        """
        new_routes = deepcopy(routes)
        
        # Chọn ngẫu nhiên route có ít nhất 4 khách hàng
        valid_routes = [i for i, r in enumerate(new_routes) if len(r) >= 4]
        if not valid_routes:
            return None
        
        route_idx = random.choice(valid_routes)
        route = new_routes[route_idx]
        
        # Chọn ngẫu nhiên 2 điểm cắt
        i = random.randint(0, len(route) - 3)
        j = random.randint(i + 2, len(route) - 1)
        
        # Đảo ngược đoạn [i+1, j]
        new_route = route[:i+1] + route[i+1:j+1][::-1] + route[j+1:]
        
        # Kiểm tra time window
        if not self._check_time_window_feasibility(new_route):
            return None
        
        new_routes[route_idx] = new_route
        
        return new_routes
    
    def _get_neighbor(self, routes):
        """
        Tạo neighbor ngẫu nhiên bằng một trong các operators
        """
        operators = [
            self._get_neighbor_relocate,
            self._get_neighbor_exchange,
            self._get_neighbor_2opt
        ]
        
        # Thử các operators theo thứ tự ngẫu nhiên
        random.shuffle(operators)
        
        for operator in operators:
            neighbor = operator(routes)
            if neighbor is not None:
                return neighbor
        
        return None
    
    def _acceptance_probability(self, current_cost, new_cost, temperature):
        """
        Tính xác suất chấp nhận solution tệ hơn
        Công thức: exp(-(new_cost - current_cost) / temperature)
        """
        if new_cost < current_cost:
            return 1.0
        else:
            return math.exp(-(new_cost - current_cost) / temperature)
    
    def get_recommended_hyperparameters(self):
        """
        Tự động đề xuất siêu tham số dựa trên kích thước bài toán
        """
        n = self.n_customers
        
        # Initial temperature: Khoảng 10-20% của average distance
        avg_distance = np.mean(self.distance_matrix[self.distance_matrix > 0])
        initial_temp = avg_distance * 10
        
        # Final temperature: 0.1-1% của initial
        final_temp = initial_temp * 0.001
        
        # Cooling rate: 0.95-0.99
        if n <= 50:
            cooling_rate = 0.97
            max_iterations_per_temp = 100
        elif n <= 100:
            cooling_rate = 0.98
            max_iterations_per_temp = 150
        else:
            cooling_rate = 0.99
            max_iterations_per_temp = 200
        
        return {
            'initial_temperature': initial_temp,
            'final_temperature': final_temp,
            'cooling_rate': cooling_rate,
            'max_iterations_per_temp': max_iterations_per_temp,
            'time_limit': 60
        }
    
    def solve(self, 
              initial_temperature=1000.0,
              final_temperature=1.0,
              cooling_rate=0.98,
              max_iterations_per_temp=150,
              time_limit=60):
        """
        Giải bài toán bằng Simulated Annealing
        
        Args:
            initial_temperature: Nhiệt độ ban đầu (cao → chấp nhận nhiều worse solution)
            final_temperature: Nhiệt độ cuối (thấp → chỉ chấp nhận better solution)
            cooling_rate: Tốc độ giảm nhiệt (0.95-0.99)
            max_iterations_per_temp: Số vòng lặp ở mỗi mức nhiệt độ
            time_limit: Giới hạn thời gian (giây)
        """
        print(f"\n{'='*80}")
        print(f"XÂY DỰNG GIẢI PHÁP BẰNG SIMULATED ANNEALING")
        print(f"{'='*80}")
        print(f"Dataset: {self.dataset_name}")
        print(f"Số khách hàng: {self.n_customers}")
        print(f"Sức chứa xe: {self.vehicle_capacity}")
        print(f"Số xe tối đa: {self.max_vehicles}")
        print(f"\n🌡️ SIÊU THAM SỐ:")
        print(f"  - Nhiệt độ ban đầu: {initial_temperature:.2f}")
        print(f"  - Nhiệt độ cuối: {final_temperature:.2f}")
        print(f"  - Tốc độ làm lạnh: {cooling_rate}")
        print(f"  - Iterations/nhiệt độ: {max_iterations_per_temp}")
        print(f"  - Thời gian giới hạn: {time_limit}s")
        print(f"{'='*80}\n")
        
        start_time = time.time()
        
        # Tạo solution ban đầu
        current_routes = self._create_initial_solution_nearest_neighbor()
        current_distance = self._calculate_total_distance(current_routes)
        
        best_routes = deepcopy(current_routes)
        best_distance = current_distance
        
        print(f"\nBắt đầu Simulated Annealing...")
        print(f"Solution ban đầu: {best_distance:.2f}")
        
        temperature = initial_temperature
        iterations = 0
        improvements_log = []
        accepted_count = 0
        rejected_count = 0
        
        while temperature > final_temperature:
            elapsed_time = time.time() - start_time
            if elapsed_time > time_limit:
                print(f"\n⏱ Đạt giới hạn thời gian ({time_limit}s)")
                break
            
            for iter_at_temp in range(max_iterations_per_temp):
                iterations += 1
                
                # Tạo neighbor
                neighbor_routes = self._get_neighbor(current_routes)
                
                if neighbor_routes is None:
                    continue
                
                neighbor_distance = self._calculate_total_distance(neighbor_routes)
                
                # Tính xác suất chấp nhận
                acceptance_prob = self._acceptance_probability(
                    current_distance, neighbor_distance, temperature
                )
                
                # Quyết định chấp nhận hay không
                if random.random() < acceptance_prob:
                    current_routes = neighbor_routes
                    current_distance = neighbor_distance
                    accepted_count += 1
                    
                    # Cập nhật best solution
                    if current_distance < best_distance:
                        best_routes = deepcopy(current_routes)
                        best_distance = current_distance
                        improvements_log.append({
                            'iteration': iterations,
                            'distance': best_distance,
                            'temperature': temperature,
                            'time': time.time() - start_time
                        })
                        print(f"  🔥 Temp={temperature:.2f}, Iter={iterations}: "
                              f"Cải thiện! Distance = {best_distance:.2f}")
                else:
                    rejected_count += 1
            
            # Giảm nhiệt độ (cooling)
            temperature *= cooling_rate
            
            # In tiến độ
            if iterations % (max_iterations_per_temp * 5) == 0:
                acceptance_rate = accepted_count / (accepted_count + rejected_count) if (accepted_count + rejected_count) > 0 else 0
                print(f"  🌡️ Temp={temperature:.2f}, Iter={iterations}, "
                      f"Current={current_distance:.2f}, Best={best_distance:.2f}, "
                      f"Accept rate={acceptance_rate:.2%}")
        
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
        
        # Tính acceptance rate tổng thể
        total_attempts = accepted_count + rejected_count
        acceptance_rate = accepted_count / total_attempts if total_attempts > 0 else 0
        
        # In kết quả
        print(f"\n{'='*80}")
        print(f"KẾT QUẢ GIẢI")
        print(f"{'='*80}")
        print(f"Trạng thái: Feasible (Simulated Annealing)")
        print(f"Thời gian giải: {solve_time:.2f} giây")
        print(f"Tổng số iterations: {iterations}")
        print(f"Số lần cải thiện: {len(improvements_log)}")
        print(f"Acceptance rate: {acceptance_rate:.2%}")
        print(f"Số xe sử dụng: {len(self.solution)}")
        print(f"Tổng quãng đường: {best_distance:.2f}")
        
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
            'status': 'Feasible (Simulated Annealing)',
            'objective': best_distance,
            'time': solve_time,
            'routes': self.solution,
            'iterations': iterations,
            'improvements': len(improvements_log),
            'improvements_log': improvements_log,
            'acceptance_rate': acceptance_rate
        }
    
    def visualize_solution_comprehensive(self, save=False):
        """
        Vẽ biểu đồ tổng hợp với nhiều sub-plots
        """
        if self.solution is None:
            print("❌ Chưa có solution để vẽ!")
            return
        
        # Tắt chế độ interactive
        plt.ioff()
        
        fig = plt.figure(figsize=(20, 12))
        gs = fig.add_gridspec(2, 3, hspace=0.3, wspace=0.3)
        
        # ============= 1. VẼ CÁC TUYẾN ĐƯỜNG =============
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
        
        # Vẽ các routes
        colors = plt.cm.tab20(np.linspace(0, 1, len(self.solution)))
        
        for idx, (route_id, info) in enumerate(self.solution.items()):
            route = [0] + info['route'] + [0]
            color = colors[idx]
            
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
                ax1.annotate('', xy=(x2, y2), xytext=(x1, y1),
                            arrowprops=dict(arrowstyle='->', color=color, lw=2, alpha=0.7))
            
            # Label
            if len(info['route']) > 0:
                mid_idx = len(info['route']) // 2
                mid_customer = info['route'][mid_idx]
                mid_x = self.customers.loc[mid_customer-1, 'XCOORD.']
                mid_y = self.customers.loc[mid_customer-1, 'YCOORD.']
                
                ax1.text(mid_x, mid_y + 5, f"Xe {route_id+1}", 
                        fontsize=10, fontweight='bold',
                        ha='center', bbox=dict(boxstyle='round,pad=0.4', facecolor=color, alpha=0.8))
        
        # Thêm số thứ tự
        for idx, row in self.customers.iterrows():
            ax1.annotate(str(idx + 1), (row['XCOORD.'], row['YCOORD.']),
                        fontsize=9, ha='center', va='center', fontweight='bold')
        
        ax1.set_xlabel('Tọa độ X', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Tọa độ Y', fontsize=12, fontweight='bold')
        ax1.set_title('① Các tuyến đường (Simulated Annealing)',
                     fontsize=14, fontweight='bold', pad=12)
        ax1.legend(fontsize=11, loc='best')
        ax1.grid(True, alpha=0.3, linestyle='--')
        
        # ============= 2. THỐNG KÊ XE =============
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
        
        colors_pie = plt.cm.Set3(np.linspace(0, 1, len(vehicles)))
        wedges, texts, autotexts = ax3.pie(num_customers_per_vehicle, 
                                            labels=[f'Xe {v+1}' for v in vehicles],
                                            autopct='%1.1f%%',
                                            startangle=90,
                                            colors=colors_pie,
                                            textprops={'fontsize': 10, 'fontweight': 'bold'})
        
        ax3.set_title('③ Phân bố số khách hàng', fontsize=13, fontweight='bold', pad=10)
        
        legend_labels = [f'Xe {v+1}: {num_customers_per_vehicle[i]} KH' 
                        for i, v in enumerate(vehicles)]
        ax3.legend(legend_labels, loc='upper left', bbox_to_anchor=(1, 1), fontsize=9)
        
        # ============= TIÊU ĐỀ CHÍNH =============
        total_distance = sum([info['distance'] for info in self.solution.values()])
        total_customers = sum(num_customers_per_vehicle)
        
        fig.suptitle(
            f'KẾT QUẢ SIMULATED ANNEALING - {self.dataset_name}\n'
            f'Số xe: {len(self.solution)} | Tổng quãng đường: {total_distance:.2f} | '
            f'Khách hàng phục vụ: {total_customers}/{self.n_customers}',
            fontsize=16, fontweight='bold', y=0.98
        )
        
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        
        if save:
            output_dir = Path(__file__).parent / 'result' / 'images'
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f'{self.dataset_name}_sa_solution.png'
            plt.savefig(str(output_path), dpi=300, bbox_inches='tight')
            print(f"✓ Đã lưu hình ảnh: {output_path}")
        
        plt.close(fig)
    
    def visualize_solution(self, save=False):
        """Wrapper để tương thích"""
        self.visualize_solution_comprehensive(save)
    
    def save_solution(self, solve_time=None, status=None, iterations=None, 
                     improvements=None, acceptance_rate=None):
        """Lưu solution ra file TXT"""
        if self.solution is None:
            print("❌ Chưa có solution để lưu!")
            return
        
        output_dir = Path(__file__).parent / 'result' / 'text'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f'{self.dataset_name}_sa_solution.txt'
        
        total_distance = sum([r['distance'] for r in self.solution.values()])
        total_load = sum([r['load'] for r in self.solution.values()])
        total_customers_served = sum([r['num_customers'] for r in self.solution.values()])
        
        with open(str(output_path), 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write(f"BÁO CÁO KẾT QUẢ SIMULATED ANNEALING\n")
            f.write(f"Metaheuristic - Temperature-based for VRPTW\n")
            f.write("="*80 + "\n\n")
            
            f.write(f"Dataset: {self.dataset_name}\n")
            f.write(f"Ngày giờ: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # THÔNG SỐ
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
                f.write(f"Số iterations: {iterations}\n")
            if improvements:
                f.write(f"Số lần cải thiện: {improvements}\n")
            if acceptance_rate is not None:
                f.write(f"Acceptance rate: {acceptance_rate:.2%}\n")
            f.write("\n")
            
            # PHƯƠNG PHÁP
            f.write("="*80 + "\n")
            f.write("PHƯƠNG PHÁP SIMULATED ANNEALING\n")
            f.write("="*80 + "\n")
            f.write("Đặc điểm:\n")
            f.write("  - Metaheuristic mô phỏng quá trình luyện kim\n")
            f.write("  - Chấp nhận worse solution với xác suất giảm dần theo nhiệt độ\n")
            f.write("  - Thoát khỏi local optimum hiệu quả\n")
            f.write("  - Công thức acceptance: exp(-(new_cost - current_cost) / T)\n\n")
            
            # KẾT QUẢ
            f.write("="*80 + "\n")
            f.write("KẾT QUẢ TỔNG HỢP\n")
            f.write("="*80 + "\n")
            f.write(f"Số xe sử dụng: {len(self.solution)}\n")
            f.write(f"Tổng quãng đường: {total_distance:.2f}\n")
            f.write(f"Quãng đường TB/xe: {total_distance/len(self.solution):.2f}\n")
            f.write(f"Tổng tải trọng: {total_load}\n")
            f.write(f"Tải trọng TB/xe: {total_load/len(self.solution):.2f}\n")
            f.write(f"Khách hàng phục vụ: {total_customers_served}/{self.n_customers}\n\n")
            
            # CHI TIẾT ROUTES
            f.write("="*80 + "\n")
            f.write("CHI TIẾT CÁC TUYẾN ĐƯỜNG\n")
            f.write("="*80 + "\n\n")
            
            for route_id, info in self.solution.items():
                f.write(f"{'─'*80}\n")
                f.write(f"XE {route_id + 1}\n")
                f.write(f"{'─'*80}\n")
                f.write(f"Tuyến đường: 0 (Kho) → {' → '.join(map(str, info['route']))} → 0\n")
                f.write(f"Số khách hàng: {info['num_customers']}\n")
                f.write(f"Tổng nhu cầu: {info['load']}/{self.vehicle_capacity}\n")
                f.write(f"Quãng đường: {info['distance']:.2f}\n\n")
            
            f.write("="*80 + "\n")
            f.write("KẾT THÚC BÁO CÁO\n")
            f.write("="*80 + "\n")
        
        print(f"✓ Đã lưu báo cáo: {output_path}")


def main():
    """Hàm chính"""
    
    current_dir = Path(__file__).parent
    code_dir = current_dir.parent.parent
    dataset_path = code_dir / "dataset" / "C1" / "C101.csv"
    
    print("="*80)
    print("SIMULATED ANNEALING FOR VRPTW")
    print("="*80)
    print("✓ Metaheuristic mô phỏng quá trình luyện kim")
    print("✓ Chấp nhận worse solution để thoát local optimum")
    print("✓ Giải toàn bộ dataset (100+ khách hàng)")
    print("✓ Chất lượng rất tốt, balance giữa exploration và exploitation")
    print("="*80)
    
    solver = SimulatedAnnealingVRPTWSolver(
        dataset_path=str(dataset_path),
        vehicle_capacity=200,
        max_vehicles=25
    )
    
    # Lấy tham số tự động
    hyperparams = solver.get_recommended_hyperparameters()
    
    result = solver.solve(**hyperparams)
    
    if result:
        print("\n" + "="*80)
        print("TẠO TRỰC QUAN HÓA VÀ BÁO CÁO")
        print("="*80)
        solver.visualize_solution(save=True)
        solver.save_solution(
            solve_time=result['time'],
            status=result['status'],
            iterations=result['iterations'],
            improvements=result['improvements'],
            acceptance_rate=result.get('acceptance_rate')
        )
        print("✓ Hoàn thành!")


if __name__ == "__main__":
    main()
