"""
VRPTW Solver using Constraint Programming (CP)
Giải bài toán VRP với cửa sổ thời gian bằng Lập trình ràng buộc

Sử dụng thư viện OR-Tools của Google
"""

import pandas as pd
import numpy as np
import time
from pathlib import Path
import matplotlib.pyplot as plt
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp


class CPVRPTWSolver:
    """
    Class giải bài toán VRPTW bằng phương pháp Constraint Programming
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
        
        # OR-Tools data model
        self.data_model = None
        self.manager = None
        self.routing = None
        self.solution = None
        
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
    
    def build_model(self):
        """
        Xây dựng mô hình CP cho bài toán VRPTW
        """
        print(f"\n{'='*80}")
        print(f"XÂY DỰNG MÔ HÌNH CP CHO DATASET: {self.dataset_name}")
        print(f"{'='*80}")
        print(f"Số khách hàng: {self.n_customers}")
        print(f"Số xe tối đa: {self.max_vehicles}")
        print(f"Sức chứa xe: {self.vehicle_capacity}")
        print(f"{'='*80}\n")
        
        # Chuẩn bị data model cho OR-Tools
        self.data_model = {}
        
        # Distance matrix (chuyển sang int để OR-Tools xử lý nhanh hơn)
        self.data_model['distance_matrix'] = (self.distance_matrix * 100).astype(int).tolist()
        self.data_model['time_matrix'] = (self.time_matrix * 100).astype(int).tolist()
        
        # Demands (bao gồm depot có demand = 0)
        demands = [0] + self.customers['DEMAND'].tolist()
        self.data_model['demands'] = demands
        
        # Time windows (bao gồm depot)
        time_windows = [(0, 999999)]  # Depot không có giới hạn thời gian
        for idx in range(len(self.customers)):
            ready = int(self.customers.loc[idx, 'READY TIME'])
            due = int(self.customers.loc[idx, 'DUE DATE'])
            time_windows.append((ready, due))
        self.data_model['time_windows'] = time_windows
        
        # Service times
        service_times = [0] + self.customers['SERVICE TIME'].astype(int).tolist()
        self.data_model['service_times'] = service_times
        
        # Vehicle info
        self.data_model['vehicle_capacities'] = [self.vehicle_capacity] * self.max_vehicles
        self.data_model['num_vehicles'] = self.max_vehicles
        self.data_model['depot'] = 0
        
        # Tạo routing index manager
        self.manager = pywrapcp.RoutingIndexManager(
            len(self.data_model['distance_matrix']),
            self.data_model['num_vehicles'],
            self.data_model['depot']
        )
        
        # Tạo routing model
        self.routing = pywrapcp.RoutingModel(self.manager)
        
        print("Thiết lập ràng buộc...")
        
        # ==================== DISTANCE CALLBACK ====================
        def distance_callback(from_index, to_index):
            """Trả về khoảng cách giữa 2 nodes"""
            from_node = self.manager.IndexToNode(from_index)
            to_node = self.manager.IndexToNode(to_index)
            return self.data_model['distance_matrix'][from_node][to_node]
        
        transit_callback_index = self.routing.RegisterTransitCallback(distance_callback)
        
        # Thiết lập hàm mục tiêu: minimize tổng quãng đường
        self.routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
        
        # ==================== CAPACITY CONSTRAINT ====================
        print("  - Ràng buộc: Sức chứa xe")
        def demand_callback(from_index):
            """Trả về demand của node"""
            from_node = self.manager.IndexToNode(from_index)
            return self.data_model['demands'][from_node]
        
        demand_callback_index = self.routing.RegisterUnaryTransitCallback(demand_callback)
        
        self.routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,  # null capacity slack
            self.data_model['vehicle_capacities'],  # vehicle maximum capacities
            True,  # start cumul to zero
            'Capacity'
        )
        
        # ==================== TIME WINDOW CONSTRAINT ====================
        print("  - Ràng buộc: Cửa sổ thời gian")
        def time_callback(from_index, to_index):
            """Trả về thời gian di chuyển + service time"""
            from_node = self.manager.IndexToNode(from_index)
            to_node = self.manager.IndexToNode(to_index)
            travel_time = self.data_model['time_matrix'][from_node][to_node]
            service_time = self.data_model['service_times'][from_node]
            return travel_time + service_time
        
        time_callback_index = self.routing.RegisterTransitCallback(time_callback)
        
        # Tạo time dimension
        horizon = 999999  # Giới hạn thời gian tối đa
        self.routing.AddDimension(
            time_callback_index,
            horizon,  # allow waiting time
            horizon,  # maximum time per vehicle
            False,  # Don't force start cumul to zero
            'Time'
        )
        
        time_dimension = self.routing.GetDimensionOrDie('Time')
        
        # Thêm time window constraints cho từng location
        for location_idx, time_window in enumerate(self.data_model['time_windows']):
            if location_idx == self.data_model['depot']:
                continue
            index = self.manager.NodeToIndex(location_idx)
            time_dimension.CumulVar(index).SetRange(time_window[0], time_window[1])
        
        # Thêm time window cho depot (start time)
        depot_idx = self.data_model['depot']
        for vehicle_id in range(self.data_model['num_vehicles']):
            index = self.routing.Start(vehicle_id)
            time_dimension.CumulVar(index).SetRange(
                self.data_model['time_windows'][depot_idx][0],
                self.data_model['time_windows'][depot_idx][1]
            )
        
        # Minimize thời gian của xe cuối cùng về depot
        for vehicle_id in range(self.data_model['num_vehicles']):
            self.routing.AddVariableMinimizedByFinalizer(
                time_dimension.CumulVar(self.routing.Start(vehicle_id))
            )
            self.routing.AddVariableMinimizedByFinalizer(
                time_dimension.CumulVar(self.routing.End(vehicle_id))
            )
        
        print("\n✓ Hoàn thành xây dựng mô hình CP!")
        print(f"  - Nodes: {self.manager.GetNumberOfNodes()}")
        print(f"  - Vehicles: {self.manager.GetNumberOfVehicles()}")
    
    def solve(self, time_limit=60):
        """
        Giải bài toán CP
        
        Args:
            time_limit: Giới hạn thời gian giải (giây) - Mặc định 1 phút
        """
        if self.routing is None:
            print("❌ Chưa xây dựng model! Hãy gọi build_model() trước.")
            return None
        
        print(f"\n{'='*80}")
        print(f"BẮT ĐẦU GIẢI BÀI TOÁN CP")
        print(f"{'='*80}")
        print(f"Giới hạn thời gian: {time_limit} giây")
        print("Đang giải...")
        
        # Thiết lập search parameters
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.seconds = time_limit
        search_parameters.log_search = True
        
        start_time = time.time()
        
        # Giải bài toán
        solution = self.routing.SolveWithParameters(search_parameters)
        
        solve_time = time.time() - start_time
        
        print(f"\n{'='*80}")
        print(f"KẾT QUẢ GIẢI")
        print(f"{'='*80}")
        print(f"Thời gian giải: {solve_time:.2f} giây")
        
        if solution:
            obj_value = solution.ObjectiveValue() / 100.0  # Chia 100 vì đã nhân lên khi tạo matrix
            print(f"Trạng thái: Optimal/Feasible")
            print(f"Tổng quãng đường: {obj_value:.2f}")
            
            # Trích xuất solution
            self._extract_solution(solution)
            
            return {
                'status': 'Optimal/Feasible',
                'objective': obj_value,
                'time': solve_time,
                'routes': self.solution
            }
        else:
            print("❌ Không tìm được nghiệm khả thi!")
            return None
    
    def _extract_solution(self, solution):
        """Trích xuất nghiệm từ OR-Tools solution"""
        routes = {}
        route_id = 0
        
        time_dimension = self.routing.GetDimensionOrDie('Time')
        
        for vehicle_id in range(self.data_model['num_vehicles']):
            route = []
            route_distance = 0
            route_load = 0
            
            index = self.routing.Start(vehicle_id)
            
            while not self.routing.IsEnd(index):
                node_index = self.manager.IndexToNode(index)
                
                if node_index != 0:  # Không tính depot
                    route.append(node_index)
                    route_load += self.data_model['demands'][node_index]
                
                previous_index = index
                index = solution.Value(self.routing.NextVar(index))
                route_distance += self.routing.GetArcCostForVehicle(
                    previous_index, index, vehicle_id
                )
            
            if len(route) > 0:
                distance = route_distance / 100.0  # Chia 100 vì đã nhân lên
                
                routes[route_id] = {
                    'route': route,
                    'distance': distance,
                    'load': route_load,
                    'num_customers': len(route)
                }
                route_id += 1
        
        self.solution = routes
        
        # In thông tin routes
        print(f"\n{'='*80}")
        print(f"CHI TIẾT CÁC TUYẾN ĐƯỜNG")
        print(f"{'='*80}")
        print(f"Số xe sử dụng: {len(routes)}")
        
        for route_id, info in routes.items():
            print(f"\nXe {route_id + 1}:")
            print(f"  Tuyến đường: 0 → {' → '.join(map(str, info['route']))} → 0")
            print(f"  Số khách hàng: {info['num_customers']}")
            print(f"  Tổng nhu cầu: {info['load']}/{self.vehicle_capacity}")
            print(f"  Quãng đường: {info['distance']:.2f}")
    
    def visualize_solution_comprehensive(self, save=False):
        """
        Vẽ biểu đồ tổng hợp với nhiều sub-plots
        Bao gồm: Routes, Thống kê xe, Phân bố demand
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
        ax1.scatter(self.depot['XCOORD.'], self.depot['YCOORD.'],
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
                    x1, y1 = self.depot['XCOORD.'], self.depot['YCOORD.']
                else:
                    x1, y1 = self.customers.loc[node1-1, 'XCOORD.'], self.customers.loc[node1-1, 'YCOORD.']
                
                if node2 == 0:
                    x2, y2 = self.depot['XCOORD.'], self.depot['YCOORD.']
                else:
                    x2, y2 = self.customers.loc[node2-1, 'XCOORD.'], self.customers.loc[node2-1, 'YCOORD.']
                
                ax1.plot([x1, x2], [y1, y2], color=color, linewidth=2.5, alpha=0.7, zorder=2)
                
                # Vẽ mũi tên
                dx, dy = x2 - x1, y2 - y1
                ax1.annotate('', xy=(x2, y2), xytext=(x1, y1),
                            arrowprops=dict(arrowstyle='->', color=color, lw=2, alpha=0.7))
            
            # Label cho route
            mid_idx = len(info['route']) // 2
            mid_customer = info['route'][mid_idx]
            mid_x = self.customers.loc[mid_customer-1, 'XCOORD.']
            mid_y = self.customers.loc[mid_customer-1, 'YCOORD.']
            ax1.text(mid_x, mid_y + 5, f"Xe {route_id+1}", fontsize=11, fontweight='bold',
                    ha='center', bbox=dict(boxstyle='round,pad=0.4', facecolor=color, alpha=0.8))
        
        # Thêm số thứ tự khách hàng
        for idx, row in self.customers.iterrows():
            ax1.annotate(str(idx + 1), (row['XCOORD.'], row['YCOORD.']),
                        fontsize=9, ha='center', va='center', fontweight='bold')
        
        ax1.set_xlabel('Tọa độ X', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Tọa độ Y', fontsize=12, fontweight='bold')
        ax1.set_title('① Các tuyến đường tối ưu',
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
        
        # ============= 3. PHÂN BỐ DEMAND TRÊN CÁC XE =============
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
            f'KẾT QUẢ GIẢI THUẬT CP - {self.dataset_name}\n'
            f'Số xe: {len(self.solution)} | Tổng quãng đường: {total_distance:.2f} | '
            f'Khách hàng phục vụ: {total_customers}/{self.n_customers}',
            fontsize=16, fontweight='bold', y=0.98
        )
        
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        
        if save:
            output_dir = Path(__file__).parent / 'result' / 'images'
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f'{self.dataset_name}_cp_solution.png'
            plt.savefig(str(output_path), dpi=300, bbox_inches='tight')
            print(f"✓ Đã lưu hình ảnh: {output_path}")
        
        plt.close(fig)  # Đóng figure để giải phóng bộ nhớ
    
    def visualize_solution(self, save=False):
        """Wrapper để tương thích - gọi comprehensive visualization"""
        self.visualize_solution_comprehensive(save)
    
    def save_solution(self, solve_time=None, status=None):
        """Lưu solution ra file TXT chi tiết"""
        if self.solution is None:
            print("❌ Chưa có solution để lưu!")
            return
        
        output_dir = Path(__file__).parent / 'result' / 'text'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f'{self.dataset_name}_cp_solution.txt'
        
        total_distance = sum([r['distance'] for r in self.solution.values()])
        total_load = sum([r['load'] for r in self.solution.values()])
        total_customers_served = sum([r['num_customers'] for r in self.solution.values()])
        
        with open(str(output_path), 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write(f"BÁO CÁO KẾT QUẢ GIẢI THUẬT CP\n")
            f.write(f"Constraint Programming for VRPTW\n")
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
                f.write(f"  {'-'*70}\n")
                
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
    """Hàm chính để chạy CP solver"""
    
    # Đường dẫn đến dataset
    current_dir = Path(__file__).parent
    code_dir = current_dir.parent.parent
    dataset_path = code_dir / "dataset" / "C1" / "C101.csv"
    
    print("="*80)
    print("CP SOLVER FOR VRPTW - Constraint Programming")
    print("="*80)
    print("✓ CP có thể giải toàn bộ dataset (100+ khách hàng)")
    print("✓ Sử dụng Google OR-Tools")
    print("="*80)
    
    # Tạo solver
    solver = CPVRPTWSolver(
        dataset_path=str(dataset_path),
        vehicle_capacity=200,
        max_vehicles=25
    )
    
    # Xây dựng model
    solver.build_model()
    
    # Giải bài toán (giới hạn 1 phút = 60 giây)
    result = solver.solve(time_limit=60)
    
    if result:
        # Vẽ và lưu solution
        print("\n" + "="*80)
        print("TẠO TRỰC QUAN HÓA VÀ BÁO CÁO")
        print("="*80)
        solver.visualize_solution(save=True)
        solver.save_solution(solve_time=result['time'], status=result['status'])
        print("✓ Đã tạo file PNG và TXT trong thư mục 'result/'")
    else:
        print("\n❌ Không thể tạo solution!")
    
    print("\n" + "="*80)
    print("HOÀN THÀNH!")
    print("="*80)


if __name__ == "__main__":
    main()
