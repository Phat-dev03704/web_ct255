# BÁO CÁO KỸ THUẬT: THUẬT TOÁN ANT COLONY OPTIMIZATION CHO VRPTW

**Thuật toán**: Ant Colony Optimization (ACO) — Swarm Intelligence  
**Bài toán**: Vehicle Routing Problem with Time Windows (VRPTW)  
**File triển khai**: `aco_vrptw_solver.py`

---

## 1. KIẾN TRÚC VÀ THÀNH PHẦN

### 1.1. Kiến trúc tổng quát

Class `AntColonyVRPTWSolver` gồm 4 giai đoạn chính:

**Phase 1 – Initialization**: Đọc dữ liệu CSV, tách depot/khách hàng, tính **ma trận khoảng cách** Euclid và **ma trận thời gian** (giả định vận tốc = 1), khởi tạo **pheromone matrix** đồng nhất.

**Phase 2 – Ant Solution Construction**: Mỗi “kiến” xây dựng một nghiệm tuyến đường khả thi từ depot bằng **quy tắc xác suất** dựa trên **pheromone** và **heuristic** (visibility = 1/distance), có kiểm tra **capacity** và **time windows**.

**Phase 3 – Pheromone Update + Local Search**: Sau mỗi vòng lặp (iteration), thực hiện **global evaporation** và **deposit pheromone** theo nghiệm tốt nhất; trong quá trình kiến đi, dùng **local evaporation** trên cung vừa đi qua. Tuỳ chọn **2‑opt local search** cải thiện từng route.

