"""
Script test Large Neighborhood Search trên tất cả 56 datasets Solomon
"""

import pandas as pd
from pathlib import Path
import time
from lns_vrptw_solver import LargeNeighborhoodSearchVRPTWSolver


def test_all_datasets():
    """Test LNS trên tất cả 56 datasets"""
    
    print("="*100)
    print("BATCH TEST - LARGE NEIGHBORHOOD SEARCH FOR VRPTW")
    print("="*100)
    print("✓ Sẽ test trên 56 datasets Solomon")
    print("✓ Mỗi dataset sẽ tự động tính toán siêu tham số tối ưu")
    print("✓ Thời gian dự kiến: 40-60 phút")
    print("="*100 + "\n")
    
    # Đường dẫn
    current_dir = Path(__file__).parent
    code_dir = current_dir.parent.parent
    dataset_dir = code_dir / "dataset"
    
    # Danh sách các categories
    categories = ['C1', 'C2', 'R1', 'R2', 'RC1', 'RC2']
    
    # Kết quả
    results = []
    
    total_datasets = 0
    for category in categories:
        category_path = dataset_dir / category
        if category_path.exists():
            csv_files = list(category_path.glob("*.csv"))
            total_datasets += len(csv_files)
    
    print(f"📊 Tổng số datasets tìm thấy: {total_datasets}\n")
    
    dataset_count = 0
    
    # Test từng category
    for category in categories:
        category_path = dataset_dir / category
        
        if not category_path.exists():
            print(f"⚠️ Không tìm thấy thư mục: {category}")
            continue
        
        csv_files = sorted(category_path.glob("*.csv"))
        
        if not csv_files:
            print(f"⚠️ Không có file CSV trong thư mục: {category}")
            continue
        
        print(f"\n{'='*100}")
        print(f"CATEGORY: {category} ({len(csv_files)} datasets)")
        print(f"{'='*100}\n")
        
        for csv_file in csv_files:
            dataset_count += 1
            dataset_name = csv_file.stem
            
            print(f"\n[{dataset_count}/{total_datasets}] Testing {dataset_name}...")
            print(f"{'─'*100}")
            
            try:
                # Khởi tạo solver
                solver = LargeNeighborhoodSearchVRPTWSolver(
                    dataset_path=str(csv_file),
                    vehicle_capacity=200,
                    max_vehicles=25
                )
                
                # Lấy hyperparameters tự động
                hyperparams = solver.get_recommended_hyperparameters()
                
                print(f"🔧 Siêu tham số tự động:")
                print(f"   - Max iterations: {hyperparams['max_iterations']}")
                print(f"   - Destroy size: {hyperparams['destroy_size_min']}-{hyperparams['destroy_size_max']}")
                print(f"   - Use local search: {hyperparams['use_local_search']}")
                print(f"   - Time limit: {hyperparams['time_limit']}s")
                
                # Giải
                start_time = time.time()
                result = solver.solve(**hyperparams)
                solve_time = time.time() - start_time
                
                if result:
                    # Lưu kết quả
                    results.append({
                        'Category': category,
                        'Dataset': dataset_name,
                        'Status': 'Feasible',
                        'Vehicles': len(solver.solution),
                        'Total_Distance': result['objective'],
                        'Solve_Time': solve_time,
                        'Iterations': result['iterations'],
                        'Improvements': result['improvements'],
                        'Max_Iterations': hyperparams['max_iterations'],
                        'Destroy_Size': f"{hyperparams['destroy_size_min']}-{hyperparams['destroy_size_max']}"
                    })
                    
                    # Tạo visualization và report
                    solver.visualize_solution(save=True)
                    solver.save_solution(
                        solve_time=solve_time,
                        status=result['status'],
                        iterations=result['iterations'],
                        improvements=result['improvements'],
                        operator_stats=result.get('operator_stats')
                    )
                    
                    print(f"✓ {dataset_name}: {result['objective']:.2f} ({len(solver.solution)} xe, {solve_time:.2f}s)")
                else:
                    results.append({
                        'Category': category,
                        'Dataset': dataset_name,
                        'Status': 'Failed',
                        'Vehicles': 0,
                        'Total_Distance': None,
                        'Solve_Time': solve_time,
                        'Iterations': 0,
                        'Improvements': 0,
                        'Max_Iterations': hyperparams['max_iterations'],
                        'Destroy_Size': f"{hyperparams['destroy_size_min']}-{hyperparams['destroy_size_max']}"
                    })
                    print(f"❌ {dataset_name}: Failed")
            
            except Exception as e:
                print(f"❌ Lỗi khi test {dataset_name}: {e}")
                results.append({
                    'Category': category,
                    'Dataset': dataset_name,
                    'Status': f'Error: {str(e)[:50]}',
                    'Vehicles': 0,
                    'Total_Distance': None,
                    'Solve_Time': 0,
                    'Iterations': 0,
                    'Improvements': 0,
                    'Max_Iterations': 0,
                    'Destroy_Size': 'N/A'
                })
    
    # Lưu kết quả vào CSV
    print(f"\n{'='*100}")
    print("LƯU KẾT QUẢ")
    print(f"{'='*100}\n")
    
    results_df = pd.DataFrame(results)
    
    output_dir = current_dir / 'result'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    csv_path = output_dir / 'test_summary.csv'
    results_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"✓ Đã lưu bảng tổng hợp: {csv_path}")
    
    # In báo cáo tổng hợp
    report_path = output_dir / 'test_report.txt'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("="*100 + "\n")
        f.write("BÁO CÁO TỔNG HỢP - LARGE NEIGHBORHOOD SEARCH FOR VRPTW\n")
        f.write("="*100 + "\n\n")
        
        f.write(f"Tổng số datasets: {len(results)}\n")
        f.write(f"Thành công: {len([r for r in results if r['Status'] == 'Feasible'])}\n")
        f.write(f"Thất bại: {len([r for r in results if r['Status'] != 'Feasible'])}\n\n")
        
        # Thống kê theo category
        f.write("="*100 + "\n")
        f.write("THỐNG KÊ THEO CATEGORY\n")
        f.write("="*100 + "\n\n")
        
        for category in categories:
            category_results = [r for r in results if r['Category'] == category and r['Status'] == 'Feasible']
            
            if category_results:
                f.write(f"\n{category}:\n")
                f.write(f"  Số datasets: {len(category_results)}\n")
                
                avg_distance = sum([r['Total_Distance'] for r in category_results]) / len(category_results)
                avg_vehicles = sum([r['Vehicles'] for r in category_results]) / len(category_results)
                avg_time = sum([r['Solve_Time'] for r in category_results]) / len(category_results)
                avg_iterations = sum([r['Iterations'] for r in category_results]) / len(category_results)
                avg_improvements = sum([r['Improvements'] for r in category_results]) / len(category_results)
                
                f.write(f"  Trung bình quãng đường: {avg_distance:.2f}\n")
                f.write(f"  Trung bình số xe: {avg_vehicles:.2f}\n")
                f.write(f"  Trung bình thời gian: {avg_time:.2f}s\n")
                f.write(f"  Trung bình iterations: {avg_iterations:.1f}\n")
                f.write(f"  Trung bình improvements: {avg_improvements:.1f}\n")
        
        # Chi tiết từng dataset
        f.write("\n\n" + "="*100 + "\n")
        f.write("CHI TIẾT TỪNG DATASET\n")
        f.write("="*100 + "\n\n")
        
        for result in results:
            f.write(f"{result['Dataset']}:\n")
            f.write(f"  Category: {result['Category']}\n")
            f.write(f"  Status: {result['Status']}\n")
            
            if result['Status'] == 'Feasible':
                f.write(f"  Số xe: {result['Vehicles']}\n")
                f.write(f"  Tổng quãng đường: {result['Total_Distance']:.2f}\n")
                f.write(f"  Thời gian: {result['Solve_Time']:.2f}s\n")
                f.write(f"  Iterations: {result['Iterations']}\n")
                f.write(f"  Improvements: {result['Improvements']}\n")
                f.write(f"  Hyperparameters: max_iter={result['Max_Iterations']}, destroy={result['Destroy_Size']}\n")
            
            f.write("\n")
        
        f.write("="*100 + "\n")
        f.write("KẾT THÚC BÁO CÁO\n")
        f.write("="*100 + "\n")
    
    print(f"✓ Đã lưu báo cáo: {report_path}")
    
    # In tóm tắt ra console
    print(f"\n{'='*100}")
    print("TÓM TẮT KẾT QUẢ")
    print(f"{'='*100}\n")
    
    print(f"Tổng số datasets: {len(results)}")
    print(f"Thành công: {len([r for r in results if r['Status'] == 'Feasible'])}")
    print(f"Thất bại: {len([r for r in results if r['Status'] != 'Feasible'])}")
    
    feasible_results = [r for r in results if r['Status'] == 'Feasible']
    if feasible_results:
        avg_distance = sum([r['Total_Distance'] for r in feasible_results]) / len(feasible_results)
        avg_vehicles = sum([r['Vehicles'] for r in feasible_results]) / len(feasible_results)
        avg_time = sum([r['Solve_Time'] for r in feasible_results]) / len(feasible_results)
        avg_iterations = sum([r['Iterations'] for r in feasible_results]) / len(feasible_results)
        
        print(f"\nTrung bình (các dataset thành công):")
        print(f"  - Quãng đường: {avg_distance:.2f}")
        print(f"  - Số xe: {avg_vehicles:.2f}")
        print(f"  - Thời gian: {avg_time:.2f}s")
        print(f"  - Iterations: {avg_iterations:.1f}")
    
    print(f"\n{'='*100}")
    print("✓ HOÀN THÀNH BATCH TEST!")
    print(f"{'='*100}\n")


if __name__ == "__main__":
    test_all_datasets()
