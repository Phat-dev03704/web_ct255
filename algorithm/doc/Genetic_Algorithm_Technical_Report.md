# BÁO CÁO KỸ THUẬT: THUẬT TOÁN GENETIC ALGORITHM CHO VRPTW

**Thuật toán**: Genetic Algorithm (GA) — Metaheuristic tiến hóa  
**Bài toán**: Vehicle Routing Problem with Time Windows (VRPTW)  
**File triển khai**: `ga_vrptw_solver.py`

---

## 1. KIẾN TRÚC VÀ THÀNH PHẦN

### 1.1. Kiến trúc tổng quát

Class `GeneticAlgorithmVRPTWSolver` được tổ chức theo 4 giai đoạn tuần tự:

**Phase 1 – Initialization**: Đọc CSV, tách depot/khách hàng, tính **ma trận khoảng cách** Euclid và **ma trận thời gian** (giả định vận tốc = 1); khởi tạo biến lưu solution và fitness tốt nhất.

**Phase 2 – Initial Population (Nearest Neighbor + Randomization)**: Sinh **population** ban đầu bằng heuristic **Nearest Neighbor** có ngẫu nhiên (nhiều điểm khởi đầu, hệ số nhiễu khi đo khoảng cách) để tăng đa dạng.

**Phase 3 – Evolutionary Loop (Selection → Crossover → Mutation → Elitism)**: Ở mỗi thế hệ:
- **Selection**: Tournament selection (kích thước k).
- **Crossover**: **Order Crossover (OX)** trên chuỗi khách hàng phẳng hóa.
- **Mutation**: hai phép **Swap** (hoán đổi) và **Reverse** (đảo đoạn kiểu 2-opt) có kiểm tra tính khả thi.
- **Elitism**: Giữ lại `elite_size` cá thể tốt nhất.
- Cập nhật best individual/fitness và log cải thiện.

