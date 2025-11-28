#!/usr/bin/env python3
"""
关键电路测试 - 验证改进算法的效果

重点测试高分区数电路，这些电路最能体现"惯性优化"的效果：
- square_root_7: 229 个分区 (最高)
- adr4_197: 109 个分区
- radd_250: 96 个分区
- z4_268: 83 个分区
- sym6_145: 49 个分区
- qv_16_15: 25 个分区 (随机拓扑)
- QFT_30: QFT 电路 (论文核心案例)
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
    # 👑 终极测试 (Boss Level)
    {
        "name": "square_root_7",
        "file": "square_root_7.qasm",
        "path": "Data/Q_Tetris",
        "priority": "⭐⭐⭐⭐⭐",
        "expected_partitions": 229,
        "description": "终极测试 - 最高分区数，优化空间最大"
    },
    {
        "name": "adr4_197",
        "file": "adr4_197.qasm",
        "path": "Data/Q_Tetris",
        "priority": "⭐⭐⭐⭐⭐",
        "expected_partitions": 109,
        "description": "终极测试 - 极高收益"
    },
    
    # 🚀 重点测试 (High Priority)
    {
        "name": "radd_250",
        "file": "radd_250.qasm",
        "path": "Data/Q_Tetris",
        "priority": "⭐⭐⭐⭐",
        "expected_partitions": 96,
        "description": "重点测试 - 算术类电路代表"
    },
    {
        "name": "z4_268",
        "file": "z4_268.qasm",
        "path": "Data/Q_Tetris",
        "priority": "⭐⭐⭐⭐",
        "expected_partitions": 83,
        "description": "重点测试 - 重度移动场景"
    },
    {
        "name": "sym6_145",
        "file": "sym6_145.qasm",
        "path": "Data/Q_Tetris",
        "priority": "⭐⭐⭐",
        "expected_partitions": 49,
        "description": "重点测试 - 中等规模代表"
    },
    
    # 🧪 结构化测试 (Topology Benchmarks)
    {
        "name": "QFT_30",
        "file": "qft_30.qasm",
        "path": "Data/qiskit-bench/qft",
        "priority": "⭐⭐⭐⭐⭐",
        "expected_partitions": "N/A",
        "description": "拓扑测试 - 论文核心案例，关注保真度提升"
    },
    {
        "name": "QV_16",
        "file": "quantum_volume_16.qasm",
        "path": "Data/qiskit-bench/quantum_volume",
        "priority": "⭐⭐⭐",
        "expected_partitions": 25,
        "description": "拓扑测试 - 随机拓扑代表"
    }
]

INTERACTION_RADIUS = 2

# ============================================================================
# 测试函数
# ============================================================================

def test_circuit_detailed(circuit_config, Rb=2):
    """
    详细测试单个电路
    
    返回完整的测试指标，包括：
    - 基本信息：量子比特数、门数、深度
    - 分区信息：分区数、每个分区的大小
    - 嵌入信息：硬件图大小、扩展次数
    - 移动信息：移动次数、移动距离
    - 保真度指标：总保真度、移动保真度
    - 性能指标：运行时间
    """
    
    name = circuit_config['name']
    file = circuit_config['file']
    path = circuit_config['path']
    
    print(f"\n{'='*90}")
    print(f"🔬 测试电路: {name} {circuit_config['priority']}")
    print(f"{'='*90}")
    print(f"  文件: {file}")
    print(f"  描述: {circuit_config['description']}")
    print(f"  预期分区数: {circuit_config['expected_partitions']}")
    print(f"{'='*90}\n")
    
    try:
        start_time = time.time()
        
        # ===== 步骤 1: 加载电路 =====
        print("📥 步骤 1: 加载 QASM 电路...", end=" ", flush=True)
        step_start = time.time()
        qasm_circuit = CreateCircuitFromQASM(file, path)
        print(f"✓ ({time.time()-step_start:.2f}s)")
        
        # ===== 步骤 2: 提取双量子比特门 =====
        print("🔍 步骤 2: 提取双量子比特门...", end=" ", flush=True)
        step_start = time.time()
        two_qubit_gates = get_2q_gates_list(qasm_circuit)
        
        if len(two_qubit_gates) == 0:
            print("✗ 无双量子比特门")
            return None
        
        qc, dag = gates_list_to_QC(two_qubit_gates)
        num_qubits = get_qubits_num(two_qubit_gates)
        print(f"✓ ({time.time()-step_start:.2f}s) - {len(two_qubit_gates)} 个门，{num_qubits} 个量子比特")
        
        # ===== 步骤 3: DAG 层次结构 =====
        print("📊 步骤 3: 构建 DAG 层次...", end=" ", flush=True)
        step_start = time.time()
        gate_layers = get_layer_gates(dag)
        print(f"✓ ({time.time()-step_start:.2f}s) - {len(gate_layers)} 层")
        
        # ===== 步骤 4: 硬件拓扑 =====
        print("🔷 步骤 4: 生成硬件拓扑图...", end=" ", flush=True)
        step_start = time.time()
        grid_size = math.ceil(math.sqrt(num_qubits))
        coupling_graph = generate_grid_with_Rb(grid_size, grid_size, Rb)
        print(f"✓ ({time.time()-step_start:.2f}s) - {grid_size}x{grid_size} 网格，"
              f"{len(coupling_graph.nodes())} 节点，{len(coupling_graph.edges())} 边")
        
        # ===== 步骤 5: 贪心分区 =====
        print("✂️  步骤 5: 贪心分区...", end=" ", flush=True)
        step_start = time.time()
        partitions = partition_from_DAG(dag, coupling_graph)
        partition_sizes = [len(p) for p in partitions]
        print(f"✓ ({time.time()-step_start:.2f}s) - {len(partitions)} 个分区")
        print(f"           分区大小: 平均={sum(partition_sizes)/len(partition_sizes):.1f}, "
              f"最小={min(partition_sizes)}, 最大={max(partition_sizes)}")
        
        # ===== 步骤 6: VF2 嵌入 =====
        print("🗺️  步骤 6: VF2 子图同构嵌入...", end=" ", flush=True)
        step_start = time.time()
        embeddings, extend_pos = get_embeddings(
            partitions, coupling_graph, num_qubits, grid_size, Rb
        )
        print(f"✓ ({time.time()-step_start:.2f}s) - {len(embeddings)} 个嵌入")
        if extend_pos:
            print(f"           ⚠️  硬件图扩展了 {len(extend_pos)} 次，位置: {extend_pos}")
        
        # ===== 步骤 7: 并行门分组 =====
        print("⚡ 步骤 7: 并行门分组...", end=" ", flush=True)
        step_start = time.time()
        all_parallel = []
        for i, part in enumerate(partitions):
            pg = get_parallel_gates(part, coupling_graph, embeddings[i], 2*Rb)
            all_parallel.extend(pg)
        print(f"✓ ({time.time()-step_start:.2f}s) - {len(all_parallel)} 个并行组")
        
        # ===== 步骤 8: 原子穿梭 =====
        print("🚀 步骤 8: 计算原子移动...", end=" ", flush=True)
        step_start = time.time()
        router = QuantumRouter(num_qubits, embeddings, partitions, [grid_size, grid_size])
        router.run()
        movements = router.movement_list
        
        # 统计移动信息
        total_move_steps = sum(len(m) for m in movements)
        total_atoms_moved = sum(sum(len(step) for step in m) for m in movements)
        
        print(f"✓ ({time.time()-step_start:.2f}s)")
        print(f"           移动阶段: {len(movements)} 个")
        print(f"           移动步数: {total_move_steps} 步")
        print(f"           原子移动总次数: {total_atoms_moved} 次")
        
        # ===== 步骤 9: 保真度计算 =====
        print("🎯 步骤 9: 计算保真度...", end=" ", flush=True)
        step_start = time.time()
        para = set_parameters()
        t_idle, fidelity, move_fid, t_total, n_trans, n_move, move_dist = compute_fidelity(
            all_parallel, movements, num_qubits, len(two_qubit_gates), para
        )
        print(f"✓ ({time.time()-step_start:.2f}s)")
        
        total_time = time.time() - start_time
        
        # ===== 结果汇总 =====
        print(f"\n{'='*90}")
        print(f"📊 测试结果汇总")
        print(f"{'='*90}")
        
        result = {
            # 基本信息
            "circuit_name": name,
            "file": file,
            "priority": circuit_config['priority'],
            "description": circuit_config['description'],
            "expected_partitions": circuit_config['expected_partitions'],
            
            # 电路规模
            "num_qubits": num_qubits,
            "num_2q_gates": len(two_qubit_gates),
            "circuit_depth": qc.depth(),
            "dag_layers": len(gate_layers),
            
            # 分区信息
            "num_partitions": len(partitions),
            "partition_avg_size": sum(partition_sizes) / len(partition_sizes),
            "partition_min_size": min(partition_sizes),
            "partition_max_size": max(partition_sizes),
            
            # 硬件信息
            "grid_size": f"{grid_size}x{grid_size}",
            "hardware_nodes": len(coupling_graph.nodes()),
            "hardware_edges": len(coupling_graph.edges()),
            "num_extended": len(extend_pos),
            
            # 并行化
            "num_parallel_groups": len(all_parallel),
            
            # 移动信息
            "num_movement_stages": len(movements),
            "total_move_steps": total_move_steps,
            "total_atoms_moved": total_atoms_moved,
            "avg_atoms_per_stage": total_atoms_moved / len(movements) if movements else 0,
            
            # 保真度
            "fidelity": fidelity,
            "move_fidelity": move_fid,
            
            # 时间
            "total_runtime_us": t_total,
            "idle_time_us": t_idle,
            
            # 物理操作
            "num_transfers": n_trans,
            "num_atom_moves": n_move,
            "total_move_distance_um": move_dist,
            
            # 性能
            "execution_time_s": total_time,
            
            "success": True
        }
        
        # 打印关键指标
        print(f"  🔢 电路规模: {num_qubits} 量子比特, {len(two_qubit_gates)} 个门")
        print(f"  ✂️  分区数量: {len(partitions)} (预期: {circuit_config['expected_partitions']})")
        print(f"  🚀 移动阶段: {len(movements)} 个，{total_move_steps} 步，{total_atoms_moved} 次原子移动")
        print(f"  🎯 总保真度: {fidelity:.8f}")
        print(f"  🎯 移动保真度: {move_fid:.8f}")
        print(f"  ⏱️  总运行时间: {t_total:.2f} μs")
        print(f"  ⏱️  执行时间: {total_time:.2f} s")
        print(f"{'='*90}\n")
        
        return result
        
    except Exception as e:
        print(f"\n✗ 失败: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            "circuit_name": name,
            "file": file,
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }

# ============================================================================
# 结果分析
# ============================================================================

def save_results(results, filename="key_circuits_results.json"):
    """保存结果到JSON"""
    output = {
        "test_info": {
            "test_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "interaction_radius": INTERACTION_RADIUS,
            "description": "关键电路测试 - 验证改进算法效果",
            "circuits_tested": len(results),
            "successful": sum(1 for r in results if r.get('success', False))
        },
        "results": results
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"✓ 详细结果已保存到: {filename}")

def print_comparison_table(results):
    """打印对比表格"""
    successful = [r for r in results if r.get('success', False)]
    
    if not successful:
        print("\n⚠️  没有成功的测试结果")
        return
    
    print(f"\n{'='*120}")
    print(f"📊 关键电路测试对比表")
    print(f"{'='*120}\n")
    
    # 表头
    print(f"{'电路名称':<20} {'优先级':<8} {'量子比特':<8} {'门数':<8} {'分区数':<8} "
          f"{'移动阶段':<8} {'保真度':<12} {'运行时间(μs)':<12}")
    print("-" * 120)
    
    # 按分区数排序
    for r in sorted(successful, key=lambda x: x['num_partitions'], reverse=True):
        print(f"{r['circuit_name']:<20} {r['priority']:<8} {r['num_qubits']:<8} "
              f"{r['num_2q_gates']:<8} {r['num_partitions']:<8} "
              f"{r['num_movement_stages']:<8} {r['fidelity']:<12.6f} {r['total_runtime_us']:<12.2f}")
    
    print("\n" + "="*120)
    
    # 统计信息
    print(f"\n📈 统计摘要:")
    print(f"  测试成功: {len(successful)}/{len(results)}")
    print(f"  平均保真度: {sum(r['fidelity'] for r in successful)/len(successful):.6f}")
    print(f"  最高保真度: {max(r['fidelity'] for r in successful):.6f} ({max(successful, key=lambda x: x['fidelity'])['circuit_name']})")
    print(f"  最低保真度: {min(r['fidelity'] for r in successful):.6f} ({min(successful, key=lambda x: x['fidelity'])['circuit_name']})")
    print(f"  平均分区数: {sum(r['num_partitions'] for r in successful)/len(successful):.1f}")
    print(f"  平均移动阶段: {sum(r['num_movement_stages'] for r in successful)/len(successful):.1f}")
    
    # 重点指标：移动效率
    print(f"\n🚀 移动效率分析:")
    for r in sorted(successful, key=lambda x: x['num_partitions'], reverse=True):
        move_per_partition = r['total_atoms_moved'] / r['num_partitions'] if r['num_partitions'] > 0 else 0
        print(f"  {r['circuit_name']:<20} 分区数={r['num_partitions']:>3}, "
              f"移动阶段={r['num_movement_stages']:>3}, "
              f"原子移动={r['total_atoms_moved']:>4}, "
              f"平均移动/分区={move_per_partition:.2f}")

# ============================================================================
# 主程序
# ============================================================================

def main():
    print("="*120)
    print("🎯 关键电路测试 - 验证改进算法效果")
    print("="*120)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"交互半径: {INTERACTION_RADIUS}")
    print(f"测试电路数: {len(KEY_CIRCUITS)}")
    print("="*120)
    
    results = []
    
    # 逐个测试关键电路
    for i, circuit_config in enumerate(KEY_CIRCUITS, 1):
        print(f"\n[{i}/{len(KEY_CIRCUITS)}] 开始测试...")
        
        result = test_circuit_detailed(circuit_config, INTERACTION_RADIUS)
        if result:
            results.append(result)
            
            # 每个电路测试后保存中间结果
            save_results(results, "key_circuits_results_temp.json")
    
    # 最终结果
    save_results(results, "key_circuits_results.json")
    
    # 打印对比表
    print_comparison_table(results)
    
    print(f"\n{'='*120}")
    print("✅ 所有关键电路测试完成！")
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*120)

if __name__ == "__main__":
    main()

