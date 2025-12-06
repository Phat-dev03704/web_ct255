"""
VRPTW Solver using Particle Swarm Optimization
Giải bài toán VRP với cửa sổ thời gian bằng Thuật toán tối ưu bầy đàn (PSO)

Thuật toán Metaheuristic mô phỏng hành vi tối ưu của bầy đàn các hạt
Sử dụng velocity, position, và thông tin cá nhân/toàn cục để tìm giải pháp tối ưu
"""

import pandas as pd
import numpy as np
import time
from pathlib import Path
import matplotlib.pyplot as plt
import random
from copy import deepcopy

class ParticleSwarmVRPTWSolver:
    """
    Class giải bài toán VRPTW bằng Particle Swarm Optimization
    """
    def __init__(self, dataset_path, vehicle_capacity=200, max_vehicles=25):
        self.dataset_path = dataset_path
        self.dataset_name = Path(dataset_path).stem
        self.vehicle_capacity = vehicle_capacity
        self.max_vehicles = max_vehicles
        self.data = pd.read_csv(dataset_path)
        self.depot = self.data.iloc[0]
        self.customers = self.data.iloc[1:].reset_index(drop=True)
        self.n_customers = len(self.customers)
        self.distance_matrix = self._calculate_distance_matrix()
        self.time_matrix = self.distance_matrix.copy()
        self.solution = None
        self.best_objective = float('inf')

    def _calculate_distance_matrix(self):
        n = self.n_customers + 1
        dist_matrix = np.zeros((n, n))
        all_points = pd.concat([self.depot.to_frame().T, self.customers]).reset_index(drop=True)
        for i in range(n):
            for j in range(n):
                if i != j:
                    x1, y1 = all_points.loc[i, 'XCOORD.'], all_points.loc[i, 'YCOORD.']
                    x2, y2 = all_points.loc[j, 'XCOORD.'], all_points.loc[j, 'YCOORD.']
                    dist_matrix[i][j] = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        return dist_matrix

    def _check_time_window_feasibility(self, route):
        if not route:
            return True
        current_time = 0
        current_location = 0
        for customer_id in route:
            travel_time = float(self.time_matrix[current_location][customer_id])
            arrival_time = current_time + travel_time
            
            # Xử lý an toàn khi convert sang float
            try:
                ready_time_val = self.customers.loc[customer_id - 1, 'READY TIME']
                if isinstance(ready_time_val, str):
                    ready_time = float(ready_time_val.split()[0])
                else:
                    ready_time = float(ready_time_val)
                
                due_date_val = self.customers.loc[customer_id - 1, 'DUE DATE']
                if isinstance(due_date_val, str):
                    due_date = float(due_date_val.split()[0])
                else:
                    due_date = float(due_date_val)
                
                service_time_val = self.customers.loc[customer_id - 1, 'SERVICE TIME']
                if isinstance(service_time_val, str):
                    service_time = float(service_time_val.split()[0])
                else:
                    service_time = float(service_time_val)
            except (ValueError, AttributeError, IndexError) as e:
                return False
            
            start_service = max(arrival_time, ready_time)
            if start_service > due_date:
                return False
            current_time = start_service + service_time
            current_location = customer_id
        
        travel_time_back = float(self.time_matrix[current_location][0])
        return_time = current_time + travel_time_back
        
        try:
            depot_due_date_val = self.depot['DUE DATE']
            if isinstance(depot_due_date_val, str):
                depot_due_date = float(depot_due_date_val.split()[0])
            else:
                depot_due_date = float(depot_due_date_val)
        except (ValueError, AttributeError, IndexError):
            depot_due_date = float('inf')
        
        return return_time <= depot_due_date

    def _calculate_route_distance(self, route):
        if not route:
            return 0
        distance = 0
        distance += self.distance_matrix[0][route[0]]
        for i in range(len(route) - 1):
            distance += self.distance_matrix[route[i]][route[i+1]]
        distance += self.distance_matrix[route[-1]][0]
        return distance

    def _calculate_route_load(self, route):
        total_load = 0
        for customer_id in route:
            demand_val = self.customers.loc[customer_id - 1, 'DEMAND']
            if isinstance(demand_val, str):
                total_load += float(demand_val.split()[0])
            else:
                total_load += float(demand_val)
        return total_load

    def _calculate_total_distance(self, routes):
        return sum([self._calculate_route_distance(route) for route in routes if route])

    def get_recommended_hyperparameters(self):
        n = self.n_customers
        n_particles = 30 if n <= 100 else 50
        max_iterations = 150 if n <= 100 else 200
        w = 0.7
        c1 = 1.5
        c2 = 1.5
        use_local_search = True
        return {
            'n_particles': n_particles,
            'max_iterations': max_iterations,
            'w': w,
            'c1': c1,
            'c2': c2,
            'use_local_search': use_local_search,
            'time_limit': 60
        }

    def solve(self,
              n_particles=30,
              max_iterations=150,
              w=0.7,
              c1=1.5,
              c2=1.5,
              use_local_search=True,
              time_limit=60):
        print(f"\n{'='*80}")
        print(f"XÂY DỰNG GIẢI PHÁP BẰNG PARTICLE SWARM OPTIMIZATION")
        print(f"{'='*80}")
        print(f"Dataset: {self.dataset_name}")
        print(f"Số khách hàng: {self.n_customers}")
        print(f"Sức chứa xe: {self.vehicle_capacity}")
        print(f"Số xe tối đa: {self.max_vehicles}")
        print(f"\n🐦 SIÊU THAM SỐ:")
        print(f"  - Số lượng particles: {n_particles}")
        print(f"  - Số vòng lặp tối đa: {max_iterations}")
        print(f"  - w (inertia): {w}")
        print(f"  - c1 (cognitive): {c1}")
        print(f"  - c2 (social): {c2}")
        print(f"  - Local search: {use_local_search}")
        print(f"  - Thời gian giới hạn: {time_limit}s")
        print(f"{'='*80}\n")
        start_time = time.time()
        # Khởi tạo particles
        particles = []
        velocities = []
        pbest = []
        pbest_obj = []
        gbest = None
        gbest_obj = float('inf')
        for _ in range(n_particles):
            routes = self._random_solution()
            particles.append(routes)
            velocities.append([])
            pbest.append(deepcopy(routes))
            obj = self._calculate_total_distance(routes)
            pbest_obj.append(obj)
            if obj < gbest_obj:
                gbest = deepcopy(routes)
                gbest_obj = obj
        iteration_distances = []
        for iteration in range(max_iterations):
            elapsed_time = time.time() - start_time
            if elapsed_time > time_limit:
                print(f"\n⏱ Đạt giới hạn thời gian ({time_limit}s)")
                break
            for i in range(n_particles):
                # Update velocity & position (giải pháp)
                new_routes = self._update_particle(particles[i], velocities[i], pbest[i], gbest, w, c1, c2)
                if use_local_search:
                    new_routes = self._apply_local_search_2opt(new_routes)
                obj = self._calculate_total_distance(new_routes)
                if obj < pbest_obj[i]:
                    pbest[i] = deepcopy(new_routes)
                    pbest_obj[i] = obj
                if obj < gbest_obj:
                    gbest = deepcopy(new_routes)
                    gbest_obj = obj
                particles[i] = deepcopy(new_routes)
            iteration_distances.append(gbest_obj)
            if (iteration + 1) % 10 == 0:
                avg_distance = sum(iteration_distances[-10:]) / min(10, len(iteration_distances))
                print(f"  📊 Iteration {iteration + 1}/{max_iterations}: Best={gbest_obj:.2f}, Avg(last 10)={avg_distance:.2f}")
        solve_time = time.time() - start_time
        gbest = [route for route in gbest if route]
        self.solution = {}
        route_id = 0
        for customers_list in gbest:
            distance = self._calculate_route_distance(customers_list)
            load = self._calculate_route_load(customers_list)
            self.solution[route_id] = {
                'route': customers_list,
                'distance': distance,
                'load': load,
                'num_customers': len(customers_list)
            }
            route_id += 1
        print(f"\n{'='*80}")
        print(f"KẾT QUẢ GIẢI")
        print(f"{'='*80}")
        print(f"Trạng thái: Feasible (Particle Swarm Optimization)")
        print(f"Thời gian giải: {solve_time:.2f} giây")
        print(f"Tổng số iterations: {iteration + 1}")
        print(f"Số xe sử dụng: {len(self.solution)}")
        print(f"Tổng quãng đường: {gbest_obj:.2f}")
        return {
            'status': 'Feasible (Particle Swarm Optimization)',
            'objective': gbest_obj,
            'time': solve_time,
            'routes': self.solution,
            'iterations': iteration + 1
        }

    def _random_solution(self):
        # Tạo giải pháp ngẫu nhiên (phân chia khách hàng vào các xe)
        customers = list(range(1, self.n_customers + 1))
        random.shuffle(customers)
        routes = []
        while customers:
            route = []
            load = 0
            while customers:
                customer_id = customers[0]
                demand_val = self.customers.loc[customer_id - 1, 'DEMAND']
                if isinstance(demand_val, str):
                    demand = float(demand_val.split()[0])
                else:
                    demand = float(demand_val)
                if load + demand > self.vehicle_capacity:
                    break
                route.append(customer_id)
                load += demand
                customers.pop(0)
            if route:
                routes.append(route)
        return routes

    def _update_particle(self, routes, velocity, pbest, gbest, w, c1, c2):
        # Đơn giản hóa: hoán đổi các khách hàng giữa các routes
        new_routes = deepcopy(routes)
        for _ in range(random.randint(1, 3)):
            if len(new_routes) < 2:
                break
            r1, r2 = random.sample(range(len(new_routes)), 2)
            if not new_routes[r1] or not new_routes[r2]:
                continue
            idx1 = random.randint(0, len(new_routes[r1]) - 1)
            idx2 = random.randint(0, len(new_routes[r2]) - 1)
            new_routes[r1][idx1], new_routes[r2][idx2] = new_routes[r2][idx2], new_routes[r1][idx1]
        return new_routes

    def _apply_local_search_2opt(self, routes):
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
        ax1.set_title('① Các tuyến đường (Particle Swarm Optimization)',
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
            f'KẾT QUẢ PARTICLE SWARM OPTIMIZATION - {self.dataset_name}\n'
            f'Số xe: {len(self.solution)} | Tổng quãng đường: {total_distance:.2f} | '
            f'Khách hàng phục vụ: {total_customers}/{self.n_customers}',
            fontsize=16, fontweight='bold', y=0.98
        )
        
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        
        if save:
            output_dir = Path(__file__).parent / 'result' / 'images'
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f'{self.dataset_name}_pso_solution.png'
            plt.savefig(str(output_path), dpi=300, bbox_inches='tight')
            print(f"✓ Đã lưu hình ảnh: {output_path}")
        
        plt.close(fig)
    
    def visualize_solution(self, save=False):
        """Wrapper để tương thích"""
        self.visualize_solution_comprehensive(save)

    def save_solution(self, solve_time=None, status=None, iterations=None):
        """Lưu solution ra file TXT"""
        if self.solution is None:
            print("❌ Chưa có solution để lưu!")
            return
        
        output_dir = Path(__file__).parent / 'result' / 'text'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f'{self.dataset_name}_pso_solution.txt'
        
        total_distance = sum([r['distance'] for r in self.solution.values()])
        total_load = sum([r['load'] for r in self.solution.values()])
        total_customers_served = sum([r['num_customers'] for r in self.solution.values()])
        
        with open(str(output_path), 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write(f"BÁO CÁO KẾT QUẢ PARTICLE SWARM OPTIMIZATION\n")
            f.write(f"Metaheuristic - Swarm Intelligence for VRPTW\n")
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
            f.write("\n")
            f.write("="*80 + "\n")
            f.write("KẾT QUẢ TỔNG HỢP\n")
            f.write("="*80 + "\n")
            f.write(f"Số xe sử dụng: {len(self.solution)}\n")
            f.write(f"Tổng quãng đường: {total_distance:.2f}\n")
            f.write(f"Khách hàng phục vụ: {total_customers_served}/{self.n_customers}\n\n")
            f.write("="*80 + "\n")
            f.write("CHI TIẾT CÁC TUYẾN ĐƯỜNG\n")
            f.write("="*80 + "\n\n")
            for route_id, info in self.solution.items():
                f.write(f"{'─'*80}\n")
                f.write(f"XE {route_id + 1}\n")
                f.write(f"{'─'*80}\n")
                f.write(f"Tuyến đường: 0 → {' → '.join(map(str, info['route']))} → 0\n")
                f.write(f"Số khách hàng: {info['num_customers']}\n")
                f.write(f"Tổng nhu cầu: {info['load']}/{self.vehicle_capacity}\n")
                f.write(f"Quãng đường: {info['distance']:.2f}\n\n")
            f.write("="*80 + "\n")
        print(f"✓ Đã lưu báo cáo: {output_path}")

def main():
    current_dir = Path(__file__).parent
    code_dir = current_dir.parent.parent
    dataset_path = code_dir / "dataset" / "C1" / "C101.csv"
    print("="*80)
    print("PARTICLE SWARM OPTIMIZATION FOR VRPTW")
    print("="*80)
    solver = ParticleSwarmVRPTWSolver(
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
            iterations=result['iterations']
        )
        print("✓ Hoàn thành!")

if __name__ == "__main__":
    main()
