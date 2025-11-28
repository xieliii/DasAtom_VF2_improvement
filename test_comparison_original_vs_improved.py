#!/usr/bin/env python3
"""
对比测试：原始 DasAtom vs 改进后的 DasAtom
测试关键电路，对比优化效果
"""

import os
import json
import time
import math
from datetime import datetime
from DasAtom_fun import *
from Enola.route import QuantumRouter

# ============================================================================
# 关键电路配置
# ============================================================================

KEY_CIRCUITS = [
    {
        "name": "square_root_7",
        "file": "square_root_7.qasm",
        "path": "Data/Q_Tetris",
    },
    {
        "name": "adr4_197",
        "file": "adr4_197.qasm",
        "path": "Data/Q_Tetris",
    },
    {
        "name": "radd_250",
        "file": "radd_250.qasm",
        "path": "Data/Q_Tetris",
    },
    {
        "name": "z4_268",
        "file": "z4_268.qasm",
        "path": "Data/Q_Tetris",
    },
    {
        "name": "sym6_145",
        "file": "sym6_145.qasm",
        "path": "Data/Q_Tetris",
    },
    {
        "name": "QFT_30",
        "file": "qft_30.qasm",
        "path": "Data/qiskit-bench/qft",
    }
]

INTERACTION_RADIUS = 2

# ============================================================================
# 原始算法版本（不使用惯性优化）
# ============================================================================

def get_embeddings_original(partition_gates, coupling_graph, num_q, arch_size, Rb):
    """
    原始版本的嵌入函数 - 不使用惯性优化
    每次都随机选择VF2的第一个解
    """
    embeddings = []
    extend_position = []
    
    for i in range(len(partition_gates)):
        tmp_graph = nx.Graph()
        tmp_graph.add_edges_from(partition_gates[i])
        
        # 检查是否需要扩展硬件图
        if not rx_is_subgraph_iso(coupling_graph, tmp_graph):
            coupling_graph = extend_graph(coupling_graph, arch_size, Rb)
            extend_position.append(i)
        
        # 原始方法：直接使用第一个VF2解（不优化移动）
        next_embedding = get_rx_one_mapping(tmp_graph, coupling_graph)
        next_embedding = map2list(next_embedding, num_q)
        embeddings.append(next_embedding)
    
    # 补齐未参与的量子比特映射
    for i in range(len(embeddings)):
        indices = [idx for idx, val in enumerate(embeddings[i]) if val == -1]
        if indices:
            embeddings[i] = complete_mapping(i, embeddings, indices, coupling_graph)
    
    return embeddings, extend_position

# ============================================================================
# 测试函数
# ============================================================================

