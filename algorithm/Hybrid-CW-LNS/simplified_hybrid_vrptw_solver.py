"""
Simplified Hybrid VRPTW Solver: Clarke-Wright + Tabu Search
Giải pháp đơn giản và hiệu quả

Phase 1: Clarke-Wright (Fast - 0.1-0.5s)
Phase 2: Tabu Search improvement (10-30s)

Vì LNS phức tạp, ta dùng Tabu Search để cải thiện CW solution
"""

import sys
import os
import pandas as pd
import numpy as np
from pathlib import Path
import time
import random
from copy import deepcopy
import matplotlib.pyplot as plt
from datetime import datetime

# Add parent directories to path
current_dir = os.path.dirname(os.path.abspath(__file__))
cw_dir = os.path.join(current_dir, '..', 'Clarke-Wright-Saving')

if cw_dir not in sys.path:
    sys.path.insert(0, cw_dir)

# Import CW solver
try:
    from cw_vrptw_solver import ClarkeWrightVRPTWSolver
except ImportError as e:
    print(f"Error importing CW solver: {e}")
    print(f"CW directory: {cw_dir}")
    print(f"Current sys.path: {sys.path}")
    raise
from copy import deepcopy
import matplotlib.pyplot as plt
from datetime import datetime


class SimplifiedHybridVRPTWSolver:
    """
    Simplified Hybrid VRPTW Solver
    
    Chiến lược đơn giản:
    1. Clarke-Wright để tạo initial solution (0.1-0.5s)
    2. Simple improvement operators (2-opt, swap, relocate) (10-30s)
    
    Ưu điểm:
    - Đơn giản, dễ hiểu
    - Nhanh và hiệu quả
    - Không phụ thuộc nhiều vào các solvers phức tạp
    """
    
    def __init__(self, 
                 dataset_path,
                 vehicle_capacity=200,
                 max_vehicles=25,
                 improvement_time_limit=20,
                 improvement_iterations=1000,
                 mode='balanced'):
        """
        Args:
            mode: 'fast' (10s, 500 iter), 'balanced' (20s, 1000 iter), 
                  'quality' (40s, 2000 iter), 'cw_only'
        """
        self.dataset_path = dataset_path
        self.dataset_name = Path(dataset_path).stem
        self.vehicle_capacity = vehicle_capacity
        self.max_vehicles = max_vehicles
        
        # Mode settings
        self.mode = mode
        if mode == 'fast':
            self.improvement_time_limit = 10
            self.improvement_iterations = 500
        elif mode == 'balanced':
            self.improvement_time_limit = 20
            self.improvement_iterations = 1000
        elif mode == 'quality':
            self.improvement_time_limit = 40
            self.improvement_iterations = 2000
        elif mode == 'cw_only':
            self.improvement_time_limit = 0
            self.improvement_iterations = 0
        else:
            self.improvement_time_limit = improvement_time_limit
            self.improvement_iterations = improvement_iterations
        
        # Initialize CW solver
        self.cw_solver = ClarkeWrightVRPTWSolver(
            dataset_path, vehicle_capacity, max_vehicles
        )
        
        # Read data
        self.data = pd.read_csv(dataset_path)
        self.depot = self.data.iloc[0]
        self.customers = self.data.iloc[1:].reset_index(drop=True)
        self.n_customers = len(self.customers)
        
        # Distance matrix
        self.distance_matrix = self._calculate_distance_matrix()
        self.time_matrix = self.distance_matrix.copy()
        
        # Results
        self.cw_solution = None
        self.final_solution = None
        self.solve_time = 0
        self.improvement_percentage = 0
    
    def _calculate_distance_matrix(self):
        """Calculate Euclidean distance matrix"""
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
    
    def _calculate_route_distance(self, route):
        """Calculate total distance of a route"""
        if not route:
            return 0
        
        distance = self.distance_matrix[0][route[0]]  # Depot to first
        
        for i in range(len(route) - 1):
            distance += self.distance_matrix[route[i]][route[i+1]]
        
        distance += self.distance_matrix[route[-1]][0]  # Last to depot
        
        return distance
    
    def _calculate_total_distance(self, routes):
        """Calculate total distance of all routes"""
        return sum(self._calculate_route_distance(route) for route in routes)
    
    def _check_time_window_feasibility(self, route):
        """Check if route satisfies time windows"""
        if not route:
            return True
        
        current_time = 0
        current_location = 0
        
        for customer_id in route:
            travel_time = self.time_matrix[current_location][customer_id]
            arrival_time = current_time + travel_time
            
            ready_time = self.customers.loc[customer_id - 1, 'READY TIME']
            due_date = self.customers.loc[customer_id - 1, 'DUE DATE']
            service_time = self.customers.loc[customer_id - 1, 'SERVICE TIME']
            
            start_service = max(arrival_time, ready_time)
            
            if start_service > due_date:
                return False
            
            current_time = start_service + service_time
            current_location = customer_id
        
        # Check return to depot
        travel_back = self.time_matrix[current_location][0]
        return_time = current_time + travel_back
        depot_due = self.depot['DUE DATE']
        
        return return_time <= depot_due
    
    def _check_capacity_feasibility(self, route):
        """Check if route satisfies capacity constraint"""
        if not route:
            return True
        
        total_demand = sum(self.customers.loc[cust_id - 1, 'DEMAND'] 
                          for cust_id in route)
        
        return total_demand <= self.vehicle_capacity
    
    def _two_opt_single_route(self, route):
        """Apply 2-opt to a single route"""
        if len(route) < 4:
            return route
        
        best_route = route[:]
        best_distance = self._calculate_route_distance(best_route)
        improved = True
        
        while improved:
            improved = False
            
            for i in range(1, len(best_route) - 2):
                for j in range(i + 1, len(best_route)):
                    # Reverse segment [i:j+1]
                    new_route = best_route[:i] + best_route[i:j+1][::-1] + best_route[j+1:]
                    
                    # Check feasibility
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
        
        return best_route
    
    def _relocate_move(self, routes):
        """Try to relocate a customer to another route"""
        best_routes = deepcopy(routes)
        best_distance = self._calculate_total_distance(best_routes)
        
        for i, route_i in enumerate(routes):
            if not route_i:
                continue
            
            for cust_idx, customer in enumerate(route_i):
                # Try moving to other routes
                for j, route_j in enumerate(routes):
                    if i == j:
                        continue
                    
                    # Remove from route i
                    new_route_i = route_i[:cust_idx] + route_i[cust_idx+1:]
                    
                    # Try all positions in route j
                    for pos in range(len(route_j) + 1):
                        new_route_j = route_j[:pos] + [customer] + route_j[pos:]
                        
                        # Check feasibility
                        if not self._check_time_window_feasibility(new_route_i):
                            continue
                        if not self._check_time_window_feasibility(new_route_j):
                            continue
                        if not self._check_capacity_feasibility(new_route_j):
                            continue
                        
                        # Calculate new distance
                        new_routes = deepcopy(routes)
                        new_routes[i] = new_route_i
                        new_routes[j] = new_route_j
                        new_distance = self._calculate_total_distance(new_routes)
                        
                        if new_distance < best_distance:
                            best_routes = new_routes
                            best_distance = new_distance
        
        return best_routes
    
    def _swap_move(self, routes):
        """Try to swap two customers between routes"""
        best_routes = deepcopy(routes)
        best_distance = self._calculate_total_distance(best_routes)
        
        for i in range(len(routes)):
            for j in range(i + 1, len(routes)):
                if not routes[i] or not routes[j]:
                    continue
                
                # Try swapping each pair of customers
                for idx_i, cust_i in enumerate(routes[i]):
                    for idx_j, cust_j in enumerate(routes[j]):
                        new_route_i = routes[i][:idx_i] + [cust_j] + routes[i][idx_i+1:]
                        new_route_j = routes[j][:idx_j] + [cust_i] + routes[j][idx_j+1:]
                        
                        # Check feasibility
                        if not self._check_time_window_feasibility(new_route_i):
                            continue
                        if not self._check_time_window_feasibility(new_route_j):
                            continue
                        if not self._check_capacity_feasibility(new_route_i):
                            continue
                        if not self._check_capacity_feasibility(new_route_j):
                            continue
                        
                        # Calculate distance
                        new_routes = deepcopy(routes)
                        new_routes[i] = new_route_i
                        new_routes[j] = new_route_j
                        new_distance = self._calculate_total_distance(new_routes)
                        
                        if new_distance < best_distance:
                            best_routes = new_routes
                            best_distance = new_distance
        
        return best_routes
    
    def _improve_solution(self, initial_routes, verbose=True):
        """Improve solution using local search operators"""
        if not self.improvement_iterations:
            return initial_routes
        
        if verbose:
            print(f"\n🔧 PHASE 2: SOLUTION IMPROVEMENT")
            print("-" * 80)
            print(f"   Max Iterations: {self.improvement_iterations}")
            print(f"   Time Limit: {self.improvement_time_limit}s")
        
        start_time = time.time()
        
        current_routes = deepcopy(initial_routes)
        best_routes = deepcopy(current_routes)
        best_distance = self._calculate_total_distance(best_routes)
        
        initial_distance = best_distance
        
        improvement_count = 0
        
        for iteration in range(self.improvement_iterations):
            # Check time limit
            if time.time() - start_time > self.improvement_time_limit:
                if verbose:
                    print(f"\n   ⏱️  Time limit reached")
                break
            
            # Apply operators randomly
            operator = random.choice(['2opt', 'relocate', 'swap'])
            
            if operator == '2opt':
                # Apply 2-opt to each route
                new_routes = []
                for route in current_routes:
                    new_routes.append(self._two_opt_single_route(route))
            elif operator == 'relocate':
                new_routes = self._relocate_move(current_routes)
            else:  # swap
                new_routes = self._swap_move(current_routes)
            
            new_distance = self._calculate_total_distance(new_routes)
            
            # Accept if better
            if new_distance < best_distance:
                best_routes = deepcopy(new_routes)
                best_distance = new_distance
                current_routes = deepcopy(new_routes)
                improvement_count += 1
                
                if verbose and improvement_count % 5 == 0:
                    improvement_pct = (initial_distance - best_distance) / initial_distance * 100
                    print(f"   ✓ Improvement #{improvement_count}: {best_distance:.2f} ({improvement_pct:.2f}% better)")
            
            # Progress
            if verbose and (iteration + 1) % 200 == 0:
                elapsed = time.time() - start_time
                print(f"   📊 Iteration {iteration+1}/{self.improvement_iterations} ({elapsed:.1f}s)")
        
        elapsed_time = time.time() - start_time
        improvement_pct = (initial_distance - best_distance) / initial_distance * 100
        
        if verbose:
            print(f"\n✅ Improvement phase completed")
            print(f"   ⏱️  Time: {elapsed_time:.2f}s")
            print(f"   📈 Total Improvements: {improvement_count}")
            print(f"   📏 Distance: {initial_distance:.2f} → {best_distance:.2f}")
            print(f"   💹 Improvement: {improvement_pct:.2f}%")
        
        return best_routes
    
    def solve(self, verbose=True):
        """Solve VRPTW using hybrid approach"""
        start_time = time.time()
        
        if verbose:
            print("=" * 80)
            print(f"SIMPLIFIED HYBRID VRPTW SOLVER - Mode: {self.mode.upper()}")
            print(f"Dataset: {self.dataset_name}")
            print("=" * 80)
        
        # Phase 1: Clarke-Wright
        if verbose:
            print("\n📊 PHASE 1: CLARKE-WRIGHT INITIALIZATION")
            print("-" * 80)
        
        # Suppress CW output nếu không verbose
        import sys
        import io
        old_stdout = None
        
        try:
            if not verbose:
                old_stdout = sys.stdout
                sys.stdout = io.StringIO()
            
            phase1_start = time.time()
            cw_result = self.cw_solver.solve()
            phase1_time = time.time() - phase1_start
            
        finally:
            # Khôi phục stdout
            if old_stdout is not None:
                sys.stdout = old_stdout
        
        # Convert CW solution format
        if cw_result and 'routes' in cw_result:
            # Chuyển đổi từ CW format sang format chuẩn
            cw_routes = []
            for route_info in cw_result['routes'].values():
                cw_routes.append(route_info['route'])
            
            cw_distance = cw_result['objective']
            cw_num_vehicles = len(cw_result['routes'])
            cw_status = cw_result['status']
            
            # Tạo solution format chuẩn
            self.cw_solution = {
                'routes': cw_routes,
                'total_distance': cw_distance,
                'num_vehicles': cw_num_vehicles,
                'customers_served': sum(len(r) for r in cw_routes),
                'status': 'Success' if 'Feasible' in cw_status or 'Optimal' in cw_status else cw_status
            }
        else:
            # Nếu CW không trả về kết quả hợp lệ
            self.cw_solution = {
                'routes': [],
                'total_distance': 0,
                'num_vehicles': 0,
                'customers_served': 0,
                'status': 'Failed'
            }
        
        if verbose:
            if self.cw_solution['status'] == 'Success':
                print(f"✅ Clarke-Wright completed")
                print(f"   ⏱️  Time: {phase1_time:.2f}s")
                print(f"   📏 Distance: {self.cw_solution['total_distance']:.2f}")
                print(f"   🚗 Vehicles: {self.cw_solution['num_vehicles']}")
            else:
                print(f"❌ Clarke-Wright failed")
        
        if self.cw_solution['status'] != 'Success':
            return self.cw_solution
        
        # Phase 2: Improvement
        if self.mode != 'cw_only':
            initial_routes = self.cw_solution['routes']
            improved_routes = self._improve_solution(initial_routes, verbose=verbose)
            
            # Remove empty routes
            improved_routes = [r for r in improved_routes if r]
            
            # Build final solution
            final_distance = self._calculate_total_distance(improved_routes)
            
            self.final_solution = {
                'routes': improved_routes,
                'num_vehicles': len(improved_routes),
                'total_distance': final_distance,
                'customers_served': sum(len(r) for r in improved_routes),
                'status': 'Success',
                'mode': self.mode
            }
            
            self.improvement_percentage = (self.cw_solution['total_distance'] - final_distance) / self.cw_solution['total_distance'] * 100
        else:
            self.final_solution = self.cw_solution
        
        self.solve_time = time.time() - start_time
        
        if verbose:
            print("\n" + "=" * 80)
            print(f"🎉 HYBRID SOLVER COMPLETED")
            print(f"   ⏱️  Total Time: {self.solve_time:.2f}s")
            print(f"   📏 Final Distance: {self.final_solution['total_distance']:.2f}")
            print(f"   🚗 Final Vehicles: {self.final_solution['num_vehicles']}")
            if self.mode != 'cw_only':
                print(f"   📈 Improvement: {self.improvement_percentage:.2f}%")
            print("=" * 80)
        
        return self.final_solution
    
    def visualize_solution(self, save_path=None, show_plot=False):
        """
        Visualize solution với GridSpec 2x3 giống y chang MILP
        
        Args:
            save_path: Đường dẫn để lưu hình ảnh (nếu None thì không lưu)
            show_plot: Có hiển thị plot không (default False)
        """
        if not self.final_solution or not self.final_solution.get('routes'):
            print("❌ Chưa có solution để visualize")
            return
        
        plt.ioff()  # Tắt interactive mode
        
        # Tạo figure với GridSpec 2x3 giống MILP
        fig = plt.figure(figsize=(20, 12))
        gs = fig.add_gridspec(2, 3, hspace=0.3, wspace=0.3)
        
        # Subplot 1: Các tuyến đường (chiếm 2 hàng x 2 cột bên trái) gs[0:2, 0:2]
        ax1 = fig.add_subplot(gs[0:2, 0:2])
        self._plot_routes_map(ax1)
        
        # Subplot 2: Thống kê các xe (hàng 0, cột 2) gs[0, 2]
        ax2 = fig.add_subplot(gs[0, 2])
        self._plot_vehicle_stats(ax2)
        
        # Subplot 3: Phân bố khách hàng (hàng 1, cột 2) gs[1, 2]
        ax3 = fig.add_subplot(gs[1, 2])
        self._plot_customer_distribution(ax3)
        
        # Tiêu đề chính
        total_distance = self.final_solution['total_distance']
        num_vehicles = self.final_solution['num_vehicles']
        customers_served = self.final_solution['customers_served']
        
        fig.suptitle(
            f'KẾT QUẢ GIẢI THUẬT HYBRID CW + LOCAL SEARCH - {self.dataset_name}\n'
            f'Số xe: {num_vehicles} | Tổng quãng đường: {total_distance:.2f} | '
            f'Khách hàng phục vụ: {customers_served}/{self.n_customers}',
            fontsize=16, fontweight='bold', y=0.98
        )
        
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        
        # Lưu hình
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"✅ Đã lưu visualization: {save_path}")
        
        if show_plot:
            plt.show()
        else:
            plt.close(fig)
    
    def _plot_routes_map(self, ax):
        """Vẽ bản đồ các tuyến đường giống y chang MILP"""
        routes = self.final_solution['routes']
        
        # Vẽ depot giống MILP
        ax.scatter(self.depot['XCOORD.'], self.depot['YCOORD.'],
                   c='red', s=600, marker='s', edgecolors='black',
                   linewidth=3, label='Kho', zorder=5)
        
        # Vẽ customers giống MILP
        ax.scatter(self.customers['XCOORD.'], self.customers['YCOORD.'],
                   c='lightblue', s=200, edgecolors='black',
                   linewidth=1.5, label='Khách hàng', zorder=3)
        
        # Vẽ các routes với màu khác nhau giống MILP
        colors = plt.cm.tab20(np.linspace(0, 1, len(routes)))
        
        for idx, route in enumerate(routes):
            if not route:
                continue
                
            full_route = [0] + route + [0]  # [0, customer1, customer2, ..., 0]
            color = colors[idx]
            
            # Vẽ đường đi
            for i in range(len(full_route) - 1):
                node1, node2 = full_route[i], full_route[i+1]
                
                if node1 == 0:
                    x1, y1 = self.depot['XCOORD.'], self.depot['YCOORD.']
                else:
                    x1, y1 = self.customers.loc[node1-1, 'XCOORD.'], self.customers.loc[node1-1, 'YCOORD.']
                
                if node2 == 0:
                    x2, y2 = self.depot['XCOORD.'], self.depot['YCOORD.']
                else:
                    x2, y2 = self.customers.loc[node2-1, 'XCOORD.'], self.customers.loc[node2-1, 'YCOORD.']
                
                ax.plot([x1, x2], [y1, y2], color=color, linewidth=2.5, alpha=0.7, zorder=2)
                
                # Vẽ mũi tên giống MILP
                dx, dy = x2 - x1, y2 - y1
                ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                            arrowprops=dict(arrowstyle='->', color=color, lw=2, alpha=0.7))
            
            # Label cho route giống MILP
            if len(route) > 0:
                mid_idx = len(route) // 2
                mid_customer = route[mid_idx]
                mid_x = self.customers.loc[mid_customer-1, 'XCOORD.']
                mid_y = self.customers.loc[mid_customer-1, 'YCOORD.']
                ax.text(mid_x, mid_y + 5, f"Xe {idx+1}", fontsize=11, fontweight='bold',
                        ha='center', bbox=dict(boxstyle='round,pad=0.4', facecolor=color, alpha=0.8))
        
        # Thêm số thứ tự khách hàng giống MILP
        for idx, row in self.customers.iterrows():
            ax.annotate(str(idx + 1), (row['XCOORD.'], row['YCOORD.']),
                        fontsize=9, ha='center', va='center', fontweight='bold')
        
        ax.set_xlabel('Tọa độ X', fontsize=12, fontweight='bold')
        ax.set_ylabel('Tọa độ Y', fontsize=12, fontweight='bold')
        ax.set_title('① Các tuyến đường tối ưu',
                     fontsize=14, fontweight='bold', pad=12)
        ax.legend(fontsize=11, loc='best')
        ax.grid(True, alpha=0.3, linestyle='--')
    
    def _plot_vehicle_stats(self, ax):
        """Vẽ biểu đồ thống kê các xe với 2 trục y giống y chang MILP"""
        routes = self.final_solution['routes']
        vehicles = list(range(len(routes)))
        
        distances = [self._calculate_route_distance(route) for route in routes]
        loads = [sum(self.customers.loc[cust_id - 1, 'DEMAND'] for cust_id in route) 
                for route in routes]
        
        x = np.arange(len(vehicles))
        width = 0.35
        
        # Vẽ cột distance với trục y bên trái (màu steelblue như MILP)
        bars1 = ax.bar(x - width/2, distances, width, label='Quãng đường',
                       color='steelblue', alpha=0.8, edgecolor='black', linewidth=1.5)
        
        # Tạo trục y thứ 2 cho load (màu coral như MILP)
        ax_twin = ax.twinx()
        bars2 = ax_twin.bar(x + width/2, loads, width, label='Tải trọng',
                            color='coral', alpha=0.8, edgecolor='black', linewidth=1.5)
        
        ax.set_xlabel('Xe', fontsize=11, fontweight='bold')
        ax.set_ylabel('Quãng đường', fontsize=11, fontweight='bold', color='steelblue')
        ax_twin.set_ylabel('Tải trọng', fontsize=11, fontweight='bold', color='coral')
        ax.set_title('② Thống kê các xe', fontsize=13, fontweight='bold', pad=10)
        ax.set_xticks(x)
        ax.set_xticklabels([f'Xe {v+1}' for v in vehicles], fontsize=9)
        ax.tick_params(axis='y', labelcolor='steelblue')
        ax_twin.tick_params(axis='y', labelcolor='coral')
        ax.grid(True, alpha=0.3, axis='y', linestyle='--')
        
        # Thêm giá trị trên các cột giống MILP
        for bar in bars1:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}', ha='center', va='bottom', fontsize=8)
        
        for bar in bars2:
            height = bar.get_height()
            ax_twin.text(bar.get_x() + bar.get_width()/2., height,
                         f'{int(height)}', ha='center', va='bottom', fontsize=8)
    
    def _plot_customer_distribution(self, ax):
        """Vẽ biểu đồ phân bố khách hàng giống y chang MILP"""
        routes = self.final_solution['routes']
        vehicles = list(range(len(routes)))
        num_customers_per_vehicle = [len(route) for route in routes]
        
        # Pie chart với màu Set3 giống MILP
        colors_pie = plt.cm.Set3(np.linspace(0, 1, len(vehicles)))
        wedges, texts, autotexts = ax.pie(num_customers_per_vehicle, 
                                            labels=[f'Xe {v+1}' for v in vehicles],
                                            autopct='%1.1f%%',
                                            startangle=90,
                                            colors=colors_pie,
                                            textprops={'fontsize': 10, 'fontweight': 'bold'})
        
        ax.set_title('③ Phân bố số khách hàng', fontsize=13, fontweight='bold', pad=10)
        
        # Thêm legend với thông tin chi tiết giống MILP
        legend_labels = [f'Xe {v+1}: {num_customers_per_vehicle[i]} KH' 
                        for i, v in enumerate(vehicles)]
        ax.legend(legend_labels, loc='upper left', bbox_to_anchor=(1, 1), fontsize=9)
    
    def save_solution_text(self, save_path):
        """
        Lưu solution ra file text chi tiết
        
        Args:
            save_path: Đường dẫn file .txt
        """
        if not self.final_solution:
            print("❌ Chưa có solution để lưu")
            return
        
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write("=" * 100 + "\n")
            f.write(f"HYBRID VRPTW SOLVER - DETAILED SOLUTION REPORT\n")
            f.write("=" * 100 + "\n\n")
            
            # Dataset info
            f.write("DATASET INFORMATION\n")
            f.write("-" * 100 + "\n")
            f.write(f"Dataset Name: {self.dataset_name}\n")
            f.write(f"Number of Customers: {self.n_customers}\n")
            f.write(f"Vehicle Capacity: {self.vehicle_capacity}\n")
            f.write(f"Max Vehicles: {self.max_vehicles}\n\n")
            
            # Solver settings
            f.write("SOLVER SETTINGS\n")
            f.write("-" * 100 + "\n")
            f.write(f"Mode: {self.mode.upper()}\n")
            f.write(f"Improvement Time Limit: {self.improvement_time_limit}s\n")
            f.write(f"Improvement Iterations: {self.improvement_iterations}\n\n")
            
            # Results summary
            f.write("RESULTS SUMMARY\n")
            f.write("-" * 100 + "\n")
            f.write(f"Status: {self.final_solution['status']}\n")
            f.write(f"Total Distance: {self.final_solution['total_distance']:.4f}\n")
            f.write(f"Number of Vehicles: {self.final_solution['num_vehicles']}\n")
            f.write(f"Customers Served: {self.final_solution['customers_served']}/{self.n_customers}\n")
            f.write(f"Total Solve Time: {self.solve_time:.4f} seconds\n")
            
            # CW vs Final
            if self.cw_solution and self.mode != 'cw_only':
                f.write(f"\nClarke-Wright Distance: {self.cw_solution['total_distance']:.4f}\n")
                f.write(f"Clarke-Wright Vehicles: {self.cw_solution['num_vehicles']}\n")
                f.write(f"Improvement: {self.improvement_percentage:.2f}%\n")
                f.write(f"Distance Reduction: {self.cw_solution['total_distance'] - self.final_solution['total_distance']:.4f}\n")
                f.write(f"Vehicle Reduction: {self.cw_solution['num_vehicles'] - self.final_solution['num_vehicles']}\n")
            
            f.write("\n")
            
            # Detailed routes
            f.write("DETAILED ROUTES\n")
            f.write("=" * 100 + "\n\n")
            
            for idx, route in enumerate(self.final_solution['routes']):
                f.write(f"Route {idx + 1}:\n")
                f.write("-" * 100 + "\n")
                
                # Route path
                route_str = "0 → " + " → ".join(map(str, route)) + " → 0"
                f.write(f"Path: {route_str}\n")
                
                # Route metrics
                route_distance = self._calculate_route_distance(route)
                route_load = sum(self.customers.loc[cust_id - 1, 'DEMAND'] for cust_id in route)
                
                f.write(f"Number of Customers: {len(route)}\n")
                f.write(f"Total Distance: {route_distance:.4f}\n")
                f.write(f"Total Load: {route_load}/{self.vehicle_capacity}\n")
                
                # Customer details
                f.write(f"\nCustomer Details:\n")
                f.write(f"  {'Cust':<6} {'X':<8} {'Y':<8} {'Demand':<8} {'Ready':<8} {'Due':<8} {'Service':<8}\n")
                
                for cust_id in route:
                    cust = self.customers.loc[cust_id - 1]
                    f.write(f"  {cust_id:<6} "
                           f"{cust['XCOORD.']:<8.2f} "
                           f"{cust['YCOORD.']:<8.2f} "
                           f"{cust['DEMAND']:<8} "
                           f"{cust['READY TIME']:<8} "
                           f"{cust['DUE DATE']:<8} "
                           f"{cust['SERVICE TIME']:<8}\n")
                
                f.write("\n")
            
            f.write("=" * 100 + "\n")
            f.write("END OF REPORT\n")
            f.write("=" * 100 + "\n")
        
        print(f"✅ Đã lưu detailed report: {save_path}")
    
    def save_all_results(self, output_dir):
        """
        Lưu tất cả kết quả: hình ảnh, text report, và return dict để lưu CSV
        
        Args:
            output_dir: Thư mục để lưu kết quả
            
        Returns:
            dict: Summary data để ghi vào CSV
        """
        from pathlib import Path
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Tạo các thư mục con
        images_dir = output_path / 'images'
        text_dir = output_path / 'text'
        images_dir.mkdir(exist_ok=True)
        text_dir.mkdir(exist_ok=True)
        
        # Lưu visualization
        image_path = images_dir / f"{self.dataset_name}_{self.mode}.png"
        self.visualize_solution(save_path=str(image_path), show_plot=False)
        
        # Lưu text report
        text_path = text_dir / f"{self.dataset_name}_{self.mode}.txt"
        self.save_solution_text(save_path=str(text_path))
        
        # Tạo summary data cho CSV
        summary_data = {
            'Dataset': self.dataset_name,
            'Mode': self.mode,
            'Status': self.final_solution['status'],
            'Total_Distance': round(self.final_solution['total_distance'], 4),
            'Num_Vehicles': self.final_solution['num_vehicles'],
            'Customers_Served': self.final_solution['customers_served'],
            'Solve_Time_s': round(self.solve_time, 4),
        }
        
        # Thêm thông tin CW và improvement nếu có
        if self.cw_solution and self.mode != 'cw_only':
            summary_data['CW_Distance'] = round(self.cw_solution['total_distance'], 4)
            summary_data['CW_Vehicles'] = self.cw_solution['num_vehicles']
            summary_data['Improvement_Percent'] = round(self.improvement_percentage, 2)
            summary_data['Distance_Reduction'] = round(
                self.cw_solution['total_distance'] - self.final_solution['total_distance'], 4
            )
            summary_data['Vehicle_Reduction'] = (
                self.cw_solution['num_vehicles'] - self.final_solution['num_vehicles']
            )
        else:
            summary_data['CW_Distance'] = None
            summary_data['CW_Vehicles'] = None
            summary_data['Improvement_Percent'] = 0.0
            summary_data['Distance_Reduction'] = 0.0
            summary_data['Vehicle_Reduction'] = 0
        
        return summary_data


