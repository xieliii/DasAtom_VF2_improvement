#!/usr/bin/env python3
"""
7类可扩展通用电路的全面基准测试
测试算法随量子比特数增加的扩展性（5-50 qubits）

电路类型：
1. QFT (Quantum Fourier Transform): 量子傅里叶变换，全连接图结构
2. Quantum Volume (QV): 量子体积，几乎全连接
3. Two-local random: 随机电路，全连接
4. 3-regular MaxCut QAOA: 3-正则图结构
5. Deutsch-Jozsa (DJ): 星型拓扑结构
6. GHZ: 线性拓扑结构
7. W-state: 线性拓扑结构
"""

import os
import json
import time
import math
import pandas as pd
from datetime import datetime
from DasAtom_fun import *
from Enola.route import QuantumRouter

# ============================================================================
# 测试配置
# ============================================================================

# 电路配置
CIRCUITS_CONFIG = {
    "QFT": {
        "path": "Data/qiskit-bench/qft",
        "filename_pattern": "qft_{n}.qasm",
        "qubit_sizes": [5, 10, 15, 20, 25, 30, 35, 40, 45, 50],
        "topology": "全连接图",
        "description": "量子傅里叶变换，交互最密集"
    },
    "Quantum_Volume": {
        "path": "Data/qiskit-bench/quantum_volume",
        "filename_pattern": "quantum_volume_{n}.qasm",
        "qubit_sizes": [5, 10, 15, 20, 25, 30, 35, 40, 45, 50],
        "topology": "几乎全连接",
        "description": "综合性能测试电路"
    },
    "Two_Local_Random": {
        "path": "Data/mqt-bench/two_local_random",
        "filename_pattern": "twolocalrandom_indep_qiskit_{n}.qasm",
        "qubit_sizes": [5, 10, 15, 20, 25, 30, 35, 40, 45, 50],
        "topology": "全连接",
        "description": "随机电路"
    },
    "3_Regular": {
        "path": "Data/3_regular_graph",
        "filename_pattern": "3_regular_{n}.qasm",
        "qubit_sizes": [10, 12, 14, 16, 18, 20, 22, 30, 40, 50],
        "topology": "3-正则图",
        "description": "MaxCut QAOA电路"
    },
    "Deutsch_Jozsa": {
        "path": "Data/mqt-bench/DJ",
        "filename_pattern": "dj_indep_qiskit_{n}.qasm",
        "qubit_sizes": [5, 10, 15, 20, 25, 30, 35, 40, 45, 50],
        "topology": "星型拓扑",
        "description": "Deutsch-Jozsa算法"
    },
    "GHZ": {
        "path": "Data/mqt-bench/GHZ",
        "filename_pattern": "ghz_indep_qiskit_{n}.qasm",
        "qubit_sizes": [5, 10, 15, 20, 25, 30, 35, 40, 45, 50],
        "topology": "线性拓扑",
        "description": "GHZ态制备"
    },
    "W_State": {
        "path": "Data/mqt-bench/Wstate",
        "filename_pattern": "wstate_indep_qiskit_{n}.qasm",
        "qubit_sizes": [5, 10, 15, 20, 25, 30, 35, 40, 45, 50],
        "topology": "线性拓扑",
        "description": "W态制备"
    }
}

# 硬件参数
INTERACTION_RADIUS = 2
EXTENDED_RADIUS = 2 * INTERACTION_RADIUS

# ============================================================================
# 核心测试函数
# ============================================================================

