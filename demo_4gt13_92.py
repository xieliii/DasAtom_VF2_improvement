#!/usr/bin/env python3
"""
DasAtom 详细流程演示脚本 - 针对 4gt13_92.qasm
展示每一步的代码、输入和输出
"""

import os
import math
import json
from DasAtom_fun import *
from Enola.route import QuantumRouter

def print_section(title, step_num):
    """打印分隔线和标题"""
    print("\n" + "=" * 100)
    print(f"📋 步骤 {step_num}: {title}")
    print("=" * 100)

def print_code(description, code_lines):
    """打印代码片段"""
    print(f"\n💻 关键代码: {description}")
    print("-" * 100)
    for line in code_lines:
        print(f"  {line}")
    print("-" * 100)

def print_input(data_dict):
    """打印输入数据"""
    print("\n📥 输入:")
    for key, value in data_dict.items():
        if isinstance(value, (list, dict)) and len(str(value)) > 200:
            print(f"  • {key}: {type(value).__name__} (长度: {len(value)})")
        else:
            print(f"  • {key}: {value}")

def print_output(data_dict):
    """打印输出数据"""
    print("\n📤 输出:")
    for key, value in data_dict.items():
        if isinstance(value, (list, dict)) and len(str(value)) > 200:
            print(f"  • {key}: {type(value).__name__} (长度: {len(value)})")
        else:
            print(f"  • {key}: {value}")

# ============================================================================
# 主程序开始
# ============================================================================
print("🔬 DasAtom 详细流程演示：4gt13_92.qasm")
print("=" * 100)

# 配置参数
qasm_file = "4gt13_92.qasm"
circuit_folder = "Data/Q_Tetris"
interaction_radius = 2
extended_radius = 2 * interaction_radius

# ============================================================================
# 步骤 1: QASM → 量子电路对象
# ============================================================================
print_section("QASM → 量子电路对象", 1)

print_code(
    "CreateCircuitFromQASM 函数",
    [
        "def CreateCircuitFromQASM(file, path):",
        "    filePath = os.path.join(path, file)",
        "    cir = qasm2.load(filePath, custom_instructions=custom)",
        "    gates_in_circuit = {op[0].name for op in cir.data}",
        "    allowed_basis_gates = {'cz', 'h', 's', 't', 'rx', 'ry', 'rz'}",
        "    if gates_in_circuit - allowed_basis_gates:",
        "        cir = transpile(cir, basis_gates=list(allowed_basis_gates))",
        "    return cir"
    ]
)

print_input({
    "file": qasm_file,
    "path": circuit_folder,
    "完整路径": os.path.join(circuit_folder, qasm_file)
})

# 执行步骤 1
qasm_circuit = CreateCircuitFromQASM(qasm_file, circuit_folder)

# 统计门类型
gate_stats = {}
for inst in qasm_circuit.data:
    gate_name = inst.operation.name
    gate_stats[gate_name] = gate_stats.get(gate_name, 0) + 1

print_output({
    "量子电路对象": "QuantumCircuit",
    "量子比特数": qasm_circuit.num_qubits,
    "总门数": len(qasm_circuit.data),
    "电路深度": qasm_circuit.depth(),
    "门类型统计": gate_stats
})

print(f"\n✓ 电路加载成功！使用了 {qasm_circuit.num_qubits} 个量子比特中的实际比特数待确定")

# ============================================================================
# 步骤 2: 提取双量子比特门列表
# ============================================================================
print_section("提取双量子比特门列表", 2)

print_code(
    "get_2q_gates_list 函数",
    [
        "def get_2q_gates_list(circ):",
        "    gate_2q_list = []",
        "    instruction = circ.data",
        "    for ins in instruction:",
        "        if ins.operation.num_qubits == 2:",
        "            gate_2q_list.append((ins.qubits[0]._index, ins.qubits[1]._index))",
        "    return gate_2q_list"
    ]
)

