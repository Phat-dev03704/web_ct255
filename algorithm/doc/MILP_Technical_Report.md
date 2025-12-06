# BÁO CÁO KỸ THUẬT: THUẬT TOÁN MILP CHO VRPTW

**Thuật toán**: Mixed Integer Linear Programming (MILP)  
**Bài toán**: Vehicle Routing Problem with Time Windows  
**File triển khai**: `milp_vrptw_solver.py`

---

## 1. KIẾN TRÚC VÀ THÀNH PHẦN

### 1.1. Kiến trúc tổng quát

Class `MILPVRPTWSolver` được tổ chức theo 5 giai đoạn xử lý tuần tự:

**Phase 1 - Initialization**: Đọc dữ liệu từ CSV, phân tách depot và customers, giới hạn số khách hàng theo `max_customers`, tính ma trận khoảng cách Euclidean và ma trận thời gian di chuyển.

**Phase 2 - Model Building**: Định nghĩa biến quyết định (x[i,j,k], t[i]), xây dựng hàm mục tiêu minimize tổng quãng đường, thêm 6 nhóm ràng buộc.

**Phase 3 - Optimization**: Sử dụng CBC solver với thuật toán Branch and Bound, áp dụng time limit và gap tolerance, trả về trạng thái Optimal/Feasible/Timeout.

**Phase 4 - Solution Extraction**: Parse giá trị biến x[i,j,k] để tái tạo routes cho từng xe, tính metrics (distance, load), fallback sang Nearest Neighbor nếu không tìm được solution.

**Phase 5 - Output**: Visualization với 3-subplot comprehensive plots và text report với báo cáo chi tiết.

### 1.2. Cấu trúc dữ liệu

**Input structures**:
- `self.data`: DataFrame chứa toàn bộ dataset
- `self.depot`: Series chứa thông tin depot
- `self.customers`: DataFrame chứa thông tin khách hàng (đã giới hạn)
- `self.n_customers`: Số khách hàng thực tế xử lý

**Computational structures**:
- `self.distance_matrix`: Ma trận khoảng cách kích thước (n+1) x (n+1)
- `self.time_matrix`: Ma trận thời gian di chuyển (n+1) x (n+1)

**Optimization model**:
- `self.model`: PuLP LpProblem object
- `self.x`: Dictionary chứa biến nhị phân x[i,j,k]
- `self.t`: Dictionary chứa biến liên tục t[i] (thời gian)

**Output structure**:
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

**`__init__(dataset_path, vehicle_capacity, max_vehicles, max_customers)`**  
Khởi tạo solver, đọc dữ liệu, giới hạn số khách hàng. Độ phức tạp: O(1).

**`_calculate_distance_matrix()`**  
Tính ma trận khoảng cách Euclidean giữa tất cả các cặp node. Độ phức tạp: O(n²).

**`build_model()`**  
Xây dựng mô hình MILP đầy đủ với biến và ràng buộc. Độ phức tạp: O(n² × m) trong đó n là số khách hàng, m là số xe.

**`solve(time_limit)`**  
Giải bài toán bằng CBC solver với Branch and Bound. Độ phức tạp worst-case: O(2^(n² × m)).

**`_extract_solution()`**  
Trích xuất routes từ giá trị biến x[i,j,k]. Độ phức tạp: O(n × m).

**`_calculate_route_distance(route)`**  
Tính tổng quãng đường của một route. Độ phức tạp: O(n).

**`_create_fallback_solution()`**  
Tạo solution bằng thuật toán Nearest Neighbor khi MILP thất bại. Độ phức tạp: O(n²).

### 1.4. Mô hình toán học

**Ký hiệu**:
- V = {0, 1, ..., n}: Tập các node (0 là depot)
- C = {1, 2, ..., n}: Tập khách hàng
- K = {1, 2, ..., m}: Tập các xe
- d_ij: Khoảng cách từ node i đến node j
- q_i: Nhu cầu của khách hàng i
- [e_i, l_i]: Time window của khách hàng i
- s_i: Thời gian phục vụ tại khách hàng i
- Q: Sức chứa xe

**Biến quyết định**:
- x_ijk ∈ {0,1}: Bằng 1 nếu xe k đi từ i đến j
- T_i ∈ R: Thời gian bắt đầu phục vụ tại node i

**Hàm mục tiêu**:
```
Minimize: Z = Σ(i∈V) Σ(j∈V, i≠j) Σ(k∈K) d_ij · x_ijk
```

**Ràng buộc**:

1. Mỗi khách hàng được phục vụ đúng 1 lần:
   ```
   Σ(i∈V, i≠j) Σ(k∈K) x_ijk = 1,  ∀j ∈ C
   ```

2. Bảo toàn luồng (xe vào phải ra):
   ```
   Σ(i∈V, i≠j) x_ijk = Σ(i∈V, i≠j) x_jik,  ∀j ∈ C, ∀k ∈ K
   ```