def test_single_circuit(circuit_file, circuit_path, interaction_radius, verbose=False):
    """
    测试单个电路
    
    返回:
        dict: 包含所有测试指标的结果字典，失败则返回None
    """
    try:
        start_time = time.time()
        
        # 步骤 1: 加载电路
        qasm_circuit = CreateCircuitFromQASM(circuit_file, circuit_path)
        
        # 步骤 2: 提取双量子比特门
        two_qubit_gates_list = get_2q_gates_list(qasm_circuit)
        if len(two_qubit_gates_list) == 0:
            if verbose:
                print(f"  ⚠️  {circuit_file}: 没有双量子比特门，跳过")
            return None
        
        qc_object, dag_object = gates_list_to_QC(two_qubit_gates_list)
        num_qubits = get_qubits_num(two_qubit_gates_list)
        
        # 步骤 3: 获取 DAG 层次结构
        gate_layer_list = get_layer_gates(dag_object)
        
        # 步骤 4: 构建硬件拓扑图
        grid_size = math.ceil(math.sqrt(num_qubits))
        coupling_graph = generate_grid_with_Rb(grid_size, grid_size, interaction_radius)
        
        # 步骤 5: 贪心分区
        partitioned_gates = partition_from_DAG(dag_object, coupling_graph)
        
        # 步骤 6: VF2 子图同构嵌入
        embeddings, extended_positions = get_embeddings(
            partitioned_gates,
            coupling_graph,
            num_qubits,
            grid_size,
            interaction_radius
        )
        
        # 步骤 7: 并行门分组
        extended_radius = 2 * interaction_radius
        all_parallel_gates = []
        merged_parallel_gates = []
        
        for i in range(len(partitioned_gates)):
            parallel_gates_i = get_parallel_gates(
                partitioned_gates[i],
                coupling_graph,
                embeddings[i],
                extended_radius
            )
            all_parallel_gates.append(parallel_gates_i)
            merged_parallel_gates.extend(parallel_gates_i)
        
        # 步骤 8: 原子穿梭（量子比特移动）
        router = QuantumRouter(
            num_qubits,
            embeddings,
            partitioned_gates,
            [grid_size, grid_size]
        )
        router.run()
        movements_list = router.movement_list
        
        # 步骤 9: 保真度计算
        para = set_parameters()
        (t_idle, fidelity, move_fidelity, total_runtime, 
         num_transfers, num_moves, total_move_distance) = compute_fidelity(
            merged_parallel_gates,
            movements_list,
            num_qubits,
            len(two_qubit_gates_list),
            para
        )
        
        execution_time = time.time() - start_time
        
        # 收集结果
        result = {
            "circuit_name": circuit_file,
            "num_qubits": num_qubits,
            "num_2q_gates": len(two_qubit_gates_list),
            "original_depth": qc_object.depth(),
            "num_dag_layers": len(gate_layer_list),
            "num_partitions": len(partitioned_gates),
            "num_parallel_groups": len(merged_parallel_gates),
            "num_movements": len(movements_list),
            "num_extended": len(extended_positions),
            "grid_size": f"{grid_size}x{grid_size}",
            "hardware_nodes": len(coupling_graph.nodes()),
            "hardware_edges": len(coupling_graph.edges()),
            "fidelity": fidelity,
            "move_fidelity": move_fidelity,
            "total_runtime_us": total_runtime,
            "idle_time_us": t_idle,
            "num_transfers": num_transfers,
            "num_atom_moves": num_moves,
            "total_move_distance_um": total_move_distance,
            "execution_time_s": execution_time,
            "success": True
        }
        
        if verbose:
            print(f"  ✓ {circuit_file}: {num_qubits} qubits, {len(two_qubit_gates_list)} gates, "
                  f"F={fidelity:.6f}, time={execution_time:.2f}s")
        
        return result
        
    except Exception as e:
        if verbose:
            print(f"  ✗ {circuit_file}: 失败 - {str(e)}")
        return {
            "circuit_name": circuit_file,
            "success": False,
            "error": str(e)
        }

def test_circuit_family(family_name, config, interaction_radius, verbose=True):
    """
    测试一个电路家族的所有规模
    
    参数:
        family_name: 电路家族名称
        config: 电路配置字典
        interaction_radius: 交互半径
        verbose: 是否输出详细信息
    
    返回:
        list: 测试结果列表
    """
    print(f"\n{'='*100}")
    print(f"📊 测试电路家族: {family_name}")
    print(f"{'='*100}")
    print(f"  拓扑结构: {config['topology']}")
    print(f"  描述: {config['description']}")
    print(f"  测试规模: {config['qubit_sizes']}")
    print(f"  交互半径: {interaction_radius}")
    print(f"{'='*100}\n")
    
    results = []
    circuit_path = config['path']
    
    for n in config['qubit_sizes']:
        circuit_file = config['filename_pattern'].format(n=n)
        full_path = os.path.join(circuit_path, circuit_file)
        
        # 检查文件是否存在
        if not os.path.exists(full_path):
            if verbose:
                print(f"  ⚠️  {circuit_file}: 文件不存在，跳过")
            continue
        
        # 测试电路
        result = test_single_circuit(circuit_file, circuit_path, interaction_radius, verbose)
        
        if result is not None:
            result['family'] = family_name
            result['topology'] = config['topology']
            result['target_qubits'] = n
            results.append(result)
    
    # 打印统计
    successful = sum(1 for r in results if r.get('success', False))
    print(f"\n  📈 {family_name} 完成: {successful}/{len(config['qubit_sizes'])} 个电路测试成功")
    
    return results

