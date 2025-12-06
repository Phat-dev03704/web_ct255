"""
VRPTW Solver using Mixed Integer Linear Programming (MILP)
Giải bài toán VRP với cửa sổ thời gian bằng Lập trình tuyến tính hỗn hợp

Sử dụng thư viện PuLP để mô hình hóa và giải quyết bài toán
"""

import pandas as pd
import numpy as np
from pulp import *
import time
from pathlib import Path
import matplotlib.pyplot as plt


class MILPVRPTWSolver:
    """
    Class giải bài toán VRPTW bằng phương pháp MILP
    """
    
    def __init__(self, dataset_path, vehicle_capacity=200, max_vehicles=25, max_customers=25):
        """
        Khởi tạo solver
        
        Args:
            dataset_path: Đường dẫn đến file CSV dataset
            vehicle_capacity: Sức chứa của mỗi xe
            max_vehicles: Số lượng xe tối đa
            max_customers: Số khách hàng tối đa để giải (MILP chỉ hiệu quả với <30 khách hàng)
        """
        self.dataset_path = dataset_path
        self.dataset_name = Path(dataset_path).stem
        self.vehicle_capacity = vehicle_capacity
        self.max_vehicles = max_vehicles
        
        # Đọc dữ liệu
        self.data = pd.read_csv(dataset_path)
        self.depot = self.data.iloc[0]
        
        # GIỚI HẠN SỐ KHÁCH HÀNG cho MILP
        all_customers = self.data.iloc[1:].reset_index(drop=True)
        if len(all_customers) > max_customers:
            print(f"⚠️ Dataset có {len(all_customers)} khách hàng - MILP chỉ giải {max_customers} khách hàng đầu tiên")
            print(f"   (MILP không hiệu quả cho bài toán lớn - nên dùng Heuristic)")
            self.customers = all_customers.iloc[:max_customers].reset_index(drop=True)
        else:
            self.customers = all_customers
        
        # Số lượng khách hàng (không tính depot)
        self.n_customers = len(self.customers)
        
        # Tính ma trận khoảng cách
        self.distance_matrix = self._calculate_distance_matrix()
        
        # Tính ma trận thời gian di chuyển (giả sử vận tốc = 1)
        self.time_matrix = self.distance_matrix.copy()
        
        # Model và biến
        self.model = None
        self.x = {}  # Biến quyết định: xe k đi từ i đến j
        self.t = {}  # Thời gian bắt đầu phục vụ tại i
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
        Xây dựng mô hình MILP cho bài toán VRPTW
        """
        print(f"\n{'='*80}")
        print(f"XÂY DỰNG MÔ HÌNH MILP CHO DATASET: {self.dataset_name}")
        print(f"{'='*80}")
        print(f"Số khách hàng: {self.n_customers}")
        print(f"Số xe tối đa: {self.max_vehicles}")
        print(f"Sức chứa xe: {self.vehicle_capacity}")
        print(f"{'='*80}\n")
        
        # Khởi tạo model
        self.model = LpProblem(f"VRPTW_{self.dataset_name}", LpMinimize)
        
        # Tập hợp các node (0 = depot, 1..n = customers)
        nodes = range(self.n_customers + 1)
        customers_only = range(1, self.n_customers + 1)
        vehicles = range(self.max_vehicles)
        
        # ===================== BIẾN QUYẾT ĐỊNH =====================
        
        # x[i,j,k] = 1 nếu xe k đi từ i đến j
        print("Tạo biến quyết định x[i,j,k]...")
        for i in nodes:
            for j in nodes:
                if i != j:
                    for k in vehicles:
                        self.x[i, j, k] = LpVariable(f"x_{i}_{j}_{k}", cat='Binary')
        
        # t[i] = thời gian bắt đầu phục vụ tại node i
        print("Tạo biến thời gian t[i]...")
        for i in nodes:
            if i == 0:  # Depot
                self.t[i] = 0
            else:
                # Lấy time window từ data
                ready_time = self.customers.loc[i-1, 'READY TIME']
                due_date = self.customers.loc[i-1, 'DUE DATE']
                self.t[i] = LpVariable(f"t_{i}", lowBound=ready_time, upBound=due_date, cat='Continuous')
        
        # ===================== HÀM MỤC TIÊU =====================
        
        print("Thiết lập hàm mục tiêu: Minimize tổng quãng đường...")
        self.model += lpSum([
            self.distance_matrix[i][j] * self.x[i, j, k]
            for i in nodes
            for j in nodes
            if i != j
            for k in vehicles
        ]), "Total_Distance"
        
        # ===================== RÀNG BUỘC =====================
        
        print("Thêm ràng buộc...")
        
        # 1. Mỗi khách hàng được phục vụ đúng 1 lần
        print("  - Ràng buộc: Mỗi khách hàng được phục vụ đúng 1 lần")
        for j in customers_only:
            self.model += lpSum([
                self.x[i, j, k]
                for i in nodes
                if i != j
                for k in vehicles
            ]) == 1, f"Visit_Customer_{j}"
        
        # 2. Bảo toàn luồng: Xe vào phải ra
        print("  - Ràng buộc: Bảo toàn luồng (flow conservation)")
        for k in vehicles:
            for j in customers_only:
                self.model += (
                    lpSum([self.x[i, j, k] for i in nodes if i != j]) ==
                    lpSum([self.x[j, i, k] for i in nodes if i != j])
                ), f"Flow_Conservation_{j}_{k}"
        
        # 3. Mỗi xe xuất phát từ depot tối đa 1 lần
        print("  - Ràng buộc: Mỗi xe xuất phát từ depot tối đa 1 lần")
        for k in vehicles:
            self.model += lpSum([
                self.x[0, j, k] for j in customers_only
            ]) <= 1, f"Vehicle_Start_{k}"
        
        # 4. Mỗi xe quay về depot tối đa 1 lần
        print("  - Ràng buộc: Mỗi xe quay về depot tối đa 1 lần")
        for k in vehicles:
            self.model += lpSum([
                self.x[i, 0, k] for i in customers_only
            ]) <= 1, f"Vehicle_End_{k}"
        
        # 5. Ràng buộc sức chứa xe
        print("  - Ràng buộc: Sức chứa xe")
        for k in vehicles:
            self.model += lpSum([
                self.customers.loc[j-1, 'DEMAND'] * self.x[i, j, k]
                for i in nodes
                for j in customers_only
                if i != j
            ]) <= self.vehicle_capacity, f"Capacity_{k}"
        
        # 6. Ràng buộc cửa sổ thời gian
        print("  - Ràng buộc: Cửa sổ thời gian")
        M = 10000  # Big M constant
        
        for i in nodes:
            for j in customers_only:
                if i != j:
                    for k in vehicles:
                        # Nếu xe k đi từ i đến j, thì t[j] >= t[i] + service[i] + travel[i,j]
                        service_time_i = 0 if i == 0 else self.customers.loc[i-1, 'SERVICE TIME']
                        
                        self.model += (
                            self.t[j] >= self.t[i] + service_time_i + self.time_matrix[i][j] 
                            - M * (1 - self.x[i, j, k])
                        ), f"Time_Window_{i}_{j}_{k}"
        
        print("\n✓ Hoàn thành xây dựng mô hình MILP!")
        print(f"  - Số biến: {self.model.numVariables()}")
        print(f"  - Số ràng buộc: {self.model.numConstraints()}")
        
    def solve(self, time_limit=60):
        """
        Giải bài toán MILP
        
        Args:
            time_limit: Giới hạn thời gian giải (giây) - Mặc định 1 phút
        """
        if self.model is None:
            print("❌ Chưa xây dựng model! Hãy gọi build_model() trước.")
            return None
        
        print(f"\n{'='*80}")
        print(f"BẮT ĐẦU GIẢI BÀI TOÁN MILP")
        print(f"{'='*80}")
        print(f"Giới hạn thời gian: {time_limit} giây")
        print("Đang giải...")
        
        start_time = time.time()
        
        # Giải bài toán với time limit - Cho phép nghiệm không tối ưu
        self.model.solve(PULP_CBC_CMD(timeLimit=time_limit, msg=1, gapRel=0.1))
        
        solve_time = time.time() - start_time
        
        # Kiểm tra trạng thái
        status = LpStatus[self.model.status]
        print(f"\n{'='*80}")
        print(f"KẾT QUẢ GIẢI")
        print(f"{'='*80}")
        print(f"Trạng thái: {status}")
        print(f"Thời gian giải: {solve_time:.2f} giây")
        
        # Chấp nhận cả nghiệm không tối ưu (Optimal, Feasible, hoặc có solution)
        if status in ['Optimal', 'Feasible'] or self.model.status == 1:
            try:
                obj_value = value(self.model.objective)
                print(f"Tổng quãng đường: {obj_value:.2f}")
                
                # Trích xuất solution
                self._extract_solution()
                
                if self.solution and len(self.solution) > 0:
                    return {
                        'status': status,
                        'objective': obj_value,
                        'time': solve_time,
                        'routes': self.solution
                    }
            except:
                pass
        
        # Nếu không có solution, tạo một solution đơn giản (nearest neighbor)
        print("⚠️ Không tìm được nghiệm khả thi từ MILP!")
        print("⚠️ Tạo nghiệm đơn giản bằng Nearest Neighbor để trực quan hóa...")
        self._create_fallback_solution()
        
        if self.solution and len(self.solution) > 0:
            total_dist = sum([r['distance'] for r in self.solution.values()])
            return {
                'status': 'Fallback (Nearest Neighbor)',
                'objective': total_dist,
                'time': solve_time,
                'routes': self.solution
            }
        
        return None
    
    def _extract_solution(self):
        """Trích xuất nghiệm từ model"""
        routes = {}
        route_id = 0
        
        for k in range(self.max_vehicles):
            route = []
            current = 0  # Bắt đầu từ depot
            
            # Tìm node đầu tiên từ depot
            for j in range(1, self.n_customers + 1):
                if (0, j, k) in self.x and value(self.x[0, j, k]) > 0.5:
                    route.append(j)
                    current = j
                    break
            
            # Tiếp tục xây dựng route
            while current != 0 and len(route) < self.n_customers:
                found = False
                for j in range(self.n_customers + 1):
                    if j != current and (current, j, k) in self.x and value(self.x[current, j, k]) > 0.5:
                        if j != 0:  # Chưa về depot
                            route.append(j)
                            current = j
                            found = True
                            break
                        else:  # Về depot
                            current = 0
                            found = True
                            break
                
                if not found:
                    break
            
            if len(route) > 0:
                # Tính toán thông tin route
                distance = self._calculate_route_distance(route)
                load = sum([self.customers.loc[i-1, 'DEMAND'] for i in route])
                
                routes[route_id] = {
                    'route': route,
                    'distance': distance,
                    'load': load,
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
    
    def _calculate_route_distance(self, route):
        """Tính quãng đường của một route"""
        distance = 0
        
        # Từ depot đến khách hàng đầu tiên
        distance += self.distance_matrix[0][route[0]]
        
        # Giữa các khách hàng
        for i in range(len(route) - 1):
            distance += self.distance_matrix[route[i]][route[i+1]]
        
        # Từ khách hàng cuối về depot
        distance += self.distance_matrix[route[-1]][0]
        
        return distance
    
    def _create_fallback_solution(self):
        """Tạo solution dự phòng bằng thuật toán Nearest Neighbor đơn giản"""
        print("\n" + "="*80)
        print("TẠO NGHIỆM DỰ PHÒNG BẰNG NEAREST NEIGHBOR")
        print("="*80)
        
        routes = {}
        route_id = 0
        unvisited = set(range(1, self.n_customers + 1))
        
        while unvisited and route_id < self.max_vehicles:
            route = []
            current_load = 0
            current = 0  # Bắt đầu từ depot
            
            while unvisited:
                # Tìm khách hàng gần nhất chưa thăm
                best_customer = None
                best_distance = float('inf')
                
                for customer in unvisited:
                    # Kiểm tra capacity
                    demand = self.customers.loc[customer-1, 'DEMAND']
                    if current_load + demand <= self.vehicle_capacity:
                        dist = self.distance_matrix[current][customer]
                        if dist < best_distance:
                            best_distance = dist
                            best_customer = customer
                
                if best_customer is None:
                    break
                
                route.append(best_customer)
                unvisited.remove(best_customer)
                current_load += self.customers.loc[best_customer-1, 'DEMAND']
                current = best_customer
            
            if len(route) > 0:
                distance = self._calculate_route_distance(route)
                load = sum([self.customers.loc[i-1, 'DEMAND'] for i in route])
                
                routes[route_id] = {
                    'route': route,
                    'distance': distance,
                    'load': load,
                    'num_customers': len(route)
                }
                route_id += 1
        
        self.solution = routes
        
        print(f"✓ Đã tạo {len(routes)} tuyến đường bằng Nearest Neighbor")
        for rid, info in routes.items():
            print(f"  Xe {rid+1}: {info['num_customers']} khách hàng, quãng đường: {info['distance']:.2f}")
    
    def visualize_solution_comprehensive(self, save=False):
        """
        Vẽ biểu đồ tổng hợp với nhiều sub-plots
        Bao gồm: Routes, Thống kê xe, Phân bố demand, Timeline
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
            f'KẾT QUẢ GIẢI THUẬT MILP - {self.dataset_name}\n'
            f'Số xe: {len(self.solution)} | Tổng quãng đường: {total_distance:.2f} | '
            f'Khách hàng phục vụ: {total_customers}/{self.n_customers}',
            fontsize=16, fontweight='bold', y=0.98
        )
        
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        
        if save:
            output_dir = Path(__file__).parent / 'result' / 'images'
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f'{self.dataset_name}_milp_solution.png'
            plt.savefig(str(output_path), dpi=300, bbox_inches='tight')
            print(f"✓ Đã lưu hình ảnh: {output_path}")
        
        plt.close(fig)  # Đóng figure để giải phóng bộ nhớ
    
    def visualize_solution(self, save=False):
        """Wrapper để tương thích - gọi comprehensive visualization"""
        self.visualize_solution_comprehensive(save)
    
    def visualize_solution_simple(self, save=False):
        """Vẽ biểu đồ solution đơn giản (giữ lại cho tương thích)"""
        if self.solution is None:
            print("❌ Chưa có solution để vẽ!")
            return
        
        # Tắt chế độ interactive để không hiển thị cửa sổ
        plt.ioff()
        
        fig, ax = plt.subplots(figsize=(14, 10))
        
        # Vẽ depot
        ax.scatter(self.depot['XCOORD.'], self.depot['YCOORD.'],
                  c='red', s=500, marker='s', edgecolors='black',
                  linewidth=3, label='Kho', zorder=5)
        
        # Vẽ customers
        ax.scatter(self.customers['XCOORD.'], self.customers['YCOORD.'],
                  c='lightblue', s=150, edgecolors='black',
                  linewidth=1, label='Khách hàng', zorder=3)
        
        # Vẽ các routes với màu khác nhau
        colors = plt.cm.tab20(np.linspace(0, 1, len(self.solution)))
        
        for idx, (route_id, info) in enumerate(self.solution.items()):
            route = [0] + info['route'] + [0]  # Thêm depot vào đầu và cuối
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
                
                ax.plot([x1, x2], [y1, y2], color=color, linewidth=2, alpha=0.7, zorder=2)
                
                # Vẽ mũi tên chỉ hướng
                dx, dy = x2 - x1, y2 - y1
                ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                           arrowprops=dict(arrowstyle='->', color=color, lw=2, alpha=0.7))
            
            # Label cho route
            mid_idx = len(info['route']) // 2
            mid_customer = info['route'][mid_idx]
            mid_x = self.customers.loc[mid_customer-1, 'XCOORD.']
            mid_y = self.customers.loc[mid_customer-1, 'YCOORD.']
            ax.text(mid_x, mid_y + 3, f"Xe {route_id+1}", fontsize=10, fontweight='bold',
                   ha='center', bbox=dict(boxstyle='round,pad=0.3', facecolor=color, alpha=0.7))
        
        # Thêm số thứ tự khách hàng
        for idx, row in self.customers.iterrows():
            ax.annotate(str(idx + 1), (row['XCOORD.'], row['YCOORD.']),
                       fontsize=8, ha='center', va='center', fontweight='bold')
        
        ax.set_xlabel('Tọa độ X', fontsize=12, fontweight='bold')
        ax.set_ylabel('Tọa độ Y', fontsize=12, fontweight='bold')
        ax.set_title(f'Giải pháp MILP cho {self.dataset_name}\nSố xe: {len(self.solution)} | Tổng quãng đường: {sum([r["distance"] for r in self.solution.values()]):.2f}',
                    fontsize=14, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save:
            output_dir = Path(__file__).parent / 'result' / 'images'
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f'{self.dataset_name}_milp_solution.png'
            plt.savefig(str(output_path), dpi=300, bbox_inches='tight')
            print(f"✓ Đã lưu hình ảnh: {output_path}")
        
        plt.close(fig)  # Đóng figure để giải phóng bộ nhớ
    
    def save_solution(self, solve_time=None, status=None):
        """Lưu solution ra file TXT chi tiết"""
        if self.solution is None:
            print("❌ Chưa có solution để lưu!")
            return
        
        output_dir = Path(__file__).parent / 'result' / 'text'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f'{self.dataset_name}_milp_solution.txt'
        
        total_distance = sum([r['distance'] for r in self.solution.values()])
        total_load = sum([r['load'] for r in self.solution.values()])
        total_customers_served = sum([r['num_customers'] for r in self.solution.values()])
        
        with open(str(output_path), 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write(f"BÁO CÁO KẾT QUẢ GIẢI THUẬT MILP\n")
            f.write(f"Mixed Integer Linear Programming for VRPTW\n")
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
        
        print(f"\n✓ Đã lưu báo cáo chi tiết: {output_path}")


def main():
    """Hàm chính để chạy MILP solver"""
    
    # Đường dẫn đến dataset
    dataset_path = "../dataset/C1/C101.csv"
    
    print("="*80)
    print("MILP SOLVER FOR VRPTW - Mixed Integer Linear Programming")
    print("="*80)
    print("⚠️ LƯU Ý: MILP chỉ hiệu quả với <30 khách hàng")
    print("   Với bài toán lớn hơn, hãy dùng Heuristic/Metaheuristic")
    print("="*80)
    
    # Tạo solver (giới hạn 25 khách hàng)
    solver = MILPVRPTWSolver(
        dataset_path=dataset_path,
        vehicle_capacity=200,
        max_vehicles=10,
        max_customers=25  # MILP chỉ giải 25 khách hàng đầu
    )
    
    # Xây dựng model
    solver.build_model()
    
    # Giải bài toán (giới hạn 1 phút = 60 giây)
    result = solver.solve(time_limit=60)
    
    if result:
        # Vẽ và lưu solution (luôn luôn tạo file)
        print("\n" + "="*80)
        print("TẠO TRỰC QUAN HÓA VÀ BÁO CÁO")
        print("="*80)
        solver.visualize_solution(save=True)
        solver.save_solution(solve_time=result['time'], status=result['status'])
        print("✓ Đã tạo file PNG và TXT trong thư mục 'results/'")
    else:
        print("\n❌ Không thể tạo solution!")
    
    print("\n" + "="*80)
    print("HOÀN THÀNH!")
    print("="*80)


if __name__ == "__main__":
    main()