**Phase 4 – Output & Visualization**: Biên dịch `self.solution` (route, distance, load, num_customers), in thống kê, trực quan hóa đa subplot (routes, thống kê xe, phân bố KH) và lưu **PNG**/**TXT** nếu cần.

### 1.2. Cấu trúc dữ liệu

**Input**
- `self.data`: DataFrame toàn bộ dataset (dòng 0 = depot).
- `self.depot`: Series thông tin depot.
- `self.customers`: DataFrame khách hàng (từ dòng 1).

**Computational**
- `self.distance_matrix`: (n+1)×(n+1) Euclid.
- `self.time_matrix`: sao chép từ distance khi tốc độ = 1.

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
- `_create_initial_population_nearest_neighbor(pop_size)`: Sinh quần thể khởi tạo **O(pop × n²)**.
- `_calculate_fitness(routes)`: `fitness = 1 / (total_distance + penalty + 1)` (phạt vi phạm **số xe**, **capacity**, **time window**).
- `_tournament_selection(pop, fitnesses, k)`: Chọn cá thể tốt nhất trong nhóm k.
- `_order_crossover(p1, p2)`: OX trên danh sách khách hàng phẳng, sau đó `_split_into_routes` để tái cấu trúc route hợp lệ.
- `_mutate_swap(routes)`, `_mutate_reverse(routes)`: Hai phép đột biến, chỉ nhận nếu **feasible**.
- `get_recommended_hyperparameters()`: Khuyến nghị tham số theo kích thước n.
- `solve(...)`: Vòng lặp GA.
- `visualize_solution_comprehensive(save)`, `save_solution(...)`: Vẽ & lưu báo cáo.

---

## 2. THUẬT TOÁN GENETIC ALGORITHM

### 2.1. Ý tưởng cốt lõi

GA mô phỏng **tiến hóa tự nhiên**: quần thể cá thể (solutions) được **lai ghép** (crossover) và **đột biến** (mutation) qua nhiều thế hệ; dùng **chọn lọc** (selection) để giữ cá thể khỏe (fitness cao). **Elitism** đảm bảo không mất đi nghiệm tốt nhất đang có.

### 2.2. Đại diện nghiệm & Hàm thích nghi

- **Biểu diễn**: mỗi cá thể là danh sách **routes**; khi lai ghép, các routes được **phẳng hóa** thành chuỗi khách hàng → OX → tách lại thành routes với `_split_into_routes` (tôn trọng capacity/time windows/bound số xe).
- **Fitness**: `1 / (total_distance + penalty + 1)` với penalty cho:
  - Vượt `max_vehicles`.
  - Vượt **vehicle_capacity**.
  - Vi phạm **time windows**.

### 2.3. Operators

- **Selection**: Tournament size = 3 (mặc định) → cân bằng áp lực chọn lọc.
- **Crossover (OX)**: Bảo toàn **trật tự tương đối** của gen; chọn 2 điểm cắt, copy đoạn giữa rồi điền phần còn lại theo thứ tự parent kia.
- **Mutation**:
  - **Swap**: đổi chỗ hai khách hàng (cùng hoặc khác route).
  - **Reverse**: đảo chiều một đoạn liên tiếp (tác dụng như 2-opt trong-route).
  - Cả hai chỉ giữ nếu route **feasible** sau biến đổi.
- **Elitism**: Sao chép `elite_size` cá thể tốt nhất thẳng sang thế hệ mới.

### 2.4. Vòng lặp tiến hóa

```text
Khởi tạo population khả thi và đa dạng
Tính fitness cho tất cả cá thể
best ← cá thể có fitness cao nhất
lặp qua generations hoặc hết time_limit:
    - Giữ lại elite individuals
    - Lặp đến khi đủ population_size:
        * Chọn 2 parents bằng tournament
        * Lai ghép (OX) theo xác suất crossover_rate
        * Đột biến (swap/reverse) theo mutation_rate
        * Thêm vào thế hệ mới
    - Tính fitness thế hệ mới
    - Cập nhật best nếu có cải thiện
    - In tiến độ định kỳ, dừng sớm nếu không cải thiện lâu
Trả về best
```

---

## 3. ĐỘ PHỨC TẠP & HIỆU NĂNG

### 3.1. Thời gian

Gần đúng: **O(max_generations × population_size × cost_eval)**, trong đó `cost_eval` tỷ lệ với số route/độ dài route (tối đa O(n)). Các bước chính:

| Thành phần | Độ phức tạp | Ghi chú |
|---|---|---|
| Distance/Time matrix | O(n²) | Một lần | 
| Initial population | O(pop × n²) | NN + nhiễu |
| Fitness per individual | O(n) | Tính tổng distance + penalty |
| Selection (tournament) | O(k) | k nhỏ (2–5) |
| Crossover (OX) | O(n) | Trên chuỗi KH |
| Mutation (swap/rev) | O(k) | Với kiểm tra feasibility |

Trong thực tế với n≈100–200: thời gian **30–90s** tùy tham số và phần cứng.

### 3.2. Bộ nhớ

- Ma trận distance/time: **O(n²)**.
- Quần thể: **O(pop × n)**.
- Solution: **O(n)**.

---

## 4. SIÊU THAM SỐ & TINH CHỈNH

### 4.1. Danh sách siêu tham số

| Tham số | Vai trò | Gợi ý từ mã |
|---|---|---|
| `population_size` | Quy mô quần thể | 50 (n≤50), 100 (≤100), 150 (>100) |
| `max_generations` | Số thế hệ tối đa | 100 / 150 / 200 |
| `crossover_rate` | Xác suất lai ghép | 0.8 (balance) |
| `mutation_rate` | Xác suất đột biến | 0.2 (balance) |
| `elite_size` | Số cá thể ưu tú | 5 / 10 / 15 theo pop |
| `tournament_size` | Kích thước tournament | 3 (khuyến nghị) |
| `time_limit` | Giới hạn thời gian | 60s (tùy chỉnh) |

### 4.2. Khuyến nghị tự động (trong mã)

`get_recommended_hyperparameters()` trả về bộ tham số chuẩn hóa theo n, giữ cân bằng **đa dạng** và **hội tụ**.

### 4.3. Điều chỉnh theo mục tiêu

| Mục tiêu | Điều chỉnh |
|---|---|
| Chất lượng cao hơn | Tăng `population_size`, `max_generations`; giảm `mutation_rate` nhẹ; giữ `crossover_rate` cao |
| Tăng tốc | Giảm `population_size`, `max_generations`; tăng `mutation_rate` chút; rút gọn kiểm tra feasibility |
| Tránh kẹt local optimum | Tăng `mutation_rate`, thêm reverse mutation; tăng đa dạng khởi tạo |
| Ổn định/hội tụ | Tăng `elite_size`, giảm `mutation_rate` |

---

