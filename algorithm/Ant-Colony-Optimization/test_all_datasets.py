"""
Test Ant Colony Optimization solver với tất cả datasets Solomon
Chạy 56 datasets, tạo tổng kết và báo cáo chi tiết
"""

import sys
from pathlib import Path
import time
import pandas as pd

# Add parent directory to path
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

from aco_vrptw_solver import AntColonyVRPTWSolver


def test_all_datasets():
    """Test tất cả datasets với Ant Colony Optimization"""
    
    print("="*80)
    print("TEST ANT COLONY OPTIMIZATION VỚI TẤT CẢ DATASETS SOLOMON")
    print("="*80)
    print("📊 Tổng số datasets: 56")
    print("🐜 Phương pháp: Ant Colony Optimization (Swarm Intelligence)")
    print("✓ Tự động điều chỉnh hyperparameters theo kích thước bài toán")
    print("="*80 + "\n")
    
    # Đường dẫn đến thư mục dataset
    code_dir = current_dir.parent.parent
    dataset_base = code_dir / "dataset"
    
    # Danh sách các thư mục và files
    categories = {
        "C1": ["C101", "C102", "C103", "C104", "C105", "C106", "C107", "C108", "C109"],
        "C2": ["C201", "C202", "C203", "C204", "C205", "C206", "C207", "C208"],
        "R1": ["R101", "R102", "R103", "R104", "R105", "R106", "R107", "R108", "R109", "R110", "R111", "R112"],
        "R2": ["R201", "R202", "R203", "R204", "R205", "R206", "R207", "R208", "R209", "R210", "R211"],
        "RC1": ["RC101", "RC102", "RC103", "RC104", "RC105", "RC106", "RC107", "RC108"],
        "RC2": ["RC201", "RC202", "RC203", "RC204", "RC205", "RC206", "RC207", "RC208"]
    }
    
    # Tổng hợp kết quả
    results = []
    
    total_start_time = time.time()
    dataset_count = 0
    
    # Duyệt qua tất cả datasets
    for category, files in categories.items():
        print(f"\n{'='*80}")
        print(f"CATEGORY: {category}")
        print(f"{'='*80}")
        
        for file_name in files:
            dataset_count += 1
            dataset_path = dataset_base / category / f"{file_name}.csv"
            
            if not dataset_path.exists():
                print(f"❌ Không tìm thấy: {dataset_path}")
                continue
            
            print(f"\n[{dataset_count}/56] Đang giải: {file_name}...")
            
            try:
                # Tạo solver
                solver = AntColonyVRPTWSolver(
                    dataset_path=str(dataset_path),
                    vehicle_capacity=200,
                    max_vehicles=25
                )
                
                # Lấy hyperparameters tự động
                hyperparams = solver.get_recommended_hyperparameters()
                
                print(f"📊 Siêu tham số tự động:")
                print(f"  - Số kiến: {hyperparams['n_ants']}")
                print(f"  - Max iterations: {hyperparams['max_iterations']}")
                print(f"  - Alpha (pheromone): {hyperparams['alpha']}")
                print(f"  - Beta (heuristic): {hyperparams['beta']}")
                print(f"  - Rho (evaporation): {hyperparams['rho']}")
                
                # Giải bài toán
                start_time = time.time()
                result = solver.solve(**hyperparams)
                solve_time = time.time() - start_time
                
                if result and result['status']:
                    # Lưu kết quả
                    solver.visualize_solution(save=True)
                    solver.save_solution(
                        solve_time=result['time'],
                        status=result['status'],
                        iterations=result['iterations'],
                        improvements=result['improvements']
                    )
                    
                    # Thống kê
                    num_vehicles = len(solver.solution)
                    total_distance = sum([r['distance'] for r in solver.solution.values()])
                    total_customers = sum([r['num_customers'] for r in solver.solution.values()])
                    
                    results.append({
                        'Dataset': file_name,
                        'Category': category,
                        'Customers': solver.n_customers,
                        'Vehicles': num_vehicles,
                        'Total Distance': round(total_distance, 2),
                        'Avg Distance/Vehicle': round(total_distance/num_vehicles, 2),
                        'Customers Served': total_customers,
                        'Solve Time (s)': round(solve_time, 2),
                        'Iterations': result['iterations'],
                        'Improvements': result['improvements'],
                        'Status': 'Success'
                    })
                    
                    print(f"✓ Hoàn thành: {num_vehicles} xe, {total_distance:.2f} km, {solve_time:.2f}s")
                else:
                    results.append({
                        'Dataset': file_name,
                        'Category': category,
                        'Customers': solver.n_customers,
                        'Status': 'Failed'
                    })
                    print(f"❌ Không tìm được solution")
                    
            except Exception as e:
                print(f"❌ Lỗi khi giải {file_name}: {str(e)}")
                results.append({
                    'Dataset': file_name,
                    'Category': category,
                    'Status': f'Error: {str(e)}'
                })
    
    total_time = time.time() - total_start_time
    
    # Tạo DataFrame
    df_results = pd.DataFrame(results)
    
    # Lưu tổng kết
    output_dir = current_dir / 'result'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    summary_path = output_dir / 'test_summary.csv'
    df_results.to_csv(summary_path, index=False, encoding='utf-8-sig')
    print(f"\n✓ Đã lưu tổng kết: {summary_path}")
    
    # In báo cáo
    print(f"\n{'='*80}")
    print("TỔNG KẾT KẾT QUẢ")
    print(f"{'='*80}")
    print(f"Tổng số datasets: {len(results)}")
    print(f"Thành công: {len([r for r in results if r['Status'] == 'Success'])}")
    print(f"Thất bại: {len([r for r in results if r['Status'] != 'Success'])}")
    print(f"Tổng thời gian: {total_time/60:.2f} phút")
    
    # Thống kê theo category
    success_results = [r for r in results if r['Status'] == 'Success']
    if success_results:
        df_success = pd.DataFrame(success_results)
        
        print(f"\n{'='*80}")
        print("THỐNG KÊ THEO CATEGORY")
        print(f"{'='*80}")
        
        for category in categories.keys():
            cat_data = df_success[df_success['Category'] == category]
            if len(cat_data) > 0:
                print(f"\n{category}:")
                print(f"  Số datasets: {len(cat_data)}")
                print(f"  Trung bình số xe: {cat_data['Vehicles'].mean():.2f}")
                print(f"  Trung bình quãng đường: {cat_data['Total Distance'].mean():.2f}")
                print(f"  Trung bình thời gian: {cat_data['Solve Time (s)'].mean():.2f}s")
                print(f"  Trung bình iterations: {cat_data['Iterations'].mean():.0f}")
        
        print(f"\n{'='*80}")
        print("TOP 5 KẾT QUẢ TỐT NHẤT (Quãng đường ngắn nhất)")
        print(f"{'='*80}")
        top5_best = df_success.nsmallest(5, 'Total Distance')[['Dataset', 'Vehicles', 'Total Distance', 'Solve Time (s)']]
        print(top5_best.to_string(index=False))
        
        print(f"\n{'='*80}")
        print("TOP 5 GIẢI NHANH NHẤT")
        print(f"{'='*80}")
        top5_fastest = df_success.nsmallest(5, 'Solve Time (s)')[['Dataset', 'Vehicles', 'Total Distance', 'Solve Time (s)']]
        print(top5_fastest.to_string(index=False))
    
    # Lưu báo cáo chi tiết
    report_path = output_dir / 'test_report.txt'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("BÁO CÁO TEST ANT COLONY OPTIMIZATION - TẤT CẢ DATASETS\n")
        f.write("="*80 + "\n\n")
        
        f.write(f"Thời gian test: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Tổng số datasets: {len(results)}\n")
        f.write(f"Thành công: {len([r for r in results if r['Status'] == 'Success'])}\n")
        f.write(f"Thất bại: {len([r for r in results if r['Status'] != 'Success'])}\n")
        f.write(f"Tổng thời gian: {total_time/60:.2f} phút\n\n")
        
        f.write("="*80 + "\n")
        f.write("PHƯƠNG PHÁP: ANT COLONY OPTIMIZATION\n")
        f.write("="*80 + "\n")
        f.write("Đặc điểm:\n")
        f.write("  - Metaheuristic mô phỏng hành vi tìm đường của đàn kiến\n")
        f.write("  - Pheromone trails: Vết mùi chỉ đường cho các kiến sau\n")
        f.write("  - Heuristic: Thông tin về khoảng cách (visibility = 1/distance)\n")
        f.write("  - Xác suất chọn: P = (pheromone^alpha) * (heuristic^beta) / sum\n")
        f.write("  - Evaporation: Pheromone bay hơi theo thời gian (rho)\n")
        f.write("  - Reinforcement: Best solutions deposit nhiều pheromone\n")
        f.write("  - Local search: 2-opt để cải thiện mỗi ant solution\n")
        f.write("  - Tự động điều chỉnh hyperparameters theo kích thước bài toán\n\n")
        
        f.write("Hyperparameters:\n")
        f.write("  - Số kiến: 20-40 (tùy kích thước)\n")
        f.write("  - Max iterations: 100-200 (tùy kích thước)\n")
        f.write("  - Alpha (pheromone influence): 1.0\n")
        f.write("  - Beta (heuristic influence): 3.0\n")
        f.write("  - Rho (evaporation rate): 0.2\n")
        f.write("  - Rho local (local evaporation): 0.1\n")
        f.write("  - Q (deposit constant): 1.0\n")
        f.write("  - Local search: 2-opt enabled\n\n")
        
        if success_results:
            f.write("="*80 + "\n")
            f.write("THỐNG KÊ THEO CATEGORY\n")
            f.write("="*80 + "\n\n")
            
            for category in categories.keys():
                cat_data = df_success[df_success['Category'] == category]
                if len(cat_data) > 0:
                    f.write(f"{category}:\n")
                    f.write(f"  Số datasets: {len(cat_data)}\n")
                    f.write(f"  Trung bình số xe: {cat_data['Vehicles'].mean():.2f}\n")
                    f.write(f"  Trung bình quãng đường: {cat_data['Total Distance'].mean():.2f}\n")
                    f.write(f"  Trung bình thời gian: {cat_data['Solve Time (s)'].mean():.2f}s\n")
                    f.write(f"  Trung bình iterations: {cat_data['Iterations'].mean():.0f}\n\n")
            
            f.write("="*80 + "\n")
            f.write("CHI TIẾT TẤT CẢ KẾT QUẢ\n")
            f.write("="*80 + "\n\n")
            f.write(df_success.to_string(index=False))
    
    print(f"✓ Đã lưu báo cáo chi tiết: {report_path}")
    print(f"\n{'='*80}")
    print("HOÀN THÀNH TEST TẤT CẢ DATASETS")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    test_all_datasets()
