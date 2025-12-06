"""
Trainer for DQN VRPTW
Training using Deep Q-Learning with Experience Replay
"""

import torch
import numpy as np
import pandas as pd
from pathlib import Path
import time
from tqdm import tqdm
import matplotlib.pyplot as plt

from dqn_model import DQNAgent


class VRPTWEnvironment:
    """VRPTW Environment for DQN"""
    def __init__(self, dataset_path, vehicle_capacity=200):
        self.dataset_path = dataset_path
        self.vehicle_capacity = vehicle_capacity
        
        # Load data
        self.data = pd.read_csv(dataset_path)
        
        # Preprocess: Convert string values to float
        for col in self.data.columns:
            if col != 'CUST NO.':
                self.data[col] = self.data[col].apply(
                    lambda x: float(str(x).split()[0]) if isinstance(x, str) else float(x)
                )
        
        self.depot = self.data.iloc[0]
        self.customers = self.data.iloc[1:].reset_index(drop=True)
        self.n_customers = len(self.customers)
        
        # Calculate distance matrix
        self.distance_matrix = self._calculate_distance_matrix()
        
        # State
        self.reset()
    
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
    
    def reset(self):
        """Reset environment to initial state"""
        self.current_node = 0  # Start at depot
        self.current_load = 0
        self.current_time = 0
        self.visited = np.zeros(self.n_customers + 1, dtype=bool)
        self.visited[0] = True  # Depot always visited
        self.total_distance = 0
        self.route = [0]
        
        return self._get_state()
    
    def _get_state(self):
        """Get current state representation with normalization"""
        # State: [current_node_features, vehicle_state, unvisited_customers_features]
        if self.current_node == 0:
            node_features = np.array([
                float(self.depot['XCOORD.']) / 100.0,  # Normalize coordinates
                float(self.depot['YCOORD.']) / 100.0,
                0.0,  # demand (normalized)
                float(self.depot['READY TIME']) / 1000.0,  # Normalize time
                float(self.depot['DUE DATE']) / 1000.0,
                0.0   # service time (normalized)
            ], dtype=np.float32)
        else:
            customer = self.customers.loc[self.current_node - 1]
            node_features = np.array([
                float(customer['XCOORD.']) / 100.0,
                float(customer['YCOORD.']) / 100.0,
                float(customer['DEMAND']) / 200.0,
                float(customer['READY TIME']) / 1000.0,
                float(customer['DUE DATE']) / 1000.0,
                float(customer['SERVICE TIME']) / 100.0
            ], dtype=np.float32)
        
        # Vehicle state (normalized)
        vehicle_state = np.array([
            self.current_load / self.vehicle_capacity,
            self.current_time / 1000.0,
            np.sum(~self.visited) / self.n_customers
        ], dtype=np.float32)
        
        # Combine
        state = np.concatenate([node_features, vehicle_state])
        
        return torch.FloatTensor(state)
    
    def _get_valid_actions_mask(self):
        """Get mask of valid actions"""
        mask = torch.zeros(self.n_customers + 1, dtype=torch.bool)
        
        for i in range(self.n_customers + 1):
            if self.visited[i]:
                continue
            
            if i == 0:  # Can always return to depot
                mask[i] = True
                continue
            
            # Check capacity constraint
            demand = float(self.customers.loc[i - 1, 'DEMAND'])
            if self.current_load + demand > self.vehicle_capacity:
                continue
            
            # Check time window
            travel_time = self.distance_matrix[self.current_node][i]
            arrival_time = self.current_time + travel_time
            ready_time = float(self.customers.loc[i - 1, 'READY TIME'])
            due_date = float(self.customers.loc[i - 1, 'DUE DATE'])
            
            service_start = max(arrival_time, ready_time)
            if service_start <= due_date:
                mask[i] = True
        
        # If no valid customer, must return to depot
        if not mask.any():
            mask[0] = True
        
        return mask
    
    def step(self, action):
        """
        Take action and return (next_state, reward, done, info)
        
        Args:
            action: Node index to visit
        Returns:
            next_state, reward, done, info
        """
        if action < 0 or action > self.n_customers:
            raise ValueError(f"Invalid action: {action}")
        
        # Calculate distance and reward
        distance = self.distance_matrix[self.current_node][action]
        self.total_distance += distance
        
        # Improved reward shaping
        reward = -distance / 10.0  # Scale down distance penalty
        
        # Update time
        travel_time = distance
        self.current_time += travel_time
        
        # Update node
        prev_node = self.current_node
        self.current_node = action
        self.route.append(action)
        
        # If visiting customer
        if action > 0:
            customer = self.customers.loc[action - 1]
            demand = float(customer['DEMAND'])
            ready_time = float(customer['READY TIME'])
            due_date = float(customer['DUE DATE'])
            service_time = float(customer['SERVICE TIME'])
            
            # Wait if early
            wait_time = 0
            if self.current_time < ready_time:
                wait_time = ready_time - self.current_time
                self.current_time = ready_time
                reward -= wait_time / 100.0  # Small penalty for waiting
            
            # Service
            self.current_time += service_time
            self.current_load += demand
            self.visited[action] = True
            
            # Reward for serving customer
            reward += 5.0
            
            # Bonus for good timing (within time window)
            time_slack = due_date - self.current_time
            if time_slack > 0:
                reward += min(time_slack / 100.0, 2.0)  # Bonus for having slack
        
        # If returned to depot, reset vehicle
        if action == 0 and prev_node != 0:
            self.current_load = 0
            # Bonus for completing a route efficiently
            n_customers_in_route = sum(1 for node in self.route if node > 0)
            reward += 20.0 + n_customers_in_route * 2.0  # More customers = better
        
        # Check if done
        done = np.all(self.visited)
        
        # Get next state
        next_state = self._get_state()
        
        info = {
            'total_distance': self.total_distance,
            'n_visited': np.sum(self.visited) - 1,  # -1 for depot
            'route': self.route.copy()
        }
        
        return next_state, reward, done, info