print_input({
    "circ": "QuantumCircuit 对象",
    "circ.data": f"包含 {len(qasm_circuit.data)} 条指令"
})

# 执行步骤 2a
two_qubit_gates_list = get_2q_gates_list(qasm_circuit)

print_output({
    "gate_2q_list": f"列表，长度 {len(two_qubit_gates_list)}",
    "前10个门": two_qubit_gates_list[:10],
    "后10个门": two_qubit_gates_list[-10:] if len(two_qubit_gates_list) > 10 else "N/A"
})

print("\n" + "-" * 100)
print_code(
    "gates_list_to_QC 函数",
    [
        "def gates_list_to_QC(gate_list):",
        "    Lqubit = get_qubits_num(gate_list)  # 获取量子比特数",
        "    circ = QuantumCircuit(Lqubit)",
        "    for two_qubit_gate in gate_list:",
        "        circ.cz(two_qubit_gate[0], two_qubit_gate[1])  # 添加CZ门",
        "    dag = circuit_to_dag(circ)  # 转换为DAG",
        "    return circ, dag"
    ]
)

print_input({
    "gate_list": f"双量子比特门列表，长度 {len(two_qubit_gates_list)}"
})

# 执行步骤 2b
qc_object, dag_object = gates_list_to_QC(two_qubit_gates_list)
num_qubits = get_qubits_num(two_qubit_gates_list)

print_output({
    "circ": "新的 QuantumCircuit（只含CZ门）",
    "dag": "DAGCircuit 对象",
    "量子比特数": qc_object.num_qubits,
    "CZ门数": len(two_qubit_gates_list),
    "新电路深度": qc_object.depth()
})

# ============================================================================
# 步骤 3: 获取 DAG 层次结构
# ============================================================================
print_section("获取 DAG 层次结构", 3)

print_code(
    "get_layer_gates 函数",
    [
        "def get_layer_gates(dag):",
        "    gate_layer_list = []",
        "    for item in dag.layers():  # 遍历DAG的每一层",
        "        gate_layer = []",
        "        for gate in item['partition']:  # 每层中的门",
        "            c0 = gate[0]._index",
        "            c1 = gate[1]._index",
        "            gate_layer.append([c0, c1])",
        "        gate_layer_list.append(gate_layer)",
        "    return gate_layer_list"
    ]
)

print_input({
    "dag": "DAGCircuit 对象",
    "dag 层数": "待计算"
})

# 执行步骤 3
gate_layer_list = get_layer_gates(dag_object)

print_output({
    "gate_layer_list": f"三维列表，层数: {len(gate_layer_list)}",
    "总门数": sum(len(layer) for layer in gate_layer_list),
})

print("\n详细的层结构（前10层）:")
for i, layer in enumerate(gate_layer_list[:10]):
    print(f"  层 {i:2d}: {layer}")
if len(gate_layer_list) > 10:
    print(f"  ... 还有 {len(gate_layer_list) - 10} 层")
    print(f"  层 {len(gate_layer_list)-1:2d}: {gate_layer_list[-1]}")

# ============================================================================
# 步骤 4: 构建硬件拓扑图
# ============================================================================
print_section("构建硬件拓扑图", 4)

print_code(
    "generate_grid_with_Rb 函数",
    [
        "def generate_grid_with_Rb(n, m, Rb):",
        "    G = nx.grid_2d_graph(n, m)  # 生成 n×m 网格",
        "    for node1 in G.nodes():",
        "        for node2 in G.nodes():",
        "            if node1 != node2:",
        "                distance = euclidean_distance(node1, node2)",
        "                if distance <= Rb:  # 在交互半径内",
        "                    G.add_edge(node1, node2)",
        "    return G",
        "",
        "def euclidean_distance(node1, node2):",
        "    x1, y1 = node1",
        "    x2, y2 = node2",
        "    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)"
    ]
)

