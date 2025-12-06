"""
Trainer for Attention Model VRPTW
Training using REINFORCE algorithm with baseline
"""

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import pandas as pd
from pathlib import Path
import time
from tqdm import tqdm
import matplotlib.pyplot as plt

from attention_model import AttentionModelVRPTW


class VRPTWDataset:
    """Dataset loader for VRPTW"""
    def __init__(self, dataset_paths, batch_size=32):
        self.dataset_paths = dataset_paths
        self.batch_size = batch_size
        self.data_cache = []
        
        # Load all datasets
        for path in dataset_paths:
            df = pd.read_csv(path)
            self.data_cache.append(self._preprocess(df))
    
    def _preprocess(self, df):
        """Preprocess dataset to tensor format"""
        # Extract features: [x, y, demand, ready_time, due_date, service_time]
        features = df[['XCOORD.', 'YCOORD.', 'DEMAND', 'READY TIME', 'DUE DATE', 'SERVICE TIME']].values
        
        # Convert to float (handle string values)
        features_float = np.zeros_like(features, dtype=np.float32)
        for i in range(features.shape[0]):
            for j in range(features.shape[1]):
                val = features[i, j]
                if isinstance(val, str):
                    # If string, take first number (e.g., "0.00    1" -> "0.00")
                    features_float[i, j] = float(val.split()[0])
                else:
                    features_float[i, j] = float(val)
        
        # Normalize
        features_float[:, 0:2] = features_float[:, 0:2] / 100.0  # Normalize coordinates
        features_float[:, 2] = features_float[:, 2] / 200.0  # Normalize demand
        features_float[:, 3:6] = features_float[:, 3:6] / 1000.0  # Normalize time
        
        return torch.FloatTensor(features_float)
    
    def get_batch(self):
        """Get a random batch"""
        indices = np.random.choice(len(self.data_cache), self.batch_size, replace=True)
        batch = torch.stack([self.data_cache[i] for i in indices])
        return batch


class BaselineCritic(nn.Module):
    """Critic network for baseline estimation"""
    def __init__(self, embed_dim):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(embed_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 1)
        )
    
    def forward(self, encoded):
        """
        Args:
            encoded: (batch, n_nodes, embed_dim)
        Returns:
            baseline: (batch,) - estimated tour length
        """
        # Global average pooling
        pooled = encoded.mean(dim=1)
        baseline = self.network(pooled).squeeze(-1)
        return baseline


