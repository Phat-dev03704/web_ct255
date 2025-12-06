# 🚗 VRP Solver - Vehicle Routing Problem with Time Windows

> Giải bài toán tối ưu tuyến đường giao hàng cho nhiều xe với các ràng buộc về thời gian, sức chứa và khoảng cách.

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![OR-Tools](https://img.shields.io/badge/OR--Tools-9.8%2B-orange.svg)](https://developers.google.com/optimization)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 📸 Demo

<div align="center">
  <img src="docs/demo.gif" alt="VRP Solver Demo" width="800"/>
  <p><em>Trực quan hóa tuyến đường giao hàng trên bản đồ tương tác</em></p>
</div>

## ✨ Tính năng

- 🎯 **10+ Thuật toán tối ưu**: OR-Tools (Google), Genetic Algorithm, Simulated Annealing, Tabu Search, MILP...
- 🗺️ **Visualization đẹp mắt**: Bản đồ tương tác với Folium/Leaflet, hiển thị số thứ tự giao hàng
- 🛣️ **Đường đi thực tế**: Tích hợp OSRM/OpenRouteService để tính route theo đường phố, không xuyên tường!
- 📍 **Layer Control**: Bật/tắt từng xe riêng lẻ để phân tích chi tiết
- 🧭 **Turn-by-turn directions**: Chỉ dẫn rẽ trái/phải từng bước
- 🎨 **Map Editor**: Tạo điểm khách hàng bằng cách click trên bản đồ
- ⚡ **Smart Caching**: Lưu trữ routing data để tăng tốc 50-300 lần khi chạy lại
- 🐳 **Docker Support**: Chạy ngay không cần cài đặt phức tạp

## 🎬 Quick Start

### Cách nhanh nhất - Dùng Docker 🐳

```bash
# 1. Clone repository
git clone https://github.com/YOUR_USERNAME/vrp-solver.git
cd vrp-solver

# 2. Chạy ngay với Docker (không cần cài Python!)
docker-compose up vrp-solver

# Kết quả xuất hiện trong thư mục maps/
```

### Hoặc cài đặt truyền thống

```bash
# 1. Clone repository
git clone https://github.com/YOUR_USERNAME/vrp-solver.git
cd vrp-solver

# 2. Tạo virtual environment
python -m venv .venv

# 3. Activate venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Linux/Mac:
source .venv/bin/activate

# 4. Cài đặt dependencies
pip install -r requirements.txt

# 5. Chạy thử với dữ liệu mẫu
python scripts/run_and_visualize.py --use-osrm

# 6. Mở file HTML trong maps/ để xem kết quả
```

## 📋 Yêu cầu hệ thống

### Không dùng Docker:
- Python 3.9 trở lên
- 4GB RAM (8GB khuyến nghị)
- Windows 10/11, Linux, hoặc MacOS

### Dùng Docker:
- Docker Desktop 4.0+ ([Download](https://www.docker.com/products/docker-desktop))
- 8GB RAM khuyến nghị

## 📖 Hướng dẫn sử dụng

### 🚀 Chạy với dữ liệu mẫu

#### Không dùng Docker:
```bash
# Đảm bảo đã activate virtual environment
.\.venv\Scripts\Activate.ps1  # Windows
# source .venv/bin/activate    # Linux/Mac

# Chạy OR-Tools với đường thẳng (nhanh nhất)
python scripts/run_and_visualize.py

# Chạy với đường đi thực tế (đẹp hơn)
python scripts/run_and_visualize.py --use-osrm
```

#### Dùng Docker:
```bash
# Chạy mặc định
docker-compose up vrp-solver

# Chạy với tham số tùy chỉnh
docker-compose run --rm vrp-solver python scripts/run_and_visualize.py --use-osrm --vehicle_capacity 200
```

**Kết quả** xuất hiện tại `maps/ortools_ninh_kieu.html` - mở file này trong browser để xem bản đồ!

---

### 🎨 Thử các thuật toán khác

```bash
# Genetic Algorithm
python scripts/run_and_visualize.py --algorithm ga --use-osrm

# Simulated Annealing
python scripts/run_and_visualize.py --algorithm sa --use-osrm

# Tabu Search
python scripts/run_and_visualize.py --algorithm tabu --use-osrm

# Xem danh sách đầy đủ thuật toán ở phần dưới
```

---

### ⚙️ Tùy chỉnh tham số

```bash
python scripts/run_and_visualize.py \
  --input data/input/khach_hang_mau.csv \
  --algorithm ortools \
  --use-osrm \
  --vehicle_capacity 200 \
  --max_vehicles 25 \
  --time_limit 120 \
  --depot-lat 10.0275 \
  --depot-lon 105.7700 \
  --out maps/my_solution.html
```

**Các tham số quan trọng:**
| Tham số | Mô tả | Mặc định |
|---------|-------|----------|
| `--input` | File CSV khách hàng | `data/input/khach_hang.csv` |
| `--algorithm` | Thuật toán (ortools, ga, sa...) | `ortools` |
| `--use-osrm` | Dùng đường đi thực tế | `False` (đường thẳng) |
| `--vehicle_capacity` | Sức chứa mỗi xe | `200` |
| `--max_vehicles` | Số xe tối đa | `25` |
| `--time_limit` | Thời gian chạy (giây) | `120` |
| `--out` | File HTML đầu ra | `maps/ortools_ninh_kieu.html` |

---

### 📍 Tạo dữ liệu khách hàng mới

#### **Cách 1: Map Editor (Dễ nhất!)**

```bash
# Không dùng Docker:
python add_coordinates/serve_map.py
# Mở http://localhost:8000/map_editor.html

# Dùng Docker:
docker-compose up map-editor
# Mở http://localhost:8001/map_editor.html
```

**Hướng dẫn:**
1. Click trên bản đồ để thêm điểm khách hàng (tự động đánh số KH_1, KH_2...)
2. Nhập thông tin demand, time window cho mỗi điểm
3. Click "Download CSV" để tải file
4. Đặt file vào `data/input/` và chạy solver!

#### **Cách 2: Command Line**

```bash
python add_coordinates/create_customers.py --auto-sample
```

---

### 🗺️ Xem kết quả

```bash
# Windows
start maps/ortools_ninh_kieu.html

# Linux
xdg-open maps/ortools_ninh_kieu.html

# Mac
open maps/ortools_ninh_kieu.html
```

**Tính năng bản đồ:**
- 🔍 Zoom in/out, pan around
- 🎛️ Layer Control (góc phải trên): Bật/tắt từng xe
- 📊 Legend (góc phải dưới): Màu sắc xe
- 📈 Summary (góc trái dưới): Số xe, tổng km
- 🧭 Click vào route để xem hướng dẫn chi tiết (turn-by-turn)
- 🔢 Số thứ tự trên marker = thứ tự giao hàng

## 📁 Cấu trúc dự án

```
vrp-solver/
├── 📂 algorithm/              # Các thuật toán giải VRP
│   ├── OR-Tools/             # OR-Tools solver (Google)
│   ├── GA/                   # Genetic Algorithm
│   ├── Simulated-Annealing/  # Simulated Annealing
│   ├── Tabu/                 # Tabu Search
│   ├── MILP/                 # Mixed Integer Linear Programming
│   └── ...                   # 10+ thuật toán khác
│
├── 📂 data/
│   ├── input/                # File CSV dữ liệu khách hàng
│   │   ├── khach_hang_mau.csv      # Dữ liệu mẫu
│   │   └── khach_hang.csv          # File mặc định
│   └── cache/                # Cache OSRM routing (tự động tạo)
│
├── 📂 maps/                   # File HTML bản đồ kết quả
│   └── ortools_ninh_kieu.html
│
├── 📂 scripts/
│   └── run_and_visualize.py  # ⭐ Script chính để chạy solver
│
├── 📂 src/
│   └── osm_routing_client.py # Client gọi OSRM/ORS API
│
├── 📂 add_coordinates/        # Công cụ tạo dữ liệu
│   ├── map_editor.html       # Web UI tạo điểm khách hàng
│   ├── serve_map.py          # Web server cho map editor
│   └── create_customers.py   # CLI tạo điểm
│
├── 📄 requirements.txt        # Dependencies Python
├── 📄 Dockerfile             # Docker image definition
├── 📄 docker-compose.yml     # Docker compose config
├── 📄 .gitignore             # Git ignore rules
└── 📄 README.md              # Tài liệu này
```

## 📊 Format file CSV đầu vào

File `data/input/khach_hang_mau.csv`:

```csv
id,name,lat,lon,demand,ready_time,due_date,service_time
DEPOT,Kho Ninh Kieu,10.027500,105.770000,0,0,300,0
1,KH_1,10.027113,105.766936,22,0,180,10
2,KH_2,10.026141,105.765166,28,0,200,8
3,KH_3,10.028456,105.768234,15,30,220,12
...
```

**Giải thích các cột:**

| Cột | Mô tả | Ví dụ | Lưu ý |
|-----|-------|-------|-------|
| `id` | Mã điểm | `DEPOT`, `1`, `2`... | Dòng đầu phải là `DEPOT` |
| `name` | Tên điểm | `Kho Ninh Kieu`, `KH_1` | Tùy ý |
| `lat` | Vĩ độ (Latitude) | `10.027500` | Việt Nam: 8-23 |
| `lon` | Kinh độ (Longitude) | `105.770000` | Việt Nam: 102-110 |
| `demand` | Nhu cầu hàng hóa | `22` | Depot = 0 |
| `ready_time` | Thời gian sớm nhất (phút) | `0` | Từ 0:00 sáng |
| `due_date` | Thời gian muộn nhất (phút) | `180` | 180 = 3 giờ sáng |
| `service_time` | Thời gian phục vụ (phút) | `10` | Thời gian giao hàng |

**Quy tắc quan trọng:**
- ⚠️ **Dòng đầu tiên PHẢI là DEPOT** (kho/depot)
- ⚠️ DEPOT có `demand = 0`
- ✅ Tọa độ phải hợp lệ (có thể dùng Google Maps để lấy)
- ✅ Time window: `ready_time ≤ due_date`

## 🎯 Danh sách thuật toán

Sử dụng flag `--algorithm <tên>` để chọn:

| Tên | Command | Đặc điểm | Tốc độ | Chất lượng |
|-----|---------|----------|--------|------------|
| **OR-Tools** | `ortools` | Google, constraint programming | ⚡⚡⚡ | ⭐⭐⭐⭐⭐ |
| **MILP** | `milp` | Tối ưu toàn cục (nhỏ < 30 KH) | 🐌 | ⭐⭐⭐⭐⭐ |
| **Genetic Algorithm** | `ga` | Evolutionary, khám phá tốt | ⚡⚡ | ⭐⭐⭐⭐ |
| **Simulated Annealing** | `sa` | Tránh local optimum | ⚡⚡ | ⭐⭐⭐ |
| **Tabu Search** | `tabu` | Memory-based search | ⚡⚡ | ⭐⭐⭐⭐ |
| **Ant Colony** | `aco` | Swarm intelligence | ⚡⚡ | ⭐⭐⭐ |
| **Particle Swarm** | `pso` | Swarm optimization | ⚡⚡ | ⭐⭐⭐ |
| **Clarke-Wright** | `cw` | Heuristic cổ điển | ⚡⚡⚡⚡⚡ | ⭐⭐ |
| **Sweep** | `sweep` | Geometric heuristic | ⚡⚡⚡⚡⚡ | ⭐⭐ |
| **LNS** | `lns` | Destroy & repair | ⚡⚡ | ⭐⭐⭐⭐ |

**Khuyến nghị:**
- 🏆 **OR-Tools** - Tốt nhất cho hầu hết trường hợp
- 🔬 **MILP** - Nếu cần optimal và dataset nhỏ
- 🎲 **GA/Tabu** - Nếu cần khám phá nhiều giải pháp

## ⚙️ Cấu hình nâng cao

### 🌐 Dùng OpenRouteService thay OSRM

OSRM public API có thể bị rate limit. Nếu gặp vấn đề, dùng OpenRouteService:

1. **Đăng ký miễn phí** tại https://openrouteservice.org/dev/#/signup
2. **Lấy API key** từ dashboard
3. **Set biến môi trường:**

```bash
# Windows PowerShell
$env:ORS_API_KEY="your-api-key-here"

# Linux/Mac
export ORS_API_KEY="your-api-key-here"

# Chạy như bình thường
python scripts/run_and_visualize.py --use-osrm
# Script tự động dùng ORS thay vì OSRM!
```

**Free tier:** 2,000 requests/ngày (đủ dùng cho hầu hết trường hợp + cache)

### 🗑️ Xóa cache routing

Cache giúp tăng tốc nhưng đôi khi cần xóa (khi đổi tọa độ khách hàng):

```bash
# Windows
Remove-Item -Recurse -Force data\cache\*

# Linux/Mac
rm -rf data/cache/*
```

### 🐳 Docker Tips

```bash
# Build lại image sau khi sửa code
docker-compose build

# Xem logs
docker-compose logs -f vrp-solver

# Chạy interactive shell trong container
docker-compose run --rm vrp-solver bash

# Dọn dẹp containers/images
docker-compose down
docker system prune -a
```

## 🐛 Troubleshooting

### ❌ "No solution found"

**Nguyên nhân:** Không tìm được giải pháp khả thi với các ràng buộc hiện tại.

**Giải pháp:**
```bash
# 1. Tăng thời gian tìm kiếm
python scripts/run_and_visualize.py --time_limit 300

# 2. Tăng số xe
python scripts/run_and_visualize.py --max_vehicles 30

# 3. Giảm capacity (buộc dùng nhiều xe hơn)
python scripts/run_and_visualize.py --vehicle_capacity 150

# 4. Kiểm tra time windows trong CSV
# Đảm bảo: ready_time < due_date
# và các time window không quá chặt
```

---

### ❌ "OSRM timeout" / "Rate limit exceeded"

**Nguyên nhân:** OSRM public API bị quá tải hoặc rate limit.

**Giải pháp:**
```bash
# Cách 1: Chạy lại (cache sẽ giúp bỏ qua các đoạn đã tính)
python scripts/run_and_visualize.py --use-osrm

# Cách 2: Dùng OpenRouteService
$env:ORS_API_KEY="your-api-key"
python scripts/run_and_visualize.py --use-osrm

# Cách 3: Chạy không có --use-osrm (dùng đường thẳng)
python scripts/run_and_visualize.py
```

---

### ❌ Map không hiển thị / tọa độ sai

**Kiểm tra:**
```bash
# 1. Xem file CSV có đúng format không
cat data/input/khach_hang_mau.csv

# 2. Kiểm tra tọa độ
# Việt Nam: lat (8-23), lon (102-110)
# Sai: lat=105, lon=10 (bị đảo ngược!)

# 3. Mở DevTools trong browser
# Press F12 → Console tab → xem error
```

---

### ❌ "ModuleNotFoundError: No module named 'ortools'"

**Nguyên nhân:** Chưa cài dependencies hoặc chưa activate venv.

**Giải pháp:**
```bash
# 1. Activate venv
.\.venv\Scripts\Activate.ps1  # Windows
source .venv/bin/activate     # Linux/Mac

# 2. Kiểm tra có (venv) ở đầu dòng không
# (.venv) PS D:\...\code>

# 3. Cài lại dependencies
pip install -r requirements.txt
```

---

### ❌ Docker: "Cannot connect to Docker daemon"

**Giải pháp:**
```bash
# Mở Docker Desktop và đợi khởi động xong
# Kiểm tra:
docker version

# Nếu vẫn lỗi, restart Docker Desktop
```

---

### ❌ Chạy chậm / Timeout

**Tối ưu:**
```bash
# 1. Giảm time_limit (chấp nhận giải không tối ưu)
python scripts/run_and_visualize.py --time_limit 30

# 2. Dùng thuật toán nhanh hơn
python scripts/run_and_visualize.py --algorithm cw  # Clarke-Wright rất nhanh

# 3. Giảm số khách hàng trong CSV
```

---

### ❌ "Permission denied" khi chạy script

**Windows:**
```powershell
# Cho phép chạy script
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Linux/Mac:**
```bash
chmod +x scripts/run_and_visualize.py
```

## 📚 Tài liệu tham khảo

- 📖 [OR-Tools Documentation](https://developers.google.com/optimization/routing)
- 🗺️ [OSRM API Docs](http://project-osrm.org/docs/v5.24.0/api/)
- 🌐 [OpenRouteService API](https://openrouteservice.org/dev/#/api-docs)
- 📘 [VRP Wikipedia](https://en.wikipedia.org/wiki/Vehicle_routing_problem)
- 📊 [Solomon Benchmarks](https://www.sintef.no/projectweb/top/vrptw/solomon-benchmark/)

## 🤝 Đóng góp

Contributions, issues và feature requests đều được chào đón!

1. Fork repository
2. Tạo branch mới (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Mở Pull Request

## 📝 License

Dự án này được phân phối dưới giấy phép MIT License. Xem file `LICENSE` để biết thêm chi tiết.

## 👤 Tác giả



- 🌐 GitHub: [@]()
- 📧 Email: [your.email@example.com]()

## ⭐ Show your support

Nếu dự án này hữu ích, hãy cho nó một ⭐ trên GitHub!

---

<div align="center">
  <p>Made with ❤️ and ☕</p>
  <p>© 2025 VRP Solver Project</p>
</div>
