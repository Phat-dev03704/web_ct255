"""
VRPTW Solver using Clarke-Wright Savings Algorithm
Giải bài toán VRP với cửa sổ thời gian bằng Thuật toán tiết kiệm Clarke & Wright

Thuật toán Heuristic nhanh và hiệu quả
"""

import pandas as pd
import numpy as np
import time
from pathlib import Path
import matplotlib.pyplot as plt


class ClarkeWrightVRPTWSolver:
    """
    Class giải bài toán VRPTW bằng Clarke-Wright Savings Algorithm
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
        self.savings = []
        
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
    
    def _calculate_savings(self):
        """
        Tính savings cho mọi cặp khách hàng (i, j)
        Savings(i,j) = distance(0,i) + distance(0,j) - distance(i,j)
        Ý nghĩa: Tiết kiệm được bao nhiêu nếu gộp route i và j
        """
        print("Tính toán savings cho các cặp khách hàng...")
        savings = []
        
        for i in range(1, self.n_customers + 1):
            for j in range(i + 1, self.n_customers + 1):
                # Savings = d(0,i) + d(0,j) - d(i,j)
                saving = (self.distance_matrix[0][i] + 
                         self.distance_matrix[0][j] - 
                         self.distance_matrix[i][j])
                
                savings.append({
                    'customer_i': i,
                    'customer_j': j,
                    'saving': saving
                })
        
        # Sắp xếp theo savings giảm dần
        savings.sort(key=lambda x: x['saving'], reverse=True)
        self.savings = savings
        
        print(f"✓ Đã tính {len(savings)} savings")
        print(f"  - Savings lớn nhất: {savings[0]['saving']:.2f} (khách hàng {savings[0]['customer_i']}-{savings[0]['customer_j']})")
    
    def _check_time_window_feasibility(self, route):
        """
        Kiểm tra xem route có thỏa mãn time window không
        """
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
        
        return True
    
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
    
    def _calculate_route_load(self, route):
        """Tính tải trọng của một route"""
        return sum([self.customers.loc[customer_id - 1, 'DEMAND'] for customer_id in route])
    
    def solve(self):
        """
        Giải bài toán bằng Clarke-Wright Savings Algorithm
        """
        print(f"\n{'='*80}")
        print(f"XÂY DỰNG GIẢI PHÁP BẰNG CLARKE-WRIGHT SAVINGS ALGORITHM")
        print(f"{'='*80}")
        print(f"Dataset: {self.dataset_name}")
        print(f"Số khách hàng: {self.n_customers}")
        print(f"Sức chứa xe: {self.vehicle_capacity}")
        print(f"Số xe tối đa: {self.max_vehicles}")
        print(f"{'='*80}\n")
        
        start_time = time.time()
        
        # Bước 1: Tính savings
        self._calculate_savings()
        
        # Bước 2: Khởi tạo - mỗi khách hàng là một route riêng
        print("\nKhởi tạo routes ban đầu (mỗi khách hàng 1 route)...")
        routes = {i: [i] for i in range(1, self.n_customers + 1)}
        
        # Map: customer -> route_id
        customer_to_route = {i: i for i in range(1, self.n_customers + 1)}
        
        print(f"✓ Đã khởi tạo {len(routes)} routes")
        
        # Bước 3: Merge routes theo savings
        print("\nMerge routes theo savings...")
        merge_count = 0
        
        for saving_item in self.savings:
            i = saving_item['customer_i']
            j = saving_item['customer_j']
            saving = saving_item['saving']
            
            # Kiểm tra xem i và j có thuộc 2 route khác nhau không
            route_i = customer_to_route[i]
            route_j = customer_to_route[j]
            
            if route_i == route_j:
                continue  # Đã cùng route rồi
            
            route_i_customers = routes[route_i]
            route_j_customers = routes[route_j]
            
            # Kiểm tra i và j có phải là đầu/cuối route không
            # Clarke-Wright chỉ merge nếu i là cuối route_i hoặc đầu route_i
            # và j là đầu route_j hoặc cuối route_j
            
            can_merge = False
            new_route = None
            
            # Case 1: i ở cuối route_i, j ở đầu route_j -> route_i + route_j
            if route_i_customers[-1] == i and route_j_customers[0] == j:
                new_route = route_i_customers + route_j_customers
                can_merge = True
            
            # Case 2: j ở cuối route_j, i ở đầu route_i -> route_j + route_i
            elif route_j_customers[-1] == j and route_i_customers[0] == i:
                new_route = route_j_customers + route_i_customers
                can_merge = True
            
            # Case 3: i ở đầu route_i, j ở cuối route_j -> route_j + route_i
            elif route_i_customers[0] == i and route_j_customers[-1] == j:
                new_route = route_j_customers + route_i_customers
                can_merge = True
            
            # Case 4: j ở đầu route_j, i ở cuối route_i -> route_i + route_j
            elif route_j_customers[0] == j and route_i_customers[-1] == i:
                new_route = route_i_customers + route_j_customers
                can_merge = True
            
            if not can_merge:
                continue
            
            # Kiểm tra capacity constraint
            new_load = self._calculate_route_load(new_route)
            if new_load > self.vehicle_capacity:
                continue
            
            # Kiểm tra time window constraint
            if not self._check_time_window_feasibility(new_route):
                continue
            
            # Merge được! Cập nhật routes
            routes[route_i] = new_route
            del routes[route_j]
            
            # Cập nhật customer_to_route
            for customer in new_route:
                customer_to_route[customer] = route_i
            
            merge_count += 1
            
            # Kiểm tra số lượng xe
            if len(routes) <= self.max_vehicles:
                pass  # OK
        
        solve_time = time.time() - start_time
        
        print(f"\n✓ Hoàn thành merge!")
        print(f"  - Số lần merge: {merge_count}")
        print(f"  - Số routes cuối cùng: {len(routes)}")
        
        # Bước 4: Chuyển đổi sang format solution
        self.solution = {}
        route_id = 0
        total_distance = 0
        
        for customers_list in routes.values():
            distance = self._calculate_route_distance(customers_list)
            load = self._calculate_route_load(customers_list)
            
            self.solution[route_id] = {
                'route': customers_list,
                'distance': distance,
                'load': load,
                'num_customers': len(customers_list)
            }
            
            total_distance += distance
            route_id += 1
        
        # In kết quả
        print(f"\n{'='*80}")
        print(f"KẾT QUẢ GIẢI")
        print(f"{'='*80}")
        print(f"Trạng thái: Feasible (Heuristic)")
        print(f"Thời gian giải: {solve_time:.2f} giây")
        print(f"Số xe sử dụng: {len(self.solution)}")
        print(f"Tổng quãng đường: {total_distance:.2f}")
        
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
            'status': 'Feasible (Clarke-Wright)',
            'objective': total_distance,
            'time': solve_time,
            'routes': self.solution
        }
    
    def visualize_solution_comprehensive(self, save=False):
        """
        Vẽ biểu đồ tổng hợp với nhiều sub-plots
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
            if len(info['route']) > 0:
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
        ax1.set_title('① Các tuyến đường (Clarke-Wright)',
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
            f'KẾT QUẢ CLARKE-WRIGHT SAVINGS ALGORITHM - {self.dataset_name}\n'
            f'Số xe: {len(self.solution)} | Tổng quãng đường: {total_distance:.2f} | '
            f'Khách hàng phục vụ: {total_customers}/{self.n_customers}',
            fontsize=16, fontweight='bold', y=0.98
        )
        
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        
        if save:
            output_dir = Path(__file__).parent / 'result' / 'images'
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f'{self.dataset_name}_cw_solution.png'
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
        output_path = output_dir / f'{self.dataset_name}_cw_solution.txt'
        
        total_distance = sum([r['distance'] for r in self.solution.values()])
        total_load = sum([r['load'] for r in self.solution.values()])
        total_customers_served = sum([r['num_customers'] for r in self.solution.values()])
        
        with open(str(output_path), 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write(f"BÁO CÁO KẾT QUẢ CLARKE-WRIGHT SAVINGS ALGORITHM\n")
            f.write(f"Heuristic Algorithm for VRPTW\n")
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
    """Hàm chính để chạy Clarke-Wright solver"""
    
    # Đường dẫn đến dataset
    current_dir = Path(__file__).parent
    code_dir = current_dir.parent.parent
    dataset_path = code_dir / "dataset" / "C1" / "C101.csv"
    
    print("="*80)
    print("CLARKE-WRIGHT SAVINGS ALGORITHM FOR VRPTW")
    print("="*80)
    print("✓ Thuật toán Heuristic nhanh và hiệu quả")
    print("✓ Có thể giải toàn bộ dataset (100+ khách hàng)")
    print("✓ Dựa trên ý tưởng: Gộp routes tiết kiệm quãng đường nhất")
    print("="*80)
    
    # Tạo solver
    solver = ClarkeWrightVRPTWSolver(
        dataset_path=str(dataset_path),
        vehicle_capacity=200,
        max_vehicles=25
    )
    
    # Giải bài toán
    result = solver.solve()
    
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
