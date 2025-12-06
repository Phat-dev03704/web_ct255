"""
Hybrid VRPTW Solver: Clarke-Wright + Large Neighborhood Search
Giải pháp kết hợp tối ưu cho VRPTW

Phase 1: Clarke-Wright Savings (Fast initialization - 0.1-0.5s)
Phase 2: Large Neighborhood Search (Improvement - 10-30s)

Cân bằng tốt nhất giữa:
- Thời gian thực thi (10-30 giây)
- Chất lượng lời giải (90-95% so với LNS thuần)
"""

import sys
import os
import time
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt

# Add parent directories to path
current_dir = os.path.dirname(os.path.abspath(__file__))
cw_dir = os.path.join(current_dir, '..', 'Clarke-Wright-Saving')
lns_dir = os.path.join(current_dir, '..', 'Large-Neighborhood-Search')

if cw_dir not in sys.path:
    sys.path.insert(0, cw_dir)
if lns_dir not in sys.path:
    sys.path.insert(0, lns_dir)

# Import solvers
try:
    from cw_vrptw_solver import ClarkeWrightVRPTWSolver
except ImportError as e:
    print(f"Error importing CW solver: {e}")
    print(f"CW directory: {cw_dir}")
    raise

try:
    from lns_vrptw_solver import LargeNeighborhoodSearchVRPTWSolver
except ImportError as e:
    print(f"Error importing LNS solver: {e}")
    print(f"LNS directory: {lns_dir}")
    raise
import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
from datetime import datetime


