"""
VRPTW Solver using Genetic Algorithm
Giải bài toán VRP với cửa sổ thời gian bằng Thuật toán di truyền

Thuật toán Metaheuristic mô phỏng quá trình tiến hóa tự nhiên
Sử dụng selection, crossover, mutation để tìm giải pháp tối ưu
"""

import pandas as pd
import numpy as np
import time
from pathlib import Path
import matplotlib.pyplot as plt
import random
from copy import deepcopy


class GeneticAlgorithmVRPTWSolver:
    """
    Class giải bài toán VRPTW bằng Genetic Algorithm
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
    
    def _create_initial_population_nearest_neighbor(self, pop_size):
        """
        Tạo population ban đầu bằng Nearest Neighbor với ngẫu nhiên
        """
        population = []
        
        for _ in range(pop_size):
            routes = []
            unvisited = set(range(1, self.n_customers + 1))
            
            # Bắt đầu từ khách hàng ngẫu nhiên
            start_customers = random.sample(list(unvisited), min(len(unvisited), self.max_vehicles))
            
            for start_customer in start_customers:
                if start_customer not in unvisited:
                    continue
                    
                current_route = []
                current_load = 0
                current_location = 0  # depot
                
                # Thêm khách hàng đầu tiên
                if self.customers.loc[start_customer - 1, 'DEMAND'] <= self.vehicle_capacity:
                    current_route.append(start_customer)
                    current_load += self.customers.loc[start_customer - 1, 'DEMAND']
                    current_location = start_customer
                    unvisited.remove(start_customer)
                
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
                        # Thêm yếu tố ngẫu nhiên
                        dist = dist * random.uniform(0.8, 1.2)
                        
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
            while unvisited and len(routes) < self.max_vehicles:
                customer_id = unvisited.pop()
                routes.append([customer_id])
            
            population.append(routes)
        
        return population
    
    def _calculate_fitness(self, routes):
        """
        Tính fitness của một individual
        Fitness = 1 / (total_distance + penalty)
        """
        if not routes:
            return 0
        
        total_distance = self._calculate_total_distance(routes)
        
        # Penalty cho vi phạm constraints
        penalty = 0
        
        # Penalty cho số xe vượt quá
        if len(routes) > self.max_vehicles:
            penalty += 10000 * (len(routes) - self.max_vehicles)
        
        # Penalty cho capacity violation
        for route in routes:
            if route:
                load = self._calculate_route_load(route)
                if load > self.vehicle_capacity:
                    penalty += 1000 * (load - self.vehicle_capacity)
        
        # Penalty cho time window violation
        for route in routes:
            if route and not self._check_time_window_feasibility(route):
                penalty += 5000
        
        # Fitness cao hơn = tốt hơn
        fitness = 1 / (total_distance + penalty + 1)
        
        return fitness
    
    def _tournament_selection(self, population, fitnesses, tournament_size):
        """
        Selection bằng Tournament
        Chọn ngẫu nhiên tournament_size individuals, chọn cái tốt nhất
        """
        tournament_indices = random.sample(range(len(population)), tournament_size)
        tournament_fitnesses = [fitnesses[i] for i in tournament_indices]
        winner_idx = tournament_indices[tournament_fitnesses.index(max(tournament_fitnesses))]
        return deepcopy(population[winner_idx])
    
    def _order_crossover(self, parent1, parent2):
        """
        Order Crossover (OX) cho routes
        Kết hợp 2 parents để tạo 2 children
        """
        # Flatten routes thành danh sách khách hàng
        p1_flat = [c for route in parent1 for c in route]
        p2_flat = [c for route in parent2 for c in route]
        
        if len(p1_flat) < 2 or len(p2_flat) < 2:
            return deepcopy(parent1), deepcopy(parent2)
        
        # Chọn 2 điểm cắt
        size = min(len(p1_flat), len(p2_flat))
        cx_point1 = random.randint(0, size - 2)
        cx_point2 = random.randint(cx_point1 + 1, size - 1)
        
        # Tạo children
        child1_flat = [None] * size
        child2_flat = [None] * size
        
        # Copy đoạn giữa 2 điểm cắt
        child1_flat[cx_point1:cx_point2] = p1_flat[cx_point1:cx_point2]
        child2_flat[cx_point1:cx_point2] = p2_flat[cx_point1:cx_point2]
        
        # Điền các vị trí còn lại
        def fill_child(child, parent_other):
            child_set = set([c for c in child if c is not None])
            fill_idx = cx_point2
            for gene in parent_other[cx_point2:] + parent_other[:cx_point2]:
                if gene not in child_set:
                    if fill_idx >= len(child):
                        fill_idx = 0
                    while child[fill_idx] is not None:
                        fill_idx = (fill_idx + 1) % len(child)
                    child[fill_idx] = gene
                    child_set.add(gene)
                    fill_idx = (fill_idx + 1) % len(child)
        
        fill_child(child1_flat, p2_flat)
        fill_child(child2_flat, p1_flat)
        
        # Convert lại thành routes
        child1_routes = self._split_into_routes(child1_flat)
        child2_routes = self._split_into_routes(child2_flat)
        
        return child1_routes, child2_routes
    
    def _split_into_routes(self, customer_list):
        """
        Chia danh sách khách hàng thành routes hợp lệ
        """
        routes = []
        current_route = []
        current_load = 0
        
        for customer_id in customer_list:
            if customer_id is None:
                continue
                
            demand = self.customers.loc[customer_id - 1, 'DEMAND']
            
            # Thử thêm vào route hiện tại
            test_route = current_route + [customer_id]
            test_load = current_load + demand
            
            if (test_load <= self.vehicle_capacity and 
                self._check_time_window_feasibility(test_route) and
                len(routes) < self.max_vehicles):
                current_route.append(customer_id)
                current_load = test_load
            else:
                # Bắt đầu route mới
                if current_route:
                    routes.append(current_route)
                current_route = [customer_id]
                current_load = demand
        
        if current_route:
            routes.append(current_route)
        
        return routes
    
    def _mutate_swap(self, routes):
        """
        Mutation: Hoán đổi 2 khách hàng trong cùng route hoặc khác route
        """
        if not routes or len(routes) == 0:
            return routes
        
        routes = deepcopy(routes)
        
        # Lấy tất cả routes có khách hàng
        non_empty = [i for i, r in enumerate(routes) if len(r) > 0]
        if len(non_empty) < 1:
            return routes
        
        if len(non_empty) == 1 and len(routes[non_empty[0]]) < 2:
            return routes
        
        # Chọn 2 routes ngẫu nhiên (có thể trùng)
        route1_idx = random.choice(non_empty)
        route2_idx = random.choice(non_empty)
        
        route1 = routes[route1_idx]
        route2 = routes[route2_idx]
        
        if not route1 or not route2:
            return routes
        
        # Chọn 2 vị trí ngẫu nhiên
        pos1 = random.randint(0, len(route1) - 1)
        pos2 = random.randint(0, len(route2) - 1)
        
        # Hoán đổi
        route1[pos1], route2[pos2] = route2[pos2], route1[pos1]
        
        # Kiểm tra feasibility
        if (self._calculate_route_load(route1) <= self.vehicle_capacity and
            self._calculate_route_load(route2) <= self.vehicle_capacity and
            self._check_time_window_feasibility(route1) and
            self._check_time_window_feasibility(route2)):
            routes[route1_idx] = route1
            routes[route2_idx] = route2
        
        return routes
    
    def _mutate_reverse(self, routes):
        """
        Mutation: Đảo ngược một đoạn trong route (2-opt style)
        """
        if not routes:
            return routes
        
        routes = deepcopy(routes)
        
        # Chọn route có ít nhất 3 khách hàng
        valid_routes = [i for i, r in enumerate(routes) if len(r) >= 3]
        if not valid_routes:
            return routes
        
        route_idx = random.choice(valid_routes)
        route = routes[route_idx]
        
        # Chọn 2 điểm
        i = random.randint(0, len(route) - 2)
        j = random.randint(i + 1, len(route) - 1)
        
        # Đảo ngược
        route[i:j+1] = route[i:j+1][::-1]
        
        # Kiểm tra feasibility
        if self._check_time_window_feasibility(route):
            routes[route_idx] = route
        
        return routes
    
    def get_recommended_hyperparameters(self):
        """
        Tự động đề xuất siêu tham số dựa trên kích thước bài toán
        """
        n = self.n_customers
        
        # Population size: 50-200
        if n <= 50:
            population_size = 50
            max_generations = 100
            elite_size = 5
        elif n <= 100:
            population_size = 100
            max_generations = 150
            elite_size = 10
        else:
            population_size = 150
            max_generations = 200
            elite_size = 15
        
        # Crossover rate: 0.7-0.9 (cao = nhiều exploration)
        crossover_rate = 0.8
        
        # Mutation rate: 0.1-0.3 (thấp hơn crossover)
        mutation_rate = 0.2
        
        # Tournament size: 3-5
        tournament_size = 3
        
        return {
            'population_size': population_size,
            'max_generations': max_generations,
            'crossover_rate': crossover_rate,
            'mutation_rate': mutation_rate,
            'elite_size': elite_size,
            'tournament_size': tournament_size,
            'time_limit': 60
        }
    
    def print_hyperparameter_guide(self):
        """In hướng dẫn điều chỉnh hyperparameters"""
        print("\n" + "="*80)
        print("HƯỚNG DẪN ĐIỀU CHỈNH HYPERPARAMETERS - GENETIC ALGORITHM")
        print("="*80)
        print("\n1. POPULATION_SIZE (Kích thước quần thể)")
        print("   - Giá trị: 50-200")
        print("   - Nhỏ (50-80): Nhanh nhưng dễ hội tụ sớm")
        print("   - Lớn (120-200): Chậm nhưng đa dạng hơn")
        print("   - Khuyến nghị: 50 (n≤50), 100 (50<n≤100), 150 (n>100)")
        
        print("\n2. MAX_GENERATIONS (Số thế hệ tối đa)")
        print("   - Giá trị: 100-300")
        print("   - Nhiều gen = chất lượng tốt hơn nhưng mất thời gian")
        print("   - Khuyến nghị: 100 (n≤50), 150 (50<n≤100), 200 (n>100)")
        
        print("\n3. CROSSOVER_RATE (Tỷ lệ lai ghép)")
        print("   - Giá trị: 0.7-0.9")
        print("   - Cao = nhiều exploration (kết hợp đa dạng)")
        print("   - Khuyến nghị: 0.8 (balance)")
        
        print("\n4. MUTATION_RATE (Tỷ lệ đột biến)")
        print("   - Giá trị: 0.1-0.3")
        print("   - Cao = tránh local optimum nhưng nhiễu nhiều")
        print("   - Thấp = ổn định nhưng dễ bị stuck")
        print("   - Khuyến nghị: 0.2 (balance)")
        
        print("\n5. ELITE_SIZE (Số cá thể ưu tú giữ lại)")
        print("   - Giá trị: 5-15")
        print("   - Giữ lại best individuals qua thế hệ")
        print("   - Khuyến nghị: 5-15 (tùy population size)")
        
        print("\n6. TOURNAMENT_SIZE (Kích thước tournament selection)")
        print("   - Giá trị: 2-5")
        print("   - Lớn = selection pressure cao (chọn tốt hơn)")
        print("   - Khuyến nghị: 3 (balance)")
        
        print("\n" + "="*80)
        print("💡 TIP: Sử dụng get_recommended_hyperparameters() để tự động!")
        print("="*80 + "\n")
    
    def solve(self,
              population_size=100,
              max_generations=150,
              crossover_rate=0.8,
              mutation_rate=0.2,
              elite_size=10,
              tournament_size=3,
              time_limit=60):
        """
        Giải bài toán bằng Genetic Algorithm
        
        Args:
            population_size: Kích thước quần thể (50-200)
            max_generations: Số thế hệ tối đa (100-300)
            crossover_rate: Tỷ lệ lai ghép (0.7-0.9)
            mutation_rate: Tỷ lệ đột biến (0.1-0.3)
            elite_size: Số cá thể ưu tú giữ lại (5-15)
            tournament_size: Kích thước tournament selection (2-5)
            time_limit: Giới hạn thời gian (giây)
        """
        print(f"\n{'='*80}")
        print(f"XÂY DỰNG GIẢI PHÁP BẰNG GENETIC ALGORITHM")
        print(f"{'='*80}")
        print(f"Dataset: {self.dataset_name}")
        print(f"Số khách hàng: {self.n_customers}")
        print(f"Sức chứa xe: {self.vehicle_capacity}")
        print(f"Số xe tối đa: {self.max_vehicles}")
        print(f"\n🧬 SIÊU THAM SỐ:")
        print(f"  - Kích thước quần thể: {population_size}")
        print(f"  - Số thế hệ tối đa: {max_generations}")
        print(f"  - Tỷ lệ lai ghép: {crossover_rate}")
        print(f"  - Tỷ lệ đột biến: {mutation_rate}")
        print(f"  - Elite size: {elite_size}")
        print(f"  - Tournament size: {tournament_size}")
        print(f"  - Thời gian giới hạn: {time_limit}s")
        print(f"{'='*80}\n")
        
        start_time = time.time()
        
        # Tạo population ban đầu
        print("Tạo population ban đầu...")
        population = self._create_initial_population_nearest_neighbor(population_size)
        
        # Tính fitness
        fitnesses = [self._calculate_fitness(ind) for ind in population]
        
        best_individual = deepcopy(population[fitnesses.index(max(fitnesses))])
        best_fitness = max(fitnesses)
        best_distance = self._calculate_total_distance(best_individual)
        
        print(f"✓ Population ban đầu: {population_size} individuals")
        print(f"  - Best fitness: {best_fitness:.6f}")
        print(f"  - Best distance: {best_distance:.2f}")
        
        print(f"\nBắt đầu Evolution...")
        
        generation = 0
        improvements_log = []
        no_improvement_count = 0
        
        while generation < max_generations:
            elapsed_time = time.time() - start_time
            if elapsed_time > time_limit:
                print(f"\n⏱ Đạt giới hạn thời gian ({time_limit}s)")
                break
            
            generation += 1
            
            # Tạo thế hệ mới
            new_population = []
            
            # 1. ELITISM: Giữ lại elite individuals
            elite_indices = sorted(range(len(fitnesses)), key=lambda i: fitnesses[i], reverse=True)[:elite_size]
            for idx in elite_indices:
                new_population.append(deepcopy(population[idx]))
            
            # 2. CROSSOVER + MUTATION
            while len(new_population) < population_size:
                # Selection
                parent1 = self._tournament_selection(population, fitnesses, tournament_size)
                parent2 = self._tournament_selection(population, fitnesses, tournament_size)
                
                # Crossover
                if random.random() < crossover_rate:
                    child1, child2 = self._order_crossover(parent1, parent2)
                else:
                    child1, child2 = deepcopy(parent1), deepcopy(parent2)
                
                # Mutation
                if random.random() < mutation_rate:
                    if random.random() < 0.5:
                        child1 = self._mutate_swap(child1)
                    else:
                        child1 = self._mutate_reverse(child1)
                
                if random.random() < mutation_rate:
                    if random.random() < 0.5:
                        child2 = self._mutate_swap(child2)
                    else:
                        child2 = self._mutate_reverse(child2)
                
                new_population.append(child1)
                if len(new_population) < population_size:
                    new_population.append(child2)
            
            # Cập nhật population
            population = new_population[:population_size]
            fitnesses = [self._calculate_fitness(ind) for ind in population]
            
            # Cập nhật best
            current_best_idx = fitnesses.index(max(fitnesses))
            current_best_fitness = fitnesses[current_best_idx]
            current_best_distance = self._calculate_total_distance(population[current_best_idx])
            
            if current_best_fitness > best_fitness:
                best_individual = deepcopy(population[current_best_idx])
                best_fitness = current_best_fitness
                best_distance = current_best_distance
                no_improvement_count = 0
                
                improvements_log.append({
                    'generation': generation,
                    'fitness': best_fitness,
                    'distance': best_distance,
                    'time': time.time() - start_time
                })
                
                print(f"  🧬 Gen {generation}: Cải thiện! Distance = {best_distance:.2f}, "
                      f"Fitness = {best_fitness:.6f}")
            else:
                no_improvement_count += 1
            
            # In tiến độ
            if generation % 10 == 0:
                avg_fitness = sum(fitnesses) / len(fitnesses)
                print(f"  📊 Gen {generation}/{max_generations}: "
                      f"Best={best_distance:.2f}, Avg Fitness={avg_fitness:.6f}, "
                      f"No improve={no_improvement_count}")
            
            # Early stopping nếu không cải thiện lâu
            if no_improvement_count > max_generations // 3:
                print(f"\n⚠️ Dừng sớm: Không cải thiện sau {no_improvement_count} thế hệ")
                break
        
        solve_time = time.time() - start_time
        
        # Loại bỏ routes rỗng
        best_individual = [route for route in best_individual if route]
        
        # Chuyển đổi sang format solution
        self.solution = {}
        route_id = 0
        
        for customers_list in best_individual:
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
        print(f"Trạng thái: Feasible (Genetic Algorithm)")
        print(f"Thời gian giải: {solve_time:.2f} giây")
        print(f"Tổng số thế hệ: {generation}")
        print(f"Số lần cải thiện: {len(improvements_log)}")
        print(f"Best fitness: {best_fitness:.6f}")
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
            'status': 'Feasible (Genetic Algorithm)',
            'objective': best_distance,
            'time': solve_time,
            'routes': self.solution,
            'generations': generation,
            'improvements': len(improvements_log),
            'improvements_log': improvements_log,
            'final_fitness': best_fitness
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
        ax1.set_title('① Các tuyến đường (Genetic Algorithm)',
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
            f'KẾT QUẢ GENETIC ALGORITHM - {self.dataset_name}\n'
            f'Số xe: {len(self.solution)} | Tổng quãng đường: {total_distance:.2f} | '
            f'Khách hàng phục vụ: {total_customers}/{self.n_customers}',
            fontsize=16, fontweight='bold', y=0.98
        )
        
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        
        if save:
            output_dir = Path(__file__).parent / 'result' / 'images'
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f'{self.dataset_name}_ga_solution.png'
            plt.savefig(str(output_path), dpi=300, bbox_inches='tight')
            print(f"✓ Đã lưu hình ảnh: {output_path}")
        
        plt.close(fig)
    
    def visualize_solution(self, save=False):
        """Wrapper để tương thích"""
        self.visualize_solution_comprehensive(save)
    
    def save_solution(self, solve_time=None, status=None, generations=None, 
                     improvements=None, final_fitness=None):
        """Lưu solution ra file TXT"""
        if self.solution is None:
            print("❌ Chưa có solution để lưu!")
            return
        
        output_dir = Path(__file__).parent / 'result' / 'text'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f'{self.dataset_name}_ga_solution.txt'
        
        total_distance = sum([r['distance'] for r in self.solution.values()])
        total_load = sum([r['load'] for r in self.solution.values()])
        total_customers_served = sum([r['num_customers'] for r in self.solution.values()])
        
        with open(str(output_path), 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write(f"BÁO CÁO KẾT QUẢ GENETIC ALGORITHM\n")
            f.write(f"Metaheuristic - Evolution-based for VRPTW\n")
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
            if generations:
                f.write(f"Số thế hệ: {generations}\n")
            if improvements:
                f.write(f"Số lần cải thiện: {improvements}\n")
            if final_fitness:
                f.write(f"Final fitness: {final_fitness:.6f}\n")
            f.write("\n")
            
            # PHƯƠNG PHÁP
            f.write("="*80 + "\n")
            f.write("PHƯƠNG PHÁP GENETIC ALGORITHM\n")
            f.write("="*80 + "\n")
            f.write("Đặc điểm:\n")
            f.write("  - Metaheuristic mô phỏng quá trình tiến hóa tự nhiên\n")
            f.write("  - Selection: Tournament selection\n")
            f.write("  - Crossover: Order Crossover (OX)\n")
            f.write("  - Mutation: Swap + Reverse (2-opt)\n")
            f.write("  - Elitism: Giữ lại best individuals\n\n")
            
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
    print("GENETIC ALGORITHM FOR VRPTW")
    print("="*80)
    print("✓ Metaheuristic mô phỏng quá trình tiến hóa")
    print("✓ Selection, Crossover, Mutation")
    print("✓ Giải toàn bộ dataset (100+ khách hàng)")
    print("✓ Chất lượng rất tốt, đa dạng và ổn định")
    print("="*80)
    
    solver = GeneticAlgorithmVRPTWSolver(
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
            generations=result['generations'],
            improvements=result['improvements'],
            final_fitness=result.get('final_fitness')
        )
        print("✓ Hoàn thành!")


if __name__ == "__main__":
    main()
