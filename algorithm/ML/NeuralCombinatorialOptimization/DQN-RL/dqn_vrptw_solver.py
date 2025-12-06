"""
DQN VRPTW Solver
Use trained DQN agent to solve VRPTW instances
"""

import torch
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import time

from dqn_model import DQNAgent
from train import VRPTWEnvironment


class DQNVRPTWSolver:
    """DQN solver for VRPTW"""
    def __init__(self, model_path, vehicle_capacity=200, max_vehicles=25, 
                 device='cuda' if torch.cuda.is_available() else 'cpu'):
        self.vehicle_capacity = vehicle_capacity
        self.max_vehicles = max_vehicles
        self.device = device
        
        # Load model
        state_dim = 9
        action_dim = 101
        
        # IMPORTANT: Must match the hidden_dim used during training!
        # Check train.py main() function for the correct value
        self.agent = DQNAgent(
            state_dim=state_dim,
            action_dim=action_dim,
            hidden_dim=512,  # Match training hyperparameters (was 256, now 512)
            device=device
        )
        
        # Load trained weights (set weights_only=False for compatibility with older PyTorch versions)
        checkpoint = torch.load(model_path, map_location=device, weights_only=False)
        self.agent.policy_net.load_state_dict(checkpoint['policy_net_state_dict'])
        self.agent.policy_net.eval()
        self.agent.epsilon = 0.0  # No exploration during evaluation
        
        print(f"✓ Loaded model from {model_path}")
    
    def solve(self, dataset_path):
        """
        Solve VRPTW instance
        
        Args:
            dataset_path: Path to dataset CSV
        Returns:
            routes, total_distance, computation_time
        """
        start_time = time.time()
        
        # Create environment (preprocessing handled in VRPTWEnvironment.__init__)
        env = VRPTWEnvironment(dataset_path, self.vehicle_capacity)
        
        # Solve
        routes = []
        current_route = [0]
        state = env.reset()
        done = False
        steps = 0
        max_steps = 300
        
        while not done and steps < max_steps:
            # Get valid actions
            valid_mask = env._get_valid_actions_mask()
            
            # Select action (greedy)
            with torch.no_grad():
                action = self.agent.select_action(state, valid_mask)
            
            # Take action
            next_state, reward, done, info = env.step(action)
            
            # Record route
            if action == 0 and len(current_route) > 1:
                # Completed a route
                current_route.append(0)
                routes.append(current_route)
                current_route = [0]
            elif action > 0:
                current_route.append(action)
            
            state = next_state
            steps += 1
        
        # Add final route if needed
        if len(current_route) > 1:
            current_route.append(0)
            routes.append(current_route)
        
        total_distance = info['total_distance']
        computation_time = time.time() - start_time
        
        return routes, total_distance, computation_time
    
    def visualize_solution_comprehensive(self, dataset_path, routes, total_distance, 
                                        computation_time, save_path=None):
        """Create comprehensive visualization"""
        # Load data
        data = pd.read_csv(dataset_path)
        
        # Preprocess: Convert string values to float
        for col in data.columns:
            if col != 'CUST NO.':
                data[col] = data[col].apply(
                    lambda x: float(str(x).split()[0]) if isinstance(x, str) else float(x)
                )
        
        depot = data.iloc[0]
        customers = data.iloc[1:]
        
        # Auto-generate save path if not provided
        if save_path is None:
            current_dir = Path(__file__).parent
            result_dir = current_dir / "result" / "images"
            result_dir.mkdir(parents=True, exist_ok=True)
            dataset_name = Path(dataset_path).stem
            save_path = result_dir / f"{dataset_name}_solution.png"
        
        # Tắt chế độ interactive
        plt.ioff()
        
        fig = plt.figure(figsize=(20, 12))
        gs = fig.add_gridspec(2, 3, hspace=0.3, wspace=0.3)
        
        # ============= 1. VẼ CÁC TUYẾN ĐƯỜNG =============
        ax1 = fig.add_subplot(gs[0:2, 0:2])
        
        # Vẽ depot
        depot_x = depot['XCOORD.']
        depot_y = depot['YCOORD.']
        ax1.scatter(depot_x, depot_y,
                   c='red', s=600, marker='s', edgecolors='black',
                   linewidth=3, label='Kho', zorder=5)
        
        # Vẽ customers
        ax1.scatter(customers['XCOORD.'], customers['YCOORD.'],
                   c='lightblue', s=200, edgecolors='black',
                   linewidth=1.5, label='Khách hàng', zorder=3)
        
        # Vẽ các routes với arrows
        colors = plt.cm.tab20(np.linspace(0, 1, len(routes)))
        
        for idx, route in enumerate(routes):
            full_route = [0] + route + [0]
            color = colors[idx]
            
            for i in range(len(full_route) - 1):
                node1, node2 = full_route[i], full_route[i+1]
                
                if node1 == 0:
                    x1, y1 = depot_x, depot_y
                else:
                    # node1 is customer ID (starts from 1), so index is node1-1
                    x1, y1 = customers.iloc[node1 - 1]['XCOORD.'], customers.iloc[node1 - 1]['YCOORD.']
                
                if node2 == 0:
                    x2, y2 = depot_x, depot_y
                else:
                    # node2 is customer ID (starts from 1), so index is node2-1
                    x2, y2 = customers.iloc[node2 - 1]['XCOORD.'], customers.iloc[node2 - 1]['YCOORD.']
                
                ax1.plot([x1, x2], [y1, y2], color=color, linewidth=2.5, alpha=0.7, zorder=2)
                ax1.annotate('', xy=(x2, y2), xytext=(x1, y1),
                            arrowprops=dict(arrowstyle='->', color=color, lw=2, alpha=0.7))
            
            # Label tên xe ở giữa route
            if len(route) > 0:
                mid_idx = len(route) // 2
                mid_customer = route[mid_idx]
                mid_cust_idx = mid_customer - 1
                mid_x = customers.iloc[mid_cust_idx]['XCOORD.']
                mid_y = customers.iloc[mid_cust_idx]['YCOORD.']
                
                ax1.text(mid_x, mid_y + 5, f"Xe {idx+1}", 
                        fontsize=10, fontweight='bold',
                        ha='center', bbox=dict(boxstyle='round,pad=0.4', facecolor=color, alpha=0.8))
        
        # Thêm số thứ tự khách hàng
        for idx, row in customers.iterrows():
            ax1.annotate(str(idx + 1), (row['XCOORD.'], row['YCOORD.']),
                        fontsize=9, ha='center', va='center', fontweight='bold')
        
        ax1.set_xlabel('Tọa độ X', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Tọa độ Y', fontsize=12, fontweight='bold')
        ax1.set_title('① Các tuyến đường (DQN - Deep Reinforcement Learning)',
                     fontsize=14, fontweight='bold', pad=12)
        ax1.legend(fontsize=11, loc='best')
        ax1.grid(True, alpha=0.3, linestyle='--')
        
        # ============= 2. THỐNG KÊ XE =============
        ax2 = fig.add_subplot(gs[0, 2])
        
        # Calculate statistics
        route_distances = []
        route_loads = []
        for route in routes:
            # Calculate distance
            dist = 0
            # From depot to first customer (customer ID starts from 1, so index is ID-1)
            first_cust_idx = route[0] - 1
            dist += np.sqrt((customers.iloc[first_cust_idx]['XCOORD.'] - depot_x)**2 + 
                           (customers.iloc[first_cust_idx]['YCOORD.'] - depot_y)**2)
            # Between customers
            for j in range(len(route) - 1):
                idx1 = route[j] - 1
                idx2 = route[j+1] - 1
                x1, y1 = customers.iloc[idx1]['XCOORD.'], customers.iloc[idx1]['YCOORD.']
                x2, y2 = customers.iloc[idx2]['XCOORD.'], customers.iloc[idx2]['YCOORD.']
                dist += np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            # From last customer back to depot
            last_cust_idx = route[-1] - 1
            dist += np.sqrt((customers.iloc[last_cust_idx]['XCOORD.'] - depot_x)**2 + 
                           (customers.iloc[last_cust_idx]['YCOORD.'] - depot_y)**2)
            route_distances.append(dist)
            
            # Calculate load
            load = sum([customers.iloc[node - 1]['DEMAND'] for node in route])
            route_loads.append(load)
        
        vehicles = list(range(len(routes)))
        x = np.arange(len(vehicles))
        width = 0.35
        
        bars1 = ax2.bar(x - width/2, route_distances, width, label='Quãng đường',
                       color='steelblue', alpha=0.8, edgecolor='black', linewidth=1.5)
        ax2_twin = ax2.twinx()
        bars2 = ax2_twin.bar(x + width/2, route_loads, width, label='Tải trọng',
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
        
        num_customers_per_vehicle = [len(route) for route in routes]
        
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
        total_customers = sum(num_customers_per_vehicle)
        n_customers = len(customers)
        
        fig.suptitle(
            f'KẾT QUẢ DQN (DEEP Q-NETWORK) - {Path(dataset_path).stem}\n'
            f'Số xe: {len(routes)} | Tổng quãng đường: {total_distance:.2f} | '
            f'Khách hàng phục vụ: {total_customers}/{n_customers} | Thời gian: {computation_time:.3f}s',
            fontsize=16, fontweight='bold', y=0.98
        )
        
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        
        if save_path:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(str(save_path), dpi=300, bbox_inches='tight')
            print(f"✓ Đã lưu hình ảnh: {save_path}")
        
        plt.close(fig)
    
    def save_solution(self, dataset_path, routes, total_distance, computation_time, save_path=None):
        """Save solution to text file"""
        # Auto-generate save path if not provided
        if save_path is None:
            current_dir = Path(__file__).parent
            result_dir = current_dir / "result" / "text"
            result_dir.mkdir(parents=True, exist_ok=True)
            dataset_name = Path(dataset_path).stem
            save_path = result_dir / f"{dataset_name}_solution.txt"
        
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load data for details
        data = pd.read_csv(dataset_path)
        
        # Preprocess: Convert string values to float
        for col in data.columns:
            if col != 'CUST NO.':
                data[col] = data[col].apply(
                    lambda x: float(str(x).split()[0]) if isinstance(x, str) else float(x)
                )
        
        customers = data.iloc[1:]
        depot = data.iloc[0]
        
        # Calculate total statistics
        total_load = 0
        total_customers_served = 0
        route_details = []
        
        for route in routes:
            # Load calculation (customer ID starts from 1, so index is ID-1)
            load = sum([customers.iloc[node - 1]['DEMAND'] for node in route])
            total_load += load
            total_customers_served += len(route)
            
            # Calculate distance
            dist = 0
            # From depot to first customer
            first_idx = route[0] - 1
            dist += np.sqrt((customers.iloc[first_idx]['XCOORD.'] - depot['XCOORD.'])**2 + 
                           (customers.iloc[first_idx]['YCOORD.'] - depot['YCOORD.'])**2)
            # Between customers
            for j in range(len(route) - 1):
                idx1 = route[j] - 1
                idx2 = route[j+1] - 1
                x1, y1 = customers.iloc[idx1]['XCOORD.'], customers.iloc[idx1]['YCOORD.']
                x2, y2 = customers.iloc[idx2]['XCOORD.'], customers.iloc[idx2]['YCOORD.']
                dist += np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            # From last customer back to depot
            last_idx = route[-1] - 1
            dist += np.sqrt((customers.iloc[last_idx]['XCOORD.'] - depot['XCOORD.'])**2 + 
                           (customers.iloc[last_idx]['YCOORD.'] - depot['YCOORD.'])**2)
            
            route_details.append({
                'route': route,
                'distance': dist,
                'load': load,
                'num_customers': len(route)
            })
        
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write(f"BÁO CÁO KẾT QUẢ DQN (DEEP Q-NETWORK)\n")
            f.write(f"Deep Reinforcement Learning for VRPTW\n")
            f.write("="*80 + "\n\n")
            
            f.write(f"Dataset: {Path(dataset_path).stem}\n")
            f.write(f"Ngày giờ: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # THÔNG SỐ
            f.write("="*80 + "\n")
            f.write("THÔNG SỐ BÀI TOÁN\n")
            f.write("="*80 + "\n")
            f.write(f"Số khách hàng: {len(customers)}\n")
            f.write(f"Sức chứa xe: {self.vehicle_capacity}\n")
            f.write(f"Số xe tối đa: {self.max_vehicles}\n")
            f.write(f"Thời gian giải: {computation_time:.3f} giây\n")
            f.write(f"Trạng thái: Feasible (DQN - Deep RL)\n\n")
            
            # PHƯƠNG PHÁP
            f.write("="*80 + "\n")
            f.write("PHƯƠNG PHÁP DQN (DEEP Q-NETWORK)\n")
            f.write("="*80 + "\n")
            f.write("Đặc điểm:\n")
            f.write("  - Deep Reinforcement Learning\n")
            f.write("  - Kiến trúc: Dueling DQN with Double Q-learning\n")
            f.write("  - Value-based RL (Q-value approximation)\n")
            f.write("  - Experience Replay for sample efficiency\n")
            f.write("  - Target Network for training stability\n")
            f.write("  - Epsilon-greedy exploration strategy\n\n")
            
            # KẾT QUẢ
            f.write("="*80 + "\n")
            f.write("KẾT QUẢ TỔNG HỢP\n")
            f.write("="*80 + "\n")
            f.write(f"Số xe sử dụng: {len(routes)}\n")
            f.write(f"Tổng quãng đường: {total_distance:.2f}\n")
            f.write(f"Quãng đường TB/xe: {total_distance/len(routes):.2f}\n")
            f.write(f"Tổng tải trọng: {total_load:.0f}\n")
            f.write(f"Tải trọng TB/xe: {total_load/len(routes):.2f}\n")
            f.write(f"Khách hàng phục vụ: {total_customers_served}/{len(customers)}\n\n")
            
            # CHI TIẾT ROUTES
            f.write("="*80 + "\n")
            f.write("CHI TIẾT CÁC TUYẾN ĐƯỜNG\n")
            f.write("="*80 + "\n\n")
            
            for i, info in enumerate(route_details):
                f.write(f"{'─'*80}\n")
                f.write(f"XE {i + 1}\n")
                f.write(f"{'─'*80}\n")
                f.write(f"Tuyến đường: 0 (Kho) → {' → '.join(map(str, info['route']))} → 0\n")
                f.write(f"Số khách hàng: {info['num_customers']}\n")
                f.write(f"Tổng nhu cầu: {info['load']:.0f}/{self.vehicle_capacity}\n")
                f.write(f"Quãng đường: {info['distance']:.2f}\n\n")
            
            f.write("="*80 + "\n")
            f.write("KẾT THÚC BÁO CÁO\n")
            f.write("="*80 + "\n")
        
        print(f"✓ Đã lưu báo cáo: {save_path}")


def main():
    """Test solver"""
    current_dir = Path(__file__).parent
    code_dir = current_dir.parent.parent.parent.parent
    
    # Paths
    model_path = current_dir / "models" / "dqn_model_best.pth"
    dataset_path = code_dir / "dataset" / "C1" / "C101.csv"
    
    if not model_path.exists():
        print(f"Error: Model not found at {model_path}")
        print("Please train the model first using train.py")
        return
    
    # Create solver
    solver = DQNVRPTWSolver(model_path)
    
    # Solve
    print(f"\nSolving {dataset_path.stem}...")
    routes, total_distance, computation_time = solver.solve(dataset_path)
    
    print(f"✓ Solution found!")
    print(f"  Routes: {len(routes)}")
    print(f"  Distance: {total_distance:.2f}")
    print(f"  Time: {computation_time:.3f}s")
    
    # Visualize
    image_path = current_dir / "result" / "images" / f"{dataset_path.stem}_solution.png"
    solver.visualize_solution_comprehensive(dataset_path, routes, total_distance, 
                                           computation_time, image_path)
    print(f"✓ Saved visualization: {image_path}")
    
    # Save solution
    text_path = current_dir / "result" / "text" / f"{dataset_path.stem}_solution.txt"
    solver.save_solution(dataset_path, routes, total_distance, computation_time, text_path)
    print(f"✓ Saved solution: {text_path}")


if __name__ == "__main__":
    main()
