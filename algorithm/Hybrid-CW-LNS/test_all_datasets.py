"""
Test Simplified Hybrid Solver trên tất cả datasets
"""

import sys
import os
from pathlib import Path
import pandas as pd
import time
from simplified_hybrid_vrptw_solver import SimplifiedHybridVRPTWSolver
import traceback

# Thư mục dataset
BASE_DIR = Path(r"d:\My Studing\Nghiệp vụ thông minh\project\Vehicle Routing Problem\code")
DATASET_DIR = BASE_DIR / "dataset"
RESULT_DIR = BASE_DIR / "algorithm" / "Hybrid-CW-LNS" / "result"

# Tạo thư mục kết quả
RESULT_DIR.mkdir(parents=True, exist_ok=True)


def test_all_datasets(mode='balanced'):
    """
    Test solver trên tất cả datasets
    """
    print("=" * 100)
    print(f"TESTING SIMPLIFIED HYBRID VRPTW SOLVER - MODE: {mode.upper()}")
    print("=" * 100)
    
    # Danh sách categories
    categories = {
        'C1': DATASET_DIR / 'C1',
        'C2': DATASET_DIR / 'C2',
        'R1': DATASET_DIR / 'R1',
        'R2': DATASET_DIR / 'R2',
        'RC1': DATASET_DIR / 'RC1',
        'RC2': DATASET_DIR / 'RC2'
    }
    
    results = []
    
    for category_name, category_path in categories.items():
        if not category_path.exists():
            print(f"\n⚠️ Category {category_name} không tồn tại")
            continue
        
        print(f"\n{'='*100}")
        print(f"CATEGORY: {category_name}")
        print(f"{'='*100}")
        
        # Lấy tất cả file CSV
        csv_files = sorted(list(category_path.glob('*.csv')))
        
        if not csv_files:
            print(f"Không tìm thấy dataset trong {category_name}")
            continue
        
        for csv_file in csv_files:
            dataset_name = csv_file.stem
            print(f"\n{'─'*100}")
            print(f"Dataset: {dataset_name} ({category_name})")
            print(f"{'─'*100}")
            
            try:
                # Tạo solver
                solver = SimplifiedHybridVRPTWSolver(
                    dataset_path=str(csv_file),
                    mode=mode
                )
                
                # Solve
                start_time = time.time()
                solution = solver.solve(verbose=False)  # Tắt verbose để output gọn
                solve_time = time.time() - start_time
                
                # Lưu kết quả chi tiết (hình ảnh + text)
                result_data = solver.save_all_results(output_dir=str(RESULT_DIR))
                
                # Thêm category vào result data
                result_data['Category'] = category_name
                
                # Di chuyển Category lên đầu
                result_data = {'Category': result_data.pop('Category'), **result_data}
                
                results.append(result_data)
                
                print(f"✅ {dataset_name}: Success")
                print(f"   Distance: {result_data['Total_Distance']:.2f}")
                print(f"   Vehicles: {result_data['Num_Vehicles']}")
                print(f"   Time: {result_data['Solve_Time_s']:.2f}s")
                if mode != 'cw_only' and 'Improvement_Percent' in result_data:
                    print(f"   Improvement: {result_data['Improvement_Percent']:.2f}%")
                
            except Exception as e:
                print(f"❌ Error processing {dataset_name}: {str(e)}")
                traceback.print_exc()
                
                # Thêm error record
                results.append({
                    'Dataset': dataset_name,
                    'Category': category_name,
                    'Mode': mode,
                    'Status': f"Error: {str(e)}",
                    'Total_Distance': 0,
                    'Num_Vehicles': 0,
                    'Customers_Served': 0,
                    'Solve_Time_s': 0,
                    'CW_Distance': None,
                    'CW_Vehicles': None,
                    'Improvement_Percent': 0.0,
                    'Distance_Reduction': 0.0,
                    'Vehicle_Reduction': 0
                })
    
    # Lưu kết quả ra CSV
    if results:
        results_df = pd.DataFrame(results)
        
        # Sắp xếp cột
        column_order = [
            'Dataset', 'Category', 'Mode', 'Status',
            'Total_Distance', 'Num_Vehicles', 'Customers_Served', 'Solve_Time_s',
            'CW_Distance', 'CW_Vehicles', 'Improvement_Percent',
            'Distance_Reduction', 'Vehicle_Reduction'
        ]
        
        # Chỉ giữ các cột có trong dataframe
        column_order = [col for col in column_order if col in results_df.columns]
        results_df = results_df[column_order]
        
        output_csv = RESULT_DIR / f'test_summary_{mode}.csv'
        results_df.to_csv(output_csv, index=False)
        print(f"\n\n{'='*100}")
        print(f"✅ Đã lưu CSV summary: {output_csv}")
        print(f"✅ Đã lưu {len(results)} hình ảnh trong: {RESULT_DIR / 'images'}")
        print(f"✅ Đã lưu {len(results)} text reports trong: {RESULT_DIR / 'text'}")
        print(f"{'='*100}")
    
    # In summary
    print("\n" + "="*100)
    print("SUMMARY STATISTICS")
    print("="*100)
    
    if results:
        results_df = pd.DataFrame(results)
        success_df = results_df[results_df['Status'] == 'Success']
    else:
        results_df = pd.DataFrame()
        success_df = pd.DataFrame()
    
    success_count = len(success_df)
    total_count = len(results_df)
    
    print(f"\nTotal datasets: {total_count}")
    print(f"Success: {success_count} ({success_count/total_count*100:.1f}%)" if total_count > 0 else "Success: 0")
    print(f"Failed: {total_count - success_count}")
    
    if success_count > 0:
        print(f"\nAverage solve time: {success_df['Solve_Time_s'].mean():.2f}s")
        print(f"Average distance: {success_df['Total_Distance'].mean():.2f}")
        print(f"Average vehicles: {success_df['Num_Vehicles'].mean():.1f}")
        
        if mode != 'cw_only' and 'Improvement_Percent' in success_df.columns:
            avg_improvement = success_df['Improvement_Percent'].mean()
            print(f"Average improvement: {avg_improvement:.2f}%")
            print(f"Average distance reduction: {success_df['Distance_Reduction'].mean():.2f}")
            print(f"Average vehicle reduction: {success_df['Vehicle_Reduction'].mean():.1f}")
        
        # Best results per category
        print("\n" + "-"*100)
        print("BEST RESULTS PER CATEGORY:")
        print("-"*100)
        print(f"{'Cat':<6} {'Dataset':<12} {'Distance':<12} {'Vehicles':<10} {'Time (s)':<10} {'Improvement %':<15}")
        print("-"*100)
        
        for cat in ['C1', 'C2', 'R1', 'R2', 'RC1', 'RC2']:
            cat_df = success_df[success_df['Category'] == cat]
            if len(cat_df) > 0:
                best = cat_df.nsmallest(1, 'Total_Distance').iloc[0]
                imp_str = f"{best.get('Improvement_Percent', 0):.2f}%" if mode != 'cw_only' else "N/A"
                print(f"{cat:<6} {best['Dataset']:<12} {best['Total_Distance']:<12.2f} "
                      f"{best['Num_Vehicles']:<10} {best['Solve_Time_s']:<10.2f} {imp_str:<15}")
    
    return results_df