grid_size = math.ceil(math.sqrt(num_qubits))

print_input({
    "n (行数)": grid_size,
    "m (列数)": grid_size,
    "Rb (交互半径)": interaction_radius,
    "num_qubits": num_qubits
})

# 执行步骤 4
coupling_graph = generate_grid_with_Rb(grid_size, grid_size, interaction_radius)

print_output({
    "coupling_graph": "NetworkX Graph",
    "节点数": len(coupling_graph.nodes()),
    "边数": len(coupling_graph.edges()),
    "节点列表": sorted(coupling_graph.nodes()),
})

print("\n硬件拓扑可视化 (3×3 网格, Rb=2):")
print("  节点布局:")
for i in range(grid_size):
    row_nodes = [f"({i},{j})" for j in range(grid_size)]
    print("    " + "  ".join(row_nodes))

print("\n  连接示例（前15条边）:")
edges = list(coupling_graph.edges())[:15]
for i, (n1, n2) in enumerate(edges):
    dist = euclidean_distance(n1, n2)
    print(f"    {n1} ━ {n2}  (距离: {dist:.2f})")
if len(coupling_graph.edges()) > 15:
    print(f"    ... 还有 {len(coupling_graph.edges()) - 15} 条边")

# ============================================================================
# 步骤 5: 贪心分区
# ============================================================================
print_section("贪心分区（基于子图同构）", 5)

print_code(
    "partition_from_DAG 函数（核心逻辑）",
    [
        "def partition_from_DAG(dag, coupling_graph):",
        "    gate_layer_list = get_layer_gates(dag)",
        "    partition_gates = []",
        "    last_index = 0",
        "    ",
        "    for i in range(len(gate_layer_list)):",
        "        # 贪心合并：从 last_index 到 i+1",
        "        merge_gates = sum(gate_layer_list[last_index:i+1], [])",
        "        tmp_graph = nx.Graph()",
        "        tmp_graph.add_edges_from(merge_gates)  # 构建逻辑图",
        "        ",
        "        # 检查每个连通分量是否能嵌入硬件图",
        "        connected_components = list(nx.connected_components(tmp_graph))",
        "        isIso = True",
        "        for component in connected_components:",
        "            subgraph = tmp_graph.subgraph(component)",
        "            # 路径拓扑跳过检查",
        "            if len(subgraph.edges()) == nx.diameter(subgraph):",
        "                continue",
        "            # VF2 子图同构检查",
        "            if not rx_is_subgraph_iso(coupling_graph, subgraph):",
        "                isIso = False",
        "                break",
        "        ",
        "        if not isIso:  # 无法继续合并",
        "            merge_gates = sum(gate_layer_list[last_index:i], [])",
        "            partition_gates.append(merge_gates)",
        "            last_index = i",
        "    return partition_gates"
    ]
)

print_input({
    "dag": "DAGCircuit 对象",
    "coupling_graph": f"硬件拓扑图 ({len(coupling_graph.nodes())} 节点)",
    "gate_layer_list": f"{len(gate_layer_list)} 层"
})

# 执行步骤 5
partitioned_gates = partition_from_DAG(dag_object, coupling_graph)

print_output({
    "partition_gates": f"分区列表，共 {len(partitioned_gates)} 个分区",
})

print("\n详细的分区结构:")
for i, partition in enumerate(partitioned_gates):
    print(f"\n  分区 {i}:")
    print(f"    - 门数: {len(partition)}")
    print(f"    - 门列表: {partition[:5]}" + (f" ... 还有{len(partition)-5}个" if len(partition) > 5 else ""))
    
    # 分析逻辑图
    tmp_graph = nx.Graph()
    tmp_graph.add_edges_from(partition)
    print(f"    - 逻辑图: {len(tmp_graph.nodes())} 个节点, {len(tmp_graph.edges())} 条边")
    print(f"    - 涉及量子比特: {sorted(tmp_graph.nodes())}")

