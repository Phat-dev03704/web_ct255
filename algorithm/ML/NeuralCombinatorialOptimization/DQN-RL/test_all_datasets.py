"""
Test DQN (Deep Q-Network) Algorithm on all 56 Solomon VRPTW datasets
"""

import sys
from pathlib import Path
import pandas as pd
import time
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend

from dqn_vrptw_solver import DQNVRPTWSolver


def test_all_datasets():
    """Test solver on all Solomon datasets"""
    
    print("="*100)
    print("TEST DQN (DEEP Q-NETWORK) ALGORITHM ON ALL DATASETS")
    print("="*100)
    print("Algorithm: Deep Q-Network (Deep Reinforcement Learning)")
    print("Features: Value-based RL, Experience Replay, Double DQN, Dueling Architecture")
    print("Advantages: Learns from experience, handles complex constraints")
    print("⭐ MODEL: Pre-trained neural network for action-value estimation")
    print("Expected speed: 0.1-1 second/dataset (after training)")
    print("="*100)
    
    # Paths
    current_dir = Path(__file__).parent
    code_dir = current_dir.parent.parent.parent.parent
    dataset_dir = code_dir / "dataset"
    model_path = current_dir / "models" / "dqn_model_best.pth"
    
    # Check model exists
    if not model_path.exists():
        print(f"\n❌ Model not found at {model_path}")
        print("Please train the model first using train.py")
        return
    
    print(f"✓ Found trained model: {model_path}")
    
    # Check dataset directory
    if not dataset_dir.exists():
        print(f"❌ Dataset directory not found: {dataset_dir}")
        return
    
    print(f"✓ Found dataset directory: {dataset_dir}\n")
    
    # Create solver
    solver = DQNVRPTWSolver(model_path)
    
    # Dataset categories
    categories = ['C1', 'C2', 'R1', 'R2', 'RC1', 'RC2']
    
    # Collect all datasets
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
    
    print(f"✓ Found {len(all_datasets)} datasets to test\n")
    
    # Show dataset counts
    for category in categories:
        category_datasets = [d for d in all_datasets if d['category'] == category]
        if category_datasets:
            print(f"  {category}: {len(category_datasets)} files")
    
    print("\n" + "="*100)
    print("STARTING TESTS")
    print("="*100 + "\n")
    
    # Results storage
    results = []
    
    # Test each dataset
    for idx, dataset_info in enumerate(all_datasets, 1):
        print(f"\n{'─'*100}")
        print(f"[{idx}/{len(all_datasets)}] Testing: {dataset_info['category']}/{dataset_info['filename']}")
        print(f"{'─'*100}")
        
        try:
            # Solve
            routes, total_distance, computation_time = solver.solve(str(dataset_info['path']))
            
            # Visualize and save (will auto-save to result/images/)
            solver.visualize_solution_comprehensive(
                str(dataset_info['path']), 
                routes, 
                total_distance,
                computation_time
            )
            
            # Save solution text (will auto-save to result/text/)
            solver.save_solution(
                str(dataset_info['path']),
                routes,
                total_distance,
                computation_time
            )
            
            # Store results
            results.append({
                'Dataset': dataset_info['filename'].replace('.csv', ''),
                'Category': dataset_info['category'],
                'Status': 'Success',
                'Vehicles': len(routes),
                'Total Distance': f"{total_distance:.2f}",
                'Solve Time (s)': f"{computation_time:.3f}"
            })
            
            print(f"✓ Success!")
            print(f"  - Vehicles: {len(routes)}")
            print(f"  - Total distance: {total_distance:.2f}")
            print(f"  - Time: {computation_time:.3f}s")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                'Dataset': dataset_info['filename'].replace('.csv', ''),
                'Category': dataset_info['category'],
                'Status': f'Error: {str(e)[:50]}',
                'Vehicles': 'N/A',
                'Total Distance': 'N/A',
                'Solve Time (s)': 'N/A'
            })
    
    # Create results DataFrame
    df_results = pd.DataFrame(results)
    
    # Save summary CSV
    output_csv = current_dir / 'test_summary.csv'
    df_results.to_csv(str(output_csv), index=False, encoding='utf-8-sig')
    print(f"\n✓ Saved summary results: {output_csv}")
    
    # Generate detailed report
    report_path = current_dir / 'test_report.txt'
    with open(str(report_path), 'w', encoding='utf-8') as f:
        f.write("="*100 + "\n")
        f.write("TEST REPORT - DQN (DEEP Q-NETWORK) ALGORITHM ON ALL DATASETS\n")
        f.write("="*100 + "\n\n")
        f.write(f"Test time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total datasets: {len(all_datasets)}\n")
        f.write(f"Algorithm: Deep Q-Network (Deep Reinforcement Learning)\n")
        f.write(f"⭐ Model: Pre-trained neural network\n")
        f.write(f"Architecture: Dueling DQN with Double Q-learning\n")
        f.write(f"Experience Replay: Enabled\n")
        f.write(f"Target Network: Enabled\n\n")
        
        # Statistics by category
        f.write("="*100 + "\n")
        f.write("STATISTICS BY CATEGORY\n")
        f.write("="*100 + "\n\n")
        
        for category in categories:
            category_results = [r for r in results if r['Category'] == category]
            if category_results:
                f.write(f"\n{category}:\n")
                f.write(f"  Number of datasets: {len(category_results)}\n")
                
                # Calculate averages (only for successful results)
                successful = [r for r in category_results if r['Status'] == 'Success']
                if successful:
                    avg_vehicles = sum([int(r['Vehicles']) for r in successful]) / len(successful)
                    avg_distance = sum([float(r['Total Distance']) for r in successful]) / len(successful)
                    avg_time = sum([float(r['Solve Time (s)']) for r in successful]) / len(successful)
                    
                    f.write(f"  Success rate: {len(successful)}/{len(category_results)}\n")
                    f.write(f"  Avg vehicles: {avg_vehicles:.1f}\n")
                    f.write(f"  Avg distance: {avg_distance:.2f}\n")
                    f.write(f"  Avg time: {avg_time:.3f}s\n")
        
        # Detailed results for each dataset
        f.write("\n" + "="*100 + "\n")
        f.write("DETAILED RESULTS\n")
        f.write("="*100 + "\n\n")
        
        f.write(df_results.to_string(index=False))
        f.write("\n\n")
        
        f.write("="*100 + "\n")
        f.write("END OF REPORT\n")
        f.write("="*100 + "\n")
    
    print(f"✓ Saved detailed report: {report_path}")
    
    # Print summary
    print("\n" + "="*100)
    print("SUMMARY")
    print("="*100)
    
    successful_count = len([r for r in results if r['Status'] == 'Success'])
    print(f"Total datasets tested: {len(all_datasets)}")
    print(f"Successful: {successful_count}")
    print(f"Failed: {len(all_datasets) - successful_count}")
    
    if successful_count > 0:
        successful_results = [r for r in results if r['Status'] == 'Success']
        avg_vehicles = sum([int(r['Vehicles']) for r in successful_results]) / len(successful_results)
        avg_distance = sum([float(r['Total Distance']) for r in successful_results]) / len(successful_results)
        avg_time = sum([float(r['Solve Time (s)']) for r in successful_results]) / len(successful_results)
        
        print(f"\nAverage results:")
        print(f"  - Vehicles: {avg_vehicles:.1f}")
        print(f"  - Distance: {avg_distance:.2f}")
        print(f"  - Time: {avg_time:.3f}s")
    
    print("\n" + "="*100)
    print("COMPLETED!")
    print("="*100)


if __name__ == "__main__":
    test_all_datasets()