def main():
    """Test simplified hybrid solver"""
    dataset_path = r"d:\My Studing\Nghiệp vụ thông minh\project\Vehicle Routing Problem\code\dataset\C1\C101.csv"
    
    modes = ['cw_only', 'fast', 'balanced', 'quality']
    
    print("Testing Simplified Hybrid VRPTW Solver\n")
    
    results = []
    
    for mode in modes:
        print("\n" + "="*100)
        print(f"Testing mode: {mode.upper()}")
        print("="*100)
        
        solver = SimplifiedHybridVRPTWSolver(
            dataset_path=dataset_path,
            mode=mode
        )
        
        solution = solver.solve(verbose=True)
        
        results.append({
            'mode': mode,
            'distance': solution['total_distance'],
            'vehicles': solution['num_vehicles'],
            'time': solver.solve_time,
            'improvement': solver.improvement_percentage if mode != 'cw_only' else 0
        })
    
    # Summary
    print("\n" + "="*100)
    print("SUMMARY - COMPARISON OF MODES")
    print("="*100)
    print(f"{'Mode':<15} {'Distance':<15} {'Vehicles':<12} {'Time (s)':<12} {'Improvement %':<15}")
    print("-"*100)
    for r in results:
        print(f"{r['mode']:<15} {r['distance']:<15.2f} {r['vehicles']:<12} {r['time']:<12.2f} {r['improvement']:<15.2f}")
    
    print("\n" + "="*100)
    print("RECOMMENDATION:")
    print("- CW Only: Fastest (< 1s) but basic quality")
    print("- Fast: Good balance for real-time needs (10-15s)")
    print("- Balanced: RECOMMENDED - Best overall (20-25s) ⭐")
    print("- Quality: Best results when time allows (40-50s)")
    print("="*100)


if __name__ == "__main__":
    main()