def test_circuit_both_versions(circuit_config, Rb=2):
    """测试电路的原始版本和改进版本"""
    
    name = circuit_config['name']
    file = circuit_config['file']
    path = circuit_config['path']
    
    print(f"\n{'='*80}")
    print(f"🔬 测试电路: {name}")
    print(f"{'='*80}")
    
    try:
        # ===== 共同的前期准备 =====
        qasm_circuit = CreateCircuitFromQASM(file, path)
        two_qubit_gates = get_2q_gates_list(qasm_circuit)
        
        if len(two_qubit_gates) == 0:
            print("无双量子比特门，跳过")
            return None
        
        qc, dag = gates_list_to_QC(two_qubit_gates)
        num_qubits = get_qubits_num(two_qubit_gates)
        gate_layers = get_layer_gates(dag)
        grid_size = math.ceil(math.sqrt(num_qubits))
        coupling_graph = generate_grid_with_Rb(grid_size, grid_size, Rb)
        partitions = partition_from_DAG(dag, coupling_graph)
        
        print(f"  电路规模: {num_qubits} 量子比特, {len(two_qubit_gates)} 个门, {len(partitions)} 个分区")
        
        # ===== 测试原始版本 =====
        print(f"\n  🔵 测试原始算法...", end=" ", flush=True)
        start_time = time.time()
        
        # 使用原始嵌入方法
        coupling_graph_orig = generate_grid_with_Rb(grid_size, grid_size, Rb)
        embeddings_orig, extend_pos_orig = get_embeddings_original(
            partitions, coupling_graph_orig, num_qubits, grid_size, Rb
        )
        
        # 并行门分组
        all_parallel_orig = []
        for i, part in enumerate(partitions):
            pg = get_parallel_gates(part, coupling_graph_orig, embeddings_orig[i], 2*Rb)
            all_parallel_orig.extend(pg)
        
        # 移动
        router_orig = QuantumRouter(num_qubits, embeddings_orig, partitions, [grid_size, grid_size])
        router_orig.run()
        movements_orig = router_orig.movement_list
        
        # 保真度
        para = set_parameters()
        t_idle_orig, fidelity_orig, move_fid_orig, t_total_orig, n_trans_orig, n_move_orig, move_dist_orig = compute_fidelity(
            all_parallel_orig, movements_orig, num_qubits, len(two_qubit_gates), para
        )
        
        time_orig = time.time() - start_time
        total_atoms_moved_orig = sum(sum(len(step) for step in move_step) for move_step in movements_orig)
        
        print(f"✓ ({time_orig:.2f}s, F={fidelity_orig:.6f})")
        
        # ===== 测试改进版本 =====
        print(f"  🟢 测试改进算法...", end=" ", flush=True)
        start_time = time.time()
        
        # 使用改进的嵌入方法（带惯性优化）
        coupling_graph_new = generate_grid_with_Rb(grid_size, grid_size, Rb)
        embeddings_new, extend_pos_new = get_embeddings(
            partitions, coupling_graph_new, num_qubits, grid_size, Rb,
            optimize_movement=True  # 启用移动优化
        )
        
        # 并行门分组
        all_parallel_new = []
        for i, part in enumerate(partitions):
            pg = get_parallel_gates(part, coupling_graph_new, embeddings_new[i], 2*Rb)
            all_parallel_new.extend(pg)
        
        # 移动
        router_new = QuantumRouter(num_qubits, embeddings_new, partitions, [grid_size, grid_size])
        router_new.run()
        movements_new = router_new.movement_list
        
        # 保真度
        t_idle_new, fidelity_new, move_fid_new, t_total_new, n_trans_new, n_move_new, move_dist_new = compute_fidelity(
            all_parallel_new, movements_new, num_qubits, len(two_qubit_gates), para
        )
        
        time_new = time.time() - start_time
        total_atoms_moved_new = sum(sum(len(step) for step in move_step) for move_step in movements_new)
        
        print(f"✓ ({time_new:.2f}s, F={fidelity_new:.6f})")
        
        # ===== 对比结果 =====
        result = {
            "circuit_name": name,
            "num_qubits": num_qubits,
            "num_2q_gates": len(two_qubit_gates),
            "num_partitions": len(partitions),
            
            # 原始版本
            "original": {
                "fidelity": fidelity_orig,
                "move_fidelity": move_fid_orig,
                "total_runtime_us": t_total_orig,
                "idle_time_us": t_idle_orig,
                "num_movement_stages": len(movements_orig),
                "total_atoms_moved": total_atoms_moved_orig,
                "total_move_distance_um": move_dist_orig,
                "num_transfers": n_trans_orig,
                "execution_time_s": time_orig
            },
            
            # 改进版本
            "improved": {
                "fidelity": fidelity_new,
                "move_fidelity": move_fid_new,
                "total_runtime_us": t_total_new,
                "idle_time_us": t_idle_new,
                "num_movement_stages": len(movements_new),
                "total_atoms_moved": total_atoms_moved_new,
                "total_move_distance_um": move_dist_new,
                "num_transfers": n_trans_new,
                "execution_time_s": time_new
            },
            
            # 改进幅度
            "improvement": {
                "fidelity_gain": (fidelity_new - fidelity_orig) / fidelity_orig * 100 if fidelity_orig > 0 else 0,
                "move_distance_reduction": (move_dist_orig - move_dist_new) / move_dist_orig * 100 if move_dist_orig > 0 else 0,
                "atoms_moved_reduction": (total_atoms_moved_orig - total_atoms_moved_new) / total_atoms_moved_orig * 100 if total_atoms_moved_orig > 0 else 0,
                "runtime_reduction": (t_total_orig - t_total_new) / t_total_orig * 100 if t_total_orig > 0 else 0
            },
            
            "success": True
        }
        
        # 打印对比
        print(f"\n  📊 对比结果:")
        print(f"     原始算法 → 改进算法")
        print(f"     保真度:   {fidelity_orig:.6e} → {fidelity_new:.6e} ({result['improvement']['fidelity_gain']:+.1f}%)")
        print(f"     移动距离: {move_dist_orig:.1f} → {move_dist_new:.1f} μm ({result['improvement']['move_distance_reduction']:+.1f}%)")
        print(f"     原子移动: {total_atoms_moved_orig} → {total_atoms_moved_new} 次 ({result['improvement']['atoms_moved_reduction']:+.1f}%)")
        
        return result
        
    except Exception as e:
        print(f"✗ 失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "circuit_name": name,
            "success": False,
            "error": str(e)
        }

# ============================================================================
# 主程序
# ============================================================================

def main():
    print("=" * 80)
    print("🔬 DasAtom 算法对比测试：原始 vs 改进")
    print("=" * 80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    all_results = []
    
    for i, circuit_config in enumerate(KEY_CIRCUITS, 1):
        print(f"\n[{i}/{len(KEY_CIRCUITS)}]")
        result = test_circuit_both_versions(circuit_config, INTERACTION_RADIUS)
        if result and result.get('success', False):
            all_results.append(result)
    
    # 保存结果
    output = {
        "test_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "description": "原始DasAtom vs 改进DasAtom对比测试",
        "results": all_results
    }
    
    with open('comparison_results.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*80}")
    print(f"✅ 对比测试完成！结果已保存到: comparison_results.json")
    print(f"成功测试: {len(all_results)}/{len(KEY_CIRCUITS)}")
    print("=" * 80)

if __name__ == "__main__":
    main()