# ============================================================================
# 步骤 6: VF2 子图同构嵌入
# ============================================================================
print_section("VF2 子图同构嵌入", 6)

print_code(
    "get_embeddings 函数",
    [
        "def get_embeddings(partition_gates, coupling_graph, num_q, arch_size, Rb):",
        "    embeddings = []",
        "    extend_position = []",
        "    ",
        "    for i, partition in enumerate(partition_gates):",
        "        # 1. 构建逻辑拓扑图",
        "        tmp_graph = nx.Graph()",
        "        tmp_graph.add_edges_from(partition)",
        "        ",
        "        # 2. 检查是否需要扩展硬件图",
        "        if not rx_is_subgraph_iso(coupling_graph, tmp_graph):",
        "            coupling_graph = extend_graph(coupling_graph, arch_size, Rb)",
        "            extend_position.append(i)",
        "        ",
        "        # 3. VF2 算法获取嵌入",
        "        next_embedding = get_rx_one_mapping(tmp_graph, coupling_graph)",
        "        next_embedding = map2list(next_embedding, num_q)",
        "        embeddings.append(next_embedding)",
        "    ",
        "    # 4. 补齐未参与的量子比特映射",
        "    for i in range(len(embeddings)):",
        "        indices = [idx for idx, val in enumerate(embeddings[i]) if val == -1]",
        "        if indices:",
        "            embeddings[i] = complete_mapping(i, embeddings, indices, coupling_graph)",
        "    ",
        "    return embeddings, extend_position"
    ]
)

print_input({
    "partition_gates": f"{len(partitioned_gates)} 个分区",
    "coupling_graph": f"{len(coupling_graph.nodes())} 节点",
    "num_q": num_qubits,
    "arch_size": grid_size,
    "Rb": interaction_radius
})

# 执行步骤 6
embeddings, extended_positions = get_embeddings(
    partitioned_gates,
    coupling_graph,
    num_qubits,
    grid_size,
    interaction_radius
)

print_output({
    "embeddings": f"嵌入列表，共 {len(embeddings)} 个",
    "extend_position": extended_positions if extended_positions else "无需扩展硬件图"
})

print("\n详细的嵌入映射:")
for i, embedding in enumerate(embeddings):
    print(f"\n  分区 {i} 的嵌入:")
    for logic_qubit, physical_pos in enumerate(embedding):
        print(f"    逻辑比特 {logic_qubit} → 物理位置 {physical_pos}")

# 保存嵌入到文件
with open("demo_embeddings_4gt13_92.json", "w") as f:
    # 转换为可序列化的格式
    serializable_embeddings = []
    for emb in embeddings:
        serializable_embeddings.append([list(pos) if isinstance(pos, tuple) else pos for pos in emb])
    json.dump(serializable_embeddings, f, indent=2)
print("\n✓ 嵌入数据已保存到: demo_embeddings_4gt13_92.json")

# ============================================================================
# 步骤 7: 并行门分组
# ============================================================================
print_section("并行门分组（基于扩展半径）", 7)

print_code(
    "get_parallel_gates 函数",
    [
        "def get_parallel_gates(gates, coupling_graph, mapping, r_re):",
        "    gates_list = []",
        "    _, dag = gates_list_to_QC(gates)  # 重新生成DAG",
        "    gate_layer_list = get_layer_gates(dag)",
        "    ",
        "    for items in gate_layer_list:",
        "        gates_copy = deepcopy(items)",
        "        while len(gates_copy) != 0:",
        "            parallel_gates = []",
        "            parallel_gates.append(gates_copy[0])  # 第一个门",
        "            ",
        "            for i in range(1, len(gates_copy)):",
        "                flag = True",
        "                for gate in parallel_gates:",
        "                    # 检查是否与已选门冲突",
        "                    if check_intersect_ver2(gate, gates_copy[i],",
        "                                           coupling_graph, mapping, r_re):",
        "                        continue  # 不冲突，可以并行",
        "                    else:",
        "                        flag = False",
        "                        break",
        "                if flag:",
        "                    parallel_gates.append(gates_copy[i])",
        "            ",
        "            for gate in parallel_gates:",
        "                gates_copy.remove(gate)",
        "            gates_list.append(parallel_gates)",
        "    return gates_list"
    ]
)

