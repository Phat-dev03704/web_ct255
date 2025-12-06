"""
Test OR-Tools solver trên tất cả các datasets
"""

import sys
from pathlib import Path
import pandas as pd
import time

sys.path.insert(0, str(Path(__file__).parent))
from ortools_vrptw_solver import ORToolsVRPTWSolver


def test_all_datasets(time_limit_per_dataset=60):
    """Test trên tất cả datasets"""
    
    dataset_base = Path(__file__).parent.parent.parent / 'dataset'
    categories = ['C1', 'C2', 'R1', 'R2', 'RC1', 'RC2']
    all_results = []
    
    print("\n" + "="*120)
    print("TESTING OR-TOOLS (GOOGLE OPTIMIZATION) ON ALL DATASETS")
    print("="*120)
    
    total_start_time = time.time()
    
    for category in categories:
        category_path = dataset_base / category
        
        if not category_path.exists():
            print(f"\n⚠️ Không tìm thấy thư mục: {category_path}")
            continue
        
        csv_files = sorted(list(category_path.glob('*.csv')))
        
        print(f"\n{'='*120}")
        print(f"CATEGORY: {category} - {len(csv_files)} datasets")
        print(f"{'='*120}")
        
        for csv_file in csv_files:
            dataset_name = csv_file.stem
            
            print(f"\n{'─'*120}")
            print(f"Testing: {dataset_name}")
            print(f"{'─'*120}")
            
            try:
                solver = ORToolsVRPTWSolver(
                    dataset_path=str(csv_file),
                    vehicle_capacity=200,
                    max_vehicles=30
                )
                
                solution = solver.solve(time_limit=time_limit_per_dataset)
                
                output_dir = Path(__file__).parent / 'result'
                result_data = solver.save_all_results(output_dir)
                
                all_results.append(result_data)
                
                print(f"\n✓ {dataset_name}: "
                      f"Distance={solution['total_distance']:.2f}, "
                      f"Vehicles={solution['num_vehicles']}, "
                      f"Time={solver.solve_time:.2f}s")
                
            except Exception as e:
                print(f"\n❌ Lỗi khi test {dataset_name}: {e}")
                import traceback
                traceback.print_exc()
                
                all_results.append({
                    'Dataset': dataset_name,
                    'Algorithm': 'OR-Tools',
                    'Status': 'Error',
                    'Total_Distance': None,
                    'Num_Vehicles': None,
                    'Customers_Served': None,
                    'Solve_Time_s': None,
                    'Error': str(e)
                })
    
    total_time = time.time() - total_start_time
    
    # Lưu kết quả
    if all_results:
        output_dir = Path(__file__).parent / 'result'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        df_results = pd.DataFrame(all_results)
        csv_path = output_dir / 'ortools_summary.csv'
        df_results.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        print(f"\n{'='*120}")
        print("TỔNG KẾT")
        print(f"{'='*120}")
        print(f"Tổng số datasets: {len(all_results)}")
        print(f"Thành công: {len([r for r in all_results if r.get('Status') != 'Error'])}")
        print(f"Lỗi: {len([r for r in all_results if r.get('Status') == 'Error'])}")
        print(f"Tổng thời gian: {total_time:.2f}s ({total_time/60:.2f} phút)")
        print(f"\n✓ Đã lưu summary: {csv_path}")
        
        df_success = df_results[df_results['Status'] != 'Error']
        
        if not df_success.empty:
            df_success['Category'] = df_success['Dataset'].str[:2]
            
            print(f"\n{'='*120}")
            print("THỐNG KÊ THEO CATEGORY")
            print(f"{'='*120}")
            
            summary = df_success.groupby('Category').agg({
                'Total_Distance': ['mean', 'min', 'max'],
                'Num_Vehicles': ['mean', 'min', 'max'],
                'Solve_Time_s': ['mean', 'min', 'max'],
                'Dataset': 'count'
            }).round(2)
            
            print(summary)
            
            print(f"\n{'='*120}")
            print("TOP 10 KẾT QUẢ TỐT NHẤT")
            print(f"{'='*120}")
            
            top10 = df_success.nsmallest(10, 'Total_Distance')[
                ['Dataset', 'Total_Distance', 'Num_Vehicles', 'Solve_Time_s']
            ]
            print(top10.to_string(index=False))
    
    print(f"\n{'='*120}")
    print("HOÀN THÀNH!")
    print(f"{'='*120}\n")


if __name__ == "__main__":
    test_all_datasets(time_limit_per_dataset=60)
    