# Pointer Network Training Guide

## Training Improvements Overview

Pointer Network đã được tối ưu hóa với các cải tiến sau:

### 1. Reward Shaping (Quan trọng nhất!)

Reward function được thiết kế để hướng dẫn model học hiệu quả:

```python
# Base reward: Negative distance (scaled)
reward = -total_distance / 10.0

# Penalties
reward -= time_window_violations * 100.0  # TW violations rất nghiêm trọng
reward -= num_vehicles * 50.0             # Khuyến khích dùng ít xe
reward -= 1000.0 if infeasible           # Penalty lớn cho infeasible solutions

# Bonuses
reward += customers_served * 5.0          # Khuyến khích phục vụ nhiều khách
```

**Lý do**: REINFORCE cần reward signal rõ ràng để học. Simple negative distance không đủ thông tin.

### 2. Input Normalization

Tất cả features được normalize về cùng scale:

```python
x, y: coordinates / 100.0      # Scale xuống [0, 1]
demand: demand / 200.0         # Normalize với vehicle capacity
time: time / 1000.0            # Normalize time windows
```

**Lý do**: Neural networks học tốt hơn khi input có scale tương đương nhau.

### 3. Network Architecture

**Encoder**: Bidirectional LSTM với 2 layers
- Hidden dim: 256 (đủ lớn để capture complex patterns)
- Dropout: 0.1 (prevent overfitting)
- BatchNorm trong embedding layer (stabilize training)

**Decoder**: Unidirectional LSTM với 2 layers
- Hidden dim: 256
- Attention mechanism để focus vào relevant nodes

**Lý do**: Bi-LSTM cho encoder giúp capture context tốt hơn. Attention giúp model tập trung vào nodes quan trọng.

### 4. Training Strategy

**REINFORCE với Baseline**:
```python
baseline = 0.9 * baseline + 0.1 * mean_reward  # Exponential moving average
advantage = reward - baseline
loss = -log_prob * advantage - 0.01 * entropy
```

**Gradient Clipping**: Clip norm = 1.0
- Prevents gradient explosion trong REINFORCE

**Entropy Bonus**: 0.01
- Khuyến khích exploration

**Lý do**: Baseline giảm variance của policy gradient. Entropy bonus giúp tránh converge quá sớm vào local optima.

### 5. Training Datasets

Sử dụng 21 datasets đa dạng:
- 9 từ C1 (clustered, short time windows)
- 6 từ R1 (random, short time windows)
- 5 từ RC1 (mixed)

**Lý do**: Diverse training data giúp model generalize tốt hơn.

### 6. Hyperparameters

```python
learning_rate = 1e-4        # Stable learning
num_episodes = 2000         # Enough for convergence
eval_interval = 100         # Monitor regularly
baseline_momentum = 0.9     # Smooth baseline updates
gradient_clip = 1.0         # Stability
```

## Expected Results

### Training Progress

**Episode 0-500**: Model học cơ bản
- Distance: 1500-2000
- Reward: -200 to -150
- Baseline: Tăng dần từ âm lớn

**Episode 500-1000**: Model cải thiện đáng kể
- Distance: 1000-1500
- Reward: -150 to -100
- Customers served: 80-90%

**Episode 1000-2000**: Model gần converge
- Distance: 600-1000
- Reward: -100 to -60
- Customers served: 95-100%

### Final Performance (sau 2000 episodes)

**Good convergence**:
- Average distance: 600-800
- Average vehicles: 12-15
- Customer service rate: >95%
- Baseline stable: -60 to -80

**Warning signs**:
- Distance không giảm sau 1000 episodes → Learning rate quá thấp
- Baseline tăng quá nhanh → Reward function có vấn đề
- Customers served < 90% → Constraint handling yếu

## Troubleshooting

### Problem 1: Model không học (distance không giảm)

**Symptoms**: Distance vẫn >1500 sau 1000 episodes

**Causes**:
- Learning rate quá thấp
- Reward signal quá weak
- Gradient vanishing

**Solutions**:
```python
# Tăng learning rate
learning_rate = 3e-4  # từ 1e-4

# Tăng reward signal
reward = -distance / 5.0  # từ /10.0

# Check gradient norms
torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
print(f"Grad norm: {grad_norm}")  # Should be 0.1-1.0
```

### Problem 2: Training quá chậm

**Symptoms**: 2000 episodes mất >6 hours

**Causes**:
- Hidden dimension quá lớn
- Quá nhiều LSTM layers
- Không dùng GPU

**Solutions**:
```python
# Giảm model size
hidden_dim = 128  # từ 256
num_layers = 1    # từ 2

# Sử dụng GPU
device = 'cuda' if torch.cuda.is_available() else 'cpu'

# Giảm sequence length
max_steps = 50  # thay vì n_customers + 10
```

### Problem 3: Overfitting (train tốt, test kém)

**Symptoms**: Training distance <500 nhưng test distance >1000

**Causes**:
- Train trên quá ít datasets
- Dropout quá thấp
- Model quá phức tạp