class AttentionModelTrainer:
    """Trainer for Attention Model"""
    def __init__(self, 
                 model,
                 train_datasets,
                 val_datasets=None,
                 batch_size=32,
                 lr=1e-4,
                 device='cuda' if torch.cuda.is_available() else 'cpu'):
        
        self.model = model.to(device)
        self.device = device
        self.batch_size = batch_size
        
        # Baseline critic
        self.baseline = BaselineCritic(model.embed_dim).to(device)
        
        # Optimizers
        self.optimizer = optim.Adam(model.parameters(), lr=lr)
        self.baseline_optimizer = optim.Adam(self.baseline.parameters(), lr=lr)
        
        # Data loaders
        self.train_loader = VRPTWDataset(train_datasets, batch_size)
        self.val_loader = VRPTWDataset(val_datasets, batch_size) if val_datasets else None
        
        # Training stats
        self.train_losses = []
        self.val_rewards = []
        
    def compute_tour_length(self, node_features, tours):
        """Compute total tour length"""
        batch_size = node_features.size(0)
        lengths = torch.zeros(batch_size, device=self.device)
        
        for b in range(batch_size):
            coords = node_features[b, :, 0:2] * 100  # Denormalize
            tour = tours[b]
            
            # Add depot at start and end
            full_tour = torch.cat([torch.zeros(1, dtype=torch.long, device=self.device), 
                                  tour,
                                  torch.zeros(1, dtype=torch.long, device=self.device)])
            
            # Compute distances
            for i in range(len(full_tour) - 1):
                idx1, idx2 = full_tour[i], full_tour[i+1]
                if idx2 < coords.size(0):  # Valid index
                    dist = torch.norm(coords[idx1] - coords[idx2])
                    lengths[b] += dist
        
        return lengths
    
    def train_epoch(self, epoch):
        """Train for one epoch"""
        self.model.train()
        self.baseline.train()
        
        epoch_loss = 0
        epoch_reward = 0
        n_batches = 100  # Number of batches per epoch
        
        pbar = tqdm(range(n_batches), desc=f'Epoch {epoch}')
        
        for batch_idx in pbar:
            # Get batch
            batch = self.train_loader.get_batch().to(self.device)
            
            # Forward pass for policy
            tours, log_probs = self.model(batch, return_probs=True)
            
            # Compute reward (negative tour length)
            tour_lengths = self.compute_tour_length(batch, tours)
            rewards = -tour_lengths
            
            # Baseline - compute with detached encoded to avoid graph issues
            with torch.no_grad():
                encoded_baseline = self.model.encoder(batch)
            baseline_vals = self.baseline(encoded_baseline)
            
            # REINFORCE loss
            advantages = rewards - baseline_vals.detach()
            policy_loss = -(log_probs.sum(dim=1) * advantages).mean()
            
            # Optimize policy
            self.optimizer.zero_grad()
            policy_loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
            self.optimizer.step()
            
            # Baseline loss - compute separately
            encoded_for_baseline = self.model.encoder(batch)
            baseline_vals_train = self.baseline(encoded_for_baseline)
            baseline_loss = F.mse_loss(baseline_vals_train, rewards.detach())
            
            # Optimize baseline
            self.baseline_optimizer.zero_grad()
            baseline_loss.backward()
            self.baseline_optimizer.step()
            
            # Stats
            epoch_loss += policy_loss.item()
            epoch_reward += rewards.mean().item()
            
            pbar.set_postfix({
                'loss': f'{policy_loss.item():.4f}',
                'reward': f'{rewards.mean().item():.2f}',
                'tour_len': f'{tour_lengths.mean().item():.2f}'
            })
        
        avg_loss = epoch_loss / n_batches
        avg_reward = epoch_reward / n_batches
        
        self.train_losses.append(avg_loss)
        
        return avg_loss, avg_reward
    
    def validate(self):
        """Validate on validation set"""
        if self.val_loader is None:
            return 0
        
        self.model.eval()
        total_reward = 0
        n_batches = 20
        
        with torch.no_grad():
            for _ in range(n_batches):
                batch = self.val_loader.get_batch().to(self.device)
                tours = self.model.decode_greedy(batch)
                tour_lengths = self.compute_tour_length(batch, tours)
                rewards = -tour_lengths
                total_reward += rewards.mean().item()
        
        avg_reward = total_reward / n_batches
        self.val_rewards.append(avg_reward)
        
        return avg_reward
    
    def train(self, n_epochs, save_path=None):
        """Train the model"""
        print(f"\n{'='*80}")
        print(f"TRAINING ATTENTION MODEL FOR VRPTW")
        print(f"{'='*80}")
        print(f"Device: {self.device}")
        print(f"Batch size: {self.batch_size}")
        print(f"Epochs: {n_epochs}")
        print(f"{'='*80}\n")
        
        best_reward = float('-inf')
        
        for epoch in range(1, n_epochs + 1):
            # Train
            train_loss, train_reward = self.train_epoch(epoch)
            
            # Validate
            val_reward = self.validate()
            
            print(f"Epoch {epoch}/{n_epochs} - "
                  f"Train Loss: {train_loss:.4f}, "
                  f"Train Reward: {train_reward:.2f}, "
                  f"Val Reward: {val_reward:.2f}")
            
            # Save best model
            if val_reward > best_reward and save_path:
                best_reward = val_reward
                save_path = Path(save_path)
                save_path.parent.mkdir(parents=True, exist_ok=True)
                torch.save({
                    'epoch': epoch,
                    'model_state_dict': self.model.state_dict(),
                    'baseline_state_dict': self.baseline.state_dict(),
                    'optimizer_state_dict': self.optimizer.state_dict(),
                    'best_reward': best_reward,
                }, str(save_path))
                print(f"✓ Saved best model (reward: {best_reward:.2f})")
        
        print(f"\n{'='*80}")
        print(f"TRAINING COMPLETED")
        print(f"Best validation reward: {best_reward:.2f}")
        print(f"{'='*80}\n")
    
    def plot_training_curves(self, save_path=None):
        """Plot training curves"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))
        
        # Loss curve
        ax1.plot(self.train_losses)
        ax1.set_xlabel('Epoch')
        ax1.set_ylabel('Loss')
        ax1.set_title('Training Loss')
        ax1.grid(True)
        
        # Reward curve
        if self.val_rewards:
            ax2.plot(self.val_rewards)
            ax2.set_xlabel('Epoch')
            ax2.set_ylabel('Reward')
            ax2.set_title('Validation Reward')
            ax2.grid(True)
        
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
    
    # Collect training datasets
    train_datasets = []
    for category in ['C1', 'R1', 'RC1']:
        cat_dir = dataset_dir / category
        if cat_dir.exists():
            train_datasets.extend(list(cat_dir.glob('*.csv'))[:5])  # First 5 of each
    
    # Collect validation datasets
    val_datasets = []
    for category in ['C2', 'R2', 'RC2']:
        cat_dir = dataset_dir / category
        if cat_dir.exists():
            val_datasets.extend(list(cat_dir.glob('*.csv'))[:3])  # First 3 of each
    
    print(f"Training datasets: {len(train_datasets)}")
    print(f"Validation datasets: {len(val_datasets)}")
    
    # Create model
    model = AttentionModelVRPTW(
        input_dim=6,
        embed_dim=128,
        n_heads=8,
        n_encoder_layers=3,
        ff_dim=512,
        vehicle_capacity=200
    )
    
    # Create trainer
    trainer = AttentionModelTrainer(
        model=model,
        train_datasets=[str(p) for p in train_datasets],
        val_datasets=[str(p) for p in val_datasets],
        batch_size=32,
        lr=1e-4
    )
    
    # Train
    save_path = current_dir / "models" / "attention_model_best.pth"
    trainer.train(n_epochs=50, save_path=save_path)
    
    # Plot training curves
    plot_path = current_dir / "result" / "training_curves.png"
    trainer.plot_training_curves(save_path=plot_path)


if __name__ == "__main__":
    import torch.nn.functional as F
    main()
