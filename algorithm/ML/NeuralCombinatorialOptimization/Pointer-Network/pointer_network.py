"""
Pointer Network implementation for VRPTW
Based on the paper: "Pointer Networks" by Vinyals et al. (2015)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np


class Attention(nn.Module):
    """Attention mechanism for Pointer Network"""
    
    def __init__(self, hidden_dim):
        super(Attention, self).__init__()
        self.hidden_dim = hidden_dim
        
        # Attention parameters
        self.W_ref = nn.Linear(hidden_dim, hidden_dim, bias=False)
        self.W_q = nn.Linear(hidden_dim, hidden_dim, bias=False)
        self.v = nn.Linear(hidden_dim, 1, bias=False)
        
    def forward(self, query, ref, mask=None):
        """
        Args:
            query: [batch_size, hidden_dim] - decoder hidden state
            ref: [batch_size, seq_len, hidden_dim] - encoder outputs
            mask: [batch_size, seq_len] - mask for invalid positions
        Returns:
            scores: [batch_size, seq_len] - attention scores
        """
        batch_size, seq_len, _ = ref.size()
        
        # Compute attention scores
        # [batch_size, seq_len, hidden_dim]
        ref_transformed = self.W_ref(ref)
        
        # [batch_size, 1, hidden_dim]
        query_transformed = self.W_q(query).unsqueeze(1)
        
        # [batch_size, seq_len, hidden_dim]
        combined = torch.tanh(ref_transformed + query_transformed)
        
        # [batch_size, seq_len]
        scores = self.v(combined).squeeze(-1)
        
        # Apply mask (set masked positions to very negative values)
        if mask is not None:
            scores = scores.masked_fill(mask == 0, float('-inf'))
        
        return scores


class PointerNetwork(nn.Module):
    """
    Pointer Network for VRPTW
    Uses LSTM encoder-decoder with attention mechanism
    """
    
    def __init__(self, input_dim, hidden_dim, num_layers=2, dropout=0.1):
        super(PointerNetwork, self).__init__()
        
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        
        # Input embedding layer
        self.embedding = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU()
        )
        
        # Encoder LSTM
        self.encoder = nn.LSTM(
            hidden_dim,
            hidden_dim,
            num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=True
        )
        
        # Project bidirectional encoder output to hidden_dim
        self.encoder_proj = nn.Linear(hidden_dim * 2, hidden_dim)
        
        # Decoder LSTM
        self.decoder = nn.LSTM(
            hidden_dim,
            hidden_dim,
            num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )
        
        # Attention mechanism
        self.attention = Attention(hidden_dim)
        
        # Initial decoder input (learnable)
        self.decoder_start = nn.Parameter(torch.randn(1, 1, hidden_dim))
        
    def forward(self, inputs, seq_len, mask=None):
        """
        Args:
            inputs: [batch_size, seq_len, input_dim] - customer features
            seq_len: int - maximum sequence length to decode
            mask: [batch_size, num_nodes] - mask for valid actions
        Returns:
            log_probs: [batch_size, seq_len, num_nodes] - log probabilities
            actions: [batch_size, seq_len] - selected actions
            entropy: scalar - entropy for exploration
        """
        batch_size, num_nodes, _ = inputs.size()
        
        # Embed inputs
        # [batch_size, num_nodes, input_dim] -> [batch_size * num_nodes, input_dim]
        inputs_flat = inputs.view(-1, self.input_dim)
        embedded = self.embedding(inputs_flat)
        # [batch_size, num_nodes, hidden_dim]
        embedded = embedded.view(batch_size, num_nodes, self.hidden_dim)
        
        # Encode
        encoder_outputs, (hidden, cell) = self.encoder(embedded)
        
        # Project bidirectional outputs to hidden_dim
        # [batch_size, num_nodes, hidden_dim * 2] -> [batch_size, num_nodes, hidden_dim]
        encoder_outputs = self.encoder_proj(encoder_outputs)
        
        # Initialize decoder hidden state from encoder
        # Take only forward direction of last layer
        hidden = hidden[-2:].contiguous()  # [2, batch_size, hidden_dim]
        cell = cell[-2:].contiguous()
        
        # Decoder loop
        decoder_input = self.decoder_start.expand(batch_size, 1, -1)
        
        log_probs_list = []
        actions_list = []
        entropy_list = []
        
        current_mask = mask.clone() if mask is not None else torch.ones(batch_size, num_nodes, device=inputs.device)
        
        for step in range(seq_len):
            # Decode one step
            decoder_output, (hidden, cell) = self.decoder(decoder_input, (hidden, cell))
            
            # Get query from decoder hidden state
            query = hidden[-1]  # [batch_size, hidden_dim]
            
            # Compute attention scores
            scores = self.attention(query, encoder_outputs, current_mask)
            
            # Compute probabilities
            probs = F.softmax(scores, dim=-1)  # [batch_size, num_nodes]
            log_probs = F.log_softmax(scores, dim=-1)
            
            # Sample action
            dist = torch.distributions.Categorical(probs)
            action = dist.sample()  # [batch_size]
            
            # Compute entropy
            entropy = dist.entropy().mean()
            
            # Update mask (mask out selected node)
            current_mask[torch.arange(batch_size), action] = 0
            
            # Get next decoder input (embedding of selected node)
            decoder_input = encoder_outputs[torch.arange(batch_size), action].unsqueeze(1)
            
            log_probs_list.append(log_probs)
            actions_list.append(action)
            entropy_list.append(entropy)
        
        # Stack results
        log_probs = torch.stack(log_probs_list, dim=1)  # [batch_size, seq_len, num_nodes]
        actions = torch.stack(actions_list, dim=1)  # [batch_size, seq_len]
        entropy = torch.stack(entropy_list).mean()
        
        return log_probs, actions, entropy
    
    def decode_greedy(self, inputs, seq_len, mask=None):
        """Greedy decoding for inference"""
        batch_size, num_nodes, _ = inputs.size()
        
        # Embed inputs
        inputs_flat = inputs.view(-1, self.input_dim)
        embedded = self.embedding(inputs_flat)
        embedded = embedded.view(batch_size, num_nodes, self.hidden_dim)
        
        # Encode
        encoder_outputs, (hidden, cell) = self.encoder(embedded)
        encoder_outputs = self.encoder_proj(encoder_outputs)
        
        # Initialize decoder
        hidden = hidden[-2:].contiguous()
        cell = cell[-2:].contiguous()
        decoder_input = self.decoder_start.expand(batch_size, 1, -1)
        
        actions_list = []
        log_probs_list = []
        
        current_mask = mask.clone() if mask is not None else torch.ones(batch_size, num_nodes, device=inputs.device)
        
        for step in range(seq_len):
            decoder_output, (hidden, cell) = self.decoder(decoder_input, (hidden, cell))
            query = hidden[-1]
            scores = self.attention(query, encoder_outputs, current_mask)
            log_probs = F.log_softmax(scores, dim=-1)
            
            # Greedy selection
            action = scores.argmax(dim=-1)  # [batch_size]
            
            # Update mask
            current_mask[torch.arange(batch_size), action] = 0
            
            # Next decoder input
            decoder_input = encoder_outputs[torch.arange(batch_size), action].unsqueeze(1)
            
            actions_list.append(action)
            log_probs_list.append(log_probs)
        
        actions = torch.stack(actions_list, dim=1)  # [batch_size, seq_len]
        log_probs = torch.stack(log_probs_list, dim=1)  # [batch_size, seq_len, num_nodes]
        
        return actions, log_probs


class PointerNetworkAgent:
    """Agent for training and inference with Pointer Network"""
    
    def __init__(self, input_dim, hidden_dim, num_layers=2, dropout=0.1, 
                 learning_rate=1e-4, device='cuda'):
        self.device = torch.device(device if torch.cuda.is_available() else 'cpu')
        
        # Create model
        self.model = PointerNetwork(input_dim, hidden_dim, num_layers, dropout).to(self.device)
        
        # Optimizer
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)
        
        # Baseline for REINFORCE (exponential moving average)
        self.baseline = None
        self.baseline_momentum = 0.9
        
    def select_action(self, state, mask=None, greedy=False):
        """
        Select action given state
        Args:
            state: [batch_size, num_nodes, input_dim]
            mask: [batch_size, num_nodes]
            greedy: bool - use greedy decoding
        Returns:
            actions: [batch_size, seq_len]
            log_probs: [batch_size, seq_len, num_nodes]
        """
        self.model.eval()
        with torch.no_grad():
            state = torch.FloatTensor(state).to(self.device)
            if mask is not None:
                mask = torch.FloatTensor(mask).to(self.device)
            
            if greedy:
                actions, log_probs = self.model.decode_greedy(state, state.size(1), mask)
            else:
                log_probs, actions, _ = self.model(state, state.size(1), mask)
            
            return actions.cpu().numpy(), log_probs.cpu().numpy()
    
    def update(self, states, actions, rewards, masks=None):
        """
        Update model using REINFORCE with baseline
        Args:
            states: [batch_size, num_nodes, input_dim]
            actions: [batch_size, seq_len]
            rewards: [batch_size] - total rewards
            masks: [batch_size, num_nodes]
        Returns:
            loss: scalar
        """
        self.model.train()
        
        # Convert to tensors
        states = torch.FloatTensor(states).to(self.device)
        actions = torch.LongTensor(actions).to(self.device)
        rewards = torch.FloatTensor(rewards).to(self.device)
        if masks is not None:
            masks = torch.FloatTensor(masks).to(self.device)
        
        # Forward pass
        log_probs, _, entropy = self.model(states, actions.size(1), masks)
        
        # Get log probabilities of taken actions
        batch_size, seq_len = actions.size()
        action_log_probs = log_probs[torch.arange(batch_size).unsqueeze(1), 
                                      torch.arange(seq_len).unsqueeze(0), 
                                      actions]
        
        # Sum log probs over sequence
        log_likelihood = action_log_probs.sum(dim=1)  # [batch_size]
        
        # Update baseline
        if self.baseline is None:
            self.baseline = rewards.mean().item()
        else:
            self.baseline = self.baseline_momentum * self.baseline + \
                          (1 - self.baseline_momentum) * rewards.mean().item()
        
        # Compute advantage
        advantage = rewards - self.baseline
        
        # REINFORCE loss with entropy bonus
        loss = -(log_likelihood * advantage).mean() - 0.01 * entropy
        
        # Backward pass
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
        self.optimizer.step()
        
        return loss.item()
    
    def save(self, path):
        """Save model"""
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'baseline': self.baseline
        }, path)
        
    def load(self, path):
        """Load model"""
        checkpoint = torch.load(path, map_location=self.device, weights_only=False)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.baseline = checkpoint.get('baseline', None)
