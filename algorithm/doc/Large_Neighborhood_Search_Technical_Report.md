# BÁO CÁO KỸ THUẬT: THUẬT TOÁN LARGE NEIGHBORHOOD SEARCH CHO VRPTW

**Thuật toán**: Large Neighborhood Search (LNS) — Destroy & Repair Metaheuristic  
**Bài toán**: Vehicle Routing Problem with Time Windows (VRPTW)  
**File triển khai**: `lns_vrptw_solver.py`

---

## 1. KIẾN TRÚC VÀ THÀNH PHẦN

### 1.1. Kiến trúc tổng quát

Class `LargeNeighborhoodSearchVRPTWSolver` gồm **4 pha**:

**Phase 1 – Initialization**  
- Nạp CSV, tách **depot**/**customers**, tính **ma trận khoảng cách** Euclid và **ma trận thời gian** (vận tốc = 1).  
- Khởi tạo biến theo dõi `solution`, `best_objective`.

**Phase 2 – Initial Solution (Nearest Neighbor)**  
- Xây nghiệm khởi tạo bằng **Nearest Neighbor** có kiểm tra **capacity** và **time window** → đảm bảo **feasible** ngay từ đầu.

**Phase 3 – LNS Optimization (Destroy & Repair + Local Search)**  
- Lặp `max_iterations` (và/hoặc `time_limit`). Mỗi vòng:  
  1) **Destroy**: loại bỏ một **tập khách hàng lớn** khỏi nghiệm hiện tại bằng 1 trong 4 toán tử.  
  2) **Repair**: chèn lại các khách hàng đã loại bằng **Greedy** hoặc **Regret‑k**.  
  3) **Local Search** (tuỳ chọn): **2‑opt** trong từng route để giảm quãng đường.  
  4) **Acceptance**: nhận nghiệm **tốt hơn hoặc bằng** nghiệm hiện tại (first‑accept / best‑accept đơn giản).  
  5) Ghi log cải thiện, thống kê toán tử.

**Phase 4 – Output & Visualization**  
- Chuẩn hoá `self.solution` (route, distance, load, num_customers), in báo cáo tổng hợp, trực quan hoá **routes**, **thống kê xe**, **phân bố khách hàng**; hỗ trợ lưu **PNG**/**TXT**.

### 1.2. Cấu trúc dữ liệu

**Input**
- `self.data`: DataFrame toàn bộ dataset (dòng 0 là depot).  
- `self.depot`: Series depot.  
- `self.customers`: DataFrame khách hàng (1…n).

**Matrices**
- `self.distance_matrix`: (n+1)×(n+1) Euclid.  
- `self.time_matrix`: sao chép từ distance (tốc độ = 1).

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

### 1.3. Phương thức chính

- `_calculate_distance_matrix()` — **O(n²)**.  
- `_check_time_window_feasibility(route)` — **O(k)**.  
- `_calculate_route_distance(route)` / `_calculate_route_load(route)` — **O(k)**.  
- `_create_initial_solution_nearest_neighbor()` — **O(n²)**.  
- **Destroy operators**: `_destroy_random_removal`, `_destroy_worst_removal`, `_destroy_shaw_removal`, `_destroy_route_removal`.  
- **Repair operators**: `_repair_greedy_insertion`, `_repair_regret_insertion(k=2)`.  
- `_apply_local_search_2opt(routes)` — **O(n²)** trong route.  
- `get_recommended_hyperparameters()`, `solve(...)`, `visualize_solution_comprehensive(save)`, `save_solution(...)`.

---

## 2. THUẬT TOÁN LNS (DESTROY & REPAIR)

### 2.1. Ý tưởng cốt lõi

LNS **phá hủy một phần lớn** nghiệm (destroy) rồi **tái tạo** (repair) bằng heuristic thông minh. Vùng lân cận “lớn” giúp **vượt local optimum**, còn repair bảo toàn **tính khả thi** (capacity + time windows). Cuối cùng, **2‑opt** tinh chỉnh trong từng route.

### 2.2. Destroy Operators

