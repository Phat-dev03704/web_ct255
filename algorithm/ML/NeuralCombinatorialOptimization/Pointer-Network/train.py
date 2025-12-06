"""
Training script for Pointer Network on VRPTW
"""

import os
import sys
import pandas as pd
import numpy as np
import torch
from datetime import datetime
import matplotlib.pyplot as plt

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from pointer_network import PointerNetworkAgent


class VRPTWEnvironment:
    """VRPTW Environment for training Pointer Network"""
    
    def __init__(self, dataset_path, vehicle_capacity=200, max_vehicles=25):
        """Initialize environment with dataset"""
        self.vehicle_capacity = vehicle_capacity
        self.max_vehicles = max_vehicles
        
        # Load dataset
        df = pd.read_csv(dataset_path)
        
        # Preprocessing: handle string format like "0.00    1"
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].apply(lambda x: float(str(x).split()[0]) if isinstance(x, str) else float(x))
        
        self.customers = df.iloc[1:].copy()  # Skip depot
        self.depot = df.iloc[0].copy()
        self.n_customers = len(self.customers)
        
        # Normalize features for better learning
        self.max_coord = 100.0
        self.max_demand = 200.0
        self.max_time = 1000.0
        
        # Build state representation
        self._build_state()
        
    def _build_state(self):
        """Build normalized state representation"""
        # Features: [x, y, demand, ready_time, due_date, service_time]
        state_list = []
        
        # Add depot
        depot_state = [
            self.depot['XCOORD.'] / self.max_coord,
            self.depot['YCOORD.'] / self.max_coord,
            0.0,  # demand
            self.depot['READY TIME'] / self.max_time,
            self.depot['DUE DATE'] / self.max_time,
            self.depot['SERVICE TIME'] / self.max_time
        ]
        state_list.append(depot_state)
        
        # Add customers
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
        
        self.state = np.array(state_list, dtype=np.float32)
        
    def get_state(self):
        """Get current state"""
        return self.state.copy()
    
    def get_mask(self, visited, current_load, current_time):
        """
        Get mask for valid actions
        Args:
            visited: set of visited customer indices
            current_load: current vehicle load
            current_time: current time
        Returns:
            mask: [num_nodes] - 1 for valid, 0 for invalid
        """
        mask = np.ones(len(self.state), dtype=np.float32)
        
        # Mask visited customers
        for idx in visited:
            mask[idx] = 0.0
        
        # Mask customers that violate capacity constraint
        for i in range(1, len(self.state)):
            if i not in visited:
                demand = self.customers.iloc[i-1]['DEMAND']
                if current_load + demand > self.vehicle_capacity:
                    mask[i] = 0.0
        
        # Always allow returning to depot
        mask[0] = 1.0
        
        return mask
    
    def calculate_distance(self, node1_idx, node2_idx):
        """Calculate Euclidean distance between two nodes"""
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
    
    def evaluate_solution(self, action_sequence):
        """
        Evaluate a solution (action sequence)
        Returns: (total_distance, num_vehicles, feasible, time_window_violations)
        """
        routes = []
        current_route = []
        current_load = 0
        current_time = 0.0
        current_pos = 0  # Start at depot
        
        time_window_violations = 0
        total_distance = 0.0
        
        visited = set([0])  # Depot is always visited
        
        for action in action_sequence:
            if action == 0:  # Return to depot
                if len(current_route) > 0:
                    # Complete current route
                    dist = self.calculate_distance(current_pos, 0)
                    total_distance += dist
                    current_time += dist
                    
                    routes.append(current_route.copy())
                    current_route = []
                    current_load = 0
                    current_time = 0.0
                    current_pos = 0
            else:
                # Visit customer
                if action in visited:
                    continue  # Skip already visited customers
                
                customer_idx = action - 1
                customer = self.customers.iloc[customer_idx]
                
                # Check capacity
                if current_load + customer['DEMAND'] > self.vehicle_capacity:
                    # Must return to depot first
                    if len(current_route) > 0:
                        dist = self.calculate_distance(current_pos, 0)
                        total_distance += dist
                        current_time += dist
                        
                        routes.append(current_route.copy())
                        current_route = []
                        current_load = 0
                        current_time = 0.0
                        current_pos = 0
                
                # Travel to customer
                dist = self.calculate_distance(current_pos, action)
                total_distance += dist
                current_time += dist
                
                # Check time window
                if current_time < customer['READY TIME']:
                    current_time = customer['READY TIME']
                elif current_time > customer['DUE DATE']:
                    time_window_violations += 1
                
                # Service customer
                current_time += customer['SERVICE TIME']
                current_load += customer['DEMAND']
                current_route.append(action)
                visited.add(action)
                current_pos = action
        
        # Return to depot for last route
        if len(current_route) > 0:
            dist = self.calculate_distance(current_pos, 0)
            total_distance += dist
            routes.append(current_route)
        
        num_vehicles = len(routes)
        feasible = (time_window_violations == 0 and num_vehicles <= self.max_vehicles)
        
        return total_distance, num_vehicles, feasible, time_window_violations, visited