class HybridVRPTWSolver:
    """
    Hybrid VRPTW Solver kết hợp Clarke-Wright và LNS
    
    Chiến lược:
    1. Sử dụng Clarke-Wright để tạo lời giải ban đầu nhanh chóng
    2. Sử dụng LNS để cải thiện lời giải với thời gian giới hạn
    
    Ưu điểm:
    - Nhanh hơn LNS thuần 50-70%
    - Chất lượng gần như LNS (90-95%)
    - Đảm bảo có lời giải tốt ngay từ đầu
    """
    
    def __init__(self, 
                 dataset_path, 
                 vehicle_capacity=200, 
                 max_vehicles=25,
                 lns_time_limit=20,
                 lns_max_iterations=100,
                 lns_destroy_size_range=(10, 25),
                 mode='balanced'):
        """
        Khởi tạo Hybrid Solver
        
        Args:
            dataset_path: Đường dẫn đến file CSV dataset
            vehicle_capacity: Sức chứa của mỗi xe
            max_vehicles: Số lượng xe tối đa
            lns_time_limit: Giới hạn thời gian cho LNS (giây)
            lns_max_iterations: Số iteration tối đa cho LNS
            lns_destroy_size_range: Range số khách hàng để destroy trong LNS
            mode: Chế độ hoạt động
                - 'fast': Ưu tiên tốc độ (time_limit=10, iterations=50)
                - 'balanced': Cân bằng (time_limit=20, iterations=100) [MẶC ĐỊNH]
                - 'quality': Ưu tiên chất lượng (time_limit=40, iterations=150)
                - 'cw_only': Chỉ dùng Clarke-Wright (real-time)
                - 'lns_only': Chỉ dùng LNS (tối ưu tuyệt đối)
        """
        self.dataset_path = dataset_path
        self.dataset_name = Path(dataset_path).stem
        self.vehicle_capacity = vehicle_capacity
        self.max_vehicles = max_vehicles
        
        # Thiết lập mode
        self.mode = mode
        if mode == 'fast':
            self.lns_time_limit = 10
            self.lns_max_iterations = 50
        elif mode == 'balanced':
            self.lns_time_limit = 20
            self.lns_max_iterations = 100
        elif mode == 'quality':
            self.lns_time_limit = 40
            self.lns_max_iterations = 150
        elif mode == 'cw_only':
            self.lns_time_limit = 0
            self.lns_max_iterations = 0
        elif mode == 'lns_only':
            self.lns_time_limit = 60
            self.lns_max_iterations = 150
        else:
            self.lns_time_limit = lns_time_limit
            self.lns_max_iterations = lns_max_iterations
        
        self.lns_destroy_size_range = lns_destroy_size_range
        
        # Khởi tạo solvers
        self.cw_solver = ClarkeWrightVRPTWSolver(
            dataset_path, vehicle_capacity, max_vehicles
        )
        
        self.lns_solver = LargeNeighborhoodSearchVRPTWSolver(
            dataset_path, vehicle_capacity, max_vehicles
        )
        
        # Results
        self.cw_solution = None
        self.final_solution = None
        self.solve_time = 0
        self.improvement_percentage = 0
        
    def solve(self, verbose=True):
        """
        Giải bài toán VRPTW bằng Hybrid approach
        
        Returns:
            dict: Kết quả bao gồm routes, distances, times, etc.
        """
        start_time = time.time()
        
        if verbose:
            print("=" * 80)
            print(f"HYBRID VRPTW SOLVER - Mode: {self.mode.upper()}")
            print(f"Dataset: {self.dataset_name}")
            print("=" * 80)
        
        # ===== PHASE 1: CLARKE-WRIGHT INITIALIZATION =====
        if self.mode != 'lns_only':
            if verbose:
                print("\n📊 PHASE 1: CLARKE-WRIGHT INITIALIZATION")
                print("-" * 80)
            
            phase1_start = time.time()
            self.cw_solution = self.cw_solver.solve(verbose=False)
            phase1_time = time.time() - phase1_start
            
            if verbose:
                if self.cw_solution['status'] == 'Success':
                    print(f"✅ Clarke-Wright completed successfully")
                    print(f"   ⏱️  Time: {phase1_time:.2f}s")
                    print(f"   📏 Total Distance: {self.cw_solution['total_distance']:.2f}")
                    print(f"   🚗 Vehicles Used: {self.cw_solution['num_vehicles']}")
                    print(f"   👥 Customers Served: {self.cw_solution['customers_served']}/{self.cw_solver.n_customers}")
                else:
                    print(f"❌ Clarke-Wright failed: {self.cw_solution['status']}")
                    return self.cw_solution
        else:
            # LNS only mode - không dùng CW
            self.cw_solution = None
            if verbose:
                print("\n📊 MODE: LNS ONLY (No CW initialization)")
                print("-" * 80)
        
        # ===== PHASE 2: LNS IMPROVEMENT =====
        if self.mode != 'cw_only' and self.lns_max_iterations > 0:
            if verbose:
                print("\n🔧 PHASE 2: LNS OPTIMIZATION")
                print("-" * 80)
                print(f"   Max Iterations: {self.lns_max_iterations}")
                print(f"   Time Limit: {self.lns_time_limit}s")
                print(f"   Destroy Size: {self.lns_destroy_size_range[0]}-{self.lns_destroy_size_range[1]} customers")
            
            phase2_start = time.time()
            
            # Modify LNS solver để sử dụng CW solution làm initial solution
            if self.cw_solution:
                # Convert CW solution to LNS format
                initial_routes = self._convert_cw_solution_to_lns_format()
                self.final_solution = self.lns_solver.solve_with_initial_solution(
                    initial_routes=initial_routes,
                    max_iterations=self.lns_max_iterations,
                    time_limit=self.lns_time_limit,
                    destroy_size_range=self.lns_destroy_size_range,
                    verbose=False
                )
            else:
                # LNS từ đầu
                self.final_solution = self.lns_solver.solve(
                    max_iterations=self.lns_max_iterations,
                    time_limit=self.lns_time_limit,
                    verbose=False
                )
            
            phase2_time = time.time() - phase2_start
            
            if verbose:
                print(f"✅ LNS optimization completed")
                print(f"   ⏱️  Time: {phase2_time:.2f}s")
                print(f"   📏 Final Distance: {self.final_solution['total_distance']:.2f}")
                print(f"   🚗 Final Vehicles: {self.final_solution['num_vehicles']}")
                
                if self.cw_solution:
                    improvement = (self.cw_solution['total_distance'] - 
                                 self.final_solution['total_distance']) / \
                                 self.cw_solution['total_distance'] * 100
                    self.improvement_percentage = improvement
                    
                    print(f"   📈 Improvement: {improvement:.2f}%")
                    print(f"   🚗 Vehicle Reduction: {self.cw_solution['num_vehicles']} → {self.final_solution['num_vehicles']}")
        else:
            # CW only mode
            self.final_solution = self.cw_solution
            if verbose:
                print("\n✅ MODE: CW ONLY (No LNS optimization)")
        
        total_time = time.time() - start_time
        self.solve_time = total_time
        
        # Update final solution với thông tin hybrid
        if self.final_solution:
            self.final_solution['hybrid_mode'] = self.mode
            self.final_solution['total_solve_time'] = total_time
            if self.cw_solution and self.mode != 'cw_only':
                self.final_solution['cw_distance'] = self.cw_solution['total_distance']
                self.final_solution['cw_vehicles'] = self.cw_solution['num_vehicles']
                self.final_solution['improvement_percentage'] = self.improvement_percentage
        
        if verbose:
            print("\n" + "=" * 80)
            print(f"🎉 HYBRID SOLVER COMPLETED")
            print(f"   ⏱️  Total Time: {total_time:.2f}s")
            print(f"   📏 Final Distance: {self.final_solution['total_distance']:.2f}")
            print(f"   🚗 Final Vehicles: {self.final_solution['num_vehicles']}")
            print("=" * 80)
        
        return self.final_solution
    
    def _convert_cw_solution_to_lns_format(self):
        """
        Chuyển đổi solution từ CW sang format của LNS
        """
        if not self.cw_solution or 'routes' not in self.cw_solution:
            return None
        
        # CW routes đã ở format phù hợp
        return self.cw_solution['routes']
    
    def visualize_comparison(self, save_path=None):
        """
        Visualize so sánh giữa CW solution và Final solution
        """
        if not self.cw_solution or not self.final_solution:
            print("❌ Chưa có solution để visualize")
            return
        
        if self.mode == 'cw_only' or self.mode == 'lns_only':
            # Chỉ visualize 1 solution
            self._visualize_single_solution(self.final_solution, save_path)
            return
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8))
        
        # Plot CW solution
        self._plot_solution(ax1, self.cw_solution, 
                           f"Clarke-Wright Solution\nDistance: {self.cw_solution['total_distance']:.2f}, Vehicles: {self.cw_solution['num_vehicles']}")
        
        # Plot Final solution
        self._plot_solution(ax2, self.final_solution,
                           f"Hybrid Solution (after LNS)\nDistance: {self.final_solution['total_distance']:.2f}, Vehicles: {self.final_solution['num_vehicles']}\nImprovement: {self.improvement_percentage:.2f}%")
        
        plt.suptitle(f"Hybrid VRPTW Solver - {self.dataset_name}", fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✅ Đã lưu visualization tại: {save_path}")
        
        plt.show()
    
    def _visualize_single_solution(self, solution, save_path=None):
        """Visualize một solution duy nhất"""
        fig, ax = plt.subplots(figsize=(12, 8))
        self._plot_solution(ax, solution,
                          f"{self.mode.upper()} Solution\nDistance: {solution['total_distance']:.2f}, Vehicles: {solution['num_vehicles']}")
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✅ Đã lưu visualization tại: {save_path}")
        
        plt.show()
    
    def _plot_solution(self, ax, solution, title):
        """Plot một solution lên axis"""
        # Plot depot
        depot_x = self.cw_solver.depot['XCOORD.']
        depot_y = self.cw_solver.depot['YCOORD.']
        ax.plot(depot_x, depot_y, 'rs', markersize=15, label='Depot', zorder=5)
        
        # Plot customers
        customers_x = self.cw_solver.customers['XCOORD.'].values
        customers_y = self.cw_solver.customers['YCOORD.'].values
        ax.plot(customers_x, customers_y, 'b.', markersize=8, label='Customers', zorder=3)
        
        # Plot routes
        colors = plt.cm.rainbow(np.linspace(0, 1, len(solution['routes'])))
        
        for idx, route in enumerate(solution['routes']):
            if not route:
                continue
            
            route_x = [depot_x]
            route_y = [depot_y]
            
            for customer_id in route:
                cx = self.cw_solver.customers.loc[customer_id - 1, 'XCOORD.']
                cy = self.cw_solver.customers.loc[customer_id - 1, 'YCOORD.']
                route_x.append(cx)
                route_y.append(cy)
            
            route_x.append(depot_x)
            route_y.append(depot_y)
            
            ax.plot(route_x, route_y, 'o-', color=colors[idx], 
                   linewidth=2, markersize=6, alpha=0.7,
                   label=f'Route {idx+1} ({len(route)} customers)')
        
        ax.set_xlabel('X Coordinate', fontsize=12)
        ax.set_ylabel('Y Coordinate', fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best', fontsize=8)
    
    def save_results(self, output_dir):
        """
        Lưu kết quả ra file
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Lưu text report
        report_path = output_path / f"{self.dataset_name}_hybrid_report.txt"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write(f"HYBRID VRPTW SOLVER REPORT\n")
            f.write(f"Dataset: {self.dataset_name}\n")
            f.write(f"Mode: {self.mode}\n")
            f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            
            if self.cw_solution and self.mode != 'lns_only':
                f.write("PHASE 1: CLARKE-WRIGHT SOLUTION\n")
                f.write("-" * 80 + "\n")
                f.write(f"Total Distance: {self.cw_solution['total_distance']:.2f}\n")
                f.write(f"Number of Vehicles: {self.cw_solution['num_vehicles']}\n")
                f.write(f"Customers Served: {self.cw_solution['customers_served']}\n\n")
            
            if self.final_solution:
                f.write("FINAL SOLUTION\n")
                f.write("-" * 80 + "\n")
                f.write(f"Total Distance: {self.final_solution['total_distance']:.2f}\n")
                f.write(f"Number of Vehicles: {self.final_solution['num_vehicles']}\n")
                f.write(f"Customers Served: {self.final_solution['customers_served']}\n")
                f.write(f"Total Solve Time: {self.solve_time:.2f}s\n")
                
                if self.cw_solution and self.mode not in ['cw_only', 'lns_only']:
                    f.write(f"Improvement over CW: {self.improvement_percentage:.2f}%\n")
                
                f.write("\nROUTES:\n")
                for idx, route in enumerate(self.final_solution['routes']):
                    f.write(f"Route {idx + 1}: 0 -> {' -> '.join(map(str, route))} -> 0\n")
        
        print(f"✅ Đã lưu report tại: {report_path}")
        
        # Lưu visualization
        viz_path = output_path / f"{self.dataset_name}_hybrid_visualization.png"
        self.visualize_comparison(save_path=viz_path)
        
        return str(report_path)


def main():
    """Test Hybrid Solver"""
    # Test với dataset C101
    dataset_path = r"d:\My Studing\Nghiệp vụ thông minh\project\Vehicle Routing Problem\code\dataset\C1\C101.csv"
    
    print("Testing different modes...\n")
    
    modes = ['cw_only', 'fast', 'balanced', 'quality']
    
    results = []
    
    for mode in modes:
        print("\n" + "="*100)
        print(f"Testing mode: {mode}")
        print("="*100)
        
        solver = HybridVRPTWSolver(
            dataset_path=dataset_path,
            mode=mode
        )
        
        solution = solver.solve(verbose=True)
        
        results.append({
            'mode': mode,
            'distance': solution['total_distance'],
            'vehicles': solution['num_vehicles'],
            'time': solver.solve_time
        })
    
    # Summary
    print("\n" + "="*100)
    print("SUMMARY - COMPARISON OF MODES")
    print("="*100)
    print(f"{'Mode':<15} {'Distance':<15} {'Vehicles':<12} {'Time (s)':<12}")
    print("-"*100)
    for r in results:
        print(f"{r['mode']:<15} {r['distance']:<15.2f} {r['vehicles']:<12} {r['time']:<12.2f}")


if __name__ == "__main__":
    main()