1) **Random Removal** — loại ngẫu nhiên một tập khách hàng → **diversification** mạnh.  
2) **Worst Removal** — loại khách có **chi phí biên** cao nhất (savings lớn khi loại) → **intensification**.  
3) **Shaw Removal** — loại nhóm khách **tương đồng** (gần về toạ độ/cửa sổ thời gian) để mở cơ hội tái sắp xếp cụm.  
4) **Route Removal** — xoá trọn **một số route** → tái phân phối tải/khách giữa các xe.

### 2.3. Repair Operators

- **Greedy Insertion** — chèn vào vị trí **tăng chi phí ít nhất**, kiểm tra **feasibility** mỗi chèn.  
- **Regret‑k Insertion** — ưu tiên khách có **regret** lớn (chênh giữa vị trí tốt nhất và k‑tốt) → chất lượng tốt hơn Greedy.

### 2.4. Local Search & Acceptance

- **2‑opt trong‑route** giảm quãng đường nhưng **giữ feasibility**.  
- **Acceptance**: nhận nghiệm **≤ current** (không tệ hơn) → hội tụ ổn; có thể mở rộng với threshold/annealing nếu cần.

### 2.5. Pseudo‑code

```text
x ← initial_solution_by_NN()
best ← x
while it < max_iterations and time < time_limit:
    R ← random_destroy_size()
    D ← random_destroy_operator()
    x_destroyed, removed ← D(x, R)

    I ← random_repair_operator()
    x_repaired ← I(x_destroyed, removed)

    if use_local_search:
        x_repaired ← two_opt_intraroute(x_repaired)

    if cost(x_repaired) ≤ cost(x):
        x ← x_repaired
        if cost(x) < cost(best):
            best ← x
return best
```

---

## 3. ĐỘ PHỨC TẠP & HIỆU NĂNG

### 3.1. Thời gian gần đúng

| Thành phần | Độ phức tạp | Ghi chú |
|---|---|---|
| Distance/Time matrix | O(n²) | Một lần |
| Initial NN | O(n²) | Khởi tạo khả thi |
| Destroy | O(R) – O(n) | tuỳ operator |
| Greedy/Regret‑k Insertion | O(R·m·log m) ~ O(n²) | m = vị trí chèn hợp lệ |
| 2‑opt (intra‑route) | O(n²) | Trên mỗi route đủ dài |
| Vòng lặp | O(max_iter × cost_step) | với `cost_step` ≈ O(n)–O(n²) |

Thực tế n≈100–200: **40–90s** (tuỳ tham số/phần cứng), chất lượng **Very Good–Excellent**.

### 3.2. Bộ nhớ

- Ma trận distance/time: **O(n²)**.  
- Nghiệm & bản sao trong destroy/repair: **O(n)**.

---

## 4. SIÊU THAM SỐ & TINH CHỈNH

### 4.1. Tham số chính (tự động gợi ý trong mã)

| Tham số | Vai trò | Gợi ý mặc định |
|---|---|---|
| `max_iterations` | Vòng lặp tối đa | 100 (n≤50), 150 (≤100), 200 (>100) |
| `destroy_size_min/max` | Tỉ lệ khách bị remove | ≈ 10–25% n (mặc định theo n) |
| `use_local_search` | Bật 2‑opt | **True** |
| `time_limit` | Giới hạn thời gian | 60s |

```python
hp = solver.get_recommended_hyperparameters()
# Trả về: {max_iterations, destroy_size_min/max, use_local_search, time_limit}
```

### 4.2. Điều chỉnh theo mục tiêu

| Mục tiêu | Điều chỉnh |
|---|---|
| Khám phá mạnh | Tăng `destroy_size_max`, ưu tiên Random/Route Removal |
| Khai thác sâu | Ưu tiên Worst/Shaw + bật 2‑opt |
| Chất lượng cao | Tăng `max_iterations`, `time_limit`, bật 2‑opt |
| Tăng tốc | Giảm `destroy_size_*`, tắt 2‑opt, giảm `max_iterations` |

---

