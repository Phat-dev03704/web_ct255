"""
Attention Model for VRPTW
Kiến trúc Transformer-based với Graph Attention để giải VRPTW
Dựa trên paper "Attention, Learn to Solve Routing Problems!" (Kool et al., 2019)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import math


class MultiHeadAttention(nn.Module):
    """Multi-Head Attention mechanism"""
    def __init__(self, embed_dim, n_heads):
        super().__init__()
        self.embed_dim = embed_dim
        self.n_heads = n_heads
        self.head_dim = embed_dim // n_heads
        
        assert embed_dim % n_heads == 0, "embed_dim must be divisible by n_heads"
        
        self.q_linear = nn.Linear(embed_dim, embed_dim)
        self.k_linear = nn.Linear(embed_dim, embed_dim)
        self.v_linear = nn.Linear(embed_dim, embed_dim)
        self.out = nn.Linear(embed_dim, embed_dim)
        
    def forward(self, query, key, value, mask=None):
        batch_size = query.size(0)
        
        # Linear projections
        Q = self.q_linear(query).view(batch_size, -1, self.n_heads, self.head_dim).transpose(1, 2)
        K = self.k_linear(key).view(batch_size, -1, self.n_heads, self.head_dim).transpose(1, 2)
        V = self.v_linear(value).view(batch_size, -1, self.n_heads, self.head_dim).transpose(1, 2)
        
        # Attention scores
        scores = torch.matmul(Q, K.transpose(-2, -1)) / math.sqrt(self.head_dim)
        
        if mask is not None:
            scores = scores.masked_fill(mask.unsqueeze(1).unsqueeze(2), float('-inf'))
        
        attn = F.softmax(scores, dim=-1)
        out = torch.matmul(attn, V)
        
        # Concatenate heads
        out = out.transpose(1, 2).contiguous().view(batch_size, -1, self.embed_dim)
        out = self.out(out)
        
        return out, attn


class EncoderLayer(nn.Module):
    """Single Encoder Layer with Multi-Head Attention and Feed Forward"""
    def __init__(self, embed_dim, n_heads, ff_dim, dropout=0.1):
        super().__init__()
        self.attention = MultiHeadAttention(embed_dim, n_heads)
        self.norm1 = nn.LayerNorm(embed_dim)
        self.norm2 = nn.LayerNorm(embed_dim)
        self.ff = nn.Sequential(
            nn.Linear(embed_dim, ff_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(ff_dim, embed_dim)
        )
        self.dropout = nn.Dropout(dropout)
        
    def forward(self, x, mask=None):
        # Multi-head attention
        attn_out, _ = self.attention(x, x, x, mask)
        x = self.norm1(x + self.dropout(attn_out))
        
        # Feed forward
        ff_out = self.ff(x)
        x = self.norm2(x + self.dropout(ff_out))
        
        return x


class AttentionEncoder(nn.Module):
    """Graph Attention Encoder cho VRPTW"""
    def __init__(self, input_dim, embed_dim, n_heads, n_layers, ff_dim):
        super().__init__()
        self.embed_dim = embed_dim
        
        # Input embedding: [x, y, demand, ready_time, due_date, service_time]
        self.input_embed = nn.Linear(input_dim, embed_dim)
        
        # Encoder layers
        self.layers = nn.ModuleList([
            EncoderLayer(embed_dim, n_heads, ff_dim)
            for _ in range(n_layers)
        ])
        
    def forward(self, node_features, mask=None):
        """
        Args:
            node_features: (batch, n_nodes, input_dim)
            mask: (batch, n_nodes) - True for masked nodes
        Returns:
            encoded: (batch, n_nodes, embed_dim)
        """
        x = self.input_embed(node_features)
        
        for layer in self.layers:
            x = layer(x, mask)
        
        return x


class AttentionDecoder(nn.Module):
    """Attention-based Decoder for sequential decision making"""
    def __init__(self, embed_dim, n_heads):
        super().__init__()
        self.embed_dim = embed_dim
        self.n_heads = n_heads
        
        # Context embedding
        self.context_embed = nn.Linear(embed_dim * 3, embed_dim)  # current_node + depot + global
        
        # Pointer mechanism
        self.pointer = MultiHeadAttention(embed_dim, n_heads)
        self.glimpse = MultiHeadAttention(embed_dim, n_heads)
        
        self.W_q = nn.Linear(embed_dim, embed_dim)
        self.W_k = nn.Linear(embed_dim, embed_dim)
        
    def forward(self, encoded_nodes, context, mask):
        """
        Args:
            encoded_nodes: (batch, n_nodes, embed_dim) - encoded node features
            context: (batch, embed_dim) - current context (state)
            mask: (batch, n_nodes) - mask for visited nodes
        Returns:
            log_probs: (batch, n_nodes) - log probabilities for each node
            selected: (batch,) - selected node indices
        """
        batch_size, n_nodes, _ = encoded_nodes.size()
        
        # Compute attention scores
        query = self.W_q(context).unsqueeze(1)  # (batch, 1, embed_dim)
        keys = self.W_k(encoded_nodes)  # (batch, n_nodes, embed_dim)
        
        # Compute compatibility scores
        scores = torch.matmul(query, keys.transpose(1, 2)) / math.sqrt(self.embed_dim)
        scores = scores.squeeze(1)  # (batch, n_nodes)
        
        # Apply mask
        scores = scores.masked_fill(mask, float('-inf'))
        
        # Softmax to get probabilities
        log_probs = F.log_softmax(scores, dim=-1)
        
        return log_probs


class AttentionModelVRPTW(nn.Module):
    """Complete Attention Model for VRPTW"""
    def __init__(self, 
                 input_dim=6,  # [x, y, demand, ready_time, due_date, service_time]
                 embed_dim=128,
                 n_heads=8,
                 n_encoder_layers=3,
                 ff_dim=512,
                 vehicle_capacity=200):
        super().__init__()
        
        self.embed_dim = embed_dim
        self.vehicle_capacity = vehicle_capacity
        
        # Encoder
        self.encoder = AttentionEncoder(input_dim, embed_dim, n_heads, n_encoder_layers, ff_dim)
        
        # Decoder
        self.decoder = AttentionDecoder(embed_dim, n_heads)
        
        # State embedding for context
        self.state_embed = nn.Linear(3, embed_dim)  # [current_load, current_time, vehicle_id]
        
    def forward(self, node_features, return_probs=False):
        """
        Args:
            node_features: (batch, n_nodes, input_dim)
            return_probs: whether to return probabilities
        Returns:
            tours: list of node sequences
            log_probs: log probabilities of actions
        """
        batch_size, n_nodes, _ = node_features.size()
        
        # Encode all nodes
        encoded = self.encoder(node_features)
        
        # Initialize
        tours = []
        log_probs_list = []
        masks = torch.zeros(batch_size, n_nodes, dtype=torch.bool, device=node_features.device)
        masks[:, 0] = True  # Depot always masked initially
        
        current_node = torch.zeros(batch_size, dtype=torch.long, device=node_features.device)
        current_load = torch.zeros(batch_size, device=node_features.device)
        current_time = torch.zeros(batch_size, device=node_features.device)
        
        for step in range(n_nodes * 2):  # Max steps
            # Create context
            current_encoded = encoded[torch.arange(batch_size), current_node]
            depot_encoded = encoded[:, 0]
            state_features = torch.stack([current_load / self.vehicle_capacity, 
                                         current_time / 1000, 
                                         torch.zeros_like(current_load)], dim=-1)
            state_encoded = self.state_embed(state_features)
            context = (current_encoded + depot_encoded + state_encoded) / 3
            
            # Get next node probabilities
            log_probs = self.decoder(encoded, context, masks)
            
            # Sample next node
            if self.training:
                probs = torch.exp(log_probs)
                selected = torch.multinomial(probs, 1).squeeze(-1)
            else:
                selected = log_probs.argmax(dim=-1)
            
            tours.append(selected)
            log_probs_list.append(log_probs[torch.arange(batch_size), selected])
            
            # Update state - avoid in-place operation
            new_masks = masks.clone()
            new_masks[torch.arange(batch_size), selected] = True
            masks = new_masks
            current_node = selected
            
            # Check if all nodes visited
            if masks.all():
                break
        
        tours = torch.stack(tours, dim=1)
        log_probs = torch.stack(log_probs_list, dim=1)
        
        if return_probs:
            return tours, log_probs
        return tours
    
    def decode_greedy(self, node_features):
        """Greedy decoding for inference"""
        self.eval()
        with torch.no_grad():
            tours = self.forward(node_features, return_probs=False)
        return tours