**Solutions**:
```python
# Tăng training datasets
dataset_paths = [...] # Use more diverse datasets

# Tăng dropout
dropout = 0.2  # từ 0.1

# Thêm L2 regularization
optimizer = torch.optim.Adam(model.parameters(), 
                            lr=lr, weight_decay=1e-5)
```

### Problem 4: Loss explodes

**Symptoms**: Loss đột ngột tăng lên rất lớn (>1000)

**Causes**:
- Learning rate quá cao
- Gradient explosion
- Reward scale không ổn định

**Solutions**:
```python
# Giảm learning rate
learning_rate = 5e-5  # từ 1e-4

# Tăng gradient clipping
torch.nn.utils.clip_grad_norm_(model.parameters(), 0.5)

# Normalize rewards
rewards = (rewards - rewards.mean()) / (rewards.std() + 1e-8)
```

### Problem 5: Không phục vụ hết customers

**Symptoms**: Customers served < 90%

**Causes**:
- Penalty cho infeasibility quá nhẹ
- Masking logic có bug
- Model không học được constraints

**Solutions**:
```python
# Tăng infeasibility penalty
reward -= 2000.0 if infeasible  # từ 1000.0

# Tăng customer serving bonus
reward += customers_served * 10.0  # từ 5.0

# Check masking logic
print(f"Mask sum: {mask.sum()}")  # Should be >0 always
```

## Advanced Techniques

### 1. Beam Search Decoding

Thay vì greedy (chọn action tốt nhất), dùng beam search để explore:

```python
def decode_beam_search(self, inputs, beam_size=5):
    # Keep top-k candidates at each step
    # More computation but better solutions
    pass
```

### 2. Prioritized Experience Replay

Lưu và replay các episodes có reward cao:

```python
replay_buffer = []
for episode in episodes:
    replay_buffer.append((state, action, reward))
    
# Sample high-reward episodes more frequently
priorities = softmax(rewards)
sampled = np.random.choice(replay_buffer, p=priorities)
```

### 3. Curriculum Learning

Bắt đầu với instances đơn giản, tăng dần độ khó:

```python
# Week 1: Train on C101-C103 (easy)
# Week 2: Add R101-R103 (medium)
# Week 3: Add RC101-RC103 (hard)
# Week 4: All datasets
```

### 4. Multi-sample Training

Generate nhiều trajectories mỗi episode:

```python
for _ in range(num_samples):
    actions, log_probs = model.sample()
    rewards = evaluate(actions)
    # Train on all samples
```

### 5. Actor-Critic

Thêm critic network để estimate value function:

```python
class Critic(nn.Module):
    def forward(self, state):
        return value  # Estimate V(s)

# Loss
actor_loss = -log_prob * (reward - critic(state))
critic_loss = (reward - critic(state))**2
```

## Monitoring During Training

### Key Metrics

1. **Loss**: Should decrease gradually (noisy vì REINFORCE)
2. **Reward**: Should increase from -200 to -60
3. **Distance**: Should decrease from 2000 to 600-800
4. **Baseline**: Should stabilize around average reward
5. **Entropy**: Should stay >1.0 (exploration)

### Visualization

Training script tự động tạo:
- `training_curves.png`: 6 subplots (loss, reward, distance, vehicles, customers, moving avg)
- `training_history.csv`: Detailed episode-by-episode data

### Checkpoints

Model tự động save:
- `pointer_network_best.pth`: Best model based on distance
- `pointer_network_final.pth`: Final model sau training

## Recommended Training Schedule

### Phase 1: Warmup (Episode 0-200)
- Model học cơ bản về VRPTW structure
- Distance giảm từ 2000 → 1500
- Focus: Serve customers, basic routing

### Phase 2: Improvement (Episode 200-1000)
- Model học optimize distance
- Distance giảm từ 1500 → 1000
- Focus: Better routes, fewer vehicles

### Phase 3: Fine-tuning (Episode 1000-2000)
- Model fine-tune details
- Distance giảm từ 1000 → 600-800
- Focus: Time window satisfaction, load balancing

## Performance Benchmarks

### C1 datasets (Clustered, Short TW)
- Expected distance: 500-700
- Expected vehicles: 10-12
- Expected time: 0.5-1.0s

### R1 datasets (Random, Short TW)
- Expected distance: 700-900
- Expected vehicles: 12-15
- Expected time: 0.5-1.0s

### RC1 datasets (Mixed)
- Expected distance: 600-800
- Expected vehicles: 11-14
- Expected time: 0.5-1.0s

### C2, R2, RC2 (Long TW)
- Expected distance: 400-600
- Expected vehicles: 3-5
- Expected time: 0.5-1.0s

## Conclusion

Pointer Network với REINFORCE yêu cầu:
1. **Careful reward shaping**: Multi-component rewards
2. **Proper normalization**: All inputs scaled
3. **Adequate training**: 2000+ episodes
4. **Regular monitoring**: Check metrics every 100 episodes
5. **Patience**: Convergence mất 2-4 hours

Success indicators:
- ✅ Distance < 800 on average
- ✅ Customer service rate > 95%
- ✅ Baseline stable
- ✅ Loss decreasing (with noise)
- ✅ Model generalizes to unseen datasets

Happy training! 🚀
