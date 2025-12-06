# Attention Model for VRPTW

## Giới thiệu

Attention Model là một kiến trúc Deep Reinforcement Learning sử dụng Transformer (Multi-Head Attention) để giải bài toán Vehicle Routing Problem with Time Windows (VRPTW).

## Đặc điểm

- **Kiến trúc**: Transformer-based (Encoder-Decoder)
- **Encoder**: Graph Attention Network để encode thông tin nodes
- **Decoder**: Attention-based Pointer Network để chọn node tiếp theo
- **Training**: REINFORCE algorithm với baseline critic
- **End-to-end learning**: Học trực tiếp từ dữ liệu mà không cần expert knowledge

## Cấu trúc Files

```
Attention-Model/
├── attention_model.py          # Định nghĩa model architecture
├── train.py                    # Script training model
├── attention_vrptw_solver.py   # Solver sử dụng trained model
├── test_all_datasets.py        # Test trên tất cả datasets
├── README.md                   # File này
├── models/                     # Thư mục chứa trained models
└── result/                     # Thư mục chứa kết quả
    ├── images/                 # Hình ảnh trực quan hóa
    ├── text/                   # Báo cáo text
    └── test_summary.csv        # Tổng kết kết quả
```

## Cài đặt

```bash
pip install torch numpy pandas matplotlib tqdm
```

## Sử dụng

### 1. Training Model

```bash
python train.py
```

Model sẽ được train trên các datasets trong thư mục `dataset/`. Trained model sẽ được lưu vào `models/attention_model_best.pth`.

### 2. Test trên một dataset

```bash
python attention_vrptw_solver.py
```

### 3. Test trên tất cả datasets

```bash
python test_all_datasets.py
```

## Hyperparameters

### Model Architecture
- `input_dim`: 6 (x, y, demand, ready_time, due_date, service_time)
- `embed_dim`: 128
- `n_heads`: 8 (Multi-Head Attention)
- `n_encoder_layers`: 3
- `ff_dim`: 512 (Feed-forward dimension)

### Training
- `batch_size`: 32
- `learning_rate`: 1e-4
- `n_epochs`: 50
- `optimizer`: Adam

### Inference
- `n_samples`: 10 (số lần sampling để tìm best solution)
- `use_beam_search`: False (có thể bật để cải thiện chất lượng)

## Ưu điểm

✅ **Chất lượng cao**: State-of-the-art cho bài toán routing  
✅ **Generalization tốt**: Học được pattern từ dữ liệu  
✅ **Scalable**: Có thể xử lý instances lớn  
✅ **End-to-end**: Không cần expert knowledge hay hand-crafted features  

## Nhược điểm

❌ **Cần GPU**: Training tốn thời gian và cần GPU mạnh  
❌ **Data hungry**: Cần nhiều dữ liệu training  
❌ **Khó debug**: Khó hiểu được model đang học gì  
❌ **Inference time**: Chậm hơn một số heuristics truyền thống  

## Tham khảo

- **Paper**: "Attention, Learn to Solve Routing Problems!" (Kool et al., 2019)
- **ICLR 2019**: https://arxiv.org/abs/1803.08475

## Kết quả

Kết quả test trên 56 datasets Solomon sẽ được lưu trong thư mục `result/`:
- **images/**: Hình ảnh trực quan hóa routes cho mỗi dataset
- **text/**: Báo cáo chi tiết cho mỗi dataset
- **test_summary.csv**: Tổng kết tất cả kết quả
- **test_report.txt**: Báo cáo tổng quan

## Tác giả

Được phát triển dựa trên paper "Attention, Learn to Solve Routing Problems!" (Kool et al., 2019)
