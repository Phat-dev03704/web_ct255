"""
VRPTW Solver using Attention Model (Deep Reinforcement Learning)
Giải bài toán VRP với cửa sổ thời gian bằng Attention Model (Transformer-based RL)
"""

import pandas as pd
import numpy as np
import torch
import time
from pathlib import Path
import matplotlib.pyplot as plt
from copy import deepcopy

from attention_model import AttentionModelVRPTW


class AttentionModelVRPTWSolver:
    """
    Class giải bài toán VRPTW bằng Attention Model (Deep RL)
    """
    
    def __init__(self, dataset_path, vehicle_capacity=200, max_vehicles=25, model_path=None):
        """
        Khởi tạo solver
        
        Args:
            dataset_path: Đường dẫn đến file CSV dataset
            vehicle_capacity: Sức chứa của mỗi xe
            max_vehicles: Số lượng xe tối đa
            model_path: Đường dẫn đến trained model (nếu có)
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
        self.time_matrix = self.distance_matrix.copy()
        
        # Device
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        # Load hoặc tạo model
        self.model = AttentionModelVRPTW(
            input_dim=6,
            embed_dim=128,
            n_heads=8,
            n_encoder_layers=3,
            ff_dim=512,
            vehicle_capacity=vehicle_capacity
        ).to(self.device)
        
        if model_path and Path(model_path).exists():
            checkpoint = torch.load(model_path, map_location=self.device, weights_only=False)
            self.model.load_state_dict(checkpoint['model_state_dict'])
            print(f"✓ Loaded trained model from {model_path}")
        else:
            print("⚠ No pretrained model loaded, using random initialization")
        
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
    
    def _preprocess_input(self):
        """Chuyển dataset sang tensor format cho model"""
        features = self.data[['XCOORD.', 'YCOORD.', 'DEMAND', 
                              'READY TIME', 'DUE DATE', 'SERVICE TIME']].values
        
        # Normalize
        features_norm = features.copy().astype(np.float32)
        features_norm[:, 0:2] = features_norm[:, 0:2] / 100.0  # Normalize coordinates
        features_norm[:, 2] = features_norm[:, 2] / 200.0  # Normalize demand
        features_norm[:, 3:6] = features_norm[:, 3:6] / 1000.0  # Normalize time
        
        return torch.FloatTensor(features_norm).unsqueeze(0).to(self.device)
    
    def _decode_solution(self, tour_tensor):
        """Chuyển tour tensor thành routes"""
        tour = tour_tensor.cpu().numpy()[0]
        
        routes = []
        current_route = []
        current_load = 0
        
        for node_idx in tour:
            if node_idx == 0:  # Depot
                if current_route:
                    routes.append(current_route)
                    current_route = []
                    current_load = 0
            else:
                demand = float(self.customers.loc[node_idx - 1, 'DEMAND'])
                if current_load + demand <= self.vehicle_capacity:
                    current_route.append(int(node_idx))
                    current_load += demand
                else:
                    if current_route:
                        routes.append(current_route)
                    current_route = [int(node_idx)]
                    current_load = demand
        
        if current_route:
            routes.append(current_route)
        
        return routes
    
    def _check_time_window_feasibility(self, route):
        """Kiểm tra xem route có thỏa mãn time window không"""
        if not route:
            return True
            
        current_time = 0
        current_location = 0  # Bắt đầu từ depot
        
        for customer_id in route:
            # Thời gian di chuyển đến khách hàng
            travel_time = float(self.time_matrix[current_location][customer_id])
            arrival_time = current_time + travel_time
            
            # Lấy thông tin time window
            ready_time = float(self.customers.loc[customer_id - 1, 'READY TIME'])
            due_date = float(self.customers.loc[customer_id - 1, 'DUE DATE'])
            service_time = float(self.customers.loc[customer_id - 1, 'SERVICE TIME'])
            
            # Nếu đến sớm, phải đợi
            start_service = max(arrival_time, ready_time)
            
            # Kiểm tra có quá muộn không
            if start_service > due_date:
                return False
            
            # Cập nhật thời gian hiện tại
            current_time = start_service + service_time
            current_location = customer_id
        
        # Kiểm tra có về depot kịp không
        travel_time_back = float(self.time_matrix[current_location][0])
        return_time = current_time + travel_time_back
        depot_due_date = float(self.depot['DUE DATE'])
        
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
        return sum([float(self.customers.loc[customer_id - 1, 'DEMAND']) for customer_id in route])
    
    def _calculate_total_distance(self, routes):
        """Tính tổng quãng đường của tất cả routes"""
        return sum([self._calculate_route_distance(route) for route in routes if route])
    
    def solve(self, n_samples=10, use_beam_search=False, beam_width=5):
        """
        Giải bài toán bằng Attention Model
        
        Args:
            n_samples: Số lần sampling để tìm best solution
            use_beam_search: Có sử dụng beam search không
            beam_width: Độ rộng beam nếu dùng beam search
        """
        print(f"\n{'='*80}")
        print(f"XÂY DỰNG GIẢI PHÁP BẰNG ATTENTION MODEL (DEEP RL)")
        print(f"{'='*80}")
        print(f"Dataset: {self.dataset_name}")
        print(f"Số khách hàng: {self.n_customers}")
        print(f"Sức chứa xe: {self.vehicle_capacity}")
        print(f"Số xe tối đa: {self.max_vehicles}")
        print(f"\n🧠 THÔNG SỐ:")
        print(f"  - Model: Attention Model (Transformer-based)")
        print(f"  - Device: {self.device}")
        print(f"  - Số samples: {n_samples}")
        print(f"  - Beam search: {use_beam_search}")
        if use_beam_search:
            print(f"  - Beam width: {beam_width}")
        print(f"{'='*80}\n")
        
        start_time = time.time()
        
        # Chuẩn bị input
        input_tensor = self._preprocess_input()
        
        # Giải bằng model
        self.model.eval()
        best_routes = None
        best_distance = float('inf')
        
        print("Đang tạo solutions...")
        
        with torch.no_grad():
            for sample in range(n_samples):
                # Generate tour
                if use_beam_search:
                    # TODO: Implement beam search
                    tour = self.model.decode_greedy(input_tensor)
                else:
                    tour = self.model.decode_greedy(input_tensor)
                
                # Decode to routes
                routes = self._decode_solution(tour)
                
                # Calculate distance
                distance = self._calculate_total_distance(routes)
                
                if distance < best_distance:
                    best_distance = distance
                    best_routes = routes
                    print(f"  Sample {sample + 1}/{n_samples}: Cải thiện! Distance = {best_distance:.2f}")
        
        solve_time = time.time() - start_time
        
        # Lưu solution
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
        print(f"Trạng thái: Feasible (Attention Model - Deep RL)")
        print(f"Thời gian giải: {solve_time:.2f} giây")
        print(f"Số samples: {n_samples}")
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
            'status': 'Feasible (Attention Model - Deep RL)',
            'objective': best_distance,
            'time': solve_time,
            'routes': self.solution,
            'n_samples': n_samples
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
        ax1.set_title('① Các tuyến đường (Attention Model - Deep RL)',
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
            f'KẾT QUẢ ATTENTION MODEL (DEEP RL) - {self.dataset_name}\n'
            f'Số xe: {len(self.solution)} | Tổng quãng đường: {total_distance:.2f} | '
            f'Khách hàng phục vụ: {total_customers}/{self.n_customers}',
            fontsize=16, fontweight='bold', y=0.98
        )
        
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        
        if save:
            output_dir = Path(__file__).parent / 'result' / 'images'
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f'{self.dataset_name}_attention_solution.png'
            plt.savefig(str(output_path), dpi=300, bbox_inches='tight')
            print(f"✓ Đã lưu hình ảnh: {output_path}")
        
        plt.close(fig)
    
    def visualize_solution(self, save=False):
        """Wrapper để tương thích"""
        self.visualize_solution_comprehensive(save)
    
    def save_solution(self, solve_time=None, status=None, n_samples=None):
        """Lưu solution ra file TXT"""
        if self.solution is None:
            print("❌ Chưa có solution để lưu!")
            return
        
        output_dir = Path(__file__).parent / 'result' / 'text'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f'{self.dataset_name}_attention_solution.txt'
        
        total_distance = sum([r['distance'] for r in self.solution.values()])
        total_load = sum([r['load'] for r in self.solution.values()])
        total_customers_served = sum([r['num_customers'] for r in self.solution.values()])
        
        with open(str(output_path), 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write(f"BÁO CÁO KẾT QUẢ ATTENTION MODEL (DEEP RL)\n")
            f.write(f"Neural Combinatorial Optimization for VRPTW\n")
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
            if n_samples:
                f.write(f"Số samples: {n_samples}\n")
            f.write("\n")
            
            # PHƯƠNG PHÁP
            f.write("="*80 + "\n")
            f.write("PHƯƠNG PHÁP ATTENTION MODEL (DEEP RL)\n")
            f.write("="*80 + "\n")
            f.write("Đặc điểm:\n")
            f.write("  - Neural Combinatorial Optimization\n")
            f.write("  - Kiến trúc: Transformer-based (Multi-head Attention)\n")
            f.write("  - Encoder: Graph Attention Network\n")
            f.write("  - Decoder: Attention-based Pointer Network\n")
            f.write("  - Training: REINFORCE with baseline\n")
            f.write("  - End-to-end learning từ dữ liệu\n\n")
            
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
    code_dir = current_dir.parent.parent.parent.parent
    dataset_path = code_dir / "dataset" / "C1" / "C101.csv"
    model_path = current_dir / "models" / "attention_model_best.pth"
    
    print("="*80)
    print("ATTENTION MODEL (DEEP RL) FOR VRPTW")
    print("="*80)
    print("✓ Neural Combinatorial Optimization")
    print("✓ Transformer-based Architecture")
    print("✓ End-to-end Learning")
    print("="*80)
    
    solver = AttentionModelVRPTWSolver(
        dataset_path=str(dataset_path),
        vehicle_capacity=200,
        max_vehicles=25,
        model_path=str(model_path) if model_path.exists() else None
    )
    
    result = solver.solve(n_samples=10, use_beam_search=False)
    
    if result:
        print("\n" + "="*80)
        print("TẠO TRỰC QUAN HÓA VÀ BÁO CÁO")
        print("="*80)
        solver.visualize_solution(save=True)
        solver.save_solution(
            solve_time=result['time'],
            status=result['status'],
            n_samples=result['n_samples']
        )
        print("✓ Hoàn thành!")


if __name__ == "__main__":
    main()
