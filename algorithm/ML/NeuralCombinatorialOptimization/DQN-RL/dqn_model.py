"""
Deep Q-Network (DQN) for VRPTW
Giải bài toán VRPTW bằng Deep Q-Learning với Experience Replay
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from collections import deque
import random


class DQNNetwork(nn.Module):
    """Deep Q-Network for VRPTW"""
    def __init__(self, state_dim, action_dim, hidden_dim=256):
        """
        Args:
            state_dim: Dimension of state representation
            action_dim: Maximum number of actions (nodes)
            hidden_dim: Hidden layer dimension
        """
        super().__init__()
        
        self.state_dim = state_dim
        self.action_dim = action_dim
        
        # State encoding network
        self.state_encoder = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim)
        )
        
        # Action value network
        self.value_net = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, action_dim)
        )
        
    def forward(self, state):
        """
        Args:
            state: (batch, state_dim) - current state
        Returns:
            q_values: (batch, action_dim) - Q-values for each action
        """
        encoded = self.state_encoder(state)
        q_values = self.value_net(encoded)
        return q_values


class DuelingDQN(nn.Module):
    """Dueling DQN architecture - separates state value and advantage"""
    def __init__(self, state_dim, action_dim, hidden_dim=256):
        super().__init__()
        
        self.state_dim = state_dim
        self.action_dim = action_dim
        
        # Shared feature extraction with batch normalization
        self.feature = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU()
        )
        
        # Value stream
        self.value_stream = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 1)
        )
        
        # Advantage stream
        self.advantage_stream = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, action_dim)
        )
        
    def forward(self, state):
        """
        Args:
            state: (batch, state_dim)
        Returns:
            q_values: (batch, action_dim)
        """
        features = self.feature(state)
        
        # Compute value and advantage
        value = self.value_stream(features)
        advantage = self.advantage_stream(features)
        
        # Combine using dueling architecture formula
        # Q(s,a) = V(s) + (A(s,a) - mean(A(s,a)))
        q_values = value + (advantage - advantage.mean(dim=1, keepdim=True))
        
        return q_values


class ReplayBuffer:
    """Experience Replay Buffer for DQN"""
    def __init__(self, capacity=10000):
        self.buffer = deque(maxlen=capacity)
    
    def push(self, state, action, reward, next_state, done):
        """Add experience to buffer"""
        self.buffer.append((state, action, reward, next_state, done))
    
    def sample(self, batch_size):
        """Sample a batch of experiences"""
        batch = random.sample(self.buffer, min(batch_size, len(self.buffer)))
        
        states = torch.stack([x[0] for x in batch])
        actions = torch.tensor([x[1] for x in batch], dtype=torch.long)
        rewards = torch.tensor([x[2] for x in batch], dtype=torch.float)
        next_states = torch.stack([x[3] for x in batch])
        dones = torch.tensor([x[4] for x in batch], dtype=torch.bool)
        
        return states, actions, rewards, next_states, dones
    
    def __len__(self):
        return len(self.buffer)


class PrioritizedReplayBuffer:
    """Prioritized Experience Replay"""
    def __init__(self, capacity=10000, alpha=0.6):
        self.capacity = capacity
        self.alpha = alpha  # Priority exponent
        self.buffer = []
        self.priorities = []
        self.position = 0
    
    def push(self, state, action, reward, next_state, done):
        """Add experience with max priority"""
        max_priority = max(self.priorities) if self.priorities else 1.0
        
        if len(self.buffer) < self.capacity:
            self.buffer.append((state, action, reward, next_state, done))
            self.priorities.append(max_priority)
        else:
            self.buffer[self.position] = (state, action, reward, next_state, done)
            self.priorities[self.position] = max_priority
        
        self.position = (self.position + 1) % self.capacity
    
    def sample(self, batch_size, beta=0.4):
        """Sample batch with prioritization"""
        if len(self.buffer) < batch_size:
            batch_size = len(self.buffer)
        
        # Calculate sampling probabilities
        priorities = np.array(self.priorities[:len(self.buffer)])
        probs = priorities ** self.alpha
        probs /= probs.sum()
        
        # Sample indices
        indices = np.random.choice(len(self.buffer), batch_size, p=probs, replace=False)
        
        # Calculate importance sampling weights
        weights = (len(self.buffer) * probs[indices]) ** (-beta)
        weights /= weights.max()
        
        # Get samples
        batch = [self.buffer[idx] for idx in indices]
        states = torch.stack([x[0] for x in batch])
        actions = torch.tensor([x[1] for x in batch], dtype=torch.long)
        rewards = torch.tensor([x[2] for x in batch], dtype=torch.float)
        next_states = torch.stack([x[3] for x in batch])
        dones = torch.tensor([x[4] for x in batch], dtype=torch.bool)
        weights = torch.FloatTensor(weights)
        
        return states, actions, rewards, next_states, dones, weights, indices
    
    def update_priorities(self, indices, priorities):
        """Update priorities after training"""
        for idx, priority in zip(indices, priorities):
            self.priorities[idx] = priority
    
    def __len__(self):
        return len(self.buffer)


class DQNAgent:
    """DQN Agent for VRPTW"""
    def __init__(self, 
                 state_dim,
                 action_dim,
                 hidden_dim=256,
                 lr=1e-4,
                 gamma=0.99,
                 epsilon_start=1.0,
                 epsilon_end=0.01,
                 epsilon_decay=0.995,
                 use_dueling=True,
                 use_double_dqn=True,
                 use_prioritized_replay=False,
                 buffer_capacity=10000,
                 device='cpu'):
        
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.gamma = gamma
        self.epsilon = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.use_double_dqn = use_double_dqn
        self.use_prioritized_replay = use_prioritized_replay
        self.device = device
        
        # Create networks
        if use_dueling:
            self.policy_net = DuelingDQN(state_dim, action_dim, hidden_dim).to(device)
            self.target_net = DuelingDQN(state_dim, action_dim, hidden_dim).to(device)
        else:
            self.policy_net = DQNNetwork(state_dim, action_dim, hidden_dim).to(device)
            self.target_net = DQNNetwork(state_dim, action_dim, hidden_dim).to(device)
        
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()
        
        # Optimizer
        self.optimizer = torch.optim.Adam(self.policy_net.parameters(), lr=lr)
        
        # Replay buffer
        if use_prioritized_replay:
            self.memory = PrioritizedReplayBuffer(buffer_capacity)
        else:
            self.memory = ReplayBuffer(buffer_capacity)
    
    def select_action(self, state, valid_actions_mask):
        """
        Select action using epsilon-greedy policy
        
        Args:
            state: (state_dim,) - current state
            valid_actions_mask: (action_dim,) - mask of valid actions
        Returns:
            action: int - selected action
        """
        if random.random() < self.epsilon:
            # Random action from valid actions
            valid_actions = torch.nonzero(valid_actions_mask).squeeze(-1)
            if len(valid_actions) == 0:
                return 0  # Return to depot
            return valid_actions[random.randint(0, len(valid_actions) - 1)].item()
        else:
            # Greedy action - use eval mode for BatchNorm
            self.policy_net.eval()
            with torch.no_grad():
                state = state.unsqueeze(0).to(self.device)
                q_values = self.policy_net(state).squeeze(0)
                
                # Mask invalid actions
                q_values[~valid_actions_mask] = float('-inf')
                
                action = q_values.argmax().item()
            self.policy_net.train()
            return action
    
    def update(self, batch_size):
        """Update network using experience replay"""
        if len(self.memory) < batch_size:
            return 0.0
        
        # Sample from memory
        if self.use_prioritized_replay:
            states, actions, rewards, next_states, dones, weights, indices = \
                self.memory.sample(batch_size)
            weights = weights.to(self.device)
        else:
            states, actions, rewards, next_states, dones = self.memory.sample(batch_size)
            weights = torch.ones(batch_size).to(self.device)
        
        states = states.to(self.device)
        actions = actions.to(self.device)
        rewards = rewards.to(self.device)
        next_states = next_states.to(self.device)
        dones = dones.to(self.device)
        
        # Compute current Q values
        current_q_values = self.policy_net(states).gather(1, actions.unsqueeze(1)).squeeze(1)
        
        # Compute target Q values
        with torch.no_grad():
            if self.use_double_dqn:
                # Double DQN: use policy net to select action, target net to evaluate
                next_actions = self.policy_net(next_states).argmax(1)
                next_q_values = self.target_net(next_states).gather(1, next_actions.unsqueeze(1)).squeeze(1)
            else:
                # Standard DQN
                next_q_values = self.target_net(next_states).max(1)[0]
            
            target_q_values = rewards + self.gamma * next_q_values * (~dones).float()
        
        # Compute loss
        td_errors = target_q_values - current_q_values
        loss = (weights * td_errors.pow(2)).mean()
        
        # Optimize
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.policy_net.parameters(), 1.0)
        self.optimizer.step()
        
        # Update priorities
        if self.use_prioritized_replay:
            priorities = td_errors.abs().detach().cpu().numpy() + 1e-6
            self.memory.update_priorities(indices, priorities)
        
        return loss.item()
    
    def update_target_network(self):
        """Copy weights from policy network to target network"""
        self.target_net.load_state_dict(self.policy_net.state_dict())
    
    def decay_epsilon(self):
        """Decay exploration rate"""
        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)