print_input({
    "partitioned_gates": f"{len(partitioned_gates)} 个分区",
    "embeddings": f"{len(embeddings)} 个嵌入",
    "r_re (扩展半径)": extended_radius
})

# 执行步骤 7 - 为每个分区计算并行门
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

print_output({
    "all_parallel_gates": f"每个分区的并行组列表",
    "merged_parallel_gates": f"合并后的并行组，共 {len(merged_parallel_gates)} 组"
})

print("\n详细的并行门分组:")
total_groups = 0
for i, parallel_groups in enumerate(all_parallel_gates):
    print(f"\n  分区 {i} 的并行组 (共 {len(parallel_groups)} 组):")
    for j, group in enumerate(parallel_groups[:3]):  # 只显示前3组
        print(f"    组 {j}: {group}")
    if len(parallel_groups) > 3:
        print(f"    ... 还有 {len(parallel_groups) - 3} 组")
    total_groups += len(parallel_groups)

print(f"\n  总并行组数: {total_groups}")

# ============================================================================
# 步骤 8: 原子穿梭（量子比特移动）
# ============================================================================
print_section("原子穿梭（量子比特移动）", 8)

print_code(
    "QuantumRouter 类",
    [
        "class QuantumRouter:",
        "    def __init__(self, num_qubits, embeddings, partitioned_gates, window_size):",
        "        self.num_qubits = num_qubits",
        "        self.embeddings = embeddings",
        "        self.partitioned_gates = partitioned_gates",
        "        self.window_size = window_size",
        "        self.movement_list = []",
        "    ",
        "    def run(self):",
        "        # 对每对相邻分区计算移动",
        "        for i in range(len(self.embeddings) - 1):",
        "            current_map = self.embeddings[i]",
        "            next_map = self.embeddings[i + 1]",
        "            movements = get_movements(current_map, next_map, self.window_size)",
        "            self.movement_list.append(movements)",
        "        return self.movement_list"
    ]
)

print_input({
    "num_qubits": num_qubits,
    "embeddings": f"{len(embeddings)} 个嵌入",
    "partitioned_gates": f"{len(partitioned_gates)} 个分区",
    "window_size": [grid_size, grid_size]
})

# 执行步骤 8
router = QuantumRouter(
    num_qubits,
    embeddings,
    partitioned_gates,
    [grid_size, grid_size]
)
router.run()
movements_list = router.movement_list

print_output({
    "movement_list": f"移动序列列表，共 {len(movements_list)} 个分区间移动",
    "总移动操作组数": sum(len(moves) for moves in movements_list)
})

print("\n详细的移动序列:")
total_moves = 0
for i, moves in enumerate(movements_list):
    print(f"\n  分区 {i} → 分区 {i+1} 的移动 (共 {len(moves)} 组):")
    if len(moves) == 0:
        print("    无需移动")
    else:
        for j, move_group in enumerate(moves[:2]):  # 只显示前2组
            print(f"    组 {j}: {move_group}")
        if len(moves) > 2:
            print(f"    ... 还有 {len(moves) - 2} 组")
    total_moves += len(moves)

print(f"\n  总移动组数: {total_moves}")

# ============================================================================
# 步骤 9: 保真度计算
# ============================================================================
print_section("保真度计算", 9)