3. Xe xuất phát từ depot tối đa 1 lần:
   ```
   Σ(j∈C) x_0jk ≤ 1,  ∀k ∈ K
   ```

4. Xe quay về depot tối đa 1 lần:
   ```
   Σ(i∈C) x_i0k ≤ 1,  ∀k ∈ K
   ```

5. Ràng buộc sức chứa xe:
   ```
   Σ(i∈V) Σ(j∈C, i≠j) q_j · x_ijk ≤ Q,  ∀k ∈ K
   ```

6. Ràng buộc cửa sổ thời gian:
   ```
   T_j ≥ T_i + s_i + t_ij - M(1 - x_ijk),  ∀i,j ∈ V, i≠j, ∀k ∈ K
   e_i ≤ T_i ≤ l_i,  ∀i ∈ C
   ```
   (M = 10000 là hằng số Big-M)

**Kích thước model**:
- Số biến nhị phân: (n+1)² × m ≈ n² × m
- Số biến liên tục: n
- Số ràng buộc: O(n² × m)

Ví dụ với n=25, m=10: 6,785 biến và 6,805 ràng buộc.

---

## 2. ĐỘ PHỨC TẠP THUẬT TOÁN

### 2.1. Phân loại bài toán

VRPTW thuộc lớp NP-Hard vì đây là tổng quát của bài toán TSP (Traveling Salesman Problem). Không tồn tại thuật toán polynomial-time để tìm nghiệm tối ưu. Thời gian giải tăng exponentially theo kích thước bài toán.

### 2.2. Độ phức tạp tổng thể

**Time Complexity**: O(2^(n² × m)) trong trường hợp worst-case, trong đó n là số khách hàng, m là số xe.

**Space Complexity**: O(n² × m) để lưu trữ biến và ràng buộc.

### 2.3. Độ phức tạp từng giai đoạn

| Giai đoạn | Độ phức tạp | Giải thích |
|-----------|-------------|------------|
| Initialization | O(n²) | Tính distance matrix |
| Model Building | O(n² × m) | Tạo biến và ràng buộc |
| Optimization | O(2^(n² × m)) | Branch and Bound worst-case |
| Solution Extraction | O(n × m) | Parse biến x[i,j,k] |
| Visualization | O(n) | Vẽ biểu đồ |

Giai đoạn Optimization chiếm phần lớn thời gian tính toán.

### 2.4. Giải thích độ phức tạp exponential

Thuật toán Branch and Bound (CBC solver) tạo cây tìm kiếm với mỗi node là một partial solution. Mỗi biến nhị phân có 2 lựa chọn (0 hoặc 1), dẫn đến worst-case phải duyệt 2^(n² × m) nodes. Trong thực tế, kỹ thuật pruning và cutting planes làm giảm số nodes cần duyệt, nhưng vẫn exponential với bài toán lớn.

### 2.5. Phân tích thực nghiệm

Dữ liệu thực nghiệm trên Solomon datasets:

| Số khách hàng | Số biến | Số ràng buộc | Thời gian | Trạng thái |
|---------------|---------|--------------|-----------|------------|
| 5 | ~500 | ~500 | < 1s | Optimal |
| 10 | ~2,100 | ~2,100 | 1-5s | Optimal |
| 15 | ~4,650 | ~4,650 | 5-30s | Optimal/Feasible |
| 20 | ~8,200 | ~8,200 | 30-120s | Feasible |
| 25 | ~12,750 | ~12,750 | 60-300s | Feasible/Timeout |
| 30 | ~18,300 | ~18,300 | > 300s | Timeout |

Kết luận: MILP chỉ practical cho n ≤ 25 khách hàng.

---

## 3. SIÊU THAM SỐ VÀ TINH CHỈNH

### 3.1. Danh sách siêu tham số

MILP có 4 siêu tham số chính có thể tinh chỉnh:

| Tham số | Loại | Phạm vi giá trị | Mặc định |
|---------|------|-----------------|----------|
| max_customers | Problem size | 10-30 | 25 |
| time_limit | Solver | 30-600s | 60s |
| max_vehicles | Problem constraint | 5-25 | 25 |
| gap_rel | Solver | 0.0-0.2 | 0.1 |

### 3.2. Chi tiết từng siêu tham số

#### 3.2.1. max_customers

**Định nghĩa**: Giới hạn số khách hàng được giải bởi MILP. Nếu dataset có nhiều hơn, chỉ lấy max_customers đầu tiên.

**Vai trò**: Quyết định khả năng giải được bài toán, giới hạn kích thước problem space, trade-off giữa accuracy và tractability.

**Ảnh hưởng**: Số biến tăng theo n², thời gian tăng exponential. Ví dụ: n=10 có ~2,100 biến (1-5s), n=20 có ~8,200 biến (30-120s), n=25 có ~12,750 biến (60-300s).

