# Vehicle Routing Problem with Time Windows

## Technical Reports Collection

**Generated on:** Thu 10/16/2025

---

\newpage

# Table of Contents

1. [Ant Colony Optimization Technical Report](#Ant_Colony_Optimization_Technical_Report)
2. [Clarke Wright Technical Report](#Clarke_Wright_Technical_Report)
3. [Combined Technical Reports](#Combined_Technical_Reports)
4. [CP Technical Report](#CP_Technical_Report)
5. [Genetic Algorithm Technical Report](#Genetic_Algorithm_Technical_Report)
6. [Large Neighborhood Search Technical Report](#Large_Neighborhood_Search_Technical_Report)
7. [MILP Technical Report](#MILP_Technical_Report)
8. [Simulated Annealing Technical Report](#Simulated_Annealing_Technical_Report)
9. [Sweep Technical Report](#Sweep_Technical_Report)
10. [Tabu Search Technical Report](#Tabu_Search_Technical_Report)

---

\newpage

<a id="Ant_Colony_Optimization_Technical_Report"></a>

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



---

\newpage

<a id="Clarke_Wright_Technical_Report"></a>

# BÁO CÁO KỸ THUẬT: THUẬT TOÁN CLARKE-WRIGHT CHO VRPTW

**Thuật toán**: Clarke-Wright Savings Algorithm  
**Bài toán**: Vehicle Routing Problem with Time Windows  
**File triển khai**: `cw_vrptw_solver.py`

---

## 1. KIẾN TRÚC VÀ THÀNH PHẦN

### 1.1. Kiến trúc tổng quát

Class `ClarkeWrightVRPTWSolver` được tổ chức theo 4 giai đoạn xử lý tuần tự:

**Phase 1 - Initialization**: Đọc dữ liệu từ CSV, phân tách depot và customers, tính ma trận khoảng cách Euclidean và ma trận thời gian. Không giới hạn số khách hàng.

**Phase 2 - Savings Calculation**: Tính savings cho mọi cặp khách hàng (i,j) theo công thức: Savings(i,j) = d(0,i) + d(0,j) - d(i,j). Sắp xếp savings theo thứ tự giảm dần.

**Phase 3 - Route Construction**: Khởi tạo mỗi khách hàng là một route riêng, sau đó merge routes theo thứ tự savings từ cao xuống thấp với kiểm tra capacity và time window constraints.

**Phase 4 - Output**: Chuyển đổi routes sang format solution, visualization với 3-subplot comprehensive plots và text report chi tiết.

### 1.2. Cấu trúc dữ liệu

**Input structures**:
- `self.data`: DataFrame chứa toàn bộ dataset
- `self.depot`: Series chứa thông tin depot
- `self.customers`: DataFrame chứa thông tin khách hàng
- `self.n_customers`: Số khách hàng thực tế

**Computational structures**:
- `self.distance_matrix`: Ma trận khoảng cách (n+1) x (n+1)
- `self.time_matrix`: Ma trận thời gian di chuyển (n+1) x (n+1)

**Savings structure**:
```python
self.savings = [
    {
        'customer_i': int,
        'customer_j': int,
        'saving': float
    }
]
```
Được sắp xếp giảm dần theo saving value.

**Route tracking structures**:
- `routes`: Dictionary mapping route_id → list of customers
- `customer_to_route`: Dictionary mapping customer_id → route_id

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

**`__init__(dataset_path, vehicle_capacity, max_vehicles)`**  
Khởi tạo solver, đọc dữ liệu, xử lý toàn bộ khách hàng. Độ phức tạp: O(1).

**`_calculate_distance_matrix()`**  
Tính ma trận khoảng cách Euclidean giữa tất cả các cặp node. Độ phức tạp: O(n²).

**`_calculate_savings()`**  
Tính savings cho mọi cặp khách hàng và sắp xếp giảm dần. Độ phức tạp: O(n² log n) do sorting.

**`_check_time_window_feasibility(route)`**  
Kiểm tra route có thỏa mãn time window constraints không. Độ phức tạp: O(k) với k là số khách hàng trong route.

**`_calculate_route_distance(route)`**  
Tính tổng quãng đường của một route. Độ phức tạp: O(k).

**`_calculate_route_load(route)`**  
Tính tổng tải trọng của một route. Độ phức tạp: O(k).

**`solve()`**  
Giải bài toán bằng Clarke-Wright algorithm: tính savings, khởi tạo routes, merge routes theo savings. Độ phức tạp: O(n²).

### 1.4. Thuật toán Clarke-Wright

#### 1.4.1. Ý tưởng cơ bản

Clarke-Wright dựa trên khái niệm "savings" - lượng quãng đường tiết kiệm được khi gộp hai routes.

**Scenario ban đầu**: Mỗi khách hàng có một route riêng
```
Route i: 0 → i → 0  (distance = d(0,i) + d(i,0))
Route j: 0 → j → 0  (distance = d(0,j) + d(j,0))
Total: d(0,i) + d(i,0) + d(0,j) + d(j,0)
```

**Sau khi merge**: Gộp thành một route
```
Route merged: 0 → i → j → 0  (distance = d(0,i) + d(i,j) + d(j,0))
```

**Savings**:
```
Savings(i,j) = [d(0,i) + d(i,0) + d(0,j) + d(j,0)] - [d(0,i) + d(i,j) + d(j,0)]
             = d(i,0) + d(0,j) - d(i,j)
             = d(0,i) + d(0,j) - d(i,j)  (vì d(i,0) = d(0,i))
```

Savings càng lớn, việc gộp routes càng có lợi.

#### 1.4.2. Các bước thuật toán

**Bước 1**: Tính savings cho mọi cặp khách hàng (i,j) với i < j
```
Savings(i,j) = d(0,i) + d(0,j) - d(i,j)
```
Sắp xếp savings theo thứ tự giảm dần.

**Bước 2**: Khởi tạo solution
- Mỗi khách hàng i tạo một route: 0 → i → 0
- Tổng cộng n routes ban đầu

**Bước 3**: Merge routes
- Duyệt qua các savings từ cao xuống thấp
- Với mỗi savings(i,j):
  * Kiểm tra i và j có thuộc hai routes khác nhau không
  * Kiểm tra i hoặc j có phải là đầu/cuối route không
  * Kiểm tra capacity constraint của route mới
  * Kiểm tra time window feasibility của route mới
  * Nếu thỏa mãn tất cả: merge hai routes

**Bước 4**: Trả về solution với các routes đã merge

#### 1.4.3. Merge conditions

Hai routes chỉ được merge nếu thỏa mãn 4 điều kiện:

**1. Different routes**: i và j phải thuộc hai routes khác nhau

**2. Position constraint**: i và j phải ở vị trí có thể merge
- Case 1: i ở cuối route_i, j ở đầu route_j → route_i + route_j
- Case 2: j ở cuối route_j, i ở đầu route_i → route_j + route_i
- Case 3: i ở đầu route_i, j ở cuối route_j → route_j + route_i
- Case 4: j ở đầu route_j, i ở cuối route_i → route_i + route_j

**3. Capacity constraint**:
```
Total_load(new_route) ≤ vehicle_capacity
```

**4. Time window feasibility**:
```
For each customer k in new_route:
    arrival_time = current_time + travel_time
    start_service = max(arrival_time, ready_time[k])
    start_service ≤ due_date[k]
```

#### 1.4.4. Ví dụ minh họa

Giả sử có 3 khách hàng với depot tại (0,0):
- Customer 1: (10, 0)
- Customer 2: (20, 0)
- Customer 3: (0, 10)

Khoảng cách:
- d(0,1) = 10, d(0,2) = 20, d(0,3) = 10
- d(1,2) = 10, d(1,3) = 14.14, d(2,3) = 22.36

Savings:
- Savings(1,2) = 10 + 20 - 10 = 20
- Savings(1,3) = 10 + 10 - 14.14 = 5.86
- Savings(2,3) = 20 + 10 - 22.36 = 7.64

Sắp xếp: Savings(1,2) = 20 > Savings(2,3) = 7.64 > Savings(1,3) = 5.86

Merge routes theo thứ tự:
1. Merge route 1 và route 2 (savings = 20)
2. Kiểm tra merge route 2 và route 3 (savings = 7.64)
3. Kiểm tra merge route 1 và route 3 (savings = 5.86)

---

## 2. ĐỘ PHỨC TẠP THUẬT TOÁN

### 2.1. Phân loại bài toán

VRPTW thuộc lớp NP-Hard. Clarke-Wright là thuật toán heuristic constructive - xây dựng solution từng bước và không đảm bảo optimal. Độ phức tạp polynomial, phù hợp cho bài toán lớn.

### 2.2. Độ phức tạp tổng thể

**Time Complexity**: O(n² log n)

**Space Complexity**: O(n²) để lưu savings và distance matrix.

### 2.3. Độ phức tạp từng giai đoạn

| Giai đoạn | Độ phức tạp | Giải thích |
|-----------|-------------|------------|
| Initialization | O(n²) | Tính distance matrix |
| Calculate Savings | O(n²) | Tính n(n-1)/2 savings |
| Sort Savings | O(n² log n) | Sắp xếp ~n²/2 savings |
| Initialize Routes | O(n) | Tạo n routes ban đầu |
| Merge Routes | O(n²) | Duyệt savings và merge |
| Output | O(n) | Format solution |

**Tổng thể**: O(n² log n) do giai đoạn Sort Savings chiếm dominant.

### 2.4. Phân tích chi tiết merge phase

**Merge Routes** có độ phức tạp O(n²):
- Số savings cần xét: n(n-1)/2 ≈ n²/2
- Với mỗi saving:
  * Check different routes: O(1)
  * Check position: O(1) 
  * Calculate load: O(k) với k = route length
  * Check time windows: O(k)
  * Merge operation: O(1)

Worst-case: k có thể đến n, nhưng trong thực tế k << n.

Tổng độ phức tạp: O(n² × k) ≈ O(n²) trong thực tế.

### 2.5. Phân tích thực nghiệm

Dữ liệu thực nghiệm trên Solomon datasets:

| Số khách hàng | Số savings | Thời gian | Chất lượng | Số xe |
|---------------|------------|-----------|------------|-------|
| 25 | 300 | < 1s | Very Good | 3-5 |
| 50 | 1,225 | 1-2s | Very Good | 5-8 |
| 100 | 4,950 | 2-5s | Good | 10-15 |
| 200 | 19,900 | 10-20s | Good | 18-25 |
| 400 | 79,800 | 40-80s | Fair | 35-45 |

Kết luận: Clarke-Wright rất nhanh và scalable, có thể xử lý 400+ khách hàng trong vòng 1 phút.

### 2.6. So sánh với các phương pháp khác

| Thuật toán | Độ phức tạp | Thời gian (n=100) | Chất lượng | Scalability |
|------------|-------------|-------------------|------------|-------------|
| MILP | O(2^(n²×m)) | 60-300s | Optimal | Kém (n≤25) |
| CP | O(n²×k) | 30-60s | Very Good | Tốt (n≤400) |
| Clarke-Wright | O(n² log n) | 2-5s | Good | Rất tốt (n≤1000) |

Clarke-Wright có thời gian chạy nhanh nhất nhưng chất lượng thấp hơn CP một chút.

### 2.7. Phân tích từng thành phần

**Calculate Distance Matrix: O(n²)**
```python
for i in range(n):
    for j in range(n):
        distance[i][j] = euclidean_distance(i, j)
```

**Calculate Savings: O(n²)**
```python
for i in range(1, n+1):
    for j in range(i+1, n+1):
        savings.append({
            'customer_i': i,
            'customer_j': j,
            'saving': d[0][i] + d[0][j] - d[i][j]
        })
```
Tổng số savings: n(n-1)/2 ≈ n²/2

**Sort Savings: O(n² log n)**
```python
savings.sort(key=lambda x: x['saving'], reverse=True)
```
Sắp xếp n²/2 phần tử.

**Merge Loop: O(n²)**
```python
for saving_item in savings:  # n² iterations
    # Check và merge: O(k) với k << n
    if can_merge:
        merge_routes()  # O(1)
```

---

## 3. SIÊU THAM SỐ VÀ TINH CHỈNH

### 3.1. Danh sách siêu tham số

Clarke-Wright có 2 siêu tham số chính:

| Tham số | Loại | Phạm vi giá trị | Mặc định |
|---------|------|-----------------|----------|
| vehicle_capacity | Problem constraint | 50-500 | 200 |
| max_vehicles | Problem constraint | 5-50 | 25 |

**Lưu ý**: Clarke-Wright là thuật toán deterministic không có siêu tham số điều chỉnh hành vi thuật toán. Kết quả chỉ phụ thuộc vào dữ liệu đầu vào.

### 3.2. Chi tiết từng siêu tham số

#### 3.2.1. vehicle_capacity

**Định nghĩa**: Sức chứa tối đa của mỗi xe, giới hạn tổng demand có thể phục vụ trong một route.

**Vai trò**: Ràng buộc cứng quyết định khả năng merge routes. Capacity nhỏ hơn dẫn đến nhiều routes nhỏ, capacity lớn hơn cho phép routes dài hơn.

**Ảnh hưởng đến algorithm**:
- Capacity nhỏ → Nhiều routes ngắn → Ít merge → Nhiều xe
- Capacity lớn → Ít routes dài → Nhiều merge → Ít xe

**Ảnh hưởng đến solution quality**:
- Capacity quá nhỏ: Không đủ để merge routes hiệu quả, tổng quãng đường cao
- Capacity phù hợp: Cân bằng tốt giữa số xe và quãng đường
- Capacity quá lớn: Không ràng buộc, nhưng vẫn bị giới hạn bởi time windows

**Cách xác định capacity hợp lý**:
```python
total_demand = sum(customer['DEMAND'])
average_demand = total_demand / n_customers
desired_customers_per_route = 5-10

# Option 1: Dựa trên desired customers per route
vehicle_capacity = average_demand * desired_customers_per_route

# Option 2: Dựa trên desired number of vehicles
desired_vehicles = 10
vehicle_capacity = ceil(total_demand / desired_vehicles)

# Option 3: Dựa trên max demand + buffer
max_demand = max(customer['DEMAND'])
vehicle_capacity = max_demand * 10  # 10 customers buffer
```

#### 3.2.2. max_vehicles

**Định nghĩa**: Số xe tối đa có thể sử dụng. Giới hạn trên cho số routes trong solution.

**Vai trò**: Ràng buộc cứng về số lượng xe. Nếu không thể phục vụ tất cả khách hàng với max_vehicles, một số khách hàng sẽ không được phục vụ.

**Ảnh hưởng đến algorithm**:
- max_vehicles không ảnh hưởng trực tiếp đến quá trình merge
- Chỉ là check sau khi merge xong
- Trong triển khai hiện tại, thuật toán không enforce hard constraint này

**Ảnh hưởng đến feasibility**:
```python
min_vehicles_needed = ceil(total_demand / vehicle_capacity)

if max_vehicles < min_vehicles_needed:
    # Không thể phục vụ tất cả khách hàng
    # Cần tăng max_vehicles hoặc vehicle_capacity
```

**Cách xác định max_vehicles**:
```python
total_demand = sum(customer['DEMAND'])
min_vehicles = ceil(total_demand / vehicle_capacity)

# Thêm buffer 20-30%
max_vehicles = ceil(min_vehicles * 1.2)

# Hoặc cộng thêm số lượng cố định
max_vehicles = min_vehicles + 5
```

### 3.3. Các biến thể của Clarke-Wright

Mặc dù thuật toán chuẩn không có siêu tham số, có thể mở rộng với các biến thể:

#### 3.3.1. Parallel vs Sequential Clarke-Wright

**Sequential (triển khai hiện tại)**:
- Xây dựng tất cả routes đồng thời
- Merge bất kỳ hai routes nào
- Linh hoạt hơn

**Parallel**:
- Xây dựng từng route một cho đến khi đầy
- Chỉ thêm customer vào route hiện tại
- Ít linh hoạt hơn nhưng đơn giản

#### 3.3.2. Savings formula variants

**Classic savings (đang dùng)**:
```python
Savings(i,j) = d(0,i) + d(0,j) - d(i,j)
```

**Lambda-modified savings**:
```python
Savings(i,j) = d(0,i) + d(0,j) - lambda * d(i,j)
```
- lambda ∈ [0, 2]
- lambda = 1: classic savings
- lambda > 1: ưu tiên routes compact (customers gần nhau)
- lambda < 1: ưu tiên routes radial (xa depot)

**Shape parameter savings**:
```python
Savings(i,j) = d(0,i) + d(0,j) - d(i,j) + mu * |d(0,i) - d(0,j)|
```
- mu ∈ [-1, 1]
- Cân bằng giữa savings và shape của route

#### 3.3.3. Tie-breaking rules

Khi nhiều savings có giá trị bằng nhau:

**Rule 1: Farthest customer first**
```python
if saving1 == saving2:
    prefer customer farther from depot
```

**Rule 2: Largest demand first**
```python
if saving1 == saving2:
    prefer customer with larger demand
```

**Rule 3: Tightest time window first**
```python
if saving1 == saving2:
    prefer customer with tighter time window
```

### 3.4. Chiến lược cải thiện solution

Mặc dù Clarke-Wright không có siêu tham số tuning, có thể cải thiện solution bằng post-processing:

#### 3.4.1. 2-opt improvement

```python
def improve_with_2opt(solution):
    improved = True
    while improved:
        improved = False
        for route in solution.routes:
            for i in range(len(route) - 1):
                for j in range(i + 2, len(route)):
                    # Try reversing segment [i+1, j]
                    new_route = route[:i+1] + route[i+1:j+1][::-1] + route[j+1:]
                    if is_better_and_feasible(new_route, route):
                        route = new_route
                        improved = True
    return solution
```

#### 3.4.2. Or-opt improvement

```python
def improve_with_or_opt(solution):
    for route_i in solution.routes:
        for route_j in solution.routes:
            if route_i == route_j:
                continue
            # Try moving 1, 2, or 3 consecutive customers
            # from route_i to route_j
            for length in [1, 2, 3]:
                for pos_i in range(len(route_i) - length + 1):
                    segment = route_i[pos_i:pos_i+length]
                    for pos_j in range(len(route_j) + 1):
                        # Try inserting segment at pos_j
                        if is_better_and_feasible(...):
                            apply_move()
    return solution
```

#### 3.4.3. Route merging post-processing

```python
def merge_routes_post_processing(solution):
    improved = True
    while improved:
        improved = False
        for route_i in solution.routes:
            for route_j in solution.routes:
                if route_i == route_j:
                    continue
                # Try merging route_i and route_j
                merged = route_i + route_j
                if is_feasible(merged):
                    if total_distance(merged) < total_distance(route_i) + total_distance(route_j):
                        apply_merge()
                        improved = True
    return solution
```



---

\newpage

<a id="Combined_Technical_Reports"></a>

# Vehicle Routing Problem with Time Windows

## Technical Reports Collection

**Generated on:** Thu 10/16/2025

---

\newpage

# Table of Contents

1. [Ant Colony Optimization Technical Report](#Ant_Colony_Optimization_Technical_Report)
2. [Clarke Wright Technical Report](#Clarke_Wright_Technical_Report)
3. [Combined Technical Reports](#Combined_Technical_Reports)
4. [CP Technical Report](#CP_Technical_Report)
5. [Genetic Algorithm Technical Report](#Genetic_Algorithm_Technical_Report)
6. [Large Neighborhood Search Technical Report](#Large_Neighborhood_Search_Technical_Report)
7. [MILP Technical Report](#MILP_Technical_Report)
8. [Simulated Annealing Technical Report](#Simulated_Annealing_Technical_Report)
9. [Sweep Technical Report](#Sweep_Technical_Report)
10. [Tabu Search Technical Report](#Tabu_Search_Technical_Report)

---

\newpage

<a id="Ant_Colony_Optimization_Technical_Report"></a>

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



---

\newpage

<a id="Clarke_Wright_Technical_Report"></a>

# BÁO CÁO KỸ THUẬT: THUẬT TOÁN CLARKE-WRIGHT CHO VRPTW

**Thuật toán**: Clarke-Wright Savings Algorithm  
**Bài toán**: Vehicle Routing Problem with Time Windows  
**File triển khai**: `cw_vrptw_solver.py`

---

## 1. KIẾN TRÚC VÀ THÀNH PHẦN

### 1.1. Kiến trúc tổng quát

Class `ClarkeWrightVRPTWSolver` được tổ chức theo 4 giai đoạn xử lý tuần tự:

**Phase 1 - Initialization**: Đọc dữ liệu từ CSV, phân tách depot và customers, tính ma trận khoảng cách Euclidean và ma trận thời gian. Không giới hạn số khách hàng.

**Phase 2 - Savings Calculation**: Tính savings cho mọi cặp khách hàng (i,j) theo công thức: Savings(i,j) = d(0,i) + d(0,j) - d(i,j). Sắp xếp savings theo thứ tự giảm dần.

**Phase 3 - Route Construction**: Khởi tạo mỗi khách hàng là một route riêng, sau đó merge routes theo thứ tự savings từ cao xuống thấp với kiểm tra capacity và time window constraints.

**Phase 4 - Output**: Chuyển đổi routes sang format solution, visualization với 3-subplot comprehensive plots và text report chi tiết.

### 1.2. Cấu trúc dữ liệu

**Input structures**:
- `self.data`: DataFrame chứa toàn bộ dataset
- `self.depot`: Series chứa thông tin depot
- `self.customers`: DataFrame chứa thông tin khách hàng
- `self.n_customers`: Số khách hàng thực tế

**Computational structures**:
- `self.distance_matrix`: Ma trận khoảng cách (n+1) x (n+1)
- `self.time_matrix`: Ma trận thời gian di chuyển (n+1) x (n+1)

**Savings structure**:
```python
self.savings = [
    {
        'customer_i': int,
        'customer_j': int,
        'saving': float
    }
]
```
Được sắp xếp giảm dần theo saving value.

**Route tracking structures**:
- `routes`: Dictionary mapping route_id → list of customers
- `customer_to_route`: Dictionary mapping customer_id → route_id

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

**`__init__(dataset_path, vehicle_capacity, max_vehicles)`**  
Khởi tạo solver, đọc dữ liệu, xử lý toàn bộ khách hàng. Độ phức tạp: O(1).

**`_calculate_distance_matrix()`**  
Tính ma trận khoảng cách Euclidean giữa tất cả các cặp node. Độ phức tạp: O(n²).

**`_calculate_savings()`**  
Tính savings cho mọi cặp khách hàng và sắp xếp giảm dần. Độ phức tạp: O(n² log n) do sorting.

**`_check_time_window_feasibility(route)`**  
Kiểm tra route có thỏa mãn time window constraints không. Độ phức tạp: O(k) với k là số khách hàng trong route.

**`_calculate_route_distance(route)`**  
Tính tổng quãng đường của một route. Độ phức tạp: O(k).

**`_calculate_route_load(route)`**  
Tính tổng tải trọng của một route. Độ phức tạp: O(k).

**`solve()`**  
Giải bài toán bằng Clarke-Wright algorithm: tính savings, khởi tạo routes, merge routes theo savings. Độ phức tạp: O(n²).

### 1.4. Thuật toán Clarke-Wright

#### 1.4.1. Ý tưởng cơ bản

Clarke-Wright dựa trên khái niệm "savings" - lượng quãng đường tiết kiệm được khi gộp hai routes.

**Scenario ban đầu**: Mỗi khách hàng có một route riêng
```
Route i: 0 → i → 0  (distance = d(0,i) + d(i,0))
Route j: 0 → j → 0  (distance = d(0,j) + d(j,0))
Total: d(0,i) + d(i,0) + d(0,j) + d(j,0)
```

**Sau khi merge**: Gộp thành một route
```
Route merged: 0 → i → j → 0  (distance = d(0,i) + d(i,j) + d(j,0))
```

**Savings**:
```
Savings(i,j) = [d(0,i) + d(i,0) + d(0,j) + d(j,0)] - [d(0,i) + d(i,j) + d(j,0)]
             = d(i,0) + d(0,j) - d(i,j)
             = d(0,i) + d(0,j) - d(i,j)  (vì d(i,0) = d(0,i))
```

Savings càng lớn, việc gộp routes càng có lợi.

#### 1.4.2. Các bước thuật toán

**Bước 1**: Tính savings cho mọi cặp khách hàng (i,j) với i < j
```
Savings(i,j) = d(0,i) + d(0,j) - d(i,j)
```
Sắp xếp savings theo thứ tự giảm dần.

**Bước 2**: Khởi tạo solution
- Mỗi khách hàng i tạo một route: 0 → i → 0
- Tổng cộng n routes ban đầu

**Bước 3**: Merge routes
- Duyệt qua các savings từ cao xuống thấp
- Với mỗi savings(i,j):
  * Kiểm tra i và j có thuộc hai routes khác nhau không
  * Kiểm tra i hoặc j có phải là đầu/cuối route không
  * Kiểm tra capacity constraint của route mới
  * Kiểm tra time window feasibility của route mới
  * Nếu thỏa mãn tất cả: merge hai routes

**Bước 4**: Trả về solution với các routes đã merge

#### 1.4.3. Merge conditions

Hai routes chỉ được merge nếu thỏa mãn 4 điều kiện:

**1. Different routes**: i và j phải thuộc hai routes khác nhau

**2. Position constraint**: i và j phải ở vị trí có thể merge
- Case 1: i ở cuối route_i, j ở đầu route_j → route_i + route_j
- Case 2: j ở cuối route_j, i ở đầu route_i → route_j + route_i
- Case 3: i ở đầu route_i, j ở cuối route_j → route_j + route_i
- Case 4: j ở đầu route_j, i ở cuối route_i → route_i + route_j

**3. Capacity constraint**:
```
Total_load(new_route) ≤ vehicle_capacity
```

**4. Time window feasibility**:
```
For each customer k in new_route:
    arrival_time = current_time + travel_time
    start_service = max(arrival_time, ready_time[k])
    start_service ≤ due_date[k]
```

#### 1.4.4. Ví dụ minh họa

Giả sử có 3 khách hàng với depot tại (0,0):
- Customer 1: (10, 0)
- Customer 2: (20, 0)
- Customer 3: (0, 10)

Khoảng cách:
- d(0,1) = 10, d(0,2) = 20, d(0,3) = 10
- d(1,2) = 10, d(1,3) = 14.14, d(2,3) = 22.36

Savings:
- Savings(1,2) = 10 + 20 - 10 = 20
- Savings(1,3) = 10 + 10 - 14.14 = 5.86
- Savings(2,3) = 20 + 10 - 22.36 = 7.64

Sắp xếp: Savings(1,2) = 20 > Savings(2,3) = 7.64 > Savings(1,3) = 5.86

Merge routes theo thứ tự:
1. Merge route 1 và route 2 (savings = 20)
2. Kiểm tra merge route 2 và route 3 (savings = 7.64)
3. Kiểm tra merge route 1 và route 3 (savings = 5.86)

---

## 2. ĐỘ PHỨC TẠP THUẬT TOÁN

### 2.1. Phân loại bài toán

VRPTW thuộc lớp NP-Hard. Clarke-Wright là thuật toán heuristic constructive - xây dựng solution từng bước và không đảm bảo optimal. Độ phức tạp polynomial, phù hợp cho bài toán lớn.

### 2.2. Độ phức tạp tổng thể

**Time Complexity**: O(n² log n)

**Space Complexity**: O(n²) để lưu savings và distance matrix.

### 2.3. Độ phức tạp từng giai đoạn

| Giai đoạn | Độ phức tạp | Giải thích |
|-----------|-------------|------------|
| Initialization | O(n²) | Tính distance matrix |
| Calculate Savings | O(n²) | Tính n(n-1)/2 savings |
| Sort Savings | O(n² log n) | Sắp xếp ~n²/2 savings |
| Initialize Routes | O(n) | Tạo n routes ban đầu |
| Merge Routes | O(n²) | Duyệt savings và merge |
| Output | O(n) | Format solution |

**Tổng thể**: O(n² log n) do giai đoạn Sort Savings chiếm dominant.

### 2.4. Phân tích chi tiết merge phase

**Merge Routes** có độ phức tạp O(n²):
- Số savings cần xét: n(n-1)/2 ≈ n²/2
- Với mỗi saving:
  * Check different routes: O(1)
  * Check position: O(1) 
  * Calculate load: O(k) với k = route length
  * Check time windows: O(k)
  * Merge operation: O(1)

Worst-case: k có thể đến n, nhưng trong thực tế k << n.

Tổng độ phức tạp: O(n² × k) ≈ O(n²) trong thực tế.

### 2.5. Phân tích thực nghiệm

Dữ liệu thực nghiệm trên Solomon datasets:

| Số khách hàng | Số savings | Thời gian | Chất lượng | Số xe |
|---------------|------------|-----------|------------|-------|
| 25 | 300 | < 1s | Very Good | 3-5 |
| 50 | 1,225 | 1-2s | Very Good | 5-8 |
| 100 | 4,950 | 2-5s | Good | 10-15 |
| 200 | 19,900 | 10-20s | Good | 18-25 |
| 400 | 79,800 | 40-80s | Fair | 35-45 |

Kết luận: Clarke-Wright rất nhanh và scalable, có thể xử lý 400+ khách hàng trong vòng 1 phút.

### 2.6. So sánh với các phương pháp khác

| Thuật toán | Độ phức tạp | Thời gian (n=100) | Chất lượng | Scalability |
|------------|-------------|-------------------|------------|-------------|
| MILP | O(2^(n²×m)) | 60-300s | Optimal | Kém (n≤25) |
| CP | O(n²×k) | 30-60s | Very Good | Tốt (n≤400) |
| Clarke-Wright | O(n² log n) | 2-5s | Good | Rất tốt (n≤1000) |

Clarke-Wright có thời gian chạy nhanh nhất nhưng chất lượng thấp hơn CP một chút.

### 2.7. Phân tích từng thành phần

**Calculate Distance Matrix: O(n²)**
```python
for i in range(n):
    for j in range(n):
        distance[i][j] = euclidean_distance(i, j)
```

**Calculate Savings: O(n²)**
```python
for i in range(1, n+1):
    for j in range(i+1, n+1):
        savings.append({
            'customer_i': i,
            'customer_j': j,
            'saving': d[0][i] + d[0][j] - d[i][j]
        })
```
Tổng số savings: n(n-1)/2 ≈ n²/2

**Sort Savings: O(n² log n)**
```python
savings.sort(key=lambda x: x['saving'], reverse=True)
```
Sắp xếp n²/2 phần tử.

**Merge Loop: O(n²)**
```python
for saving_item in savings:  # n² iterations
    # Check và merge: O(k) với k << n
    if can_merge:
        merge_routes()  # O(1)
```

---

## 3. SIÊU THAM SỐ VÀ TINH CHỈNH

### 3.1. Danh sách siêu tham số

Clarke-Wright có 2 siêu tham số chính:

| Tham số | Loại | Phạm vi giá trị | Mặc định |
|---------|------|-----------------|----------|
| vehicle_capacity | Problem constraint | 50-500 | 200 |
| max_vehicles | Problem constraint | 5-50 | 25 |

**Lưu ý**: Clarke-Wright là thuật toán deterministic không có siêu tham số điều chỉnh hành vi thuật toán. Kết quả chỉ phụ thuộc vào dữ liệu đầu vào.

### 3.2. Chi tiết từng siêu tham số

#### 3.2.1. vehicle_capacity

**Định nghĩa**: Sức chứa tối đa của mỗi xe, giới hạn tổng demand có thể phục vụ trong một route.

**Vai trò**: Ràng buộc cứng quyết định khả năng merge routes. Capacity nhỏ hơn dẫn đến nhiều routes nhỏ, capacity lớn hơn cho phép routes dài hơn.

**Ảnh hưởng đến algorithm**:
- Capacity nhỏ → Nhiều routes ngắn → Ít merge → Nhiều xe
- Capacity lớn → Ít routes dài → Nhiều merge → Ít xe

**Ảnh hưởng đến solution quality**:
- Capacity quá nhỏ: Không đủ để merge routes hiệu quả, tổng quãng đường cao
- Capacity phù hợp: Cân bằng tốt giữa số xe và quãng đường
- Capacity quá lớn: Không ràng buộc, nhưng vẫn bị giới hạn bởi time windows

**Cách xác định capacity hợp lý**:
```python
total_demand = sum(customer['DEMAND'])
average_demand = total_demand / n_customers
desired_customers_per_route = 5-10

# Option 1: Dựa trên desired customers per route
vehicle_capacity = average_demand * desired_customers_per_route

# Option 2: Dựa trên desired number of vehicles
desired_vehicles = 10
vehicle_capacity = ceil(total_demand / desired_vehicles)

# Option 3: Dựa trên max demand + buffer
max_demand = max(customer['DEMAND'])
vehicle_capacity = max_demand * 10  # 10 customers buffer
```

#### 3.2.2. max_vehicles

**Định nghĩa**: Số xe tối đa có thể sử dụng. Giới hạn trên cho số routes trong solution.

**Vai trò**: Ràng buộc cứng về số lượng xe. Nếu không thể phục vụ tất cả khách hàng với max_vehicles, một số khách hàng sẽ không được phục vụ.

**Ảnh hưởng đến algorithm**:
- max_vehicles không ảnh hưởng trực tiếp đến quá trình merge
- Chỉ là check sau khi merge xong
- Trong triển khai hiện tại, thuật toán không enforce hard constraint này

**Ảnh hưởng đến feasibility**:
```python
min_vehicles_needed = ceil(total_demand / vehicle_capacity)

if max_vehicles < min_vehicles_needed:
    # Không thể phục vụ tất cả khách hàng
    # Cần tăng max_vehicles hoặc vehicle_capacity
```

**Cách xác định max_vehicles**:
```python
total_demand = sum(customer['DEMAND'])
min_vehicles = ceil(total_demand / vehicle_capacity)

# Thêm buffer 20-30%
max_vehicles = ceil(min_vehicles * 1.2)

# Hoặc cộng thêm số lượng cố định
max_vehicles = min_vehicles + 5
```

### 3.3. Các biến thể của Clarke-Wright

Mặc dù thuật toán chuẩn không có siêu tham số, có thể mở rộng với các biến thể:

#### 3.3.1. Parallel vs Sequential Clarke-Wright

**Sequential (triển khai hiện tại)**:
- Xây dựng tất cả routes đồng thời
- Merge bất kỳ hai routes nào
- Linh hoạt hơn

**Parallel**:
- Xây dựng từng route một cho đến khi đầy
- Chỉ thêm customer vào route hiện tại
- Ít linh hoạt hơn nhưng đơn giản

#### 3.3.2. Savings formula variants

**Classic savings (đang dùng)**:
```python
Savings(i,j) = d(0,i) + d(0,j) - d(i,j)
```

**Lambda-modified savings**:
```python
Savings(i,j) = d(0,i) + d(0,j) - lambda * d(i,j)
```
- lambda ∈ [0, 2]
- lambda = 1: classic savings
- lambda > 1: ưu tiên routes compact (customers gần nhau)
- lambda < 1: ưu tiên routes radial (xa depot)

**Shape parameter savings**:
```python
Savings(i,j) = d(0,i) + d(0,j) - d(i,j) + mu * |d(0,i) - d(0,j)|
```
- mu ∈ [-1, 1]
- Cân bằng giữa savings và shape của route

#### 3.3.3. Tie-breaking rules

Khi nhiều savings có giá trị bằng nhau:

**Rule 1: Farthest customer first**
```python
if saving1 == saving2:
    prefer customer farther from depot
```

**Rule 2: Largest demand first**
```python
if saving1 == saving2:
    prefer customer with larger demand
```

**Rule 3: Tightest time window first**
```python
if saving1 == saving2:
    prefer customer with tighter time window
```

### 3.4. Chiến lược cải thiện solution

Mặc dù Clarke-Wright không có siêu tham số tuning, có thể cải thiện solution bằng post-processing:

#### 3.4.1. 2-opt improvement

```python
def improve_with_2opt(solution):
    improved = True
    while improved:
        improved = False
        for route in solution.routes:
            for i in range(len(route) - 1):
                for j in range(i + 2, len(route)):
                    # Try reversing segment [i+1, j]
                    new_route = route[:i+1] + route[i+1:j+1][::-1] + route[j+1:]
                    if is_better_and_feasible(new_route, route):
                        route = new_route
                        improved = True
    return solution
```

#### 3.4.2. Or-opt improvement

```python
def improve_with_or_opt(solution):
    for route_i in solution.routes:
        for route_j in solution.routes:
            if route_i == route_j:
                continue
            # Try moving 1, 2, or 3 consecutive customers
            # from route_i to route_j
            for length in [1, 2, 3]:
                for pos_i in range(len(route_i) - length + 1):
                    segment = route_i[pos_i:pos_i+length]
                    for pos_j in range(len(route_j) + 1):
                        # Try inserting segment at pos_j
                        if is_better_and_feasible(...):
                            apply_move()
    return solution
```

#### 3.4.3. Route merging post-processing

```python
def merge_routes_post_processing(solution):
    improved = True
    while improved:
        improved = False
        for route_i in solution.routes:
            for route_j in solution.routes:
                if route_i == route_j:
                    continue
                # Try merging route_i and route_j
                merged = route_i + route_j
                if is_feasible(merged):
                    if total_distance(merged) < total_distance(route_i) + total_distance(route_j):
                        apply_merge()
                        improved = True
    return solution
```



---

\newpage

<a id="CP_Technical_Report"></a>

# BÁO CÁO KỸ THUẬT: THUẬT TOÁN CP CHO VRPTW

**Thuật toán**: Constraint Programming (CP)  
**Bài toán**: Vehicle Routing Problem with Time Windows  
**File triển khai**: `cp_vrptw_solver.py`

---

## 1. KIẾN TRÚC VÀ THÀNH PHẦN

### 1.1. Kiến trúc tổng quát

Class `CPVRPTWSolver` được tổ chức theo 5 giai đoạn xử lý tuần tự:

**Phase 1 - Initialization**: Đọc dữ liệu từ CSV, phân tách depot và customers, tính ma trận khoảng cách Euclidean và ma trận thời gian di chuyển. Khác với MILP, CP không giới hạn số khách hàng.

**Phase 2 - Model Building**: Chuẩn bị data model cho OR-Tools (distance matrix, time matrix, demands, time windows, service times), tạo RoutingIndexManager và RoutingModel, đăng ký callbacks và thiết lập dimensions.

**Phase 3 - Optimization**: Sử dụng Google OR-Tools routing solver với first solution strategy (PATH_CHEAPEST_ARC) và local search metaheuristic (GUIDED_LOCAL_SEARCH), áp dụng time limit.

**Phase 4 - Solution Extraction**: Parse solution từ OR-Tools routing object, trích xuất routes cho từng xe với thông tin distance và load từ dimensions.

**Phase 5 - Output**: Visualization với 3-subplot comprehensive plots và text report với báo cáo chi tiết.

### 1.2. Cấu trúc dữ liệu

**Input structures**:
- `self.data`: DataFrame chứa toàn bộ dataset
- `self.depot`: Series chứa thông tin depot
- `self.customers`: DataFrame chứa thông tin khách hàng (không giới hạn)
- `self.n_customers`: Số khách hàng thực tế

**Computational structures**:
- `self.distance_matrix`: Ma trận khoảng cách (n+1) x (n+1)
- `self.time_matrix`: Ma trận thời gian di chuyển (n+1) x (n+1)

**OR-Tools data model**:
```python
self.data_model = {
    'distance_matrix': list,      # Ma trận khoảng cách (×100, int)
    'time_matrix': list,           # Ma trận thời gian (×100, int)
    'demands': list,               # Nhu cầu khách hàng
    'time_windows': list,          # Time windows [(ready, due)]
    'service_times': list,         # Thời gian phục vụ
    'vehicle_capacities': list,    # Sức chứa các xe
    'num_vehicles': int,           # Số xe
    'depot': int                   # Index của depot (0)
}
```

**OR-Tools objects**:
- `self.manager`: RoutingIndexManager - quản lý mapping giữa node index và routing index
- `self.routing`: RoutingModel - mô hình routing chính
- `dimensions`: Capacity dimension và Time dimension

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

**`__init__(dataset_path, vehicle_capacity, max_vehicles)`**  
Khởi tạo solver, đọc dữ liệu, xử lý toàn bộ khách hàng. Độ phức tạp: O(1).

**`_calculate_distance_matrix()`**  
Tính ma trận khoảng cách Euclidean giữa tất cả các cặp node. Độ phức tạp: O(n²).

**`build_model()`**  
Xây dựng mô hình CP với OR-Tools: chuẩn bị data model, tạo routing model, đăng ký callbacks, thêm dimensions (Capacity, Time). Độ phức tạp: O(n²).

**`solve(time_limit)`**  
Giải bài toán bằng OR-Tools routing solver với Guided Local Search. Độ phức tạp phụ thuộc vào search strategy và problem size.

**`_extract_solution(solution)`**  
Trích xuất routes từ OR-Tools solution object, tính distance và load từ dimensions. Độ phức tạp: O(n × m).

### 1.4. Mô hình CP

#### 1.4.1. Biến quyết định

CP sử dụng biến quyết định khác với MILP:
- `NextVar(i)`: Node tiếp theo sau node i trong route
- `CumulVar(i)`: Giá trị tích lũy tại node i (capacity hoặc time)

#### 1.4.2. Hàm mục tiêu

```
Minimize: Tổng chi phí di chuyển trên tất cả các arcs
```

Được thiết lập thông qua:
```python
routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
```

#### 1.4.3. Ràng buộc

**1. Ràng buộc routing cơ bản**:
- Mỗi node được visit đúng 1 lần (trừ depot)
- Mỗi route bắt đầu và kết thúc tại depot
- Flow conservation được đảm bảo qua NextVar

**2. Ràng buộc sức chứa (Capacity Dimension)**:
```python
routing.AddDimensionWithVehicleCapacity(
    demand_callback_index,
    0,  # slack
    vehicle_capacities,
    True,  # start cumul to zero
    'Capacity'
)
```
- Tích lũy demand không vượt quá vehicle capacity
- Bắt đầu từ 0 tại depot

**3. Ràng buộc cửa sổ thời gian (Time Dimension)**:
```python
routing.AddDimension(
    time_callback_index,
    horizon,  # allow waiting
    horizon,  # maximum time per vehicle
    False,
    'Time'
)
```
- Time callback: travel_time + service_time
- Time window constraints cho mỗi customer:
  ```python
  time_dimension.CumulVar(index).SetRange(ready_time, due_date)
  ```
- Cho phép waiting time (xe có thể đến sớm và đợi)

**4. Optimization của time dimension**:
```python
routing.AddVariableMinimizedByFinalizer(
    time_dimension.CumulVar(routing.Start(vehicle_id))
)
routing.AddVariableMinimizedByFinalizer(
    time_dimension.CumulVar(routing.End(vehicle_id))
)
```

#### 1.4.4. Search Strategy

**First Solution Strategy**: PATH_CHEAPEST_ARC
- Xây dựng solution ban đầu bằng cách chọn arc rẻ nhất
- Greedy approach để có starting point nhanh

**Local Search Metaheuristic**: GUIDED_LOCAL_SEARCH
- Cải thiện solution bằng local search có hướng dẫn
- Sử dụng penalty để thoát khỏi local optima
- Kết hợp nhiều neighborhoods (2-opt, relocate, exchange, cross)

---

## 2. ĐỘ PHỨC TẠP THUẬT TOÁN

### 2.1. Phân loại bài toán

VRPTW thuộc lớp NP-Hard. CP không tìm nghiệm tối ưu đã chứng minh mà tìm nghiệm khả thi tốt trong thời gian cho phép. CP với Guided Local Search có độ phức tạp polynomial trong thực tế nhưng worst-case vẫn exponential.

### 2.2. Độ phức tạp tổng thể

**Time Complexity**: 
- First Solution (PATH_CHEAPEST_ARC): O(n²) 
- Local Search (GUIDED_LOCAL_SEARCH): O(n² × iterations) trong thực tế, worst-case có thể exponential
- Tổng thể: Polynomial trong thực tế với time limit

**Space Complexity**: O(n² + n×m) cho distance matrix, routing variables và dimensions.

### 2.3. Độ phức tạp từng giai đoạn

| Giai đoạn | Độ phức tạp | Giải thích |
|-----------|-------------|------------|
| Initialization | O(n²) | Tính distance matrix |
| Model Building | O(n²) | Tạo routing model và dimensions |
| First Solution | O(n²) | PATH_CHEAPEST_ARC greedy |
| Local Search | O(n² × k) | k iterations của GLS |
| Solution Extraction | O(n × m) | Parse solution từ NextVar |
| Visualization | O(n) | Vẽ biểu đồ |

Giai đoạn Local Search chiếm phần lớn thời gian tính toán.

### 2.4. Giải thích độ phức tạp local search

Guided Local Search hoạt động theo vòng lặp:
1. Khởi tạo solution bằng first solution strategy: O(n²)
2. Lặp cho đến khi hết time limit:
   - Đánh giá các neighborhoods (2-opt, relocate, exchange): O(n²) mỗi iteration
   - Chọn move tốt nhất và apply: O(1)
   - Update penalties để thoát local optima: O(n)
   - Số iterations k phụ thuộc vào time limit và problem size

Tổng: O(n² × k) trong đó k có thể rất lớn nhưng bị giới hạn bởi time limit.

### 2.5. Phân tích thực nghiệm

Dữ liệu thực nghiệm trên Solomon datasets:

| Số khách hàng | Nodes | Time limit | Thời gian thực tế | Chất lượng |
|---------------|-------|------------|-------------------|------------|
| 25 | 26 | 60s | 10-30s | Excellent |
| 50 | 51 | 60s | 30-60s | Very Good |
| 100 | 101 | 60s | 60s (timeout) | Good |
| 200 | 201 | 300s | 300s (timeout) | Fair |
| 400+ | 401+ | 600s | 600s (timeout) | Feasible |

Kết luận: CP có thể xử lý toàn bộ dataset (100+ khách hàng) và cho nghiệm khả thi tốt trong thời gian hợp lý. Không bị giới hạn như MILP.

### 2.6. So sánh với MILP

| Khía cạnh | MILP | CP |
|-----------|------|-----|
| Độ phức tạp worst-case | O(2^(n²×m)) | O(n²×k) |
| Độ phức tạp thực tế | Exponential | Polynomial |
| Giới hạn thực tế | n ≤ 25 | n ≤ 400+ |
| Chất lượng nghiệm | Optimal/Near-optimal | Good/Very Good |
| Thời gian | 60-300s cho n=25 | 10-60s cho n=100 |
| Scalability | Kém | Tốt |

---

## 3. SIÊU THAM SỐ VÀ TINH CHỈNH

### 3.1. Danh sách siêu tham số

CP có 5 siêu tham số chính có thể tinh chỉnh:

| Tham số | Loại | Phạm vi giá trị | Mặc định |
|---------|------|-----------------|----------|
| time_limit | Solver | 30-600s | 60s |
| max_vehicles | Problem constraint | 5-50 | 25 |
| first_solution_strategy | Search | 8 strategies | PATH_CHEAPEST_ARC |
| local_search_metaheuristic | Search | 7 metaheuristics | GUIDED_LOCAL_SEARCH |
| log_search | Output | True/False | True |

### 3.2. Chi tiết từng siêu tham số

#### 3.2.1. time_limit

**Định nghĩa**: Thời gian tối đa (giây) cho solver. Solver sẽ dừng khi hết thời gian và trả về best solution tìm được.

**Vai trò**: Trade-off giữa solution quality và computation time. CP luôn tìm được feasible solution nhanh, time_limit quyết định mức độ cải thiện solution.

**Ảnh hưởng**: 
- Time càng dài, solution càng tốt (diminishing returns)
- First solution thường được tìm trong vài giây đầu
- Phần lớn thời gian dành cho local search improvement

**Khuyến nghị theo kích thước**:
- n ≤ 50: 30-60s
- n ≤ 100: 60-120s  
- n ≤ 200: 120-300s
- n > 200: 300-600s

**Cách tinh chỉnh**:
```python
def get_time_limit(n_customers):
    if n_customers <= 50:
        return 60
    elif n_customers <= 100:
        return 120
    elif n_customers <= 200:
        return 300
    else:
        return 600
```

#### 3.2.2. max_vehicles

**Định nghĩa**: Số xe tối đa có thể sử dụng, giới hạn trên cho số routes.

**Vai trò**: Ảnh hưởng đến solution space và feasibility. Quá nhỏ có thể không tìm được feasible solution (đặc biệt với time windows chặt), quá lớn tăng search space.

**Ảnh hưởng**: Số vehicles ảnh hưởng tuyến tính đến search space, không như MILP (exponential). CP có thể xử lý max_vehicles lớn hơn MILP.

**Cách tính hợp lý**:
```python
total_demand = sum(customer['DEMAND'])
min_vehicles = ceil(total_demand / vehicle_capacity)
# CP có thể xử lý nhiều vehicles hơn MILP
max_vehicles = min(min_vehicles + 10, 50)
```

#### 3.2.3. first_solution_strategy

**Định nghĩa**: Chiến lược xây dựng solution ban đầu. OR-Tools cung cấp 8 strategies.

**Các options**:
1. `PATH_CHEAPEST_ARC` (mặc định): Chọn arc rẻ nhất, cân bằng tốt giữa speed và quality
2. `PATH_MOST_CONSTRAINED_ARC`: Ưu tiên arc có nhiều ràng buộc nhất
3. `EVALUATOR_STRATEGY`: Dựa trên evaluator function
4. `SAVINGS`: Thuật toán Clarke-Wright Savings
5. `SWEEP`: Thuật toán Sweep
6. `CHRISTOFIDES`: Thuật toán Christofides (cho TSP)
7. `ALL_UNPERFORMED`: Cho phép unperformed visits
8. `BEST_INSERTION`: Best insertion heuristic

**Vai trò**: Quyết định chất lượng starting point cho local search. Starting point tốt giúp local search nhanh hội tụ.

**Ảnh hưởng**: 
- PATH_CHEAPEST_ARC: Nhanh, chất lượng tốt, phù hợp đa số trường hợp
- SAVINGS: Chậm hơn nhưng starting point tốt hơn cho bài toán lớn
- SWEEP: Nhanh, phù hợp với customers có cấu trúc địa lý rõ ràng

**Khuyến nghị**:
```python
# General purpose
first_solution_strategy = PATH_CHEAPEST_ARC

# Large instances (n > 200)
first_solution_strategy = SAVINGS

# Geographic clustered customers
first_solution_strategy = SWEEP
```

#### 3.2.4. local_search_metaheuristic

**Định nghĩa**: Metaheuristic để cải thiện solution sau khi có first solution.

**Các options**:
1. `GUIDED_LOCAL_SEARCH` (mặc định): GLS với penalty mechanism, tốt nhất cho đa số trường hợp
2. `SIMULATED_ANNEALING`: SA với cooling schedule
3. `TABU_SEARCH`: Tabu search với tabu list
4. `GENERIC_TABU_SEARCH`: Generic version của tabu search
5. `AUTOMATIC`: OR-Tools tự chọn
6. `GREEDY_DESCENT`: Simple greedy descent
7. `LOCAL_SEARCH`: Basic local search

**Vai trò**: Quyết định cách thức cải thiện solution và khả năng thoát khỏi local optima.

**So sánh các metaheuristics**:

| Metaheuristic | Tốc độ | Chất lượng | Escape Local Optima | Phù hợp |
|---------------|--------|------------|---------------------|---------|
| GUIDED_LOCAL_SEARCH | Nhanh | Excellent | Excellent | General |
| SIMULATED_ANNEALING | Trung bình | Very Good | Good | Large instances |
| TABU_SEARCH | Nhanh | Good | Good | Time-constrained |
| GREEDY_DESCENT | Rất nhanh | Fair | Poor | Quick solutions |

**Khuyến nghị**:
```python
# General purpose (best overall)
local_search_metaheuristic = GUIDED_LOCAL_SEARCH

# Large instances with more time
local_search_metaheuristic = SIMULATED_ANNEALING

# Quick feasible solution
local_search_metaheuristic = GREEDY_DESCENT
```

#### 3.2.5. log_search

**Định nghĩa**: Boolean flag để bật/tắt logging trong quá trình search.

**Vai trò**: Giúp monitor tiến trình giải và debug. Hữu ích khi development nhưng có thể tắt trong production.

**Ảnh hưởng**: Logging có overhead nhỏ về performance (1-2%), nhưng cung cấp thông tin hữu ích về search progress.

**Khuyến nghị**:
```python
# Development/Debug
log_search = True

# Production
log_search = False
```

### 3.3. Chiến lược tinh chỉnh

#### 3.3.1. Rule-based tuning

```python
def get_recommended_hyperparameters(dataset):
    n = len(dataset.customers)
    total_demand = dataset.customers['DEMAND'].sum()
    
    # Xác định time_limit
    if n <= 50:
        time_limit = 60
    elif n <= 100:
        time_limit = 120
    elif n <= 200:
        time_limit = 300
    else:
        time_limit = 600
    
    # Tính max_vehicles
    min_vehicles = ceil(total_demand / dataset.vehicle_capacity)
    max_vehicles = min(min_vehicles + 10, 50)
    
    # Chọn strategies
    if n <= 100:
        first_solution_strategy = 'PATH_CHEAPEST_ARC'
    else:
        first_solution_strategy = 'SAVINGS'
    
    local_search_metaheuristic = 'GUIDED_LOCAL_SEARCH'
    
    return {
        'time_limit': time_limit,
        'max_vehicles': max_vehicles,
        'first_solution_strategy': first_solution_strategy,
        'local_search_metaheuristic': local_search_metaheuristic,
        'log_search': False
    }
```

#### 3.3.2. Adaptive tuning theo quality requirements

```python
def adaptive_tuning(quality_requirement):
    if quality_requirement == 'quick_feasible':
        return {
            'time_limit': 30,
            'first_solution_strategy': 'PATH_CHEAPEST_ARC',
            'local_search_metaheuristic': 'GREEDY_DESCENT'
        }
    elif quality_requirement == 'balanced':
        return {
            'time_limit': 120,
            'first_solution_strategy': 'PATH_CHEAPEST_ARC',
            'local_search_metaheuristic': 'GUIDED_LOCAL_SEARCH'
        }
    else:  # high_quality
        return {
            'time_limit': 600,
            'first_solution_strategy': 'SAVINGS',
            'local_search_metaheuristic': 'SIMULATED_ANNEALING'
        }
```

#### 3.3.3. Multi-strategy approach

```python
def solve_with_multiple_strategies(solver, strategies, time_per_strategy):
    """
    Chạy nhiều strategies và chọn best solution
    """
    best_solution = None
    best_objective = float('inf')
    
    for strategy in strategies:
        solver.first_solution_strategy = strategy['first_solution']
        solver.local_search_metaheuristic = strategy['local_search']
        
        result = solver.solve(time_limit=time_per_strategy)
        
        if result and result['objective'] < best_objective:
            best_objective = result['objective']
            best_solution = result
    
    return best_solution

# Example usage
strategies = [
    {'first_solution': 'PATH_CHEAPEST_ARC', 'local_search': 'GUIDED_LOCAL_SEARCH'},
    {'first_solution': 'SAVINGS', 'local_search': 'GUIDED_LOCAL_SEARCH'},
    {'first_solution': 'PATH_CHEAPEST_ARC', 'local_search': 'SIMULATED_ANNEALING'}
]

best = solve_with_multiple_strategies(solver, strategies, time_per_strategy=60)
```

---

**End of Report**


---

\newpage

<a id="Genetic_Algorithm_Technical_Report"></a>

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



---

\newpage

<a id="Large_Neighborhood_Search_Technical_Report"></a>

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



---

\newpage

<a id="MILP_Technical_Report"></a>

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


---

\newpage

<a id="Simulated_Annealing_Technical_Report"></a>

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



---

\newpage

<a id="Sweep_Technical_Report"></a>

# BÁO CÁO KỸ THUẬT: THUẬT TOÁN SWEEP CHO VRPTW

**Thuật toán**: Sweep Algorithm (Thuật toán Quét)  
**Bài toán**: Vehicle Routing Problem with Time Windows  
**File triển khai**: `sweep_vrptw_solver.py`

---

## 1. KIẾN TRÚC VÀ THÀNH PHẦN

### 1.1. Kiến trúc tổng quát

Class `SweepVRPTWSolver` được tổ chức theo 4 giai đoạn xử lý tuần tự:

**Phase 1 - Initialization**: Đọc dữ liệu từ CSV, phân tách depot và customers, tính ma trận khoảng cách Euclidean và ma trận thời gian, tính góc phương vị (polar angle) cho mỗi khách hàng.

**Phase 2 - Angle Sorting**: Sắp xếp khách hàng theo góc phương vị tăng dần (theo chiều kim đồng hồ từ góc bắt đầu). Điều chỉnh góc dựa trên start_angle.

**Phase 3 - Route Construction**: Quét theo góc đã sắp xếp, tạo routes bằng cách thêm khách hàng vào route hiện tại cho đến khi vi phạm capacity hoặc time window constraints, sau đó tối ưu thứ tự khách hàng trong mỗi route bằng nearest neighbor.

**Phase 4 - Output**: Chuyển đổi routes sang format solution, visualization với 3-subplot comprehensive plots bao gồm sweep rays và text report chi tiết.

### 1.2. Cấu trúc dữ liệu

**Input structures**:
- `self.data`: DataFrame chứa toàn bộ dataset
- `self.depot`: Series chứa thông tin depot
- `self.customers`: DataFrame chứa thông tin khách hàng
- `self.n_customers`: Số khách hàng thực tế

**Computational structures**:
- `self.distance_matrix`: Ma trận khoảng cách (n+1) x (n+1)
- `self.time_matrix`: Ma trận thời gian di chuyển (n+1) x (n+1)

**Polar angle structure**:
```python
self.polar_angles = {
    customer_id: angle_degrees  # Góc từ 0° đến 360°
}
```
Góc được tính bằng `atan2(dy, dx)` và chuyển sang độ.

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

**`__init__(dataset_path, vehicle_capacity, max_vehicles)`**  
Khởi tạo solver, đọc dữ liệu, tính polar angles. Độ phức tạp: O(n).

**`_calculate_distance_matrix()`**  
Tính ma trận khoảng cách Euclidean giữa tất cả các cặp node. Độ phức tạp: O(n²).

**`_calculate_polar_angles()`**  
Tính góc phương vị cho mỗi khách hàng so với depot. Độ phức tạp: O(n).

**`_check_time_window_feasibility(route)`**  
Kiểm tra route có thỏa mãn time window constraints không. Độ phức tạp: O(k) với k là số khách hàng trong route.

**`_optimize_route_order(route)`**  
Tối ưu thứ tự khách hàng trong route bằng nearest neighbor. Độ phức tạp: O(k²).

**`_calculate_route_distance(route)`**  
Tính tổng quãng đường của một route. Độ phức tạp: O(k).

**`_calculate_route_load(route)`**  
Tính tổng tải trọng của một route. Độ phức tạp: O(k).

**`solve(start_angle)`**  
Giải bài toán bằng Sweep algorithm: sắp xếp theo góc, quét tạo routes, tối ưu thứ tự. Độ phức tạp: O(n log n).

### 1.4. Thuật toán Sweep

#### 1.4.1. Ý tưởng cơ bản

Sweep dựa trên tư tưởng quét hình học - chia customers thành các clusters dựa trên vị trí góc của chúng so với depot.

**Khái niệm Polar Angle (Góc phương vị)**:
```
Với depot tại (x₀, y₀) và customer tại (xᵢ, yᵢ):
  dx = xᵢ - x₀
  dy = yᵢ - y₀
  angle = atan2(dy, dx)  # Góc từ -π đến π
  angle_degrees = degrees(angle)  # Chuyển sang độ
  if angle_degrees < 0:
      angle_degrees += 360  # Chuẩn hóa về 0° - 360°
```

**Sweep Process**:
1. Tính góc phương vị cho mỗi customer
2. Sắp xếp customers theo góc tăng dần
3. Quét theo chiều kim đồng hồ, tạo routes tuần tự

**Ví dụ trực quan**:
```
           90°
            |
            C3
            |
  180° ─────D───── 0°
      C2    |    C1
            |
          270°

Sorted order: C1 (0°) → C3 (90°) → C2 (180°)
```

#### 1.4.2. Các bước thuật toán

**Bước 1**: Tính polar angles
```python
for each customer i:
    dx = x[i] - x[depot]
    dy = y[i] - y[depot]
    angle[i] = atan2(dy, dx) converted to degrees [0, 360]
```

**Bước 2**: Điều chỉnh góc theo start_angle
```python
adjusted_angle[i] = (angle[i] - start_angle) % 360
```
Cho phép bắt đầu quét từ hướng khác nhau.

**Bước 3**: Sắp xếp customers theo góc tăng dần
```python
sorted_customers = sort(customers, key=adjusted_angle)
```

**Bước 4**: Sweep và tạo routes
```python
current_route = []
current_load = 0

for customer in sorted_customers:
    if can_add_to_current_route(customer):
        current_route.append(customer)
        current_load += demand[customer]
    else:
        routes.append(current_route)
        current_route = [customer]
        current_load = demand[customer]

routes.append(current_route)  # Route cuối
```

**Bước 5**: Tối ưu thứ tự trong mỗi route
```python
for each route:
    optimized_route = nearest_neighbor_tsp(route)
    if time_window_feasible(optimized_route):
        route = optimized_route
```

#### 1.4.3. Điều kiện thêm customer vào route

Customer được thêm vào route hiện tại nếu thỏa mãn:

**1. Capacity constraint**:
```
current_load + demand[customer] ≤ vehicle_capacity
```

**2. Time window feasibility**:
```
test_route = current_route + [customer]
if check_time_window_feasibility(test_route):
    accept
else:
    start new route
```

#### 1.4.4. Nearest Neighbor TSP cho route optimization

Sau khi tạo route, tối ưu thứ tự khách hàng:

```
optimized = [route[0]]  # Bắt đầu từ customer đầu tiên
remaining = route[1:]

while remaining:
    current = optimized[-1]
    nearest = argmin(distance[current][j] for j in remaining)
    optimized.append(nearest)
    remaining.remove(nearest)

if time_window_feasible(optimized):
    return optimized
else:
    return route  # Giữ nguyên nếu không feasible
```

#### 1.4.5. Ví dụ minh họa

Giả sử depot tại (50, 50) và 6 customers:

| Customer | Tọa độ | Góc | Demand |
|----------|--------|-----|--------|
| 1 | (60, 50) | 0° | 10 |
| 2 | (60, 60) | 45° | 15 |
| 3 | (50, 60) | 90° | 20 |
| 4 | (40, 60) | 135° | 10 |
| 5 | (40, 50) | 180° | 15 |
| 6 | (50, 40) | 270° | 20 |

Với vehicle_capacity = 50:

**Sweep process**:
1. Sorted order: 1→2→3→4→5→6
2. Route 1: Start từ C1 (0°)
   - Add C1: load = 10 ✓
   - Add C2: load = 25 ✓
   - Add C3: load = 45 ✓
   - Try C4: load = 55 > 50 ✗ → Start Route 2
3. Route 2: Start từ C4 (135°)
   - Add C4: load = 10 ✓
   - Add C5: load = 25 ✓
   - Add C6: load = 45 ✓
   
Final routes: {1,2,3} và {4,5,6}

#### 1.4.6. Ảnh hưởng của start_angle

start_angle cho phép quét từ hướng khác nhau:

```
start_angle = 0°:   Bắt đầu từ phía Đông (→)
start_angle = 90°:  Bắt đầu từ phía Bắc (↑)
start_angle = 180°: Bắt đầu từ phía Tây (←)
start_angle = 270°: Bắt đầu từ phía Nam (↓)
```

Điều chỉnh start_angle có thể cho kết quả khác nhau.

---

## 2. ĐỘ PHỨC TẠP THUẬT TOÁN

### 2.1. Phân loại bài toán

VRPTW thuộc lớp NP-Hard. Sweep là thuật toán heuristic constructive geometric-based - xây dựng solution dựa trên vị trí hình học của customers. Độ phức tạp polynomial, rất nhanh.

### 2.2. Độ phức tạp tổng thể

**Time Complexity**: O(n log n + n×k²) ≈ O(n log n) khi k << n

**Space Complexity**: O(n²) cho distance matrix và O(n) cho polar angles.

### 2.3. Độ phức tạp từng giai đoạn

| Giai đoạn | Độ phức tạp | Giải thích |
|-----------|-------------|------------|
| Initialization | O(n²) | Tính distance matrix |
| Calculate Polar Angles | O(n) | Tính n góc với atan2 |
| Sort by Angle | O(n log n) | Sắp xếp n customers |
| Sweep & Create Routes | O(n) | Duyệt qua n customers một lần |
| Optimize Route Order | O(m×k²) | m routes, mỗi route k customers |
| Output | O(n) | Format solution |

**Tổng thể**: O(n log n + m×k²) ≈ O(n log n) trong thực tế vì k << n.

### 2.4. Phân tích chi tiết route optimization

**Nearest Neighbor TSP** cho mỗi route:
- Số customers trong route: k (thường k << n)
- Với mỗi step: tìm nearest trong O(k) customers
- Tổng k steps
- Độ phức tạp: O(k²) cho một route

**Tổng cho tất cả routes**:
- Số routes: m (thường m = 10-20)
- Tổng số customers: n = Σkᵢ
- Tổng độ phức tạp: O(Σkᵢ²) ≈ O(n×k_avg) khi routes cân bằng

Trong thực tế: k_avg ≈ 5-10, nên O(n×k) << O(n²).

### 2.5. Phân tích thực nghiệm

Dữ liệu thực nghiệm trên Solomon datasets:

| Số khách hàng | Sort time | Sweep time | Optimize time | Total | Chất lượng |
|---------------|-----------|------------|---------------|-------|------------|
| 25 | < 0.01s | < 0.01s | < 0.1s | < 0.2s | Good |
| 50 | < 0.01s | < 0.01s | 0.1-0.2s | < 0.5s | Good |
| 100 | 0.01s | 0.01s | 0.5-1s | 1-2s | Fair |
| 200 | 0.02s | 0.02s | 2-4s | 4-6s | Fair |
| 400 | 0.05s | 0.05s | 8-15s | 15-20s | Fair |

Kết luận: Sweep rất nhanh, phù hợp với bài toán lớn. Chất lượng phụ thuộc vào cấu trúc geometric của customers.

### 2.6. So sánh với các phương pháp khác

| Thuật toán | Độ phức tạp | Thời gian (n=100) | Chất lượng | Phù hợp |
|------------|-------------|-------------------|------------|---------|
| MILP | O(2^(n²×m)) | 60-300s | Optimal | n≤25 |
| CP | O(n²×k) | 30-60s | Very Good | Tổng quát |
| Clarke-Wright | O(n² log n) | 2-5s | Good | Tổng quát |
| Sweep | O(n log n) | 1-2s | Fair-Good | Clustered |

Sweep nhanh nhất nhưng chất lượng phụ thuộc nhiều vào cấu trúc dữ liệu. Tốt nhất cho customers có cấu trúc cluster theo góc.

### 2.7. Phân tích từng thành phần

**Calculate Polar Angles: O(n)**
```python
for i in range(n):
    dx = customer[i].x - depot.x
    dy = customer[i].y - depot.y
    angle[i] = atan2(dy, dx)  # O(1)
```

**Sort by Angle: O(n log n)**
```python
sorted_customers = sorted(customers, key=lambda c: angle[c])
```
Quicksort hoặc Mergesort.

**Sweep Loop: O(n)**
```python
for customer in sorted_customers:  # n iterations
    check_capacity()  # O(1)
    check_time_window()  # O(k)
    add_to_route()  # O(1)
```
Mỗi customer được xét đúng 1 lần.

**Route Optimization: O(m×k²)**
```python
for route in routes:  # m routes
    optimized = nearest_neighbor_tsp(route)  # O(k²)
```

---

## 3. SIÊU THAM SỐ VÀ TINH CHỈNH

### 3.1. Danh sách siêu tham số

Sweep có 3 siêu tham số:

| Tham số | Loại | Phạm vi giá trị | Mặc định |
|---------|------|-----------------|----------|
| vehicle_capacity | Problem constraint | 50-500 | 200 |
| max_vehicles | Problem constraint | 5-50 | 25 |
| start_angle | Algorithm parameter | 0-360° | 0° |

### 3.2. Chi tiết từng siêu tham số

#### 3.2.1. vehicle_capacity

**Định nghĩa**: Sức chứa tối đa của mỗi xe.

**Vai trò**: Quyết định số lượng customers có thể được gom vào một route trong quá trình sweep. Ảnh hưởng trực tiếp đến số routes và độ dài mỗi route.

**Ảnh hưởng đến algorithm**:
- Capacity nhỏ → Routes ngắn → Nhiều routes → Sweep boundaries nhiều hơn
- Capacity lớn → Routes dài → Ít routes → Sweep coverage rộng hơn

**Ảnh hưởng đến solution quality**:
- Với customers có cấu trúc cluster tốt: capacity ảnh hưởng ít đến quality
- Với customers phân tán: capacity ảnh hưởng nhiều

**Khuyến nghị**: Tương tự Clarke-Wright, xác định dựa trên total demand và desired routes.

#### 3.2.2. max_vehicles

**Định nghĩa**: Số xe tối đa có thể sử dụng.

**Vai trò**: Giới hạn trên cho số routes. Trong Sweep, nếu đạt max_vehicles trước khi sweep xong, các customers còn lại sẽ được gộp vào route cuối.

**Ảnh hưởng đến algorithm**:
```python
if len(routes) >= max_vehicles:
    # Gộp customers còn lại vào route cuối
    current_route.extend(remaining_customers)
```

**Khuyến nghị**: 
```python
min_vehicles = ceil(total_demand / vehicle_capacity)
max_vehicles = min_vehicles + 5
```

#### 3.2.3. start_angle

**Định nghĩa**: Góc bắt đầu quét (độ, 0-360°), quyết định hướng bắt đầu sweep.

**Vai trò**: Tham số quan trọng nhất ảnh hưởng đến chất lượng solution của Sweep. Góc bắt đầu khác nhau có thể cho routes hoàn toàn khác nhau.

**Ảnh hưởng đến algorithm**:
```python
adjusted_angle[i] = (angle[i] - start_angle) % 360
```
Điều chỉnh góc để quét bắt đầu từ start_angle.

**Ảnh hưởng đến solution quality**:
- Có thể khác biệt lớn (5-30% total distance)
- Phụ thuộc vào cấu trúc geometric của customers
- Nếu customers tạo thành clusters rõ ràng: start_angle nên align với cluster boundaries

**Ví dụ minh họa**:
```
Customers phân bố theo 4 clusters tại 4 góc phần tư:
- Cluster A: 0-90° (Đông Bắc)
- Cluster B: 90-180° (Tây Bắc)
- Cluster C: 180-270° (Tây Nam)
- Cluster D: 270-360° (Đông Nam)

start_angle = 0°: Bắt đầu từ cluster A → tốt
start_angle = 45°: Bắt đầu giữa A và B → có thể split cluster
start_angle = 90°: Bắt đầu từ cluster B → tốt
start_angle = 135°: Bắt đầu giữa B và C → có thể split cluster
```

**Chiến lược chọn start_angle**:

**1. Fixed angles (đơn giản)**:
```python
# Cardinal directions
start_angles = [0, 90, 180, 270]  # Đông, Bắc, Tây, Nam
```

**2. Fine-grained search**:
```python
# Every 30 degrees
start_angles = range(0, 360, 30)  # 12 directions
```

**3. Cluster-based (thông minh)**:
```python
# Xác định cluster boundaries trước
clusters = identify_clusters(customers)
start_angles = [cluster.min_angle for cluster in clusters]
```

**4. Multi-start optimization**:
```python
def find_best_start_angle():
    best_solution = None
    best_distance = float('inf')
    
    for angle in range(0, 360, 15):  # 24 trials
        solution = sweep_solve(start_angle=angle)
        if solution.total_distance < best_distance:
            best_distance = solution.total_distance
            best_solution = solution
    
    return best_solution
```

### 3.3. Biến thể của Sweep Algorithm

#### 3.3.1. Multi-start Sweep

Chạy Sweep với nhiều start_angles khác nhau và chọn best:

```python
def multi_start_sweep(angles_to_try):
    solutions = []
    for angle in angles_to_try:
        solution = solve(start_angle=angle)
        solutions.append(solution)
    
    return min(solutions, key=lambda s: s.objective)

# Usage
angles = [0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330]
best_solution = multi_start_sweep(angles)
```

Độ phức tạp: O(k × n log n) với k là số angles thử.

#### 3.3.2. Adaptive Sweep Direction

Thay đổi hướng quét (clockwise vs counter-clockwise):

```python
# Clockwise (mặc định)
sorted_customers = sort(customers, key=angle, reverse=False)

# Counter-clockwise
sorted_customers = sort(customers, key=angle, reverse=True)
```

Có thể cho kết quả khác nhau với time windows chặt.

#### 3.3.3. Two-phase Sweep

Phase 1: Cluster customers bằng Sweep
Phase 2: Solve TSP cho mỗi cluster

```python
def two_phase_sweep():
    # Phase 1: Cluster
    clusters = []
    current_cluster = []
    for customer in sorted_by_angle:
        if can_add_to_cluster(customer):
            current_cluster.append(customer)
        else:
            clusters.append(current_cluster)
            current_cluster = [customer]
    
    # Phase 2: TSP for each cluster
    routes = []
    for cluster in clusters:
        route = tsp_solver(cluster)  # Optimal TSP
        routes.append(route)
    
    return routes
```

#### 3.3.4. Hybrid Sweep-CW

Kết hợp Sweep với Clarke-Wright:

```python
def hybrid_sweep_cw():
    # Step 1: Sweep tạo initial routes
    initial_routes = sweep_solve()
    
    # Step 2: CW merge routes
    merged_routes = clarke_wright_merge(initial_routes)
    
    return merged_routes
```

### 3.4. Chiến lược cải thiện solution

#### 3.4.1. Post-sweep optimization

**2-opt within routes**:
```python
for route in solution.routes:
    improved_route = two_opt(route)
    if is_better_and_feasible(improved_route):
        route = improved_route
```

**Or-opt between routes**:
```python
for route_i in solution.routes:
    for route_j in solution.routes:
        if i != j:
            improved_i, improved_j = or_opt(route_i, route_j)
            if is_better_and_feasible(improved_i, improved_j):
                apply_improvement()
```

#### 3.4.2. Angle perturbation

Thử các góc gần với best angle:

```python
best_angle = find_best_angle(coarse_search=[0, 30, 60, ...])
fine_angles = range(best_angle - 15, best_angle + 15, 1)
best_solution = multi_start_sweep(fine_angles)
```

### 3.5. Khuyến nghị sử dụng

**Khi nào dùng Sweep**:
- Customers có cấu trúc cluster theo góc/vị trí
- Cần solution rất nhanh (< 1 giây)
- Dataset lớn (100-500+ customers)
- Customers phân bố đều xung quanh depot

**Khi nào KHÔNG nên dùng**:
- Customers phân tán không có pattern
- Cần solution chất lượng cao nhất (dùng CP)
- Depot không ở trung tâm của customers
- Time windows rất chặt (CP tốt hơn)

**Best practices**:
```python
# 1. Multi-start với ít nhất 4 hướng
angles = [0, 90, 180, 270]
best = min([solve(angle=a) for a in angles], 
           key=lambda s: s.objective)

# 2. Nếu có thời gian, thử nhiều góc hơn
angles = range(0, 360, 15)  # 24 directions
best = multi_start_sweep(angles)

# 3. Post-processing improvement
best = improve_with_2opt(best)

# 4. Combine với metaheuristics
initial = sweep_solve(start_angle=0)
final = tabu_search(initial_solution=initial)
```

**Khi nào Sweep tốt nhất**:
- Customers tạo thành "pie slices" xung quanh depot
- Distribution centers với customers phân bố theo khu vực
- Urban delivery với customers phân bố theo quận/phường

**Khi nào Sweep kém**:
- Customers tạo thành clusters không liên quan đến góc
- Depot ở góc của service area
- Customers phân tán random

---

**End of Report**


---

\newpage

<a id="Tabu_Search_Technical_Report"></a>

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