# ============================================================================
# 结果分析和报告
# ============================================================================

def generate_summary_report(all_results, output_file="scalable_circuits_summary.xlsx"):
    """
    生成汇总报告（Excel格式）
    """
    print(f"\n{'='*100}")
    print("📊 生成汇总报告")
    print(f"{'='*100}\n")
    
    # 转换为 DataFrame
    df = pd.DataFrame(all_results)
    
    # 只保留成功的测试
    df_success = df[df['success'] == True].copy()
    
    if len(df_success) == 0:
        print("  ⚠️  没有成功的测试结果")
        return
    
    # 按电路家族分组统计
    print("按电路家族统计:")
    print("-" * 100)
    for family in df_success['family'].unique():
        family_df = df_success[df_success['family'] == family]
        print(f"\n{family} ({family_df['topology'].iloc[0]}):")
        print(f"  测试数量: {len(family_df)}")
        print(f"  量子比特范围: {family_df['num_qubits'].min()} - {family_df['num_qubits'].max()}")
        print(f"  平均保真度: {family_df['fidelity'].mean():.6f}")
        print(f"  最低保真度: {family_df['fidelity'].min():.6f} (@ {family_df.loc[family_df['fidelity'].idxmin(), 'num_qubits']} qubits)")
        print(f"  平均运行时间: {family_df['total_runtime_us'].mean():.2f} μs")
        print(f"  平均执行时间: {family_df['execution_time_s'].mean():.2f} s")
    
    # 创建 Excel 写入器
    with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
        # 1. 总览表
        summary_cols = [
            'family', 'circuit_name', 'topology', 'num_qubits', 'num_2q_gates',
            'fidelity', 'total_runtime_us', 'num_partitions', 'num_parallel_groups',
            'num_atom_moves', 'execution_time_s'
        ]
        df_summary = df_success[summary_cols].copy()
        df_summary = df_summary.sort_values(['family', 'num_qubits'])
        df_summary.to_excel(writer, sheet_name='Summary', index=False)
        
        # 2. 按电路家族分表
        for family in df_success['family'].unique():
            family_df = df_success[df_success['family'] == family].copy()
            family_df = family_df.sort_values('num_qubits')
            
            # 选择关键列
            detail_cols = [
                'circuit_name', 'num_qubits', 'num_2q_gates', 'original_depth',
                'num_partitions', 'num_parallel_groups', 'grid_size',
                'fidelity', 'move_fidelity', 'total_runtime_us', 'idle_time_us',
                'num_transfers', 'num_atom_moves', 'total_move_distance_um',
                'execution_time_s'
            ]
            family_df[detail_cols].to_excel(writer, sheet_name=family[:31], index=False)
        
        # 3. 对比分析表（相同量子比特数的不同电路）
        comparison_data = []
        common_sizes = set(df_success['num_qubits'])
        
        for n in sorted(common_sizes):
            size_df = df_success[df_success['num_qubits'] == n]
            for _, row in size_df.iterrows():
                comparison_data.append({
                    'Qubits': n,
                    'Family': row['family'],
                    'Topology': row['topology'],
                    '2Q_Gates': row['num_2q_gates'],
                    'Depth': row['original_depth'],
                    'Partitions': row['num_partitions'],
                    'Parallel_Groups': row['num_parallel_groups'],
                    'Fidelity': row['fidelity'],
                    'Runtime_us': row['total_runtime_us'],
                    'Atom_Moves': row['num_atom_moves']
                })
        
        df_comparison = pd.DataFrame(comparison_data)
        df_comparison = df_comparison.sort_values(['Qubits', 'Family'])
        df_comparison.to_excel(writer, sheet_name='Comparison', index=False)
        
        # 4. 可扩展性分析（每个家族的增长趋势）
        scalability_data = []
        for family in df_success['family'].unique():
            family_df = df_success[df_success['family'] == family].sort_values('num_qubits')
            for _, row in family_df.iterrows():
                scalability_data.append({
                    'Family': family,
                    'Qubits': row['num_qubits'],
                    'Fidelity': row['fidelity'],
                    'Runtime_us': row['total_runtime_us'],
                    'Gates': row['num_2q_gates'],
                    'Partitions': row['num_partitions'],
                    'Parallel_Groups': row['num_parallel_groups'],
                    'Atom_Moves': row['num_atom_moves'],
                    'Fidelity_per_Gate': row['fidelity'] / row['num_2q_gates'] if row['num_2q_gates'] > 0 else 0,
                    'Runtime_per_Gate_ns': (row['total_runtime_us'] * 1000) / row['num_2q_gates'] if row['num_2q_gates'] > 0 else 0
                })
        
        df_scalability = pd.DataFrame(scalability_data)
        df_scalability.to_excel(writer, sheet_name='Scalability', index=False)
    
    print(f"\n✓ 汇总报告已保存到: {output_file}")
    
    # 打印关键统计
    print(f"\n{'='*100}")
    print("🎯 关键统计指标")
    print(f"{'='*100}\n")
    
    print(f"总测试数: {len(df_success)}")
    print(f"电路家族数: {df_success['family'].nunique()}")
    print(f"量子比特范围: {df_success['num_qubits'].min()} - {df_success['num_qubits'].max()}")
    print(f"\n保真度统计:")
    print(f"  平均: {df_success['fidelity'].mean():.6f}")
    print(f"  最高: {df_success['fidelity'].max():.6f}")
    print(f"  最低: {df_success['fidelity'].min():.6f}")
    print(f"  标准差: {df_success['fidelity'].std():.6f}")
    
    print(f"\n运行时间统计 (μs):")
    print(f"  平均: {df_success['total_runtime_us'].mean():.2f}")
    print(f"  最短: {df_success['total_runtime_us'].min():.2f}")
    print(f"  最长: {df_success['total_runtime_us'].max():.2f}")