def compare_modes():
    """So sánh các modes khác nhau"""
    print("\n" + "="*100)
    print("COMPARING ALL MODES ON SAMPLE DATASETS")
    print("="*100)
    
    # Test trên một vài datasets mẫu
    sample_datasets = [
        DATASET_DIR / 'C1' / 'C101.csv',
        DATASET_DIR / 'R1' / 'R101.csv',
        DATASET_DIR / 'RC1' / 'RC101.csv',
    ]
    
    modes = ['cw_only', 'fast', 'balanced', 'quality']
    
    all_results = []
    
    for dataset_path in sample_datasets:
        if not dataset_path.exists():
            continue
        
        dataset_name = dataset_path.stem
        print(f"\n{'='*100}")
        print(f"Dataset: {dataset_name}")
        print(f"{'='*100}")
        
        for mode in modes:
            print(f"\nMode: {mode.upper()}")
            print("-" * 50)
            
            try:
                solver = SimplifiedHybridVRPTWSolver(
                    dataset_path=str(dataset_path),
                    mode=mode
                )
                
                solution = solver.solve(verbose=False)
                
                result = {
                    'Dataset': dataset_name,
                    'Mode': mode,
                    'Distance': round(solution['total_distance'], 2),
                    'Vehicles': solution['num_vehicles'],
                    'Time': round(solver.solve_time, 2),
                    'Improvement %': round(solver.improvement_percentage, 2) if mode != 'cw_only' else 0
                }
                
                all_results.append(result)
                
                print(f"Distance: {result['Distance']:.2f}")
                print(f"Vehicles: {result['Vehicles']}")
                print(f"Time: {result['Time']:.2f}s")
                if mode != 'cw_only':
                    print(f"Improvement: {result['Improvement %']:.2f}%")
                
            except Exception as e:
                print(f"Error: {str(e)}")
    
    # Summary table
    if all_results:
        print("\n" + "="*100)
        print("COMPARISON SUMMARY")
        print("="*100)
        
        df = pd.DataFrame(all_results)
        
        # Pivot table
        for dataset in df['Dataset'].unique():
            dataset_df = df[df['Dataset'] == dataset]
            print(f"\n{dataset}:")
            print(f"{'Mode':<12} {'Distance':<12} {'Vehicles':<10} {'Time (s)':<10} {'Improvement %':<15}")
            print("-" * 60)
            
            for _, row in dataset_df.iterrows():
                print(f"{row['Mode']:<12} {row['Distance']:<12.2f} {row['Vehicles']:<10} "
                      f"{row['Time']:<10.2f} {row['Improvement %']:<15.2f}")
        
        # Save comparison
        comparison_csv = RESULT_DIR / 'mode_comparison.csv'
        df.to_csv(comparison_csv, index=False)
        print(f"\n✅ Đã lưu so sánh vào: {comparison_csv}")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Simplified Hybrid VRPTW Solver')
    parser.add_argument('--mode', type=str, default='balanced',
                       choices=['cw_only', 'fast', 'balanced', 'quality'],
                       help='Chế độ chạy (default: balanced)')
    parser.add_argument('--compare', action='store_true',
                       help='So sánh các modes')
    
    args = parser.parse_args()
    
    if args.compare:
        compare_modes()
    else:
        test_all_datasets(mode=args.mode)


if __name__ == "__main__":
    # Test với mode balanced (mặc định)
    print("Starting tests with BALANCED mode...\n")
    test_all_datasets(mode='balanced')
    
    # Uncomment để so sánh các modes
    # print("\n\n")
    # compare_modes()
