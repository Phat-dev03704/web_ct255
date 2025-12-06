# Deep Q-Network (DQN) for VRPTW

## Overview

This implementation uses **Deep Q-Network (DQN)** with several advanced techniques to solve the Vehicle Routing Problem with Time Windows (VRPTW). DQN is a reinforcement learning algorithm that learns to make sequential decisions by approximating the Q-value function using deep neural networks.

## Algorithm Description

### Core Concept

DQN combines:
- **Q-Learning**: Learn optimal action-value function Q(s,a)
- **Deep Neural Networks**: Approximate Q-function for large state spaces
- **Experience Replay**: Break correlation between consecutive samples
- **Target Network**: Stabilize training by using separate network for targets

### Key Components

1. **State Representation** (9 dimensions):
   - Current node features (6): x, y, demand, ready time, due date, service time
   - Vehicle state (3): current load ratio, current time, unvisited ratio

2. **Action Space**:
   - Select next customer to visit (0 = depot, 1-N = customers)
   - Actions masked by feasibility constraints

3. **Reward Function**:
   - Negative distance traveled (minimize total distance)
   - Bonus reward for completing routes
   - Penalties for constraint violations

4. **Network Architecture**:
   - **Basic DQN**: State encoder → Q-values
   - **Dueling DQN**: Separates state value V(s) and advantage A(s,a)
     ```
     Q(s,a) = V(s) + A(s,a) - mean(A(s,·))
     ```

### Advanced Techniques

1. **Double DQN**:
   - Reduces overestimation bias
   - Uses policy network to select action, target network to evaluate
   - Target: `r + γ * Q_target(s', argmax_a Q_policy(s', a))`

2. **Experience Replay**:
   - Store transitions in replay buffer
   - Sample random minibatches for training
   - Breaks temporal correlation

3. **Prioritized Experience Replay** (optional):
   - Sample important transitions more frequently
   - Priority based on TD-error
   - Importance sampling weights for bias correction

4. **Epsilon-Greedy Exploration**:
   - ε-greedy: Random action with probability ε
   - Decay ε over time: ε_t = max(ε_end, ε_start * decay^t)

## File Structure

```
DQN-RL/
├── dqn_model.py              # DQN architecture and agent
├── train.py                  # Training script with environment
├── dqn_vrptw_solver.py       # Inference solver
├── test_all_datasets.py      # Batch testing
├── README.md                 # This file
├── models/                   # Saved models
│   └── dqn_model_best.pth
└── result/                   # Test results
    ├── images/               # Solution visualizations
    ├── text/                 # Detailed solutions
    └── csv/                  # Summary statistics
```

## Usage

### 1. Train the Model

```bash
python train.py
```

**Training Parameters**:
- Episodes: 1000
- Batch size: 32
- Learning rate: 1e-4
- Discount factor γ: 0.99
- Epsilon: 1.0 → 0.01 (decay: 0.995)
- Target network update: Every 10 episodes
- Buffer capacity: 10,000 transitions

**Training Features**:
- Uses datasets from C1, R1, RC1 categories
- Updates target network periodically
- Saves best model based on episode reward
- Generates training curves

### 2. Solve Single Instance

```bash
python dqn_vrptw_solver.py
```

This will:
- Load trained model
- Solve C101 dataset
- Generate visualization with 3 subplots
- Save solution details

### 3. Test All Datasets

```bash
python test_all_datasets.py
```

This will:
- Test on all 56 Solomon datasets
- Generate visualizations for each
- Create summary CSV and detailed report
- Save all results organized by category

## Model Architecture

### DQN Network

```python
State (9) → Encoder [256, 128] → Q-values (101)
```

### Dueling DQN Network

```python
State (9) → Shared Encoder [256, 128]
            ├→ Value Stream [128] → V(s) (1)
            └→ Advantage Stream [128] → A(s,a) (101)
Q(s,a) = V(s) + [A(s,a) - mean(A(s,·))]
```

## Training Process

1. **Initialize**:
   - Policy network and target network
   - Replay buffer
   - Epsilon for exploration

2. **For each episode**:
   - Reset environment
   - While not done:
     - Select action using ε-greedy
     - Execute action, observe reward and next state
     - Store transition in replay buffer
     - Sample minibatch and update policy network
   - Update target network periodically
   - Decay epsilon

3. **Loss Function** (Huber Loss):
   ```
   L = E[(Q(s,a) - target)²]
   target = r + γ * Q_target(s', argmax_a' Q_policy(s', a'))
   ```

## Solving Process

1. **Load trained model**
2. **For each dataset**:
   - Initialize environment
   - While customers remain:
     - Get current state
     - Compute valid actions (capacity + time window constraints)
     - Select action greedily: argmax_a Q(s,a) over valid actions
     - Execute action
     - Update state
   - Extract routes from solution

## Advantages

1. **Learning-based**: Learns from experience, adapts to problem structure
2. **End-to-end**: Direct policy from state to action
3. **Scalable**: Can handle varying problem sizes
4. **Flexible**: Can incorporate complex constraints
5. **No heuristics needed**: Learns good strategies automatically

## Limitations

1. **Training time**: Requires many episodes to converge
2. **Sample efficiency**: DQN can be sample-inefficient
3. **Exploration**: Needs careful balance with exploitation
4. **Discrete actions**: Best for discrete action spaces
5. **Hyperparameter sensitivity**: Performance depends on tuning

## Results

The solver generates:

1. **Visualization**:
   - Routes plot with color-coded vehicles
   - Statistics panel with route details
   - Load distribution bar chart

2. **Text Report**:
   - Dataset information
   - Solution metrics
   - Route-by-route details

3. **CSV Summary**:
   - All datasets results
   - Statistics by category

## Comparison with Other Methods

| Method | Type | Training | Solution Quality | Speed |
|--------|------|----------|------------------|-------|
| Clarke-Wright | Heuristic | None | Good | Fast |
| Tabu Search | Metaheuristic | None | Very Good | Medium |
| Genetic Algorithm | Metaheuristic | None | Good | Slow |
| Attention Model | Deep RL | Yes | Very Good | Fast (after training) |
| **DQN** | **Deep RL** | **Yes** | **Good** | **Fast (after training)** |

## Hyperparameters

```python
# Network
state_dim = 9
action_dim = 101
hidden_dim = 256

# Training
learning_rate = 1e-4
gamma = 0.99
epsilon_start = 1.0
epsilon_end = 0.01
epsilon_decay = 0.995
batch_size = 32
buffer_capacity = 10000

# Architecture
use_dueling = True          # Dueling DQN
use_double_dqn = True       # Double DQN
use_prioritized_replay = False  # Prioritized replay (optional)
```

## References

1. Mnih, V., et al. (2015). "Human-level control through deep reinforcement learning." *Nature*.
2. Van Hasselt, H., et al. (2016). "Deep Reinforcement Learning with Double Q-learning." *AAAI*.
3. Wang, Z., et al. (2016). "Dueling Network Architectures for Deep Reinforcement Learning." *ICML*.
4. Schaul, T., et al. (2016). "Prioritized Experience Replay." *ICLR*.

## Future Improvements

1. **Rainbow DQN**: Combine multiple improvements (dueling, double, prioritized, etc.)
2. **Multi-step returns**: Use n-step returns for better credit assignment
3. **Noisy networks**: Replace ε-greedy with parameter noise
4. **Distributional RL**: Learn distribution of returns instead of mean
5. **Hierarchical RL**: Two-level policy for route construction and customer selection

## Author

DQN implementation for VRPTW using PyTorch.

## License

MIT License
