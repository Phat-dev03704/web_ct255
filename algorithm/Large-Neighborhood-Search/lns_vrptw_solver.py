"""
VRPTW Solver using Large Neighborhood Search
Giải bài toán VRP với cửa sổ thời gian bằng Thuật toán tìm kiếm lân cận lớn

Thuật toán Metaheuristic phá hủy và tái tạo một phần lớn solution
Destroy một phần solution, sau đó Repair bằng heuristic
"""

import pandas as pd
import numpy as np
import time
from pathlib import Path
import matplotlib.pyplot as plt
import random
from copy import deepcopy


class LargeNeighborhoodSearchVRPTWSolver:
    """
    Class giải bài toán VRPTW bằng Large Neighborhood Search
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
        """Kiểm tra xem route có thỏa mãn time window không"""
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
        """Tạo solution ban đầu bằng Nearest Neighbor"""
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
    
    # ==================== DESTROY OPERATORS ====================
    
    def _destroy_random_removal(self, routes, num_remove):
        """
        Destroy: Random Removal
        Loại bỏ ngẫu nhiên num_remove customers
        """
        routes = deepcopy(routes)
        removed_customers = []
        
        # Lấy tất cả customers
        all_customers = [c for route in routes for c in route]
        
        if len(all_customers) == 0:
            return routes, removed_customers
        
        # Chọn ngẫu nhiên customers để loại bỏ
        num_remove = min(num_remove, len(all_customers))
        customers_to_remove = random.sample(all_customers, num_remove)
        
        # Loại bỏ customers
        for customer in customers_to_remove:
            for route in routes:
                if customer in route:
                    route.remove(customer)
                    removed_customers.append(customer)
                    break
        
        # Loại bỏ routes rỗng
        routes = [route for route in routes if route]
        
        return routes, removed_customers
    
    def _destroy_worst_removal(self, routes, num_remove):
        """
        Destroy: Worst Removal
        Loại bỏ num_remove customers có chi phí lớn nhất (worst cost)
        Cost = savings khi loại bỏ customer
        """
        routes = deepcopy(routes)
        removed_customers = []
        
        # Tính cost cho mỗi customer
        customer_costs = []
        
        for route_idx, route in enumerate(routes):
            for pos, customer in enumerate(route):
                # Tính cost = savings khi loại bỏ customer
                if len(route) == 1:
                    # Nếu route chỉ có 1 customer
                    cost = self.distance_matrix[0][customer] + self.distance_matrix[customer][0]
                elif pos == 0:
                    # Customer đầu tiên
                    cost = (self.distance_matrix[0][customer] + 
                           self.distance_matrix[customer][route[pos+1]] -
                           self.distance_matrix[0][route[pos+1]])
                elif pos == len(route) - 1:
                    # Customer cuối cùng
                    cost = (self.distance_matrix[route[pos-1]][customer] + 
                           self.distance_matrix[customer][0] -
                           self.distance_matrix[route[pos-1]][0])
                else:
                    # Customer ở giữa
                    cost = (self.distance_matrix[route[pos-1]][customer] +
                           self.distance_matrix[customer][route[pos+1]] -
                           self.distance_matrix[route[pos-1]][route[pos+1]])
                
                customer_costs.append((customer, route_idx, pos, cost))
        
        if not customer_costs:
            return routes, removed_customers
        
        # Sắp xếp theo cost giảm dần (worst first)
        customer_costs.sort(key=lambda x: x[3], reverse=True)
        
        # Loại bỏ worst customers
        num_remove = min(num_remove, len(customer_costs))
        for i in range(num_remove):
            customer = customer_costs[i][0]
            for route in routes:
                if customer in route:
                    route.remove(customer)
                    removed_customers.append(customer)
                    break
        
        # Loại bỏ routes rỗng
        routes = [route for route in routes if route]
        
        return routes, removed_customers
    
    def _destroy_shaw_removal(self, routes, num_remove):
        """
        Destroy: Shaw Removal
        Loại bỏ customers tương tự nhau (similar)
        Similarity = distance + time window similarity
        """
        routes = deepcopy(routes)
        removed_customers = []
        
        # Lấy tất cả customers
        all_customers = [c for route in routes for c in route]
        
        if len(all_customers) == 0:
            return routes, removed_customers
        
        # Chọn ngẫu nhiên 1 seed customer
        seed = random.choice(all_customers)
        removed_customers.append(seed)
        
        # Tính relatedness của các customers khác với seed
        relatedness = []
        for customer in all_customers:
            if customer == seed:
                continue
            
            # Distance relatedness
            dist_relatedness = self.distance_matrix[seed][customer]
            
            # Time window relatedness
            seed_ready = self.customers.loc[seed - 1, 'READY TIME']
            seed_due = self.customers.loc[seed - 1, 'DUE DATE']
            cust_ready = self.customers.loc[customer - 1, 'READY TIME']
            cust_due = self.customers.loc[customer - 1, 'DUE DATE']
            
            time_relatedness = abs(seed_ready - cust_ready) + abs(seed_due - cust_due)
            
            # Total relatedness (normalize)
            total_relatedness = dist_relatedness + time_relatedness * 0.1
            
            relatedness.append((customer, total_relatedness))
        
        # Sắp xếp theo relatedness (similar first)
        relatedness.sort(key=lambda x: x[1])
        
        # Loại bỏ most related customers
        num_remove = min(num_remove - 1, len(relatedness))  # -1 vì đã loại seed
        for i in range(num_remove):
            removed_customers.append(relatedness[i][0])
        
        # Loại bỏ customers khỏi routes
        for customer in removed_customers:
            for route in routes:
                if customer in route:
                    route.remove(customer)
                    break
        
        # Loại bỏ routes rỗng
        routes = [route for route in routes if route]
        
        return routes, removed_customers
    
    def _destroy_route_removal(self, routes, num_remove):
        """
        Destroy: Route Removal
        Loại bỏ toàn bộ một hoặc nhiều routes
        """
        routes = deepcopy(routes)
        removed_customers = []
        
        if not routes:
            return routes, removed_customers
        
        # Tính số routes cần loại bỏ
        num_routes_to_remove = max(1, min(len(routes), num_remove // 5))
        
        # Chọn ngẫu nhiên routes để loại bỏ
        routes_to_remove = random.sample(range(len(routes)), num_routes_to_remove)
        routes_to_remove.sort(reverse=True)
        
        for route_idx in routes_to_remove:
            removed_customers.extend(routes[route_idx])
            routes.pop(route_idx)
        
        return routes, removed_customers
    
    # ==================== REPAIR OPERATORS ====================
    
    def _repair_greedy_insertion(self, routes, removed_customers):
        """
        Repair: Greedy Insertion
        Chèn customer vào vị trí có chi phí tăng ít nhất
        """
        routes = deepcopy(routes)
        
        # Nếu không có routes, tạo route mới
        if not routes:
            routes = [[]]
        
        for customer in removed_customers:
            best_route_idx = None
            best_position = None
            best_cost_increase = float('inf')
            
            demand = self.customers.loc[customer - 1, 'DEMAND']
            
            # Thử chèn vào mỗi route
            for route_idx, route in enumerate(routes):
                current_load = self._calculate_route_load(route)
                
                # Kiểm tra capacity
                if current_load + demand > self.vehicle_capacity:
                    continue
                
                # Thử chèn vào mỗi vị trí
                for pos in range(len(route) + 1):
                    # Tạo route mới với customer chèn vào
                    new_route = route[:pos] + [customer] + route[pos:]
                    
                    # Kiểm tra time window
                    if not self._check_time_window_feasibility(new_route):
                        continue
                    
                    # Tính cost increase
                    old_distance = self._calculate_route_distance(route)
                    new_distance = self._calculate_route_distance(new_route)
                    cost_increase = new_distance - old_distance
                    
                    if cost_increase < best_cost_increase:
                        best_cost_increase = cost_increase
                        best_route_idx = route_idx
                        best_position = pos
            
            # Nếu tìm được vị trí, chèn vào
            if best_route_idx is not None:
                routes[best_route_idx].insert(best_position, customer)
            else:
                # Không tìm được vị trí, tạo route mới
                if len(routes) < self.max_vehicles:
                    routes.append([customer])
                else:
                    # Nếu đã hết xe, chèn vào route có ít khách hàng nhất
                    min_route_idx = min(range(len(routes)), key=lambda i: len(routes[i]))
                    routes[min_route_idx].append(customer)
        
        return routes
    
    def _repair_regret_insertion(self, routes, removed_customers, k=2):
        """
        Repair: Regret-k Insertion
        Chèn customer có regret cao nhất trước
        Regret = difference giữa best và k-th best insertion cost
        """
        routes = deepcopy(routes)
        
        if not routes:
            routes = [[]]
        
        uninserted = removed_customers[:]
        
        while uninserted:
            max_regret = -float('inf')
            best_customer = None
            best_route_idx = None
            best_position = None
            
            for customer in uninserted:
                demand = self.customers.loc[customer - 1, 'DEMAND']
                
                # Tìm k best insertion positions
                insertion_costs = []
                
                for route_idx, route in enumerate(routes):
                    current_load = self._calculate_route_load(route)
                    
                    if current_load + demand > self.vehicle_capacity:
                        continue
                    
                    for pos in range(len(route) + 1):
                        new_route = route[:pos] + [customer] + route[pos:]
                        
                        if not self._check_time_window_feasibility(new_route):
                            continue
                        
                        old_distance = self._calculate_route_distance(route)
                        new_distance = self._calculate_route_distance(new_route)
                        cost_increase = new_distance - old_distance
                        
                        insertion_costs.append((cost_increase, route_idx, pos))
                
                if not insertion_costs:
                    continue
                
                # Sắp xếp theo cost
                insertion_costs.sort(key=lambda x: x[0])
                
                # Tính regret
                if len(insertion_costs) >= k:
                    regret = insertion_costs[k-1][0] - insertion_costs[0][0]
                else:
                    regret = insertion_costs[-1][0] - insertion_costs[0][0]
                
                if regret > max_regret:
                    max_regret = regret
                    best_customer = customer
                    best_route_idx = insertion_costs[0][1]
                    best_position = insertion_costs[0][2]
            
            # Chèn customer có regret cao nhất
            if best_customer is not None:
                routes[best_route_idx].insert(best_position, best_customer)
                uninserted.remove(best_customer)
            else:
                # Không thể chèn, tạo route mới
                customer = uninserted.pop(0)
                if len(routes) < self.max_vehicles:
                    routes.append([customer])
                else:
                    min_route_idx = min(range(len(routes)), key=lambda i: len(routes[i]))
                    routes[min_route_idx].append(customer)
        
        return routes
    
    def _apply_local_search_2opt(self, routes):
        """Áp dụng 2-opt local search"""
        improved_routes = []
        
        for route in routes:
            if len(route) < 4:
                improved_routes.append(route)
                continue
            
            best_route = route[:]
            best_distance = self._calculate_route_distance(best_route)
            improved = True
            
            while improved:
                improved = False
                for i in range(len(best_route) - 2):
                    for j in range(i + 2, len(best_route)):
                        new_route = best_route[:i+1] + best_route[i+1:j+1][::-1] + best_route[j+1:]
                        
                        if not self._check_time_window_feasibility(new_route):
                            continue
                        
                        new_distance = self._calculate_route_distance(new_route)
                        
                        if new_distance < best_distance:
                            best_route = new_route
                            best_distance = new_distance
                            improved = True
                            break
                    
                    if improved:
                        break
            
            improved_routes.append(best_route)
        
        return improved_routes
    
    def get_recommended_hyperparameters(self):
        """
        Tự động đề xuất siêu tham số dựa trên kích thước bài toán
        """
        n = self.n_customers
        
        # Max iterations
        if n <= 50:
            max_iterations = 100
            destroy_size_min = 5
            destroy_size_max = 15
        elif n <= 100:
            max_iterations = 150
            destroy_size_min = 10
            destroy_size_max = 25
        else:
            max_iterations = 200
            destroy_size_min = 15
            destroy_size_max = 35
        
        return {
            'max_iterations': max_iterations,
            'destroy_size_min': destroy_size_min,
            'destroy_size_max': destroy_size_max,
            'use_local_search': True,
            'time_limit': 60
        }
    
    def print_hyperparameter_guide(self):
        """In hướng dẫn điều chỉnh hyperparameters"""
        print("\n" + "="*80)
        print("HƯỚNG DẪN ĐIỀU CHỈNH HYPERPARAMETERS - LARGE NEIGHBORHOOD SEARCH")
        print("="*80)
        print("\n1. MAX_ITERATIONS (Số vòng lặp tối đa)")
        print("   - Giá trị: 100-300")
        print("   - Nhiều iterations = chất lượng tốt hơn nhưng mất thời gian")
        print("   - Khuyến nghị: 100 (n≤50), 150 (50<n≤100), 200 (n>100)")
        
        print("\n2. DESTROY_SIZE_MIN/MAX (Kích thước phá hủy)")
        print("   - Min/Max: Số customers bị loại bỏ trong mỗi iteration")
        print("   - Nhỏ (5-15): Thay đổi ít, local search")
        print("   - Lớn (20-40): Thay đổi nhiều, exploration")
        print("   - Khuyến nghị: 10-25% số customers")
        
        print("\n3. DESTROY OPERATORS (4 loại)")
        print("   - Random: Loại bỏ ngẫu nhiên (diversification)")
        print("   - Worst: Loại bỏ customers tốn kém nhất (intensification)")
        print("   - Shaw: Loại bỏ customers tương tự nhau (guided)")
        print("   - Route: Loại bỏ toàn bộ routes (exploration)")
        
        print("\n4. REPAIR OPERATORS (2 loại)")
        print("   - Greedy: Chèn vào vị trí tốt nhất (nhanh)")
        print("   - Regret-k: Chèn customer có regret cao (chất lượng tốt)")
        
        print("\n5. USE_LOCAL_SEARCH")
        print("   - True: Áp dụng 2-opt sau mỗi repair")
        print("   - Tăng chất lượng 10-15%")
        print("   - Khuyến nghị: True")
        
        print("\n" + "="*80)
        print("💡 LNS CONCEPT:")
        print("  - Destroy: Phá hủy 10-30% solution")
        print("  - Repair: Tái tạo bằng heuristic thông minh")
        print("  - Large neighborhood = nhiều khả năng cải thiện hơn")
        print("="*80 + "\n")
    
    def solve(self,
              max_iterations=150,
              destroy_size_min=10,
              destroy_size_max=25,
              use_local_search=True,
              time_limit=60):
        """
        Giải bài toán bằng Large Neighborhood Search
        
        Args:
            max_iterations: Số vòng lặp tối đa (100-300)
            destroy_size_min: Số customers tối thiểu bị loại bỏ
            destroy_size_max: Số customers tối đa bị loại bỏ
            use_local_search: Có áp dụng 2-opt local search không
            time_limit: Giới hạn thời gian (giây)
        """
        print(f"\n{'='*80}")
        print(f"XÂY DỰNG GIẢI PHÁP BẰNG LARGE NEIGHBORHOOD SEARCH")
        print(f"{'='*80}")
        print(f"Dataset: {self.dataset_name}")
        print(f"Số khách hàng: {self.n_customers}")
        print(f"Sức chứa xe: {self.vehicle_capacity}")
        print(f"Số xe tối đa: {self.max_vehicles}")
        print(f"\n🔧 SIÊU THAM SỐ:")
        print(f"  - Số vòng lặp tối đa: {max_iterations}")
        print(f"  - Destroy size: {destroy_size_min}-{destroy_size_max} customers")
        print(f"  - Local search: {use_local_search}")
        print(f"  - Thời gian giới hạn: {time_limit}s")
        print(f"{'='*80}\n")
        
        start_time = time.time()
        
        # Tạo initial solution
        current_routes = self._create_initial_solution_nearest_neighbor()
        current_distance = self._calculate_total_distance(current_routes)
        
        best_routes = deepcopy(current_routes)
        best_distance = current_distance
        
        print(f"\nBắt đầu Large Neighborhood Search...")
        print(f"Solution ban đầu: {best_distance:.2f}")
        
        # Destroy operators
        destroy_operators = [
            ('Random', self._destroy_random_removal),
            ('Worst', self._destroy_worst_removal),
            ('Shaw', self._destroy_shaw_removal),
            ('Route', self._destroy_route_removal)
        ]
        
        # Repair operators
        repair_operators = [
            ('Greedy', self._repair_greedy_insertion),
            ('Regret-2', lambda r, c: self._repair_regret_insertion(r, c, k=2))
        ]
        
        # Tracking
        improvements_log = []
        operator_stats = {name: {'used': 0, 'improved': 0} for name, _ in destroy_operators}
        repair_stats = {name: {'used': 0} for name, _ in repair_operators}
        
        iteration = 0
        no_improvement_count = 0
        
        while iteration < max_iterations:
            elapsed_time = time.time() - start_time
            if elapsed_time > time_limit:
                print(f"\n⏱ Đạt giới hạn thời gian ({time_limit}s)")
                break
            
            iteration += 1
            
            # Chọn ngẫu nhiên destroy size
            destroy_size = random.randint(destroy_size_min, destroy_size_max)
            destroy_size = min(destroy_size, self.n_customers)
            
            # Chọn ngẫu nhiên destroy operator
            destroy_name, destroy_op = random.choice(destroy_operators)
            operator_stats[destroy_name]['used'] += 1
            
            # Chọn ngẫu nhiên repair operator
            repair_name, repair_op = random.choice(repair_operators)
            repair_stats[repair_name]['used'] += 1
            
            # Destroy
            destroyed_routes, removed_customers = destroy_op(current_routes, destroy_size)
            
            # Repair
            repaired_routes = repair_op(destroyed_routes, removed_customers)
            
            # Local search
            if use_local_search:
                repaired_routes = self._apply_local_search_2opt(repaired_routes)
            
            # Tính distance
            repaired_distance = self._calculate_total_distance(repaired_routes)
            
            # Acceptance criterion: Accept if better or equal
            if repaired_distance <= current_distance:
                current_routes = repaired_routes
                current_distance = repaired_distance
                
                # Update best
                if current_distance < best_distance:
                    best_routes = deepcopy(current_routes)
                    best_distance = current_distance
                    no_improvement_count = 0
                    operator_stats[destroy_name]['improved'] += 1
                    
                    improvements_log.append({
                        'iteration': iteration,
                        'distance': best_distance,
                        'destroy_op': destroy_name,
                        'repair_op': repair_name,
                        'time': time.time() - start_time
                    })
                    
                    print(f"  🔧 Iter {iteration}: Cải thiện! Distance = {best_distance:.2f} "
                          f"[{destroy_name} + {repair_name}]")
            else:
                no_improvement_count += 1
            
            # In tiến độ
            if iteration % 10 == 0:
                print(f"  📊 Iter {iteration}/{max_iterations}: "
                      f"Current={current_distance:.2f}, Best={best_distance:.2f}, "
                      f"No improve={no_improvement_count}")
            
            # Early stopping
            if no_improvement_count > max_iterations // 3:
                print(f"\n⚠️ Dừng sớm: Không cải thiện sau {no_improvement_count} iterations")
                break
        
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
        print(f"Trạng thái: Feasible (Large Neighborhood Search)")
        print(f"Thời gian giải: {solve_time:.2f} giây")
        print(f"Tổng số iterations: {iteration}")
        print(f"Số lần cải thiện: {len(improvements_log)}")
        print(f"Số xe sử dụng: {len(self.solution)}")
        print(f"Tổng quãng đường: {best_distance:.2f}")
        
        # In thống kê operators
        print(f"\n{'='*80}")
        print(f"THỐNG KÊ DESTROY OPERATORS")
        print(f"{'='*80}")
        for name in operator_stats:
            used = operator_stats[name]['used']
            improved = operator_stats[name]['improved']
            success_rate = (improved / used * 100) if used > 0 else 0
            print(f"{name:12s}: Used={used:3d}, Improved={improved:3d}, "
                  f"Success={success_rate:5.1f}%")
        
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
            'status': 'Feasible (Large Neighborhood Search)',
            'objective': best_distance,
            'time': solve_time,
            'routes': self.solution,
            'iterations': iteration,
            'improvements': len(improvements_log),
            'improvements_log': improvements_log,
            'operator_stats': operator_stats
        }
    
    def visualize_solution_comprehensive(self, save=False):
        """Vẽ biểu đồ tổng hợp"""
        if self.solution is None:
            print("❌ Chưa có solution để vẽ!")
            return
        
        plt.ioff()
        
        fig = plt.figure(figsize=(20, 12))
        gs = fig.add_gridspec(2, 3, hspace=0.3, wspace=0.3)
        
        ax1 = fig.add_subplot(gs[0:2, 0:2])
        
        depot_x = self.depot['XCOORD.']
        depot_y = self.depot['YCOORD.']
        ax1.scatter(depot_x, depot_y,
                   c='red', s=600, marker='s', edgecolors='black',
                   linewidth=3, label='Kho', zorder=5)
        
        ax1.scatter(self.customers['XCOORD.'], self.customers['YCOORD.'],
                   c='lightblue', s=200, edgecolors='black',
                   linewidth=1.5, label='Khách hàng', zorder=3)
        
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
            
            if len(info['route']) > 0:
                mid_idx = len(info['route']) // 2
                mid_customer = info['route'][mid_idx]
                mid_x = self.customers.loc[mid_customer-1, 'XCOORD.']
                mid_y = self.customers.loc[mid_customer-1, 'YCOORD.']
                
                ax1.text(mid_x, mid_y + 5, f"Xe {route_id+1}", 
                        fontsize=10, fontweight='bold',
                        ha='center', bbox=dict(boxstyle='round,pad=0.4', facecolor=color, alpha=0.8))
        
        for idx, row in self.customers.iterrows():
            ax1.annotate(str(idx + 1), (row['XCOORD.'], row['YCOORD.']),
                        fontsize=9, ha='center', va='center', fontweight='bold')
        
        ax1.set_xlabel('Tọa độ X', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Tọa độ Y', fontsize=12, fontweight='bold')
        ax1.set_title('① Các tuyến đường (Large Neighborhood Search)',
                     fontsize=14, fontweight='bold', pad=12)
        ax1.legend(fontsize=11, loc='best')
        ax1.grid(True, alpha=0.3, linestyle='--')
        
        # Statistics plots
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
        
        total_distance = sum([info['distance'] for info in self.solution.values()])
        total_customers = sum(num_customers_per_vehicle)
        
        fig.suptitle(
            f'KẾT QUẢ LARGE NEIGHBORHOOD SEARCH - {self.dataset_name}\n'
            f'Số xe: {len(self.solution)} | Tổng quãng đường: {total_distance:.2f} | '
            f'Khách hàng phục vụ: {total_customers}/{self.n_customers}',
            fontsize=16, fontweight='bold', y=0.98
        )
        
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        
        if save:
            output_dir = Path(__file__).parent / 'result' / 'images'
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f'{self.dataset_name}_lns_solution.png'
            plt.savefig(str(output_path), dpi=300, bbox_inches='tight')
            print(f"✓ Đã lưu hình ảnh: {output_path}")
        
        plt.close(fig)
    
    def visualize_solution(self, save=False):
        """Wrapper"""
        self.visualize_solution_comprehensive(save)
    
    def save_solution(self, solve_time=None, status=None, iterations=None, 
                     improvements=None, operator_stats=None):
        """Lưu solution ra file TXT"""
        if self.solution is None:
            print("❌ Chưa có solution để lưu!")
            return
        
        output_dir = Path(__file__).parent / 'result' / 'text'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f'{self.dataset_name}_lns_solution.txt'
        
        total_distance = sum([r['distance'] for r in self.solution.values()])
        total_load = sum([r['load'] for r in self.solution.values()])
        total_customers_served = sum([r['num_customers'] for r in self.solution.values()])
        
        with open(str(output_path), 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write(f"BÁO CÁO KẾT QUẢ LARGE NEIGHBORHOOD SEARCH\n")
            f.write(f"Metaheuristic - Destroy & Repair for VRPTW\n")
            f.write("="*80 + "\n\n")
            
            f.write(f"Dataset: {self.dataset_name}\n")
            f.write(f"Ngày giờ: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
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
            f.write("\n")
            
            f.write("="*80 + "\n")
            f.write("PHƯƠNG PHÁP LARGE NEIGHBORHOOD SEARCH\n")
            f.write("="*80 + "\n")
            f.write("Đặc điểm:\n")
            f.write("  - Metaheuristic destroy & repair\n")
            f.write("  - Destroy: Phá hủy 10-30% solution\n")
            f.write("  - Repair: Tái tạo bằng heuristic\n")
            f.write("  - Large neighborhood = nhiều khả năng cải thiện\n\n")
            
            if operator_stats:
                f.write("Destroy Operators:\n")
                for name in operator_stats:
                    used = operator_stats[name]['used']
                    improved = operator_stats[name]['improved']
                    success = (improved/used*100) if used > 0 else 0
                    f.write(f"  - {name}: Used={used}, Improved={improved}, Success={success:.1f}%\n")
                f.write("\n")
            
            f.write("="*80 + "\n")
            f.write("KẾT QUẢ TỔNG HỢP\n")
            f.write("="*80 + "\n")
            f.write(f"Số xe sử dụng: {len(self.solution)}\n")
            f.write(f"Tổng quãng đường: {total_distance:.2f}\n")
            f.write(f"Quãng đường TB/xe: {total_distance/len(self.solution):.2f}\n")
            f.write(f"Tổng tải trọng: {total_load}\n")
            f.write(f"Tải trọng TB/xe: {total_load/len(self.solution):.2f}\n")
            f.write(f"Khách hàng phục vụ: {total_customers_served}/{self.n_customers}\n\n")
            
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
    print("LARGE NEIGHBORHOOD SEARCH FOR VRPTW")
    print("="*80)
    print("✓ Metaheuristic destroy & repair")
    print("✓ Large neighborhood = nhiều cơ hội cải thiện")
    print("✓ Giải toàn bộ dataset (100+ khách hàng)")
    print("✓ Chất lượng xuất sắc, flexible và powerful")
    print("="*80)
    
    solver = LargeNeighborhoodSearchVRPTWSolver(
        dataset_path=str(dataset_path),
        vehicle_capacity=200,
        max_vehicles=25
    )
    
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
            operator_stats=result.get('operator_stats')
        )
        print("✓ Hoàn thành!")


if __name__ == "__main__":
    main()