def save_detailed_json(all_results, output_file="scalable_circuits_detailed_results.json"):
    """
    保存详细的 JSON 结果
    """
    output_data = {
        "test_info": {
            "test_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "interaction_radius": INTERACTION_RADIUS,
            "extended_radius": EXTENDED_RADIUS,
            "total_tests": len(all_results),
            "successful_tests": sum(1 for r in all_results if r.get('success', False))
        },
        "circuit_families": {
            name: {
                "topology": config["topology"],
                "description": config["description"],
                "qubit_sizes": config["qubit_sizes"]
            }
            for name, config in CIRCUITS_CONFIG.items()
        },
        "results": all_results
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"✓ 详细结果已保存到: {output_file}")

# ============================================================================
# 主测试流程
# ============================================================================

def main():
    print("=" * 100)
    print("🚀 7类可扩展通用电路基准测试")
    print("=" * 100)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"交互半径: {INTERACTION_RADIUS}")
    print(f"扩展半径: {EXTENDED_RADIUS}")
    print(f"电路家族数: {len(CIRCUITS_CONFIG)}")
    print("=" * 100)
    
    # 测试所有电路家族
    all_results = []
    
    for family_name, config in CIRCUITS_CONFIG.items():
        family_results = test_circuit_family(
            family_name,
            config,
            INTERACTION_RADIUS,
            verbose=True
        )
        all_results.extend(family_results)
    
    # 生成报告
    print(f"\n{'='*100}")
    print("📊 测试完成，生成报告...")
    print(f"{'='*100}\n")
    
    if len(all_results) > 0:
        # 保存详细 JSON 结果
        save_detailed_json(all_results)
        
        # 生成 Excel 汇总报告
        generate_summary_report(all_results)
    else:
        print("⚠️  没有测试结果")
    
    print(f"\n{'='*100}")
    print("✅ 所有测试完成！")
    print(f"{'='*100}\n")

if __name__ == "__main__":
    main()

