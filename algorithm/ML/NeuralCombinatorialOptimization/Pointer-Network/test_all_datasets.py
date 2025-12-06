"""
Test Pointer Network on all VRPTW datasets
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from pointer_network_vrptw_solver import PointerNetworkVRPTWSolver


def test_all_datasets():
    """Test Pointer Network on all Solomon datasets"""
    
    # Setup paths
    base_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'dataset')
    model_path = os.path.join(os.path.dirname(__file__), 'models', 'pointer_network_best.pth')
    
    # Check if model exists
    if not os.path.exists(model_path):
        print(f"Error: Model not found at {model_path}")
        print("Please train the model first using train.py")
        return
    
    # Create output directories
    result_dir = os.path.join(os.path.dirname(__file__), 'result')
    images_dir = os.path.join(result_dir, 'images')
    text_dir = os.path.join(result_dir, 'text')
    
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(text_dir, exist_ok=True)
    
    # Dataset categories
    categories = {
        'C1': ['C101', 'C102', 'C103', 'C104', 'C105', 'C106', 'C107', 'C108', 'C109'],
        'C2': ['C201', 'C202', 'C203', 'C204', 'C205', 'C206', 'C207', 'C208'],
        'R1': ['R101', 'R102', 'R103', 'R104', 'R105', 'R106', 'R107', 'R108', 'R109', 'R110', 'R111', 'R112'],
        'R2': ['R201', 'R202', 'R203', 'R204', 'R205', 'R206', 'R207', 'R208', 'R209', 'R210', 'R211'],
        'RC1': ['RC101', 'RC102', 'RC103', 'RC104', 'RC105', 'RC106', 'RC107', 'RC108'],
        'RC2': ['RC201', 'RC202', 'RC203', 'RC204', 'RC205', 'RC206', 'RC207', 'RC208']
    }
    
    # Create solver
    print("="*80)
    print("TESTING POINTER NETWORK ON ALL VRPTW DATASETS")
    print("="*80)
    print(f"Model: {model_path}")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")
    
    solver = PointerNetworkVRPTWSolver(model_path)
    
    # Results storage
    results = []
    
    # Test each dataset
    total_datasets = sum(len(datasets) for datasets in categories.values())
    current_dataset = 0
    
    for category, datasets in categories.items():
        print(f"\nTesting Category: {category}")
        print("-"*80)
        
        for dataset_name in datasets:
            current_dataset += 1
            dataset_path = os.path.join(base_path, category, f'{dataset_name}.csv')
            
            if not os.path.exists(dataset_path):
                print(f"  [{current_dataset}/{total_datasets}] {dataset_name}: Dataset not found, skipping...")
                continue
            
            try:
                # Solve
                routes, total_distance, comp_time = solver.solve(dataset_path)
                
                # Get number of customers
                num_customers = len(solver.customers)
                customers_served = sum(len(route) for route in routes)
                
                # Store results
                result = {
                    'Dataset': dataset_name,
                    'Category': category,
                    'Total_Distance': total_distance,
                    'Num_Vehicles': len(routes),
                    'Num_Customers': num_customers,
                    'Customers_Served': customers_served,
                    'Computation_Time': comp_time
                }
                results.append(result)
                
                # Print progress
                print(f"  [{current_dataset}/{total_datasets}] {dataset_name}: "
                      f"Distance={total_distance:.2f}, Vehicles={len(routes)}, "
                      f"Customers={customers_served}/{num_customers}, Time={comp_time:.4f}s")
                
                # Save visualization
                image_path = os.path.join(images_dir, f'{dataset_name}.png')
                solver.visualize_solution_comprehensive(routes, total_distance, image_path)
                
                # Save solution text
                text_path = os.path.join(text_dir, f'{dataset_name}.txt')
                solver.save_solution(routes, total_distance, text_path)
                
            except Exception as e:
                print(f"  [{current_dataset}/{total_datasets}] {dataset_name}: Error - {str(e)}")
                continue
    
    # Create summary
    print("\n" + "="*80)
    print("CREATING SUMMARY")
    print("="*80)
    
    if len(results) == 0:
        print("No results to summarize!")
        return
    
    # Save results to CSV
    results_df = pd.DataFrame(results)
    summary_csv_path = os.path.join(result_dir, 'test_summary.csv')
    results_df.to_csv(summary_csv_path, index=False)
    print(f"Summary CSV saved to: {summary_csv_path}")
    
    # Create detailed report
    report_path = os.path.join(result_dir, 'test_report.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("BÁO CÁO KẾT QUẢ POINTER NETWORK TRÊN TẤT CẢ DATASET VRPTW\n")
        f.write("="*80 + "\n\n")
        
        f.write(f"Thời gian test: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Model: {model_path}\n")
        f.write(f"Số lượng dataset: {len(results)}\n\n")
        
        # Overall statistics
        f.write("THỐNG KÊ TỔNG QUAN:\n")
        f.write("-"*80 + "\n")
        f.write(f"Tổng khoảng cách trung bình: {results_df['Total_Distance'].mean():.2f}\n")
        f.write(f"Số xe trung bình: {results_df['Num_Vehicles'].mean():.2f}\n")
        f.write(f"Thời gian tính toán trung bình: {results_df['Computation_Time'].mean():.4f}s\n")
        f.write(f"Tỷ lệ phục vụ khách hàng: {results_df['Customers_Served'].sum()}/{results_df['Num_Customers'].sum()} "
                f"({100*results_df['Customers_Served'].sum()/results_df['Num_Customers'].sum():.2f}%)\n\n")
        
        # Statistics by category
        f.write("THỐNG KÊ THEO TỪNG LOẠI:\n")
        f.write("-"*80 + "\n\n")
        
        for category in categories.keys():
            category_df = results_df[results_df['Category'] == category]
            if len(category_df) > 0:
                f.write(f"{category}:\n")
                f.write(f"  Số dataset: {len(category_df)}\n")
                f.write(f"  Khoảng cách TB: {category_df['Total_Distance'].mean():.2f}\n")
                f.write(f"  Số xe TB: {category_df['Num_Vehicles'].mean():.2f}\n")
                f.write(f"  Thời gian TB: {category_df['Computation_Time'].mean():.4f}s\n")
                f.write(f"  Tỷ lệ phục vụ: {category_df['Customers_Served'].sum()}/{category_df['Num_Customers'].sum()} "
                        f"({100*category_df['Customers_Served'].sum()/category_df['Num_Customers'].sum():.2f}%)\n\n")
        
        # Detailed results
        f.write("KẾT QUẢ CHI TIẾT:\n")
        f.write("-"*80 + "\n\n")
        
        for _, row in results_df.iterrows():
            f.write(f"{row['Dataset']} ({row['Category']}):\n")
            f.write(f"  Khoảng cách: {row['Total_Distance']:.2f}\n")
            f.write(f"  Số xe: {row['Num_Vehicles']}\n")
            f.write(f"  Khách hàng: {row['Customers_Served']}/{row['Num_Customers']}\n")
            f.write(f"  Thời gian: {row['Computation_Time']:.4f}s\n\n")
    
    print(f"Detailed report saved to: {report_path}")
    
    # Print summary to console
    print("\n" + "="*80)
    print("OVERALL STATISTICS")
    print("="*80)
    print(f"Total datasets tested: {len(results)}")
    print(f"Average distance: {results_df['Total_Distance'].mean():.2f}")
    print(f"Average vehicles: {results_df['Num_Vehicles'].mean():.2f}")
    print(f"Average computation time: {results_df['Computation_Time'].mean():.4f}s")
    print(f"Customer service rate: {results_df['Customers_Served'].sum()}/{results_df['Num_Customers'].sum()} "
          f"({100*results_df['Customers_Served'].sum()/results_df['Num_Customers'].sum():.2f}%)")
    print("="*80)
    
    print(f"\nTesting completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == '__main__':
    test_all_datasets()
