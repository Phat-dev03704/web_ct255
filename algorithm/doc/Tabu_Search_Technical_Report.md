# BÁO CÁO KỸ THUẬT: THUẬT TOÁN TABU SEARCH CHO VRPTW

**Thuật toán**: Tabu Search (Metaheuristic with Memory)  
**Bài toán**: Vehicle Routing Problem with Time Windows (VRPTW)  
**File triển khai**: `tabu_vrptw_solver.py`

---

## 1. KIẾN TRÚC VÀ THÀNH PHẦN

### 1.1. Kiến trúc tổng quát

Class `TabuSearchVRPTWSolver` được tổ chức theo 4 giai đoạn xử lý tuần tự:

**Phase 1 – Initialization**: Đọc dữ liệu CSV, tách depot/khách hàng, tính ma trận khoảng cách Euclid và ma trận thời gian (giả sử vận tốc = 1), khởi tạo bộ nhớ Tabu (deque với kích thước `tabu_tenure`).

**Phase 2 – Initial Solution (Nearest Neighbor)**: Tạo nghiệm khởi tạo bằng heuristic **Nearest Neighbor** với kiểm tra **capacity** và **time window** để đảm bảo khả thi ngay từ đầu.

**Phase 3 – Tabu Search Optimization**: Lặp cho đến khi đạt `time_limit` hoặc `max_iterations`: sinh **neighborhood** (Relocate, Exchange, 2‑opt), loại bỏ move bị **tabu**, áp dụng **aspiration** (cho phép move tabu nếu cải thiện best), cập nhật **adaptive tabu tenure** và **diversification** khi bị kẹt lâu.

**Phase 4 – Output & Visualization**: Chuẩn hóa `self.solution`, in báo cáo tổng hợp, vẽ đồ thị đa subplot (routes, thống kê xe, phân bố khách hàng) và lưu file kết quả.

### 1.2. Cấu trúc dữ liệu

**Input structures**:
- `self.data`: DataFrame chứa toàn bộ dataset (dòng 0 là depot).
- `self.depot`: Series depot.
- `self.customers`: DataFrame khách hàng (từ dòng 1 trở đi).

**Computational structures**:
- `self.distance_matrix`: ma trận khoảng cách (n+1)×(n+1).
- `self.time_matrix`: ma trận thời gian (sao chép từ distance khi vận tốc = 1).

**Solution structure**:
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

**Tabu memory**:
```python
self.tabu_list = deque(maxlen=tabu_tenure)  # lưu các move hash
```

### 1.3. Các phương thức chính

- `__init__(dataset_path, vehicle_capacity, max_vehicles)`: Khởi tạo solver, đọc dữ liệu, tính ma trận.  
- `_calculate_distance_matrix()`: Tính Euclid cho tất cả cặp node. **O(n²)**.  
- `_check_time_window_feasibility(route)`: Kiểm tra tính khả thi cửa sổ thời gian. **O(k)**.  
- `_calculate_route_distance(route)`: Tổng quãng đường của route. **O(k)**.  
- `_calculate_route_load(route)`: Tổng tải trọng route. **O(k)**.  
- `_create_initial_solution_nearest_neighbor()`: Sinh nghiệm khởi tạo khả thi. **O(n²)**.  
- `_get_neighborhood_relocate / _exchange / _2opt`: Sinh láng giềng với 3 kiểu move.  
- `solve(...)`: Vòng lặp Tabu Search với thời gian/iterations giới hạn.

---

## 2. THUẬT TOÁN TABU SEARCH

### 2.1. Ý tưởng cốt lõi

Tabu Search là **metaheuristic** sử dụng **bộ nhớ ngắn hạn (Tabu List)** để tránh lặp lại các biến đổi (move) vừa thực hiện, từ đó **vượt qua local optimum**. Cơ chế **Aspiration** cho phép bỏ qua tabu nếu move tạo nên nghiệm **tốt hơn nghiệm tốt nhất** đã biết.

### 2.2. Khung thuật toán

1) Khởi tạo nghiệm khả thi bằng Nearest Neighbor.  
2) Lặp:  
   - Sinh tập láng giềng \(N(x)\) bằng **Relocate**, **Exchange**, **2‑opt**.  
   - Lọc bỏ move **tabu**, trừ khi **aspiration** được kích hoạt.  
   - Chọn neighbor có **hàm mục tiêu nhỏ nhất**.  
   - Cập nhật `current_solution`, thêm move vào `tabu_list`.  
   - Nếu cải thiện `best_solution` → ghi log cải thiện.  
   - Nếu không cải thiện trong nhiều vòng → **diversification** (reset tabu).  
   - Nếu bật **adaptive tabu tenure** → điều chỉnh `tabu_tenure` động.