print_code(
    "compute_fidelity 函数",
    [
        "def compute_fidelity(parallel_gates, all_movements, num_q, gate_num, para=None):",
        "    if para is None:",
        "        para = set_parameters()  # 获取物理参数",
        "    ",
        "    # 1. 门执行时间（并行）",
        "    t_total = len(parallel_gates) * para['T_cz']",
        "    ",
        "    # 2. 移动时间",
        "    t_move = 0",
        "    num_trans = 0",
        "    num_move = 0",
        "    all_move_dis = 0",
        "    ",
        "    for move in all_movements:",
        "        t_total += 4 * para['T_trans']  # pick/drop 4次",
        "        t_move += 4 * para['T_trans']",
        "        num_trans += 4",
        "        ",
        "        max_dis = 0",
        "        for each_move in move:",
        "            num_move += 1",
        "            x1, y1 = each_move[1]",
        "            x2, y2 = each_move[2]",
        "            dis = sqrt((abs(x2-x1)*para['AOD_width'])**2 +",
        "                      (abs(y2-y1)*para['AOD_height'])**2)",
        "            max_dis = max(max_dis, dis)",
        "        ",
        "        all_move_dis += max_dis",
        "        t_total += max_dis / para['Move_speed']",
        "        t_move += max_dis / para['Move_speed']",
        "    ",
        "    # 3. 计算保真度",
        "    t_idle = num_q * t_total - gate_num * para['T_cz']",
        "    Fidelity = exp(-t_idle/para['T_eff']) * ",
        "               (para['F_cz']**gate_num) * ",
        "               (para['F_trans']**num_trans)",
        "    move_fidelity = exp(-t_move/para['T_eff'])",
        "    ",
        "    return t_idle, Fidelity, move_fidelity, t_total, num_trans, num_move, all_move_dis"
    ]
)

# 获取物理参数
para = set_parameters()
print("\n物理参数:")
for key, value in para.items():
    print(f"  {key}: {value}")

print_input({
    "parallel_gates": f"{len(merged_parallel_gates)} 个并行组",
    "all_movements": f"{len(movements_list)} 个移动序列",
    "num_q": num_qubits,
    "gate_num": len(two_qubit_gates_list),
    "para": "物理参数字典"
})

# 执行步骤 9
(t_idle, fidelity, move_fidelity, total_runtime, 
 num_transfers, num_moves, total_move_distance) = compute_fidelity(
    merged_parallel_gates,
    movements_list,
    num_qubits,
    len(two_qubit_gates_list),
    para
)

print_output({
    "t_idle (空闲时间)": f"{t_idle:.4f} μs",
    "Fidelity (总保真度)": f"{fidelity:.10f}",
    "move_fidelity (移动保真度)": f"{move_fidelity:.10f}",
    "total_runtime (总运行时间)": f"{total_runtime:.4f} μs",
    "num_transfers (转移次数)": num_transfers,
    "num_moves (移动量子比特数)": num_moves,
    "total_move_distance (总移动距离)": f"{total_move_distance:.4f} μm"
})

# ============================================================================
# 最终结果汇总
# ============================================================================
print("\n" + "=" * 100)
print("🎯 最终结果汇总")
print("=" * 100)

results = {
    "文件名": qasm_file,
    "量子比特数": num_qubits,
    "CZ门数": len(two_qubit_gates_list),
    "原始电路深度": qc_object.depth(),
    "分区数": len(partitioned_gates),
    "并行门组数": len(merged_parallel_gates),
    "移动操作数": len(movements_list),
    "总保真度": fidelity,
    "移动保真度": move_fidelity,
    "总运行时间 (μs)": total_runtime,
    "空闲时间 (μs)": t_idle,
}

print("\n完整结果:")
for key, value in results.items():
    print(f"  • {key}: {value}")

# 保存结果
with open("demo_results_4gt13_92.json", "w") as f:
    json.dump(results, f, indent=2)

print("\n✓ 结果已保存到: demo_results_4gt13_92.json")
print("\n" + "=" * 100)
print("✅ DasAtom 流程演示完成！")
print("=" * 100)