**Khuyến nghị**: Development/Testing (10-15), Production (20-25), Maximum practical (25).

**Cách tinh chỉnh**:
```python
if available_time < 60:
    max_customers = 15
elif available_time < 300:
    max_customers = 20
else:
    max_customers = 25
```

#### 3.2.2. time_limit

**Định nghĩa**: Thời gian tối đa (giây) cho CBC solver. Solver sẽ dừng khi hết thời gian.

**Vai trò**: Ngăn solver chạy vô hạn, trade-off giữa solution quality và computation time, cho phép chấp nhận suboptimal solutions.

**Ảnh hưởng**: Quá ngắn có thể không tìm được feasible solution, quá dài lãng phí thời gian nếu problem không tractable.

**Trạng thái có thể**: Optimal (nghiệm tối ưu chứng minh được), Feasible (nghiệm khả thi chưa chứng minh tối ưu), Infeasible (không tồn tại nghiệm), Timeout (hết thời gian chưa có solution).

**Khuyến nghị**: Minimum (30s), Balanced (60-120s), Maximum (600s).

**Cách tinh chỉnh**:
```python
def get_time_limit(n_customers):
    if n_customers <= 10:
        return 30
    elif n_customers <= 15:
        return 60
    elif n_customers <= 20:
        return 120
    elif n_customers <= 25:
        return 300
    else:
        return 600
```

#### 3.2.3. max_vehicles

**Định nghĩa**: Số xe tối đa có thể sử dụng, giới hạn trên cho số routes.

**Vai trò**: Ảnh hưởng đến số biến O(n² × m). Quá nhỏ có thể không tìm được feasible solution, quá lớn tạo nhiều biến thừa và tăng complexity.

**Ảnh hưởng**: m=5 tạo n²×5 biến, m=10 tạo n²×10 biến, m=20 tạo n²×20 biến.

**Cách tính hợp lý**:
```python
total_demand = sum(customer['DEMAND'])
min_vehicles = ceil(total_demand / vehicle_capacity)
max_vehicles = min(min_vehicles + 5, 25)
```

#### 3.2.4. gap_rel

**Định nghĩa**: Relative MIP gap - độ chênh lệch tương đối giữa upper bound và lower bound, được tính theo công thức: gap = (upper_bound - lower_bound) / upper_bound.

**Vai trò**: Cho phép solver dừng sớm khi solution "đủ tốt".

**Ý nghĩa**: gap_rel=0.0 chỉ chấp nhận optimal solution, gap_rel=0.05 chấp nhận solution trong vòng 5% của optimal, gap_rel=0.1 chấp nhận 10%, gap_rel=0.2 chấp nhận 20%.

**Ảnh hưởng**: Gap tăng thì solver dừng sớm hơn (nhanh hơn nhưng chất lượng kém hơn), gap giảm thì solver chạy lâu hơn (chậm hơn nhưng chất lượng tốt hơn).

**Khuyến nghị theo mục đích**:
- Academic research (cần optimal proven): gap_rel = 0.0
- Industry (near-optimal chấp nhận được): gap_rel = 0.05
- Testing (10% acceptable): gap_rel = 0.1
- Large instance (20% acceptable): gap_rel = 0.2

### 3.3. Chiến lược tinh chỉnh

#### 3.3.1. Rule-based tuning

```python
def get_recommended_hyperparameters(dataset):
    n = len(dataset.customers)
    total_demand = dataset.customers['DEMAND'].sum()
    
    # Xác định max_customers
    if n <= 15:
        max_customers = n
    elif n <= 25:
        max_customers = 25
    else:
        max_customers = 25
    
    # Điều chỉnh time_limit
    if max_customers <= 10:
        time_limit = 30
    elif max_customers <= 15:
        time_limit = 60
    elif max_customers <= 20:
        time_limit = 120
    else:
        time_limit = 300
    
    # Tính max_vehicles
    min_vehicles = ceil(total_demand / dataset.vehicle_capacity)
    max_vehicles = min(min_vehicles + 5, 25)
    
    # Gap tolerance
    gap_rel = 0.1
    
    return {
        'max_customers': max_customers,
        'time_limit': time_limit,
        'max_vehicles': max_vehicles,
        'gap_rel': gap_rel
    }
```

#### 3.3.2. Adaptive tuning

```python
def adaptive_tuning(available_time):
    if available_time < 60:
        return {'max_customers': 15, 'time_limit': 30, 'gap_rel': 0.2}
    elif available_time < 300:
        return {'max_customers': 20, 'time_limit': 120, 'gap_rel': 0.1}
    else:
        return {'max_customers': 25, 'time_limit': 300, 'gap_rel': 0.05}
```

---

**End of Report**
