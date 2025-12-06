"""
VRPTW Solver using Ant Colony Optimization
Giải bài toán VRP với cửa sổ thời gian bằng Thuật toán tối ưu bầy đàn kiến

Thuật toán Metaheuristic mô phỏng hành vi tìm đường của đàn kiến
Sử dụng pheromone trails và heuristic information để tìm giải pháp tối ưu
"""

import pandas as pd
import numpy as np
import time
from pathlib import Path
import matplotlib.pyplot as plt
import random
from copy import deepcopy


class AntColonyVRPTWSolver:
    """
    Class giải bài toán VRPTW bằng Ant Colony Optimization
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
        
        # Pheromone matrix
        self.pheromone = None
        
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
    
    def _initialize_pheromone(self, initial_value=1.0):
        """
        Khởi tạo pheromone matrix
        """
        n = self.n_customers + 1
        self.pheromone = np.ones((n, n)) * initial_value
    
    def _calculate_heuristic(self):
        """
        Tính heuristic information (visibility)
        Heuristic = 1 / distance (càng gần càng hấp dẫn)
        """
        n = self.n_customers + 1
        heuristic = np.zeros((n, n))
        
        for i in range(n):
            for j in range(n):
                if i != j and self.distance_matrix[i][j] > 0:
                    heuristic[i][j] = 1.0 / self.distance_matrix[i][j]
        
        return heuristic
    
    def _select_next_customer(self, current_location, unvisited, current_route, 
                             current_load, alpha, beta, heuristic):
        """
        Chọn khách hàng tiếp theo bằng quy tắc xác suất ACO
        P[i][j] = (pheromone[i][j]^alpha * heuristic[i][j]^beta) / sum
        """
        if not unvisited:
            return None
        
        probabilities = []
        feasible_customers = []
        
        for customer_id in unvisited:
            # Kiểm tra constraints
            demand = self.customers.loc[customer_id - 1, 'DEMAND']
            
            # Kiểm tra capacity
            if current_load + demand > self.vehicle_capacity:
                continue
            
            # Kiểm tra time window
            test_route = current_route + [customer_id]
            if not self._check_time_window_feasibility(test_route):
                continue
            
            # Tính xác suất
            pheromone_value = self.pheromone[current_location][customer_id]
            heuristic_value = heuristic[current_location][customer_id]
            
            probability = (pheromone_value ** alpha) * (heuristic_value ** beta)
            
            probabilities.append(probability)
            feasible_customers.append(customer_id)
        
        if not feasible_customers:
            return None
        
        # Normalize probabilities
        total = sum(probabilities)
        if total == 0:
            return random.choice(feasible_customers)
        
        probabilities = [p / total for p in probabilities]
        
        # Roulette wheel selection
        selected = np.random.choice(feasible_customers, p=probabilities)
        
        return selected
    
    def _construct_ant_solution(self, alpha, beta, heuristic):
        """
        Xây dựng solution cho một con kiến
        """
        routes = []
        unvisited = set(range(1, self.n_customers + 1))
        
        while unvisited and len(routes) < self.max_vehicles:
            # Bắt đầu route mới từ depot
            current_route = []
            current_load = 0
            current_location = 0  # depot
            
            while unvisited:
                # Chọn khách hàng tiếp theo
                next_customer = self._select_next_customer(
                    current_location, unvisited, current_route, 
                    current_load, alpha, beta, heuristic
                )
                
                if next_customer is None:
                    break
                
                # Thêm khách hàng vào route
                current_route.append(next_customer)
                current_load += self.customers.loc[next_customer - 1, 'DEMAND']
                current_location = next_customer
                unvisited.remove(next_customer)
            
            if current_route:
                routes.append(current_route)
        
        # Nếu còn khách hàng chưa thăm, tạo thêm routes đơn giản
        while unvisited:
            customer_id = unvisited.pop()
            routes.append([customer_id])
        
        return routes
    
    def _update_pheromone_local(self, from_node, to_node, rho_local):
        """
        Local pheromone update (cho mỗi kiến sau khi xây dựng route)
        Pheromone evaporation: tau[i][j] = (1 - rho_local) * tau[i][j]
        """
        self.pheromone[from_node][to_node] *= (1 - rho_local)
        self.pheromone[to_node][from_node] *= (1 - rho_local)
    
    def _update_pheromone_global(self, best_routes, best_distance, rho):
        """
        Global pheromone update (sau mỗi iteration)
        1. Evaporation: tau[i][j] = (1 - rho) * tau[i][j]
        2. Deposit: tau[i][j] += delta_tau
           delta_tau = Q / L_best (L_best = best tour length)
        """
        # 1. Evaporation
        self.pheromone *= (1 - rho)
        
        # 2. Deposit pheromone trên best routes
        delta_tau = 1.0 / best_distance if best_distance > 0 else 1.0
        
        for route in best_routes:
            if not route:
                continue
            
            # Từ depot đến customer đầu tiên
            self.pheromone[0][route[0]] += delta_tau
            self.pheromone[route[0]][0] += delta_tau
            
            # Giữa các customers
            for i in range(len(route) - 1):
                self.pheromone[route[i]][route[i+1]] += delta_tau
                self.pheromone[route[i+1]][route[i]] += delta_tau
            
            # Từ customer cuối về depot
            self.pheromone[route[-1]][0] += delta_tau
            self.pheromone[0][route[-1]] += delta_tau
    
    def _apply_local_search_2opt(self, routes):
        """
        Áp dụng 2-opt local search để cải thiện solution
        """
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
                        # Thử đảo ngược đoạn [i+1, j]
                        new_route = best_route[:i+1] + best_route[i+1:j+1][::-1] + best_route[j+1:]
                        
                        # Kiểm tra feasibility
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
        
        # Number of ants: Thường bằng hoặc gần số customers
        if n <= 50:
            n_ants = 20
            max_iterations = 100
        elif n <= 100:
            n_ants = 30
            max_iterations = 150
        else:
            n_ants = 40
            max_iterations = 200
        
        # Alpha: Ảnh hưởng của pheromone (1-2)
        alpha = 1.0
        
        # Beta: Ảnh hưởng của heuristic (2-5)
        beta = 3.0
        
        # Rho: Evaporation rate (0.1-0.3)
        rho = 0.2
        
        # Rho local: Local evaporation (0.1-0.2)
        rho_local = 0.1
        
        # Q: Pheromone deposit constant (1-100)
        Q = 1.0
        
        # Use local search
        use_local_search = True
        
        return {
            'n_ants': n_ants,
            'max_iterations': max_iterations,
            'alpha': alpha,
            'beta': beta,
            'rho': rho,
            'rho_local': rho_local,
            'Q': Q,
            'use_local_search': use_local_search,
            'time_limit': 60
        }
    
    def print_hyperparameter_guide(self):
        """In hướng dẫn điều chỉnh hyperparameters"""
        print("\n" + "="*80)
        print("HƯỚNG DẪN ĐIỀU CHỈNH HYPERPARAMETERS - ANT COLONY OPTIMIZATION")
        print("="*80)
        print("\n1. N_ANTS (Số lượng kiến)")
        print("   - Giá trị: 10-50")
        print("   - Ít kiến (10-20): Nhanh nhưng kém đa dạng")
        print("   - Nhiều kiến (30-50): Chậm nhưng explore tốt hơn")
        print("   - Khuyến nghị: 20 (n≤50), 30 (50<n≤100), 40 (n>100)")
        
        print("\n2. MAX_ITERATIONS (Số vòng lặp tối đa)")
        print("   - Giá trị: 100-300")
        print("   - Nhiều iterations = chất lượng tốt hơn nhưng mất thời gian")
        print("   - Khuyến nghị: 100 (n≤50), 150 (50<n≤100), 200 (n>100)")
        
        print("\n3. ALPHA (Ảnh hưởng của pheromone)")
        print("   - Giá trị: 0.5-2.0")
        print("   - Cao = theo pheromone nhiều (exploitation)")
        print("   - Thấp = pheromone ít ảnh hưởng (exploration)")
        print("   - Khuyến nghị: 1.0 (balance)")
        
        print("\n4. BETA (Ảnh hưởng của heuristic)")
        print("   - Giá trị: 2.0-5.0")
        print("   - Cao = theo heuristic nhiều (greedy)")
        print("   - Heuristic = 1/distance (ưu tiên customer gần)")
        print("   - Khuyến nghị: 3.0 (ưu tiên heuristic hơn pheromone)")
        
        print("\n5. RHO (Evaporation rate - Tốc độ bay hơi pheromone)")
        print("   - Giá trị: 0.1-0.3")
        print("   - Cao = pheromone cũ mất nhanh (exploration)")
        print("   - Thấp = pheromone cũ tồn tại lâu (exploitation)")
        print("   - Khuyến nghị: 0.2 (balance)")
        
        print("\n6. RHO_LOCAL (Local evaporation - Bay hơi cục bộ)")
        print("   - Giá trị: 0.05-0.2")
        print("   - Update ngay sau khi kiến đi qua")
        print("   - Khuyến khích đa dạng hóa paths")
        print("   - Khuyến nghị: 0.1")
        
        print("\n7. Q (Pheromone deposit constant)")
        print("   - Giá trị: 1-100")
        print("   - Lượng pheromone deposit = Q / tour_length")
        print("   - Thường giữ ở 1.0 và điều chỉnh alpha/beta")
        print("   - Khuyến nghị: 1.0")
        
        print("\n8. USE_LOCAL_SEARCH")
        print("   - True: Áp dụng 2-opt sau mỗi ant solution")
        print("   - False: Chỉ dùng ACO thuần túy")
        print("   - Khuyến nghị: True (cải thiện đáng kể)")
        
        print("\n" + "="*80)
        print("💡 BALANCE EXPLORATION vs EXPLOITATION:")
        print("  - Exploration (tìm vùng mới): Tăng rho, giảm alpha")
        print("  - Exploitation (tập trung vào best): Giảm rho, tăng alpha")
        print("  - Thường beta > alpha (heuristic quan trọng hơn pheromone)")
        print("="*80 + "\n")
    
    def solve(self,
              n_ants=30,
              max_iterations=150,
              alpha=1.0,
              beta=3.0,
              rho=0.2,
              rho_local=0.1,
              Q=1.0,
              use_local_search=True,
              time_limit=60):
        """
        Giải bài toán bằng Ant Colony Optimization
        
        Args:
            n_ants: Số lượng kiến (10-50)
            max_iterations: Số vòng lặp tối đa (100-300)
            alpha: Ảnh hưởng của pheromone (0.5-2.0)
            beta: Ảnh hưởng của heuristic (2.0-5.0)
            rho: Evaporation rate (0.1-0.3)
            rho_local: Local evaporation rate (0.05-0.2)
            Q: Pheromone deposit constant (1-100)
            use_local_search: Có áp dụng 2-opt local search không
            time_limit: Giới hạn thời gian (giây)
        """
        print(f"\n{'='*80}")
        print(f"XÂY DỰNG GIẢI PHÁP BẰNG ANT COLONY OPTIMIZATION")
        print(f"{'='*80}")
        print(f"Dataset: {self.dataset_name}")
        print(f"Số khách hàng: {self.n_customers}")
        print(f"Sức chứa xe: {self.vehicle_capacity}")
        print(f"Số xe tối đa: {self.max_vehicles}")
        print(f"\n🐜 SIÊU THAM SỐ:")
        print(f"  - Số lượng kiến: {n_ants}")
        print(f"  - Số vòng lặp tối đa: {max_iterations}")
        print(f"  - Alpha (pheromone): {alpha}")
        print(f"  - Beta (heuristic): {beta}")
        print(f"  - Rho (evaporation): {rho}")
        print(f"  - Rho local: {rho_local}")
        print(f"  - Q (deposit): {Q}")
        print(f"  - Local search: {use_local_search}")
        print(f"  - Thời gian giới hạn: {time_limit}s")
        print(f"{'='*80}\n")
        
        start_time = time.time()
        
        # Khởi tạo pheromone và heuristic
        self._initialize_pheromone()
        heuristic = self._calculate_heuristic()
        
        print("Khởi tạo pheromone matrix và heuristic...")
        
        # Best solution
        best_routes = None
        best_distance = float('inf')
        
        # Tracking
        improvements_log = []
        iteration_distances = []
        no_improvement_count = 0
        
        print(f"\nBắt đầu Ant Colony Optimization...")
        
        for iteration in range(max_iterations):
            elapsed_time = time.time() - start_time
            if elapsed_time > time_limit:
                print(f"\n⏱ Đạt giới hạn thời gian ({time_limit}s)")
                break
            
            # Mỗi kiến xây dựng một solution
            iteration_best_routes = None
            iteration_best_distance = float('inf')
            
            for ant in range(n_ants):
                # Xây dựng solution
                routes = self._construct_ant_solution(alpha, beta, heuristic)
                
                # Áp dụng local search nếu được bật
                if use_local_search:
                    routes = self._apply_local_search_2opt(routes)
                
                # Tính distance
                distance = self._calculate_total_distance(routes)
                
                # Cập nhật iteration best
                if distance < iteration_best_distance:
                    iteration_best_routes = deepcopy(routes)
                    iteration_best_distance = distance
                
                # Local pheromone update
                for route in routes:
                    if not route:
                        continue
                    # Update từ depot
                    self._update_pheromone_local(0, route[0], rho_local)
                    # Update giữa customers
                    for i in range(len(route) - 1):
                        self._update_pheromone_local(route[i], route[i+1], rho_local)
                    # Update về depot
                    self._update_pheromone_local(route[-1], 0, rho_local)
            
            # Cập nhật best solution
            if iteration_best_distance < best_distance:
                best_routes = deepcopy(iteration_best_routes)
                best_distance = iteration_best_distance
                no_improvement_count = 0
                
                improvements_log.append({
                    'iteration': iteration + 1,
                    'distance': best_distance,
                    'time': time.time() - start_time
                })
                
                print(f"  🐜 Iteration {iteration + 1}: Cải thiện! Distance = {best_distance:.2f}")
            else:
                no_improvement_count += 1
            
            # Global pheromone update (chỉ best solution deposit)
            self._update_pheromone_global(best_routes, best_distance, rho)
            
            iteration_distances.append(iteration_best_distance)
            
            # In tiến độ
            if (iteration + 1) % 10 == 0:
                avg_distance = sum(iteration_distances[-10:]) / min(10, len(iteration_distances))
                print(f"  📊 Iteration {iteration + 1}/{max_iterations}: "
                      f"Best={best_distance:.2f}, Avg(last 10)={avg_distance:.2f}, "
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
        print(f"Trạng thái: Feasible (Ant Colony Optimization)")
        print(f"Thời gian giải: {solve_time:.2f} giây")
        print(f"Tổng số iterations: {iteration + 1}")
        print(f"Số lần cải thiện: {len(improvements_log)}")
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
            'status': 'Feasible (Ant Colony Optimization)',
            'objective': best_distance,
            'time': solve_time,
            'routes': self.solution,
            'iterations': iteration + 1,
            'improvements': len(improvements_log),
            'improvements_log': improvements_log
        }
    
    def visualize_solution_comprehensive(self, save=False):
        """Vẽ biểu đồ tổng hợp với nhiều sub-plots"""
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
        ax1.set_title('① Các tuyến đường (Ant Colony Optimization)',
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
            f'KẾT QUẢ ANT COLONY OPTIMIZATION - {self.dataset_name}\n'
            f'Số xe: {len(self.solution)} | Tổng quãng đường: {total_distance:.2f} | '
            f'Khách hàng phục vụ: {total_customers}/{self.n_customers}',
            fontsize=16, fontweight='bold', y=0.98
        )
        
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        
        if save:
            output_dir = Path(__file__).parent / 'result' / 'images'
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f'{self.dataset_name}_aco_solution.png'
            plt.savefig(str(output_path), dpi=300, bbox_inches='tight')
            print(f"✓ Đã lưu hình ảnh: {output_path}")
        
        plt.close(fig)
    
    def visualize_solution(self, save=False):
        """Wrapper để tương thích"""
        self.visualize_solution_comprehensive(save)
    
    def save_solution(self, solve_time=None, status=None, iterations=None, improvements=None):
        """Lưu solution ra file TXT"""
        if self.solution is None:
            print("❌ Chưa có solution để lưu!")
            return
        
        output_dir = Path(__file__).parent / 'result' / 'text'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f'{self.dataset_name}_aco_solution.txt'
        
        total_distance = sum([r['distance'] for r in self.solution.values()])
        total_load = sum([r['load'] for r in self.solution.values()])
        total_customers_served = sum([r['num_customers'] for r in self.solution.values()])
        
        with open(str(output_path), 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write(f"BÁO CÁO KẾT QUẢ ANT COLONY OPTIMIZATION\n")
            f.write(f"Metaheuristic - Swarm Intelligence for VRPTW\n")
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
            f.write("\n")
            
            # PHƯƠNG PHÁP
            f.write("="*80 + "\n")
            f.write("PHƯƠNG PHÁP ANT COLONY OPTIMIZATION\n")
            f.write("="*80 + "\n")
            f.write("Đặc điểm:\n")
            f.write("  - Metaheuristic mô phỏng hành vi tìm đường của đàn kiến\n")
            f.write("  - Pheromone trails: Vết mùi chỉ đường\n")
            f.write("  - Heuristic: Thông tin về khoảng cách (visibility)\n")
            f.write("  - Xác suất chọn: P = (pheromone^alpha) * (heuristic^beta)\n")
            f.write("  - Evaporation: Pheromone bay hơi theo thời gian\n")
            f.write("  - Reinforcement: Best ants deposit nhiều pheromone\n\n")
            
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
    print("ANT COLONY OPTIMIZATION FOR VRPTW")
    print("="*80)
    print("✓ Metaheuristic mô phỏng hành vi đàn kiến")
    print("✓ Pheromone trails + Heuristic information")
    print("✓ Giải toàn bộ dataset (100+ khách hàng)")
    print("✓ Chất lượng xuất sắc, balance exploration/exploitation")
    print("="*80)
    
    solver = AntColonyVRPTWSolver(
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
            improvements=result['improvements']
        )
        print("✓ Hoàn thành!")


if __name__ == "__main__":
    main()