**Phase 4 – Output & Visualization**: Chuẩn hóa `self.solution` (route, distance, load, num_customers), tổng hợp thống kê, vẽ biểu đồ đa subplot (routes, thống kê xe, phân bố khách hàng), và lưu **PNG**/**TXT** nếu cần.

### 1.2. Cấu trúc dữ liệu

**Input**
- `self.data`: DataFrame toàn bộ dataset (dòng 0 = depot).
- `self.depot`: Series depot.
- `self.customers`: DataFrame khách hàng (từ dòng 1).

**Computational**
- `self.distance_matrix`: (n+1)×(n+1) Euclid.  
- `self.time_matrix`: sao chép từ distance khi tốc độ = 1.  
- `self.pheromone`: (n+1)×(n+1), khởi tạo hằng số.

**Solution**
```python
self.solution = {
    route_id: {
        'route': [customer_ids],
        'distance': float,
        'load': int,
        'num_customers': int
    }
}
```

### 1.3. Các phương thức chính

- `_calculate_distance_matrix()`: Ma trận khoảng cách **O(n²)**.  
- `_check_time_window_feasibility(route)`: Kiểm tra cửa sổ thời gian **O(k)**.  
- `_calculate_route_distance(route)`, `_calculate_route_load(route)`: **O(k)**.  
- `_initialize_pheromone(initial_value)`: Khởi tạo pheromone matrix.  
- `_calculate_heuristic()`: Tính visibility = 1/distance.  
- `_select_next_customer(...)`: Quy tắc chọn theo xác suất \( P_{ij} \propto \tau_{ij}^{\alpha}\,\eta_{ij}^{\beta} \).  
- `_construct_ant_solution(alpha, beta, heuristic)`: Xây nghiệm cho một kiến.  
- `_update_pheromone_local(...)`, `_update_pheromone_global(...)`: Bay hơi & bồi pheromone.  
- `_apply_local_search_2opt(routes)`: Cải thiện route trong‑route.  
- `get_recommended_hyperparameters()`: Gợi ý tham số theo kích thước n.  
- `solve(...)`: Vòng lặp ACO.  
- `visualize_solution_comprehensive(save)`, `save_solution(...)`: Vẽ & lưu báo cáo.

---

## 2. THUẬT TOÁN ANT COLONY OPTIMIZATION

### 2.1. Ý tưởng cốt lõi

ACO mô phỏng hành vi **kiến tìm đường**: trên đường đi, kiến để lại **pheromone**; đường tốt (ngắn) nhận **nhiều bồi đắp**, dẫn đến **xác suất cao** được chọn ở các lần sau. Cùng lúc, **pheromone bay hơi** giúp tránh kẹt cục bộ và khuyến khích khám phá tuyến mới.

### 2.2. Quy tắc lựa chọn xác suất

Với node hiện tại \( i \) và khách hàng khả thi \( j \):
\[
P(i \to j) =
\frac{ \tau_{ij}^{\alpha}\,\eta_{ij}^{\beta} }{ \sum_{k \in \mathcal{F}} \tau_{ik}^{\alpha}\,\eta_{ik}^{\beta} },
\quad \eta_{ij} = \frac{1}{d_{ij}}
\]
Trong đó:  
- \( \tau_{ij} \): pheromone trên cung \( i\to j \) (exploitation),  
- \( \eta_{ij} \): heuristic (visibility) (exploration),  
- \( \alpha \): trọng số pheromone (0.5–2),  
- \( \beta \): trọng số heuristic (2–5).

### 2.3. Pheromone Update

- **Local update** (khi kiến đi qua cung \( i\to j \)):  
  \( \tau_{ij} \leftarrow (1-\rho_{\text{local}})\,\tau_{ij} \)  
- **Global update** (sau mỗi iteration, trên nghiệm tốt nhất):  
  - **Evaporation**: \( \tau \leftarrow (1-\rho)\,\tau \)  
  - **Deposit**: \( \tau_{ij} \leftarrow \tau_{ij} + \Delta\tau,\ \Delta\tau = \dfrac{Q}{L_{\text{best}}} \)

### 2.4. Feasibility & Local Search

Trong quá trình xây nghiệm, mọi bước chọn đều phải thỏa **capacity** và **time windows**. Sau khi có các routes, **2‑opt** trong‑route được dùng để **giảm quãng đường** mà vẫn giữ **feasible**.

---

## 3. ĐỘ PHỨC TẠP & HIỆU NĂNG

### 3.1. Thời gian

Gần đúng: **O(max_iterations × n_ants × cost_construct)**, trong đó `cost_construct` ≈ số lần chọn kế tiếp × chi phí kiểm tra feasibility.

| Thành phần | Độ phức tạp | Ghi chú |
|---|---|---|
| Distance/Time matrix | O(n²) | Một lần |
| Khởi tạo pheromone | O(n²) | Hằng |
| Xây nghiệm mỗi kiến | O(n·log n) ~ O(n²) | Tính xác suất + feasibility |
| Local update | O(n) | Theo số cung đi qua |
| Global update | O(n) | Trên best routes |
| 2‑opt (tùy chọn) | O(n²) | Trong từng route |

### 3.2. Bộ nhớ

- Ma trận distance/time & pheromone: **O(n²)**.  
- Solution: **O(n)**.  
- Heuristic matrix: **O(n²)**.

---

## 4. SIÊU THAM SỐ & TINH CHỈNH

### 4.1. Danh sách siêu tham số

| Tham số | Vai trò | Gợi ý từ mã |
|---|---|---|
| `n_ants` | Số kiến | 20 (n≤50), 30 (≤100), 40 (>100) |
| `max_iterations` | Số vòng lặp | 100 / 150 / 200 |
| `alpha` | Trọng số pheromone | 1.0 (balance) |
| `beta` | Trọng số heuristic | 3.0 (ưu tiên gần) |
| `rho` | Global evaporation | 0.2 |
| `rho_local` | Local evaporation | 0.1 |
| `Q` | Lượng bồi pheromone | 1.0 |
| `use_local_search` | 2‑opt hậu xử lý | True |
| `time_limit` | Giới hạn thời gian | 60s |

### 4.2. Điều chỉnh theo mục tiêu

| Mục tiêu | Điều chỉnh |
|---|---|
| Khám phá mạnh | Tăng `rho`, giảm `alpha` |
| Khai thác sâu | Giảm `rho`, tăng `alpha` |
| Chất lượng cao hơn | Tăng `max_iterations`, `n_ants`, bật `use_local_search` |
| Tăng tốc | Giảm `n_ants`, `max_iterations`, tắt `use_local_search` |
| Ổn định hội tụ | Duy trì `beta > alpha`, giữ `Q=1.0` |

---