### 2.3. Neighborhood & Feasibility

- **Relocate**: chuyển 1 khách hàng từ route i → route j (duyệt mọi vị trí chèn).  
- **Exchange**: hoán đổi 1–1 khách hàng giữa hai route.  
- **2‑opt**: đảo ngược đoạn con trong cùng một route.  

Mọi ứng viên đều phải thỏa:  
- **Capacity**: tổng DEMAND của route ≤ `vehicle_capacity`.  
- **Time Windows**: tính thời điểm đến, chờ nếu sớm, không vượt **`DUE DATE`**, quay về depot kịp thời.

### 2.4. Aspiration & Adaptive Tenure

- **Aspiration**: Cho phép move tabu nếu cải thiện `best_distance`.  
- **Adaptive**: Giảm `tabu_tenure` khi vừa cải thiện (*intensification*), tăng khi dậm chân quá lâu (*diversification*).

### 2.5. Diversification

Nếu số vòng **không cải thiện** ≥ `diversification_threshold`, reset `tabu_list`, đưa tìm kiếm sang khu vực mới của không gian nghiệm.

---

## 3. ĐỘ PHỨC TẠP THUẬT TOÁN

### 3.1. Tổng thể

- **Time** ≈ `max_iterations × |N(x)|`, với \(|N(x)|\) là số láng giềng đã kiểm tra (có thể giới hạn bởi `neighborhood_size_limit`).  
- **Space**:  
  - Ma trận khoảng cách/thời gian: **O(n²)**.  
  - `tabu_list`: **O(tabu_tenure)**.  
  - Solution: **O(n)**.

### 3.2. Thành phần chính

| Giai đoạn | Độ phức tạp | Ghi chú |
|---|---|---|
| Tính ma trận | O(n²) | Euclid giữa mọi cặp |
| Khởi tạo NN | O(n²) | Thêm khách gần nhất khả thi |
| Sinh láng giềng | O(n²·k) | Tổng hợp Relocate/Exchange/2‑opt |
| Chọn neighbor | O(|N(x)|) | Sắp xếp/duyệt theo objective |

Thực nghiệm chuẩn cho thấy với n≈100–200, thuật toán đạt chất lượng **Very Good** trong **30–60s** (tùy tham số).

---

## 4. SIÊU THAM SỐ VÀ TINH CHỈNH

### 4.1. Danh sách siêu tham số

| Tham số | Vai trò | Gợi ý |
|---|---|---|
| `tabu_tenure` | Độ dài Tabu List | \(\sqrt{n}\) – \(2\sqrt{n}\) |
| `max_iterations` | Số vòng lặp tối đa | 300–800 |
| `diversification_threshold` | Ngưỡng diversify | 10–20% của `max_iterations` |
| `aspiration_plus` | Bật Aspiration Criterion | True |
| `adaptive_tabu_tenure` | Điều chỉnh động tenure | True khi n>50 |
| `neighborhood_size_limit` | Giới hạn số neighbor | 300–800 cho n≥100 |
| `time_limit` | Giới hạn thời gian chạy | 60–120s |

### 4.2. Heuristic khuyến nghị (tự động trong mã)

Hàm `get_recommended_hyperparameters()` đề xuất:  
- `tabu_tenure ≈ 1.5 * sqrt(n)`;  
- `max_iterations ∈ {300, 500, 800}` theo n;  
- `diversification_threshold ≈ 0.15 * max_iterations`;  
- `adaptive_tabu_tenure = (n > 50)`;  
- `aspiration_plus = True`;  
- `neighborhood_size_limit = None/500/800` theo n;  
- `time_limit = 60(s)`.

### 4.3. Cách chỉnh theo mục tiêu

| Mục tiêu | Điều chỉnh |
|---|---|
| Tăng chất lượng | Tăng `max_iterations`/`time_limit`, bật `adaptive_tabu_tenure`, nới `neighborhood_size_limit` |
| Tăng tốc | Giảm `max_iterations`, đặt `neighborhood_size_limit` nhỏ, giảm `tabu_tenure` |
| Khám phá rộng | Tăng `tabu_tenure`, tăng `diversification_threshold` |
| Khai thác sâu | Giảm `tabu_tenure`, giảm `diversification_threshold` |

---

