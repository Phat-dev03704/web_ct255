# Pointer Network for VRPTW

## Giới thiệu

Pointer Network là một kiến trúc neural network đặc biệt được thiết kế cho các bài toán combinatorial optimization, đặc biệt là các bài toán có output là một chuỗi các chỉ số (pointers) từ input sequence.

## Kiến trúc

### 1. Encoder-Decoder với Attention

Pointer Network sử dụng kiến trúc encoder-decoder với attention mechanism đặc biệt:

```
Input → Encoder (Bi-LSTM) → Encoder Outputs
                                    ↓
Decoder (LSTM) ← Attention ← Previous Output
       ↓
    Pointer (chọn node tiếp theo)
```

### 2. Components chính

#### Input Embedding
- **Input**: 6 features cho mỗi node
  - `x, y`: Tọa độ khách hàng (normalized by 100)
  - `demand`: Nhu cầu hàng hóa (normalized by 200)
  - `ready_time, due_date`: Cửa sổ thời gian (normalized by 1000)
  - `service_time`: Thời gian phục vụ (normalized by 1000)
- **Architecture**: 
  - Linear(6, 256) → BatchNorm → ReLU → Dropout(0.1)
  - Linear(256, 256) → BatchNorm → ReLU
- **Output**: Embedded representation [batch, num_nodes, hidden_dim=256]

#### Encoder (Bi-LSTM)
- **Architecture**: Bidirectional LSTM
  - 2 layers
  - Hidden dimension: 256
  - Dropout: 0.1 between layers
- **Output**: Encoder outputs [batch, num_nodes, 512] (bidirectional)
- **Projection**: Linear(512, 256) để giảm về hidden_dim

#### Attention Mechanism
- **Query**: Decoder hidden state [batch, 256]
- **Keys**: Encoder outputs [batch, num_nodes, 256]
- **Computation**:
  ```
  scores = v(tanh(W_ref(encoder_outputs) + W_q(decoder_hidden)))
  probs = softmax(scores, mask)
  ```
- **Masking**: Loại bỏ các nodes đã visited hoặc vi phạm constraints

#### Decoder (LSTM)
- **Architecture**: Unidirectional LSTM
  - 2 layers
  - Hidden dimension: 256
  - Dropout: 0.1 between layers
- **Input**: Embedding của node vừa được chọn
- **Initial hidden state**: Từ encoder final state

### 3. Training với REINFORCE

#### Reward Function
Pointer Network được train bằng REINFORCE algorithm với reward function:

```
reward = -distance/10.0          (scaled distance penalty)
       - tw_violations * 100.0   (time window violations)
       - num_vehicles * 50.0     (vehicle usage penalty)
       + customers_served * 5.0  (customer serving bonus)
       - 1000.0 (if infeasible)  (infeasibility penalty)
```

#### Baseline
- Exponential moving average của rewards
- Momentum: 0.9
- Giúp giảm variance trong gradient estimation

#### Loss Function
```
loss = -log_prob(actions) * (reward - baseline) - 0.01 * entropy
```

- **Policy gradient**: Maximize expected reward
- **Entropy bonus**: Khuyến khích exploration (0.01)

## Hyperparameters

### Model Architecture
- `input_dim`: 6 (customer features)
- `hidden_dim`: 256
- `num_layers`: 2 (LSTM layers)
- `dropout`: 0.1

### Training
- `learning_rate`: 1e-4 (Adam optimizer)
- `num_episodes`: 2000
- `batch_size`: 1 (single instance per episode)
- `baseline_momentum`: 0.9
- `gradient_clip`: 1.0

### VRPTW Constraints
- `vehicle_capacity`: 200
- `max_vehicles`: 25

## Cài đặt

### Requirements
```bash
pip install torch pandas numpy matplotlib
```

### Training
```bash
cd algorithm/ML/NeuralCombinatorialOptimization/Pointer-Network
python train.py
```

Training sẽ:
- Train trên 21 datasets (C1, R1, RC1)
- Chạy 2000 episodes
- Save best model dựa trên average distance
- Lưu training curves và history

### Testing
```bash
python test_all_datasets.py
```

Testing sẽ:
- Test trên tất cả 56 datasets Solomon
- Tạo visualizations (result/images/)
- Tạo solution files (result/text/)
- Tạo summary report (test_summary.csv, test_report.txt)

### Inference trên 1 dataset
```bash
python pointer_network_vrptw_solver.py
```

## Output Files

### Training
- `models/pointer_network_best.pth`: Best model checkpoint
- `models/pointer_network_final.pth`: Final model
- `models/training_curves.png`: Training visualization
- `models/training_history.csv`: Detailed training history

### Testing
- `result/images/*.png`: Route visualizations
- `result/text/*.txt`: Solution details
- `result/test_summary.csv`: Summary statistics
- `result/test_report.txt`: Detailed report

## Ưu điểm

1. **End-to-end learning**: Học trực tiếp từ data, không cần hand-crafted heuristics
2. **Attention mechanism**: Tự động học cách focus vào các nodes quan trọng
3. **Generalization**: Có thể generalize sang instances khác
4. **Fast inference**: Greedy decoding rất nhanh sau khi train

## Nhược điểm

1. **Training time**: Cần nhiều episodes để converge (2000+ episodes)
2. **Solution quality**: Có thể không tốt bằng specialized algorithms (Tabu, LNS)
3. **Constraint handling**: Khó enforce hard constraints hoàn toàn
4. **Sample efficiency**: REINFORCE có variance cao, học chậm

## So sánh với các thuật toán khác

| Algorithm | Distance (avg) | Vehicles (avg) | Time (s) | Training Time |
|-----------|----------------|----------------|----------|---------------|
| Pointer Network | ~600-800 | ~12-15 | 0.5-1.0 | 2-4 hours |
| DQN | ~500-700 | ~10-13 | 1-2 | 3-5 hours |
| Attention Model | ~400-600 | ~10-12 | 0.5-1.0 | 4-6 hours |
| Tabu Search | ~350-500 | ~10-12 | 5-10 | - |
| LNS | ~300-450 | ~10-12 | 10-30 | - |

## Cải tiến có thể

1. **Beam Search**: Thay vì greedy, dùng beam search để explore nhiều solutions
2. **Critic Network**: Thêm value network để estimate baseline tốt hơn
3. **Multi-task Learning**: Train đồng thời trên nhiều loại constraints
4. **Prioritized Experience Replay**: Lưu và replay các episodes tốt
5. **Curriculum Learning**: Bắt đầu với instances đơn giản, tăng dần độ khó

## References

1. Vinyals, O., Fortunato, M., & Jaitly, N. (2015). Pointer networks. NeurIPS.
2. Bello, I., Pham, H., Le, Q. V., Norouzi, M., & Bengio, S. (2017). Neural combinatorial optimization with reinforcement learning. ICLR.
3. Kool, W., van Hoof, H., & Welling, M. (2019). Attention, learn to solve routing problems! ICLR.

## License

MIT License

## Author

Developed for Vehicle Routing Problem with Time Windows research project.
