"""
Test Local Search Algorithm trên tất cả 56 datasets Solomon VRPTW
"""

import sys
from pathlib import Path
import pandas as pd
import time
import matplotlib
matplotlib.use('Agg')  # Sử dụng backend không cần GUI

# Import solver
from ls_vrptw_solver import LocalSearchVRPTWSolver


def test_all_datasets():
    """Test Local Search solver trên tất cả 56 datasets"""
    
    print("="*100)
    print("TEST LOCAL SEARCH / NEIGHBORHOOD SEARCH ALGORITHM TRÊN TẤT CẢ DATASETS")
    print("="*100)
    print("Thuật toán: Local Search (Improvement Heuristic)")
    print("Phép biến đổi: 2-opt, Relocate, Exchange, Cross")
    print("Ưu điểm: Cải thiện solution liên tục, chất lượng tốt")
    print("Tốc độ dự kiến: 10-30 giây/dataset (tùy số vòng lặp)")
    print("="*100)
    
    # Lấy đường dẫn đến thư mục dataset
    current_dir = Path(__file__).parent
    code_dir = current_dir.parent.parent
    dataset_dir = code_dir / "dataset"
    
    # Kiểm tra thư mục dataset có tồn tại không
    if not dataset_dir.exists():
        print(f"❌ Không tìm thấy thư mục dataset: {dataset_dir}")
        return
    
    print(f"✓ Tìm thấy thư mục dataset: {dataset_dir}\n")
    
    # Danh sách các thư mục con và files
    categories = ['C1', 'C2', 'R1', 'R2', 'RC1', 'RC2']
    
    # Thu thập tất cả file CSV
    all_datasets = []
    for category in categories:
        category_path = dataset_dir / category
        if category_path.exists():
            csv_files = sorted(category_path.glob('*.csv'))
            for csv_file in csv_files:
                all_datasets.append({
                    'category': category,
                    'filename': csv_file.name,
                    'path': csv_file
                })
    
    print(f"✓ Tìm thấy {len(all_datasets)} datasets để test\n")
    
    # Hiển thị danh sách
    for category in categories:
        category_datasets = [d for d in all_datasets if d['category'] == category]
        if category_datasets:
            print(f"  {category}: {len(category_datasets)} files")
    
    print("\n" + "="*100)
    print("BẮT ĐẦU TESTING")
    print("="*100 + "\n")
    
    # Danh sách kết quả
    results = []
    
    # Test từng dataset
    for idx, dataset_info in enumerate(all_datasets, 1):
        print(f"\n{'─'*100}")
        print(f"[{idx}/{len(all_datasets)}] Testing: {dataset_info['category']}/{dataset_info['filename']}")
        print(f"{'─'*100}")
        
        try:
            # Tạo solver
            solver = LocalSearchVRPTWSolver(
                dataset_path=str(dataset_info['path']),
                vehicle_capacity=200,
                max_vehicles=25
            )
            
            # Giải bài toán với time limit 60s
            result = solver.solve(time_limit=60, max_iterations=1000)
            
            # Vẽ và lưu solution
            solver.visualize_solution(save=True)
            solver.save_solution(
                solve_time=result['time'],
                status=result['status'],
                iterations=result['iterations'],
                improvements=result['improvements']
            )
            
            # Lưu kết quả
            results.append({
                'Dataset': dataset_info['filename'].replace('.csv', ''),
                'Category': dataset_info['category'],
                'Status': result['status'],
                'Vehicles': len(result['routes']),
                'Total Distance': f"{result['objective']:.2f}",
                'Solve Time (s)': f"{result['time']:.2f}",
                'Iterations': result['iterations'],
                'Improvements': result['improvements'],
                'Customers': solver.n_customers,
                'Customers Served': sum([r['num_customers'] for r in result['routes'].values()])
            })
            
            print(f"✓ Thành công!")
            print(f"  - Số xe: {len(result['routes'])}")
            print(f"  - Tổng quãng đường: {result['objective']:.2f}")
            print(f"  - Thời gian: {result['time']:.2f}s")
            print(f"  - Vòng lặp: {result['iterations']}")
            print(f"  - Số lần cải thiện: {result['improvements']}")
            
        except Exception as e:
            print(f"❌ Lỗi: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                'Dataset': dataset_info['filename'].replace('.csv', ''),
                'Category': dataset_info['category'],
                'Status': f'Error: {str(e)[:50]}',
                'Vehicles': 'N/A',
                'Total Distance': 'N/A',
                'Solve Time (s)': 'N/A',
                'Iterations': 'N/A',
                'Improvements': 'N/A',
                'Customers': 'N/A',
                'Customers Served': 'N/A'
            })
    
    # Tạo DataFrame kết quả
    df_results = pd.DataFrame(results)
    
    # Lưu ra file CSV
    output_csv = current_dir / 'test_summary.csv'
    df_results.to_csv(str(output_csv), index=False, encoding='utf-8-sig')
    print(f"\n✓ Đã lưu tổng hợp kết quả: {output_csv}")
    
    # Tạo báo cáo chi tiết
    report_path = current_dir / 'test_report.txt'
    with open(str(report_path), 'w', encoding='utf-8') as f:
        f.write("="*100 + "\n")
        f.write("BÁO CÁO TEST LOCAL SEARCH ALGORITHM TRÊN TẤT CẢ DATASETS\n")
        f.write("="*100 + "\n\n")
        f.write(f"Thời gian test: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Tổng số datasets: {len(all_datasets)}\n")
        f.write(f"Thuật toán: Local Search / Neighborhood Search\n")
        f.write(f"Time limit: 60 giây/dataset\n")
        f.write(f"Max iterations: 1000\n\n")
        
        # Thống kê theo category
        f.write("="*100 + "\n")
        f.write("THỐNG KÊ THEO CATEGORY\n")
        f.write("="*100 + "\n\n")
        
        for category in categories:
            category_results = [r for r in results if r['Category'] == category]
            if category_results:
                f.write(f"\n{category}:\n")
                f.write(f"  Số datasets: {len(category_results)}\n")
                
                # Tính trung bình (chỉ với các kết quả thành công)
                successful = [r for r in category_results if 'Error' not in r['Status']]
                if successful:
                    avg_vehicles = sum([int(r['Vehicles']) for r in successful]) / len(successful)
                    avg_distance = sum([float(r['Total Distance']) for r in successful]) / len(successful)
                    avg_time = sum([float(r['Solve Time (s)']) for r in successful]) / len(successful)
                    avg_iterations = sum([int(r['Iterations']) for r in successful]) / len(successful)
                    avg_improvements = sum([int(r['Improvements']) for r in successful]) / len(successful)
                    
                    f.write(f"  Thành công: {len(successful)}/{len(category_results)}\n")
                    f.write(f"  Trung bình số xe: {avg_vehicles:.1f}\n")
                    f.write(f"  Trung bình quãng đường: {avg_distance:.2f}\n")
                    f.write(f"  Trung bình thời gian: {avg_time:.2f}s\n")
                    f.write(f"  Trung bình vòng lặp: {avg_iterations:.0f}\n")
                    f.write(f"  Trung bình số lần cải thiện: {avg_improvements:.1f}\n")
        
        # Chi tiết từng dataset
        f.write("\n" + "="*100 + "\n")
        f.write("CHI TIẾT TỪNG DATASET\n")
        f.write("="*100 + "\n\n")
        
        f.write(df_results.to_string(index=False))
        f.write("\n\n")
        
        f.write("="*100 + "\n")
        f.write("KẾT THÚC BÁO CÁO\n")
        f.write("="*100 + "\n")
    
    print(f"✓ Đã lưu báo cáo chi tiết: {report_path}")
    
    # In tổng kết
    print("\n" + "="*100)
    print("TỔNG KẾT")
    print("="*100)
    
    successful_count = len([r for r in results if 'Error' not in r['Status']])
    print(f"Tổng số datasets test: {len(all_datasets)}")
    print(f"Thành công: {successful_count}")
    print(f"Thất bại: {len(all_datasets) - successful_count}")
    
    if successful_count > 0:
        successful_results = [r for r in results if 'Error' not in r['Status']]
        avg_vehicles = sum([int(r['Vehicles']) for r in successful_results]) / len(successful_results)
        avg_distance = sum([float(r['Total Distance']) for r in successful_results]) / len(successful_results)
        avg_time = sum([float(r['Solve Time (s)']) for r in successful_results]) / len(successful_results)
        avg_iterations = sum([int(r['Iterations']) for r in successful_results]) / len(successful_results)
        avg_improvements = sum([int(r['Improvements']) for r in successful_results]) / len(successful_results)
        
        print(f"\nKết quả trung bình:")
        print(f"  - Số xe: {avg_vehicles:.1f}")
        print(f"  - Quãng đường: {avg_distance:.2f}")
        print(f"  - Thời gian: {avg_time:.2f}s")
        print(f"  - Vòng lặp: {avg_iterations:.0f}")
        print(f"  - Số lần cải thiện: {avg_improvements:.1f}")
    
    print("\n" + "="*100)
    print("HOÀN THÀNH!")
    print("="*100)


if __name__ == "__main__":
    test_all_datasets()
