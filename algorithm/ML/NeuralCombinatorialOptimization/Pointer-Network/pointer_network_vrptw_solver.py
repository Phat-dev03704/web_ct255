"""
Pointer Network VRPTW Solver
Uses trained Pointer Network model to solve VRPTW instances
"""

import os
import sys
import pandas as pd
import numpy as np
import torch
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
import matplotlib.gridspec as gridspec

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from pointer_network import PointerNetworkAgent


class PointerNetworkVRPTWSolver:
    """Solver using trained Pointer Network"""
    
    def __init__(self, model_path, vehicle_capacity=200, max_vehicles=25):
        """Initialize solver with trained model"""
        self.vehicle_capacity = vehicle_capacity
        self.max_vehicles = max_vehicles
        
        # Load model
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Create agent (parameters must match training)
        self.agent = PointerNetworkAgent(
            input_dim=6,
            hidden_dim=256,
            num_layers=2,
            dropout=0.1,
            learning_rate=1e-4,
            device=self.device
        )
        
        # Load trained weights
        if os.path.exists(model_path):
            self.agent.load(model_path)
            print(f"Loaded model from {model_path}")
        else:
            print(f"Warning: Model file not found at {model_path}")
            print("Using untrained model!")
    
    def load_dataset(self, dataset_path):
        """Load VRPTW dataset"""
        df = pd.read_csv(dataset_path)
        
        # Preprocessing: handle string format
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].apply(lambda x: float(str(x).split()[0]) if isinstance(x, str) else float(x))
        
        self.df = df
        self.depot = df.iloc[0]
        self.customers = df.iloc[1:]
        
        # Normalize features
        self.max_coord = 100.0
        self.max_demand = 200.0
        self.max_time = 1000.0
        
        return df
    
    def build_state(self):
        """Build state representation"""
        state_list = []
        
        # Depot
        depot_state = [
            self.depot['XCOORD.'] / self.max_coord,
            self.depot['YCOORD.'] / self.max_coord,
            0.0,
            self.depot['READY TIME'] / self.max_time,
            self.depot['DUE DATE'] / self.max_time,
            self.depot['SERVICE TIME'] / self.max_time
        ]
        state_list.append(depot_state)
        
        # Customers
        for idx, row in self.customers.iterrows():
            customer_state = [
                row['XCOORD.'] / self.max_coord,
                row['YCOORD.'] / self.max_coord,
                row['DEMAND'] / self.max_demand,
                row['READY TIME'] / self.max_time,
                row['DUE DATE'] / self.max_time,
                row['SERVICE TIME'] / self.max_time
            ]
            state_list.append(customer_state)
        
        return np.array(state_list, dtype=np.float32)
    
    def solve(self, dataset_path):
        """
        Solve VRPTW instance
        Returns: routes, total_distance, computation_time
        """
        import time
        start_time = time.time()
        
        # Load dataset
        self.load_dataset(dataset_path)
        
        # Build state
        state = self.build_state()
        state_batch = np.expand_dims(state, 0)  # [1, num_nodes, input_dim]
        
        # Get action sequence using greedy decoding
        actions_batch, _ = self.agent.select_action(state_batch, mask=None, greedy=True)
        actions = actions_batch[0]
        
        # Convert actions to routes
        routes = self._actions_to_routes(actions)
        
        # Calculate total distance
        total_distance = self._calculate_total_distance(routes)
        
        computation_time = time.time() - start_time
        
        return routes, total_distance, computation_time
    
    def _actions_to_routes(self, actions):
        """Convert action sequence to routes"""
        routes = []
        current_route = []
        current_load = 0
        
        visited = set([0])
        
        for action in actions:
            if action == 0:  # Return to depot
                if len(current_route) > 0:
                    routes.append(current_route.copy())
                    current_route = []
                    current_load = 0
            else:
                # Visit customer
                if action in visited:
                    continue
                
                customer_idx = action - 1
                customer = self.customers.iloc[customer_idx]
                demand = customer['DEMAND']
                
                # Check capacity
                if current_load + demand > self.vehicle_capacity:
                    # Start new route
                    if len(current_route) > 0:
                        routes.append(current_route.copy())
                        current_route = []
                        current_load = 0
                
                current_route.append(action)
                current_load += demand
                visited.add(action)
        
        # Add last route
        if len(current_route) > 0:
            routes.append(current_route)
        
        return routes
    
    def _calculate_distance(self, node1_idx, node2_idx):
        """Calculate distance between two nodes"""
        if node1_idx == 0:
            node1 = self.depot
        else:
            node1 = self.customers.iloc[node1_idx - 1]
        
        if node2_idx == 0:
            node2 = self.depot
        else:
            node2 = self.customers.iloc[node2_idx - 1]
        
        dx = node1['XCOORD.'] - node2['XCOORD.']
        dy = node1['YCOORD.'] - node2['YCOORD.']
        
        return np.sqrt(dx * dx + dy * dy)
    
    def _calculate_total_distance(self, routes):
        """Calculate total distance of all routes"""
        total_distance = 0.0
        
        for route in routes:
            # Depot to first customer
            total_distance += self._calculate_distance(0, route[0])
            
            # Between customers
            for i in range(len(route) - 1):
                total_distance += self._calculate_distance(route[i], route[i+1])
            
            # Last customer to depot
            total_distance += self._calculate_distance(route[-1], 0)
        
        return total_distance
    
    def visualize_solution_comprehensive(self, routes, total_distance, save_path=None):
        """
        Comprehensive visualization matching Attention Model style
        3 subplots: routes (2x2), statistics chart, pie chart
        """
        # Create figure with GridSpec (2 rows, 3 columns)
        fig = plt.figure(figsize=(18, 10))
        gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.3, wspace=0.3)
        
        # --- Subplot 1: Routes (spans 2 rows, 2 columns) ---
        ax_routes = fig.add_subplot(gs[0:2, 0:2])
        
        # Plot depot
        depot_x = self.depot['XCOORD.']
        depot_y = self.depot['YCOORD.']
        ax_routes.plot(depot_x, depot_y, 'rs', markersize=15, label='Depot', zorder=5)
        ax_routes.text(depot_x, depot_y + 3, '0', ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        # Plot customers
        customer_x = self.customers['XCOORD.'].values
        customer_y = self.customers['YCOORD.'].values
        ax_routes.scatter(customer_x, customer_y, c='lightblue', s=100, edgecolors='black', zorder=3, label='Customers')
        
        # Add customer numbers
        for i, (x, y) in enumerate(zip(customer_x, customer_y), 1):
            ax_routes.text(x, y, str(i), ha='center', va='center', fontsize=8)
        
        # Plot routes with different colors and arrows
        colors = plt.cm.tab20(np.linspace(0, 1, len(routes)))
        
        for vehicle_idx, route in enumerate(routes):
            color = colors[vehicle_idx]
            route_with_depot = [0] + route + [0]
            
            for i in range(len(route_with_depot) - 1):
                from_node = route_with_depot[i]
                to_node = route_with_depot[i + 1]
                
                # Get coordinates
                if from_node == 0:
                    x1, y1 = self.depot['XCOORD.'], self.depot['YCOORD.']
                else:
                    customer = self.customers.iloc[from_node - 1]
                    x1, y1 = customer['XCOORD.'], customer['YCOORD.']
                
                if to_node == 0:
                    x2, y2 = self.depot['XCOORD.'], self.depot['YCOORD.']
                else:
                    customer = self.customers.iloc[to_node - 1]
                    x2, y2 = customer['XCOORD.'], customer['YCOORD.']
                
                # Draw arrow
                arrow = FancyArrowPatch(
                    (x1, y1), (x2, y2),
                    arrowstyle='->', mutation_scale=20, linewidth=2,
                    color=color, zorder=2
                )
                ax_routes.add_patch(arrow)
        
        # Add route labels in legend
        for vehicle_idx in range(len(routes)):
            ax_routes.plot([], [], color=colors[vehicle_idx], linewidth=2, 
                          label=f'Vehicle {vehicle_idx + 1}')
        
        ax_routes.set_xlabel('X Coordinate', fontsize=12)
        ax_routes.set_ylabel('Y Coordinate', fontsize=12)
        ax_routes.set_title('Vehicle Routes', fontsize=14, fontweight='bold')
        ax_routes.legend(loc='best', fontsize=9, ncol=2)
        ax_routes.grid(True, alpha=0.3)
        ax_routes.set_aspect('equal')
        
        # --- Subplot 2: Statistics Chart (row 0, col 2) ---
        ax_stats = fig.add_subplot(gs[0, 2])
        
        # Calculate statistics for each route
        route_distances = []
        route_loads = []
        
        for route in routes:
            # Calculate route distance
            route_dist = self._calculate_distance(0, route[0])
            for i in range(len(route) - 1):
                route_dist += self._calculate_distance(route[i], route[i+1])
            route_dist += self._calculate_distance(route[-1], 0)
            route_distances.append(route_dist)
            
            # Calculate route load
            route_load = sum(self.customers.iloc[node - 1]['DEMAND'] for node in route)
            route_loads.append(route_load)
        
        # Plot with dual y-axis
        x_pos = np.arange(len(routes))
        ax_stats_twin = ax_stats.twinx()
        
        bars1 = ax_stats.bar(x_pos - 0.2, route_distances, 0.4, label='Distance', color='steelblue', alpha=0.8)
        bars2 = ax_stats_twin.bar(x_pos + 0.2, route_loads, 0.4, label='Load', color='orange', alpha=0.8)
        
        ax_stats.set_xlabel('Vehicle', fontsize=10)
        ax_stats.set_ylabel('Distance', fontsize=10, color='steelblue')
        ax_stats_twin.set_ylabel('Load', fontsize=10, color='orange')
        ax_stats.set_title('Route Statistics', fontsize=12, fontweight='bold')
        ax_stats.set_xticks(x_pos)
        ax_stats.set_xticklabels([f'V{i+1}' for i in range(len(routes))])
        ax_stats.tick_params(axis='y', labelcolor='steelblue')
        ax_stats_twin.tick_params(axis='y', labelcolor='orange')
        ax_stats.grid(True, alpha=0.3, axis='y')
        
        # Add value labels on bars
        for bar in bars1:
            height = bar.get_height()
            ax_stats.text(bar.get_x() + bar.get_width()/2., height,
                         f'{height:.1f}', ha='center', va='bottom', fontsize=7)
        
        for bar in bars2:
            height = bar.get_height()
            ax_stats_twin.text(bar.get_x() + bar.get_width()/2., height,
                              f'{int(height)}', ha='center', va='bottom', fontsize=7)
        
        # --- Subplot 3: Pie Chart (row 1, col 2) ---
        ax_pie = fig.add_subplot(gs[1, 2])
        
        # Calculate customers per vehicle
        customers_per_vehicle = [len(route) for route in routes]
        
        ax_pie.pie(customers_per_vehicle, labels=[f'V{i+1}' for i in range(len(routes))],
                   autopct='%1.1f%%', startangle=90, colors=colors)
        ax_pie.set_title('Customer Distribution', fontsize=12, fontweight='bold')
        
        # Overall title
        fig.suptitle(f'Pointer Network Solution - Total Distance: {total_distance:.2f}, Vehicles: {len(routes)}',
                     fontsize=16, fontweight='bold')
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"Visualization saved to {save_path}")
        else:
            plt.show()
        
        plt.close()
    
    def save_solution(self, routes, total_distance, save_path):
        """Save solution to text file"""
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("GIẢI PHÁP VRPTW SỬ DỤNG POINTER NETWORK\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"Tổng khoảng cách: {total_distance:.2f}\n")
            f.write(f"Số lượng xe: {len(routes)}\n")
            f.write(f"Số khách hàng được phục vụ: {sum(len(route) for route in routes)}/{len(self.customers)}\n\n")
            
            f.write("Chi tiết các tuyến đường:\n")
            f.write("-" * 80 + "\n\n")
            
            for vehicle_idx, route in enumerate(routes, 1):
                f.write(f"Xe {vehicle_idx}:\n")
                f.write(f"  Tuyến: 0 -> {' -> '.join(map(str, route))} -> 0\n")
                
                # Calculate route distance
                route_dist = self._calculate_distance(0, route[0])
                for i in range(len(route) - 1):
                    route_dist += self._calculate_distance(route[i], route[i+1])
                route_dist += self._calculate_distance(route[-1], 0)
                
                # Calculate route load
                route_load = sum(self.customers.iloc[node - 1]['DEMAND'] for node in route)
                
                f.write(f"  Khoảng cách: {route_dist:.2f}\n")
                f.write(f"  Tải trọng: {route_load:.0f}/{self.vehicle_capacity}\n")
                f.write(f"  Số khách hàng: {len(route)}\n\n")
        
        print(f"Solution saved to {save_path}")


def main():
    """Test solver on a single dataset"""
    # Paths
    model_path = os.path.join(os.path.dirname(__file__), 'models', 'pointer_network_best.pth')
    dataset_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'dataset', 'C1', 'C101.csv')
    
    # Create solver
    solver = PointerNetworkVRPTWSolver(model_path)
    
    # Solve
    print("Solving VRPTW instance...")
    routes, total_distance, comp_time = solver.solve(dataset_path)
    
    # Print results
    print("\n" + "="*80)
    print("SOLUTION SUMMARY")
    print("="*80)
    print(f"Total Distance: {total_distance:.2f}")
    print(f"Number of Vehicles: {len(routes)}")
    print(f"Customers Served: {sum(len(route) for route in routes)}/{len(solver.customers)}")
    print(f"Computation Time: {comp_time:.4f} seconds")
    print("="*80)
    
    # Visualize
    output_dir = os.path.join(os.path.dirname(__file__), 'result')
    os.makedirs(output_dir, exist_ok=True)
    
    image_path = os.path.join(output_dir, 'test_solution.png')
    solver.visualize_solution_comprehensive(routes, total_distance, image_path)
    
    # Save solution
    text_path = os.path.join(output_dir, 'test_solution.txt')
    solver.save_solution(routes, total_distance, text_path)


if __name__ == '__main__':
    main()
