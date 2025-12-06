# BÁO CÁO KỸ THUẬT: THUẬT TOÁN SIMULATED ANNEALING CHO VRPTW

**Thuật toán**: Simulated Annealing (SA) — Metaheuristic dựa trên nhiệt độ  
**Bài toán**: Vehicle Routing Problem with Time Windows (VRPTW)  
**File triển khai**: `sa_vrptw_solver.py`

---

## 1. KIẾN TRÚC VÀ THÀNH PHẦN

### 1.1. Kiến trúc tổng quát

Class `SimulatedAnnealingVRPTWSolver` tổ chức theo 4 giai đoạn tuần tự:

**Phase 1 – Initialization**: Đọc CSV, tách depot/khách hàng, tính **ma trận khoảng cách** Euclid và **ma trận thời gian** (giả định vận tốc = 1), khởi tạo bộ nhớ nghiệm và biến theo dõi tiến trình.

**Phase 2 – Initial Solution (Nearest Neighbor)**: Xây nghiệm khởi tạo bằng **Nearest Neighbor** với kiểm tra **capacity** và **time window** để đảm bảo **feasible** ngay từ đầu.

**Phase 3 – Simulated Annealing Optimization**: Lặp theo lịch làm nguội (**cooling schedule**). Ở mỗi mức nhiệt độ, sinh **neighbor** ngẫu nhiên (Relocate, Exchange, 2‑opt), tính **chi phí** và quyết định **chấp nhận** theo xác suất phụ thuộc nhiệt độ.

**Phase 4 – Output & Visualization**: Biên dịch `self.solution` ở dạng {route_id → (route, distance, load, num_customers)}, in thống kê, trực quan hóa routes và biểu đồ phụ trợ; tùy chọn lưu **PNG** và **TXT**.

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
- `_create_initial_solution_nearest_neighbor()`: Sinh nghiệm khởi tạo **O(n²)**.  
- `_get_neighbor_*()`: Sinh láng giềng Relocate / Exchange / 2‑opt.  
- `_acceptance_probability(...)`: \( \exp(-(Δ)/T) \).  
- `get_recommended_hyperparameters()`: Khuyến nghị siêu tham số từ kích thước bài toán.  
- `solve(...)`: Vòng lặp SA với lịch nhiệt.  
- `visualize_solution_comprehensive(save)`, `save_solution(...)`: Vẽ & lưu báo cáo.

---

## 2. THUẬT TOÁN SIMULATED ANNEALING

### 2.1. Ý tưởng cốt lõi

SA mô phỏng quá trình luyện kim: khi **nhiệt độ cao**, thuật toán **dễ chấp nhận nghiệm tệ hơn** để **thoát local optimum**; khi **nhiệt độ hạ**, thuật toán **khắt khe hơn**, dần hội tụ về vùng nghiệm tốt.

### 2.2. Khung thuật toán

1) Tạo nghiệm khả thi ban đầu bằng Nearest Neighbor → `current`, `best = current`.  
2) Với nhiệt độ `T` từ **`initial_temperature`** đến **`final_temperature`**:  
   - Lặp `max_iterations_per_temp` lần:  
     a. Sinh **neighbor** ngẫu nhiên bởi một trong các operator: **Relocate**, **Exchange**, **2‑opt**.  
     b. Bỏ qua neighbor **không feasible** (capacity/time window).  
     c. Tính Δ = `neighbor_cost - current_cost`;  
        • Nếu Δ < 0 → **nhận** ngay;  
        • Nếu Δ ≥ 0 → **nhận** với xác suất \( p = \exp(-Δ/T) \).  
     d. Cập nhật `best` nếu `current` cải thiện.  
   - **Làm nguội**: `T ← T × cooling_rate`.
3) Trả về `best` và báo cáo.

### 2.3. Neighborhood & Feasibility