class DQNTrainer:
    """Trainer for DQN Agent"""
    def __init__(self,
                 agent,
                 train_datasets,
                 val_datasets=None,
                 device='cuda' if torch.cuda.is_available() else 'cpu'):
        
        self.agent = agent
        self.device = device
        self.train_datasets = train_datasets
        self.val_datasets = val_datasets
        
        # Training stats
        self.episode_rewards = []
        self.episode_lengths = []
        self.losses = []
    
    def train_episode(self, env, update_freq=4):
        """Train one episode with improved training strategy"""
        state = env.reset()
        total_reward = 0
        done = False
        steps = 0
        max_steps = min(env.n_customers * 3, 300)  # Adaptive max steps
        
        while not done and steps < max_steps:
            # Get valid actions
            valid_mask = env._get_valid_actions_mask()
            
            # Select action
            action = self.agent.select_action(state, valid_mask)
            
            # Take action
            next_state, reward, done, info = env.step(action)
            
            # Store in memory
            self.agent.memory.push(state, action, reward, next_state, done)
            
            # Update state
            state = next_state
            total_reward += reward
            steps += 1
            
            # Train agent more frequently with larger batches
            if len(self.agent.memory) >= 128:  # Wait for more samples
                if steps % update_freq == 0:  # Update every N steps
                    for _ in range(2):  # Multiple updates per step
                        loss = self.agent.update(batch_size=64)  # Larger batch
                        if loss is not None:
                            self.losses.append(loss)
        
        return total_reward, steps, info['total_distance']
    
    def train(self, n_episodes, target_update_freq=5, save_path=None, warmup_episodes=50):
        """Train the agent with improved strategy"""
        print(f"\n{'='*80}")
        print(f"TRAINING DQN FOR VRPTW (IMPROVED)")
        print(f"{'='*80}")
        print(f"Device: {self.device}")
        print(f"Episodes: {n_episodes}")
        print(f"Training datasets: {len(self.train_datasets)}")
        print(f"Warmup episodes: {warmup_episodes}")
        print(f"Target update frequency: {target_update_freq}")
        print(f"{'='*80}\n")
        
        best_reward = float('-inf')
        best_distance = float('inf')
        
        for episode in range(1, n_episodes + 1):
            # Sample random dataset
            dataset_path = np.random.choice(self.train_datasets)
            env = VRPTWEnvironment(dataset_path)
            
            # Train episode
            reward, steps, distance = self.train_episode(env, update_freq=4 if episode > warmup_episodes else 8)
            
            self.episode_rewards.append(reward)
            self.episode_lengths.append(distance)
            
            # Update target network more frequently
            if episode % target_update_freq == 0:
                self.agent.update_target_network()
            
            # Decay epsilon (slower decay for better exploration)
            if episode > warmup_episodes:
                self.agent.decay_epsilon()
            
            # Log
            if episode % 10 == 0:
                avg_reward = np.mean(self.episode_rewards[-10:])
                avg_distance = np.mean(self.episode_lengths[-10:])
                avg_loss = np.mean(self.losses[-100:]) if len(self.losses) > 0 else 0
                print(f"Episode {episode}/{n_episodes} - "
                      f"Reward: {reward:.2f}, "
                      f"Distance: {distance:.2f}, "
                      f"Avg Reward: {avg_reward:.2f}, "
                      f"Avg Distance: {avg_distance:.2f}, "
                      f"Loss: {avg_loss:.4f}, "
                      f"Epsilon: {self.agent.epsilon:.3f}")
            
            # Save best model (based on distance, not reward)
            if distance < best_distance and episode > warmup_episodes and save_path:
                best_distance = distance
                best_reward = reward
                save_path = Path(save_path)
                save_path.parent.mkdir(parents=True, exist_ok=True)
                torch.save({
                    'episode': episode,
                    'policy_net_state_dict': self.agent.policy_net.state_dict(),
                    'target_net_state_dict': self.agent.target_net.state_dict(),
                    'optimizer_state_dict': self.agent.optimizer.state_dict(),
                    'best_reward': best_reward,
                    'best_distance': best_distance,
                    'epsilon': self.agent.epsilon
                }, str(save_path))
                print(f"✓ Saved best model (distance: {best_distance:.2f}, reward: {best_reward:.2f})")
        
        print(f"\n{'='*80}")
        print(f"TRAINING COMPLETED")
        print(f"Best reward: {best_reward:.2f}")
        print(f"{'='*80}\n")
    
    def plot_training_curves(self, save_path=None):
        """Plot training curves"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # Rewards
        axes[0, 0].plot(self.episode_rewards)
        axes[0, 0].set_xlabel('Episode')
        axes[0, 0].set_ylabel('Total Reward')
        axes[0, 0].set_title('Episode Rewards')
        axes[0, 0].grid(True)
        
        # Tour lengths
        axes[0, 1].plot(self.episode_lengths)
        axes[0, 1].set_xlabel('Episode')
        axes[0, 1].set_ylabel('Total Distance')
        axes[0, 1].set_title('Episode Tour Lengths')
        axes[0, 1].grid(True)
        
        # Moving average rewards
        window = 50
        if len(self.episode_rewards) >= window:
            moving_avg = np.convolve(self.episode_rewards, np.ones(window)/window, mode='valid')
            axes[1, 0].plot(moving_avg)
            axes[1, 0].set_xlabel('Episode')
            axes[1, 0].set_ylabel('Avg Reward')
            axes[1, 0].set_title(f'Moving Average Reward (window={window})')
            axes[1, 0].grid(True)
        
        # Losses
        if self.losses:
            axes[1, 1].plot(self.losses)
            axes[1, 1].set_xlabel('Update Step')
            axes[1, 1].set_ylabel('Loss')
            axes[1, 1].set_title('Training Loss')
            axes[1, 1].grid(True)
        
        plt.tight_layout()
        
        if save_path:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(str(save_path), dpi=300, bbox_inches='tight')
            print(f"✓ Saved training curves: {save_path}")
        
        plt.close()


def main():
    """Main training function"""
    # Paths
    current_dir = Path(__file__).parent
    code_dir = current_dir.parent.parent.parent.parent
    dataset_dir = code_dir / "dataset"
    
    # Collect training datasets (use more datasets for better learning)
    train_datasets = []
    for category in ['C1', 'R1', 'RC1']:
        cat_dir = dataset_dir / category
        if cat_dir.exists():
            # Use more datasets for training
            train_datasets.extend([str(p) for p in list(cat_dir.glob('*.csv'))[:7]])
    
    print(f"Training datasets: {len(train_datasets)}")
    
    # Create agent with improved hyperparameters
    state_dim = 9  # 6 node features + 3 vehicle state
    action_dim = 101  # Max nodes (100 customers + 1 depot)
    
    agent = DQNAgent(
        state_dim=state_dim,
        action_dim=action_dim,
        hidden_dim=512,  # Larger network for better capacity
        lr=3e-4,  # Higher learning rate for faster learning
        gamma=0.98,  # Slightly lower discount for shorter horizon
        epsilon_start=1.0,
        epsilon_end=0.05,  # Keep some exploration
        epsilon_decay=0.997,  # Slower decay
        use_dueling=True,
        use_double_dqn=True,
        use_prioritized_replay=False,  # Can enable for better sample efficiency
        buffer_capacity=50000,  # Larger buffer for more diverse experiences
        device='cuda' if torch.cuda.is_available() else 'cpu'
    )
    
    # Create trainer
    trainer = DQNTrainer(
        agent=agent,
        train_datasets=train_datasets
    )
    
    # Train with improved settings
    save_path = current_dir / "models" / "dqn_model_best.pth"
    trainer.train(
        n_episodes=2000,  # More episodes
        target_update_freq=5,  # Update target more frequently
        save_path=save_path,
        warmup_episodes=100  # Longer warmup for exploration
    )
    
    # Plot training curves
    plot_path = current_dir / "result" / "training_curves.png"
    trainer.plot_training_curves(save_path=plot_path)


if __name__ == "__main__":
    main()