def train_episode(agent, env, max_steps=None):
    """Train one episode"""
    if max_steps is None:
        max_steps = env.n_customers + 10
    
    # Get initial state and mask
    state = env.get_state()
    visited = set([0])
    current_load = 0
    current_time = 0.0
    
    # Prepare batch (single instance for now)
    states_batch = np.expand_dims(state, 0)  # [1, num_nodes, input_dim]
    
    # Generate initial mask
    mask = env.get_mask(visited, current_load, current_time)
    masks_batch = np.expand_dims(mask, 0)  # [1, num_nodes]
    
    # Get action sequence from model
    actions_batch, log_probs_batch = agent.select_action(states_batch, masks_batch, greedy=False)
    actions = actions_batch[0]  # [seq_len]
    
    # Limit to max_steps
    actions = actions[:max_steps]
    
    # Evaluate solution
    total_distance, num_vehicles, feasible, tw_violations, visited = env.evaluate_solution(actions)
    
    # Compute reward (negative distance with penalties)
    reward = -total_distance / 10.0  # Scale down
    
    # Penalty for infeasibility
    if not feasible:
        reward -= 1000.0
        reward -= tw_violations * 100.0
    
    # Penalty for using too many vehicles
    reward -= num_vehicles * 50.0
    
    # Bonus for serving more customers
    reward += len(visited) * 5.0
    
    rewards_batch = np.array([reward], dtype=np.float32)
    
    # Update model
    loss = agent.update(states_batch, actions_batch[:, :max_steps], rewards_batch, masks_batch)
    
    return loss, reward, total_distance, num_vehicles, len(visited)


def train(agent, dataset_paths, num_episodes=2000, eval_interval=100, save_dir='./models'):
    """
    Train Pointer Network on multiple datasets
    Args:
        agent: PointerNetworkAgent
        dataset_paths: list of dataset paths
        num_episodes: number of training episodes
        eval_interval: evaluate every N episodes
        save_dir: directory to save models
    """
    os.makedirs(save_dir, exist_ok=True)
    
    # Training history
    history = {
        'episode': [],
        'loss': [],
        'reward': [],
        'distance': [],
        'num_vehicles': [],
        'customers_served': []
    }
    
    best_distance = float('inf')
    
    print("="*80)
    print("POINTER NETWORK TRAINING FOR VRPTW")
    print("="*80)
    print(f"Number of training datasets: {len(dataset_paths)}")
    print(f"Number of episodes: {num_episodes}")
    print(f"Device: {agent.device}")
    print("="*80)
    
    for episode in range(1, num_episodes + 1):
        # Randomly select a dataset
        dataset_path = np.random.choice(dataset_paths)
        env = VRPTWEnvironment(dataset_path)
        
        # Train one episode
        loss, reward, distance, num_vehicles, customers_served = train_episode(agent, env)
        
        # Record history
        history['episode'].append(episode)
        history['loss'].append(loss)
        history['reward'].append(reward)
        history['distance'].append(distance)
        history['num_vehicles'].append(num_vehicles)
        history['customers_served'].append(customers_served)
        
        # Print progress
        if episode % eval_interval == 0:
            avg_loss = np.mean(history['loss'][-eval_interval:])
            avg_reward = np.mean(history['reward'][-eval_interval:])
            avg_distance = np.mean(history['distance'][-eval_interval:])
            avg_vehicles = np.mean(history['num_vehicles'][-eval_interval:])
            avg_customers = np.mean(history['customers_served'][-eval_interval:])
            
            print(f"Episode {episode}/{num_episodes}")
            print(f"  Avg Loss: {avg_loss:.4f}")
            print(f"  Avg Reward: {avg_reward:.2f}")
            print(f"  Avg Distance: {avg_distance:.2f}")
            print(f"  Avg Vehicles: {avg_vehicles:.2f}")
            print(f"  Avg Customers Served: {avg_customers:.2f}/{env.n_customers}")
            print(f"  Baseline: {agent.baseline:.2f}")
            print("-"*80)
            
            # Save best model based on distance
            if avg_distance < best_distance:
                best_distance = avg_distance
                model_path = os.path.join(save_dir, 'pointer_network_best.pth')
                agent.save(model_path)
                print(f"  Saved best model with distance: {best_distance:.2f}")
                print("-"*80)
    
    # Save final model
    final_path = os.path.join(save_dir, 'pointer_network_final.pth')
    agent.save(final_path)
    print(f"\nTraining completed! Final model saved to {final_path}")
    
    # Plot training curves
    plot_training_curves(history, save_dir)
    
    return history


