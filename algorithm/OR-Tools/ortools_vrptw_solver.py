"""
VRPTW Solver using OR-Tools (Google Optimization Tools)
Giải bài toán VRP với cửa sổ thời gian bằng OR-Tools

OR-Tools là một solver optimization mạnh mẽ từ Google,
có sẵn Routing solver chuyên dụng cho VRP.
"""

import pandas as pd
import numpy as np
import time
from pathlib import Path
import matplotlib.pyplot as plt
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp


class ORToolsVRPTWSolver:
    """
    Solver VRPTW sử dụng OR-Tools Routing
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
        self.n_customers = len(self.customers)
        
        # Tính ma trận khoảng cách
        self.distance_matrix = self._calculate_distance_matrix()
        self.time_matrix = self.distance_matrix.copy()
        
        # Solution
        self.solution = None
        self.solve_time = 0
        
    def _calculate_distance_matrix(self):
        """Tính ma trận khoảng cách Euclidean (scaled to int)"""
        n = self.n_customers + 1
        dist_matrix = []
        
        all_points = pd.concat([self.depot.to_frame().T, self.customers]).reset_index(drop=True)
        
        for i in range(n):
            row = []
            for j in range(n):
                x1, y1 = all_points.loc[i, 'XCOORD.'], all_points.loc[i, 'YCOORD.']
                x2, y2 = all_points.loc[j, 'XCOORD.'], all_points.loc[j, 'YCOORD.']
                dist = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                row.append(int(round(dist * 100)))  # Scale by 100 for precision
            dist_matrix.append(row)
        
        return dist_matrix
    
    def solve(self, time_limit=30):
        """
        Giải bài toán bằng OR-Tools
        
        Args:
            time_limit: Giới hạn thời gian (giây)
            
        Returns:
            dict: Solution info
        """
        print(f"\n{'='*100}")
        print(f"OR-TOOLS VRPTW SOLVER - {self.dataset_name}")
        print(f"{'='*100}")
        print(f"Số khách hàng: {self.n_customers}")
        print(f"Số xe tối đa: {self.max_vehicles}")
        print(f"Sức chứa xe: {self.vehicle_capacity}")
        print(f"Giới hạn thời gian: {time_limit}s")
        print(f"{'='*100}\n")
        
        start_time = time.time()
        
        # Tạo data model
        data = self._create_data_model()
        
        # Tạo routing model
        manager = pywrapcp.RoutingIndexManager(
            len(data['distance_matrix']),
            data['num_vehicles'],
            data['depot']
        )
        routing = pywrapcp.RoutingModel(manager)
        
        # Tạo distance callback
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return data['distance_matrix'][from_node][to_node]
        
        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
        
        # Thêm capacity constraint
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
        
        # Thêm time window constraints
        def time_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return data['time_matrix'][from_node][to_node] + data['service_times'][from_node]
        
        time_callback_index = routing.RegisterTransitCallback(time_callback)
        routing.AddDimension(
            time_callback_index,
            int(1e6),  # allow waiting time
            int(1e6),  # maximum time per vehicle
            False,  # don't force start cumul to zero
            'Time'
        )
        
        time_dimension = routing.GetDimensionOrDie('Time')
        
        # Add time window constraints for each location
        for location_idx, time_window in enumerate(data['time_windows']):
            if location_idx == data['depot']:
                continue
            index = manager.NodeToIndex(location_idx)
            time_dimension.CumulVar(index).SetRange(time_window[0], time_window[1])
        
        # Add time window constraints for depots
        depot_idx = data['depot']
        for vehicle_id in range(data['num_vehicles']):
            index = routing.Start(vehicle_id)
            time_dimension.CumulVar(index).SetRange(
                data['time_windows'][depot_idx][0],
                data['time_windows'][depot_idx][1]
            )
        
        # Instantiate route start and end times to produce feasible times
        for i in range(data['num_vehicles']):
            routing.AddVariableMinimizedByFinalizer(
                time_dimension.CumulVar(routing.Start(i))
            )
            routing.AddVariableMinimizedByFinalizer(
                time_dimension.CumulVar(routing.End(i))
            )
        
        # Setting search parameters
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.FromSeconds(time_limit)
        
        # Solve
        print("Đang giải bài toán...")
        solution = routing.SolveWithParameters(search_parameters)
        
        self.solve_time = time.time() - start_time
        
        if solution:
            self.solution = self._extract_solution(data, manager, routing, solution)
            
            if self.solution:
                print(f"\n{'='*100}")
                print(f"KẾT QUẢ GIẢI THUẬT OR-TOOLS")
                print(f"{'='*100}")
                print(f"Trạng thái: Feasible")
                print(f"Số xe sử dụng: {self.solution['num_vehicles']}")
                print(f"Tổng quãng đường: {self.solution['total_distance']:.2f}")
                print(f"Khách hàng phục vụ: {self.solution['customers_served']}/{self.n_customers}")
                print(f"Thời gian giải: {self.solve_time:.2f}s")
                print(f"{'='*100}\n")
                
                return self.solution
            else:
                print(f"\n⚠️ Không thể extract solution!")
                return None
        else:
            print(f"\n⚠️ Không tìm được solution trong {time_limit}s!")
            print(f"   Dataset này có thể cần:")
            print(f"   - Thời gian giải lâu hơn (tăng time_limit)")
            print(f"   - Thêm xe (tăng max_vehicles)")
            print(f"   - Hoặc time windows quá chặt")
            return None
    
    def _create_data_model(self):
        """Tạo data model cho OR-Tools"""
        data = {}
        data['distance_matrix'] = self.distance_matrix
        data['time_matrix'] = self.time_matrix
        data['num_vehicles'] = self.max_vehicles
        data['depot'] = 0
        
        # Demands
        demands = [0]  # depot
        for idx in range(self.n_customers):
            try:
                demand_val = float(self.customers.loc[idx, 'DEMAND'])
                demands.append(int(demand_val))
            except (ValueError, TypeError):
                print(f"⚠️ Warning: Invalid demand at row {idx}, using 0")
                demands.append(0)
        data['demands'] = demands
        
        # Vehicle capacities
        data['vehicle_capacities'] = [self.vehicle_capacity] * self.max_vehicles
        
        # Time windows (scaled by 100)
        time_windows = []
        all_data = pd.concat([self.depot.to_frame().T, self.customers]).reset_index(drop=True)
        for idx in range(len(all_data)):
            try:
                ready = float(all_data.loc[idx, 'READY TIME'])
                due = float(all_data.loc[idx, 'DUE DATE'])
                tw = (int(ready * 100), int(due * 100))
            except (ValueError, TypeError):
                print(f"⚠️ Warning: Invalid time window at row {idx}, using (0, 999999)")
                tw = (0, 999999)
            time_windows.append(tw)
        data['time_windows'] = time_windows
        
        # Service times (scaled by 100)
        service_times = []
        for idx in range(len(all_data)):
            try:
                service = float(all_data.loc[idx, 'SERVICE TIME'])
                service_times.append(int(service * 100))
            except (ValueError, TypeError):
                print(f"⚠️ Warning: Invalid service time at row {idx}, using 0")
                service_times.append(0)
        data['service_times'] = service_times
        
        return data
    
    def _extract_solution(self, data, manager, routing, solution):
        """Trích xuất solution từ OR-Tools"""
        if solution is None:
            return None
        
        routes = []
        
        for vehicle_id in range(data['num_vehicles']):
            index = routing.Start(vehicle_id)
            route = []
            
            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                if node_index != 0:  # Skip depot
                    route.append(node_index)
                index = solution.Value(routing.NextVar(index))
            
            if route:  # Only add non-empty routes
                routes.append(route)
        
        # Calculate total distance (divide by 100 to get actual distance)
        total_distance = solution.ObjectiveValue() / 100.0
        
        return {
            'routes': routes,
            'num_vehicles': len(routes),
            'total_distance': total_distance,
            'customers_served': sum(len(r) for r in routes),
            'status': 'Feasible'
        }
    
    def visualize_solution(self, save_path=None):
        """Vẽ solution giống MILP với 3 subplots"""
        if not self.solution:
            print("❌ Chưa có solution để vẽ!")
            return
        
        plt.ioff()
        
        routes = self.solution['routes']
        
        # Tạo figure với GridSpec 2x3 giống MILP
        fig = plt.figure(figsize=(20, 12))
        gs = fig.add_gridspec(2, 3, hspace=0.3, wspace=0.3)
        
        # Subplot 1: Các tuyến đường
        ax1 = fig.add_subplot(gs[0:2, 0:2])
        self._plot_routes_map(ax1, routes)
        
        # Subplot 2: Thống kê các xe
        ax2 = fig.add_subplot(gs[0, 2])
        self._plot_vehicle_stats(ax2, routes)
        
        # Subplot 3: Phân bố khách hàng
        ax3 = fig.add_subplot(gs[1, 2])
        self._plot_customer_distribution(ax3, routes)
        
        # Tiêu đề chính
        fig.suptitle(
            f'KẾT QUẢ GIẢI THUẬT OR-TOOLS (GOOGLE) - {self.dataset_name}\n'
            f'Số xe: {self.solution["num_vehicles"]} | '
            f'Tổng quãng đường: {self.solution["total_distance"]:.2f} | '
            f'Khách hàng phục vụ: {self.solution["customers_served"]}/{self.n_customers}',
            fontsize=16, fontweight='bold', y=0.98
        )
        
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"✓ Đã lưu hình ảnh: {save_path}")
        
        plt.close(fig)
    
    def _plot_routes_map(self, ax, routes):
        """Vẽ bản đồ các tuyến đường"""
        # Vẽ depot
        ax.scatter(self.depot['XCOORD.'], self.depot['YCOORD.'],
                   c='red', s=600, marker='s', edgecolors='black',
                   linewidth=3, label='Kho', zorder=5)
        
        # Vẽ customers
        ax.scatter(self.customers['XCOORD.'], self.customers['YCOORD.'],
                   c='lightblue', s=200, edgecolors='black',
                   linewidth=1.5, label='Khách hàng', zorder=3)
        
        # Vẽ các routes
        colors = plt.cm.tab20(np.linspace(0, 1, len(routes)))
        
        for idx, route in enumerate(routes):
            if not route:
                continue
            
            full_route = [0] + route + [0]
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
                ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                            arrowprops=dict(arrowstyle='->', color=color, lw=2, alpha=0.7))
            
            # Label route
            if len(route) > 0:
                mid_idx = len(route) // 2
                mid_customer = route[mid_idx]
                mid_x = self.customers.loc[mid_customer-1, 'XCOORD.']
                mid_y = self.customers.loc[mid_customer-1, 'YCOORD.']
                ax.text(mid_x, mid_y + 5, f"Xe {idx+1}", fontsize=11, fontweight='bold',
                        ha='center', bbox=dict(boxstyle='round,pad=0.4', facecolor=color, alpha=0.8))
        
        # Đánh số khách hàng
        for idx, row in self.customers.iterrows():
            ax.annotate(str(idx + 1), (row['XCOORD.'], row['YCOORD.']),
                        fontsize=9, ha='center', va='center', fontweight='bold')
        
        ax.set_xlabel('Tọa độ X', fontsize=12, fontweight='bold')
        ax.set_ylabel('Tọa độ Y', fontsize=12, fontweight='bold')
        ax.set_title('① Các tuyến đường tối ưu', fontsize=14, fontweight='bold', pad=12)
        ax.legend(fontsize=11, loc='best')
        ax.grid(True, alpha=0.3, linestyle='--')
    
    def _calculate_route_distance(self, route):
        """Tính khoảng cách của một route"""
        if not route:
            return 0
        
        distance = 0
        
        # Depot -> first customer
        distance += self.distance_matrix[0][route[0]]
        
        # Between customers
        for i in range(len(route) - 1):
            distance += self.distance_matrix[route[i]][route[i+1]]
        
        # Last customer -> depot
        distance += self.distance_matrix[route[-1]][0]
        
        return distance / 100.0  # Scale back
    
    def _plot_vehicle_stats(self, ax, routes):
        """Vẽ biểu đồ thống kê các xe với 2 trục y"""
        vehicles = list(range(len(routes)))
        
        distances = [self._calculate_route_distance(route) for route in routes]
        loads = [sum(self.customers.loc[i-1, 'DEMAND'] for i in route) for route in routes]
        
        x = np.arange(len(vehicles))
        width = 0.35
        
        bars1 = ax.bar(x - width/2, distances, width, label='Quãng đường',
                       color='steelblue', alpha=0.8, edgecolor='black', linewidth=1.5)
        
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
        
        # Thêm giá trị
        for bar in bars1:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}', ha='center', va='bottom', fontsize=8)
        
        for bar in bars2:
            height = bar.get_height()
            ax_twin.text(bar.get_x() + bar.get_width()/2., height,
                         f'{int(height)}', ha='center', va='bottom', fontsize=8)
    
    def _plot_customer_distribution(self, ax, routes):
        """Vẽ biểu đồ phân bố khách hàng"""
        vehicles = list(range(len(routes)))
        num_customers_per_vehicle = [len(route) for route in routes]
        
        colors_pie = plt.cm.Set3(np.linspace(0, 1, len(vehicles)))
        wedges, texts, autotexts = ax.pie(
            num_customers_per_vehicle,
            labels=[f'Xe {v+1}' for v in vehicles],
            autopct='%1.1f%%',
            startangle=90,
            colors=colors_pie,
            textprops={'fontsize': 10, 'fontweight': 'bold'}
        )
        
        ax.set_title('③ Phân bố số khách hàng', fontsize=13, fontweight='bold', pad=10)
        
        legend_labels = [f'Xe {v+1}: {num_customers_per_vehicle[i]} KH' 
                        for i, v in enumerate(vehicles)]
        ax.legend(legend_labels, loc='upper left', bbox_to_anchor=(1, 1), fontsize=9)
    
    def save_solution_text(self, save_path):
        """Lưu solution ra file text"""
        if not self.solution:
            print("❌ Chưa có solution để lưu!")
            return
        
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write("="*100 + "\n")
            f.write("BÁO CÁO KẾT QUẢ GIẢI THUẬT OR-TOOLS\n")
            f.write("Google Optimization Tools - Routing Solver\n")
            f.write("="*100 + "\n\n")
            
            f.write(f"Dataset: {self.dataset_name}\n")
            f.write(f"Ngày giờ: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("="*100 + "\n")
            f.write("KẾT QUẢ TỔNG HỢP\n")
            f.write("="*100 + "\n")
            f.write(f"Số xe sử dụng: {self.solution['num_vehicles']}\n")
            f.write(f"Tổng quãng đường: {self.solution['total_distance']:.2f}\n")
            f.write(f"Khách hàng phục vụ: {self.solution['customers_served']}/{self.n_customers}\n")
            f.write(f"Thời gian giải: {self.solve_time:.2f}s\n\n")
            
            f.write("="*100 + "\n")
            f.write("CHI TIẾT CÁC TUYẾN ĐƯỜNG\n")
            f.write("="*100 + "\n\n")
            
            for idx, route in enumerate(self.solution['routes']):
                f.write(f"{'─'*100}\n")
                f.write(f"XE {idx + 1}\n")
                f.write(f"{'─'*100}\n")
                f.write(f"Tuyến đường: 0 (Kho) → {' → '.join(map(str, route))} → 0 (Kho)\n")
                f.write(f"Số khách hàng: {len(route)}\n")
                
                total_load = sum(self.customers.loc[i-1, 'DEMAND'] for i in route)
                f.write(f"Tổng nhu cầu: {total_load}/{self.vehicle_capacity}\n")
                
                route_dist = self._calculate_route_distance(route)
                f.write(f"Quãng đường: {route_dist:.2f}\n\n")
            
            f.write("="*100 + "\n")
        
        print(f"✓ Đã lưu báo cáo: {save_path}")
    
    def save_all_results(self, output_dir):
        """Lưu tất cả kết quả"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        images_dir = output_path / 'images'
        text_dir = output_path / 'text'
        images_dir.mkdir(exist_ok=True)
        text_dir.mkdir(exist_ok=True)
        
        # Lưu visualization
        image_path = images_dir / f"{self.dataset_name}_ortools.png"
        self.visualize_solution(save_path=str(image_path))
        
        # Lưu text report
        text_path = text_dir / f"{self.dataset_name}_ortools.txt"
        self.save_solution_text(save_path=str(text_path))
        
        # Summary data
        summary_data = {
            'Dataset': self.dataset_name,
            'Algorithm': 'OR-Tools',
            'Status': self.solution['status'],
            'Total_Distance': round(self.solution['total_distance'], 4),
            'Num_Vehicles': self.solution['num_vehicles'],
            'Customers_Served': self.solution['customers_served'],
            'Solve_Time_s': round(self.solve_time, 4)
        }
        
        return summary_data


def main():
    """Test OR-Tools solver"""
    dataset_path = r"../../dataset/C1/C101.csv"
    
    print("="*100)
    print("OR-TOOLS VRPTW SOLVER")
    print("Google Optimization Tools - Production-grade Routing Solver")
    print("="*100)
    
    solver = ORToolsVRPTWSolver(
        dataset_path=dataset_path,
        vehicle_capacity=200,
        max_vehicles=25
    )
    
    # Giải bài toán
    solution = solver.solve(time_limit=30)
    
    # Lưu kết quả
    if solution:
        print("\n" + "="*100)
        print("LƯU KẾT QUẢ")
        print("="*100)
        
        output_dir = Path(__file__).parent / 'result'
        solver.save_all_results(output_dir)
        
        print("✓ Đã lưu tất cả kết quả vào thư mục 'result/'")
    
    print("\n" + "="*100)
    print("HOÀN THÀNH!")
    print("="*100)


if __name__ == "__main__":
    main()

