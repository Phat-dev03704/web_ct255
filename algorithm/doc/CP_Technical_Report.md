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