def plot_training_curves(history, save_dir):
    """Plot and save training curves"""
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    
    # Loss
    axes[0, 0].plot(history['episode'], history['loss'])
    axes[0, 0].set_title('Training Loss')
    axes[0, 0].set_xlabel('Episode')
    axes[0, 0].set_ylabel('Loss')
    axes[0, 0].grid(True)
    
    # Reward
    axes[0, 1].plot(history['episode'], history['reward'])
    axes[0, 1].set_title('Reward')
    axes[0, 1].set_xlabel('Episode')
    axes[0, 1].set_ylabel('Reward')
    axes[0, 1].grid(True)
    
    # Distance
    axes[0, 2].plot(history['episode'], history['distance'])
    axes[0, 2].set_title('Total Distance')
    axes[0, 2].set_xlabel('Episode')
    axes[0, 2].set_ylabel('Distance')
    axes[0, 2].grid(True)
    
    # Number of vehicles
    axes[1, 0].plot(history['episode'], history['num_vehicles'])
    axes[1, 0].set_title('Number of Vehicles')
    axes[1, 0].set_xlabel('Episode')
    axes[1, 0].set_ylabel('Vehicles')
    axes[1, 0].grid(True)
    
    # Customers served
    axes[1, 1].plot(history['episode'], history['customers_served'])
    axes[1, 1].set_title('Customers Served')
    axes[1, 1].set_xlabel('Episode')
    axes[1, 1].set_ylabel('Customers')
    axes[1, 1].grid(True)
    
    # Moving average of distance
    window = 100
    if len(history['distance']) >= window:
        moving_avg = np.convolve(history['distance'], np.ones(window)/window, mode='valid')
        axes[1, 2].plot(history['episode'][window-1:], moving_avg)
        axes[1, 2].set_title(f'Distance Moving Average (window={window})')
        axes[1, 2].set_xlabel('Episode')
        axes[1, 2].set_ylabel('Distance')
        axes[1, 2].grid(True)
    
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, 'training_curves.png'), dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Training curves saved to {os.path.join(save_dir, 'training_curves.png')}")


def main():
    """Main training function"""
    # Dataset paths (use diverse set for training)
    base_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'dataset')
    
    dataset_paths = [
        # C1 - Clustered customers with short time windows
        os.path.join(base_path, 'C1', 'C101.csv'),
        os.path.join(base_path, 'C1', 'C102.csv'),
        os.path.join(base_path, 'C1', 'C103.csv'),
        os.path.join(base_path, 'C1', 'C104.csv'),
        os.path.join(base_path, 'C1', 'C105.csv'),
        os.path.join(base_path, 'C1', 'C106.csv'),
        os.path.join(base_path, 'C1', 'C107.csv'),
        os.path.join(base_path, 'C1', 'C108.csv'),
        os.path.join(base_path, 'C1', 'C109.csv'),
        
        # R1 - Random customers with short time windows
        os.path.join(base_path, 'R1', 'R101.csv'),
        os.path.join(base_path, 'R1', 'R102.csv'),
        os.path.join(base_path, 'R1', 'R103.csv'),
        os.path.join(base_path, 'R1', 'R104.csv'),
        os.path.join(base_path, 'R1', 'R105.csv'),
        os.path.join(base_path, 'R1', 'R106.csv'),
        
        # RC1 - Mix of random and clustered
        os.path.join(base_path, 'RC1', 'RC101.csv'),
        os.path.join(base_path, 'RC1', 'RC102.csv'),
        os.path.join(base_path, 'RC1', 'RC103.csv'),
        os.path.join(base_path, 'RC1', 'RC104.csv'),
        os.path.join(base_path, 'RC1', 'RC105.csv'),
    ]
    
    # Verify datasets exist
    dataset_paths = [p for p in dataset_paths if os.path.exists(p)]
    print(f"Found {len(dataset_paths)} training datasets")
    
    if len(dataset_paths) == 0:
        print("Error: No datasets found!")
        return
    
    # Hyperparameters
    input_dim = 6  # [x, y, demand, ready_time, due_date, service_time]
    hidden_dim = 256  # Hidden dimension
    num_layers = 2  # LSTM layers
    dropout = 0.1
    learning_rate = 1e-4
    num_episodes = 2000
    eval_interval = 100
    
    # Create agent
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    agent = PointerNetworkAgent(
        input_dim=input_dim,
        hidden_dim=hidden_dim,
        num_layers=num_layers,
        dropout=dropout,
        learning_rate=learning_rate,
        device=device
    )
    
    # Create save directory
    save_dir = os.path.join(os.path.dirname(__file__), 'models')
    os.makedirs(save_dir, exist_ok=True)
    
    # Train
    print(f"\nStarting training at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    history = train(
        agent=agent,
        dataset_paths=dataset_paths,
        num_episodes=num_episodes,
        eval_interval=eval_interval,
        save_dir=save_dir
    )
    print(f"Training finished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Save history
    history_df = pd.DataFrame(history)
    history_path = os.path.join(save_dir, 'training_history.csv')
    history_df.to_csv(history_path, index=False)
    print(f"Training history saved to {history_path}")


if __name__ == '__main__':
    main()