- **Relocate**: di chuyển 1 khách giữa hai route, thử vị trí chèn ngẫu nhiên.  
- **Exchange**: hoán đổi 1–1 khách giữa hai route.  
- **2‑opt**: đảo ngược một đoạn con trong cùng route.  

**Ràng buộc**:  
- **Capacity**: tổng DEMAND trong route ≤ `vehicle_capacity`.  
- **Time Windows**: tính thời gian đến, đợi nếu sớm (ready time), không vượt **due date**, về depot đúng hạn.

### 2.4. Acceptance Probability

\[
p(\text{accept}) =
\begin{cases}
1, & \text{nếu } \Delta < 0 \\
\exp(-\Delta/T), & \text{nếu } \Delta \ge 0
\end{cases}
\]

- `Δ` càng lớn hoặc `T` càng nhỏ → xác suất chấp nhận càng thấp.  
- Quy tắc này cân bằng **exploration** (nhiệt cao) và **exploitation** (nhiệt thấp).

---

## 3. ĐỘ PHỨC TẠP THUẬT TOÁN

### 3.1. Tổng thể

- **Time** ≈ \( \sum_{\text{nhiệt độ}} \text{max\_iterations\_per\_temp} \times \text{cost(neighbor)} \).  
- **Space**:  
  - Ma trận distance/time: **O(n²)**.  
  - Bộ nhớ solution & biến theo dõi: **O(n)**.

### 3.2. Thành phần chính

| Thành phần | Độ phức tạp | Ghi chú |
|---|---|---|
| Tính ma trận | O(n²) | Euclid giữa mọi cặp |
| Khởi tạo NN | O(n²) | Thêm khách gần nhất khả thi |
| Sinh neighbor | O(1) mỗi lần | Chọn operator + các kiểm tra |
| Đánh giá cost | O(k) | Khoảng cách một route / tổng distance |
| Vòng SA | O(L·M·k) | L mức nhiệt × M vòng/mức × k trung bình |

Trong thực tế, với n≈100–200, SA đạt chất lượng **Very Good** trong **~1 phút** tùy tham số.

---

## 4. SIÊU THAM SỐ VÀ TINH CHỈNH

### 4.1. Danh sách siêu tham số

| Tham số | Vai trò | Gợi ý từ mã |
|---|---|---|
| `initial_temperature` | Nhiệt ban đầu | ≈ 10× khoảng cách TB |
| `final_temperature` | Nhiệt cuối | 0.1–1% của initial |
| `cooling_rate` | Tốc độ làm nguội | 0.95–0.99 (n lớn → gần 0.99) |
| `max_iterations_per_temp` | Iterations mỗi mức nhiệt | 100 / 150 / 200 theo n |
| `time_limit` | Giới hạn thời gian | 60s (tùy chỉnh) |

**Khuyến nghị tự động** (`get_recommended_hyperparameters()`):
- Ước lượng `initial_temperature` từ **khoảng cách TB** của ma trận.  
- `final_temperature = initial × 0.001`.  
- `cooling_rate`: 0.97 (n≤50), 0.98 (n≤100), 0.99 (n>100).  
- `max_iterations_per_temp`: 100 / 150 / 200.

### 4.2. Cách chỉnh theo mục tiêu

| Mục tiêu | Điều chỉnh |
|---|---|
| Tăng chất lượng | Tăng `initial_temperature`, giảm `cooling_rate` (làm nguội chậm), tăng `max_iterations_per_temp`, tăng `time_limit` |
| Tăng tốc | Giảm `initial_temperature`, tăng `cooling_rate` (làm nguội nhanh), giảm `max_iterations_per_temp` |
| Khám phá rộng | `initial_temperature` cao hơn, `cooling_rate` gần 1, lặp nhiều ở nhiệt cao |
| Khai thác sâu | `final_temperature` thấp hơn, `cooling_rate` nhỏ hơn (nguội nhanh), giảm số neighbor chấp nhận |

---

