import rustworkx as rx
import networkx as nx
import numpy as np
import random
import math
import os
import re
import json

from qiskit import qasm2, transpile, QuantumCircuit, QuantumRegister
from qiskit.converters import dag_to_circuit, circuit_to_dag
from qiskit.circuit import library
import copy
from copy import deepcopy

custom = [
    qasm2.CustomInstruction("p",num_params= 1, num_qubits=1 ,constructor=library.PhaseGate, builtin=True),
]

def CreateCircuitFromQASM(file, path):
    filePath = os.path.join(path,file)
    # print(filePath)
    cir = qasm2.load(filePath, custom_instructions=custom)
    gates_in_circuit = {op[0].name for op in cir.data}
    allowed_basis_gates = {'cz', 'h', 's', 't', 'rx', 'ry', 'rz'}
    # Check if there are any disallowed gates by checking the difference between sets
    if gates_in_circuit - allowed_basis_gates:
        cir = transpile(cir, basis_gates=list(allowed_basis_gates),optimization_level=0)
    return cir


def get_rx_one_mapping(graph_max, G):
    sub_graph = rx.networkx_converter(graph_max)
    big_graph = rx.networkx_converter(G)
    nx_edge_s = list(graph_max.edges())
    rx_edge_s = list(sub_graph.edge_list())
    rx_nx_s = dict()
    for i in range(len(rx_edge_s)):
        if rx_edge_s[i][0] not in rx_nx_s:
            rx_nx_s[rx_edge_s[i][0]] = nx_edge_s[i][0]
        if rx_edge_s[i][1] not in rx_nx_s:
            rx_nx_s[rx_edge_s[i][1]] = nx_edge_s[i][1]
    nx_edge_G = list(G.edges())
    rx_edge_G = list(big_graph.edge_list())
    rx_nx_G = dict()
    for i in range(len(rx_edge_G)):
        if rx_edge_G[i][0] not in rx_nx_G:
            rx_nx_G[rx_edge_G[i][0]] = nx_edge_G[i][0]
        if rx_edge_G[i][1] not in rx_nx_G:
            rx_nx_G[rx_edge_G[i][1]] = nx_edge_G[i][1]
    vf2 = rx.vf2_mapping(big_graph, sub_graph, subgraph=True, induced = False)
    item = next(vf2)
    reverse_mapping = {rx_nx_s[value]: rx_nx_G[key] for  key, value in item.items()}
    return reverse_mapping


def get_best_mapping_with_inertia(graph_max, G, num_q, 
                                  prev_embedding=None,
                                  current_gates=None,
                                  max_candidates=50,
                                  idle_weight=0.3):
    """
    基于惯性启发式的改进 VF2 映射选择器
    
    通过评估多个 VF2 解，选择使原子移动距离最小的映射。
    采用加权策略：参与门操作的量子比特权重为 1.0，闲置量子比特权重为 idle_weight。
    
    参数:
        graph_max: 逻辑连接图（NetworkX Graph）
        G: 硬件拓扑图（NetworkX Graph）
        num_q: 量子比特总数
        prev_embedding: 上一个分区的嵌入映射（列表格式）
        current_gates: 当前分区的门列表 [[q0,q1], ...]
        max_candidates: 最多评估的 VF2 候选解数量
        idle_weight: 闲置量子比特的移动成本权重 (0.0-1.0)
                    0.0 = 只考虑参与门的量子比特（激进）
                    1.0 = 所有量子比特同等重要（保守）
                    0.3 = 推荐值（平衡）
    
    返回:
        reverse_mapping: 字典格式的映射 {logical_qubit: physical_position}
    """
    # 1. 图结构转换 (NetworkX -> RustworkX)
    sub_graph = rx.networkx_converter(graph_max)
    big_graph = rx.networkx_converter(G)
    
    # 2. 建立 RustworkX ID 与 NetworkX 节点的映射表
    nx_edge_s = list(graph_max.edges())
    rx_edge_s = list(sub_graph.edge_list())
    rx_nx_s = dict()
    for i in range(len(rx_edge_s)):
        if rx_edge_s[i][0] not in rx_nx_s:
            rx_nx_s[rx_edge_s[i][0]] = nx_edge_s[i][0]
        if rx_edge_s[i][1] not in rx_nx_s:
            rx_nx_s[rx_edge_s[i][1]] = nx_edge_s[i][1]
    
    nx_edge_G = list(G.edges())
    rx_edge_G = list(big_graph.edge_list())
    rx_nx_G = dict()
    for i in range(len(rx_edge_G)):
        if rx_edge_G[i][0] not in rx_nx_G:
            rx_nx_G[rx_edge_G[i][0]] = nx_edge_G[i][0]
        if rx_edge_G[i][1] not in rx_nx_G:
            rx_nx_G[rx_edge_G[i][1]] = nx_edge_G[i][1]
    
    # 3. 获取 VF2 迭代器
    vf2_iter = rx.vf2_mapping(big_graph, sub_graph, subgraph=True, induced=False)
    
    # 4. 如果没有前一个映射或门信息，使用原版逻辑
    if prev_embedding is None or current_gates is None:
        try:
            item = next(vf2_iter)
            reverse_mapping = {rx_nx_s[value]: rx_nx_G[key] 
                             for key, value in item.items()}
            return reverse_mapping
        except StopIteration:
            return None
    
    # 5. 识别参与当前分区门操作的量子比特（活跃量子比特）
    active_qubits = set()
    for gate in current_gates:
        active_qubits.add(gate[0])
        active_qubits.add(gate[1])
    
    # 6. 遍历多个 VF2 解，选择移动成本最小的
    best_mapping = None
    min_move_cost = float('inf')
    
    for candidate_idx, item in enumerate(vf2_iter):
        if candidate_idx >= max_candidates:
            break
        
        # 转换当前候选解为 NetworkX 格式
        candidate_mapping = {rx_nx_s[value]: rx_nx_G[key] 
                           for key, value in item.items()}
        
        # 计算加权移动成本
        move_cost = 0.0
        
        for logical_q, curr_pos in candidate_mapping.items():
            # 只有当该量子比特在上一个映射中存在时才计算
            if logical_q < len(prev_embedding) and prev_embedding[logical_q] != -1:
                prev_pos = prev_embedding[logical_q]
                
                # 欧几里得距离
                dist = math.sqrt(
                    (curr_pos[0] - prev_pos[0])**2 + 
                    (curr_pos[1] - prev_pos[1])**2
                )
                
                # 加权策略：活跃量子比特权重1.0，闲置量子比特权重为idle_weight
                weight = 1.0 if logical_q in active_qubits else idle_weight
                move_cost += weight * dist
        
        # 更新最优解
        if move_cost < min_move_cost:
            min_move_cost = move_cost
            best_mapping = candidate_mapping
        
        # 完美解：零移动（使用浮点数比较）
        if min_move_cost < 1e-6:
            break
    
    # 如果找到优化解则返回，否则返回最后一个候选
    return best_mapping if best_mapping is not None else candidate_mapping

def rx_is_subgraph_iso(G, subG):
    Grx = rx.networkx_converter(G)
    subGrx = rx.networkx_converter(subG)
    gm = rx.is_subgraph_isomorphic(Grx, subGrx, induced = False)   
    return gm

def get_layer_gates(dag):
    gate_layer_list = []
    for item in dag.layers():
        gate_layer = []
        graph_one = nx.Graph()
        for gate in item['partition']:
            c0 = gate[0]._index
            c1 = gate[1]._index
            gate_layer.append([c0, c1])
        gate_layer_list.append(gate_layer)
    return gate_layer_list

def partition_from_DAG(dag, coupling_graph):
    gate_layer_list = get_layer_gates(dag)
    num_of_gate = 0
    last_index = 0
    partition_gates = []
    for i in range(len(gate_layer_list)):
        #print(i)
        #print(last_index)
        merge_gates = sum(gate_layer_list[last_index:i+1], [])
        tmp_graph = nx.Graph()
        tmp_graph.add_edges_from(merge_gates)
        connected_components = list(nx.connected_components(tmp_graph))
        isIso = True
        for idx, component in enumerate(connected_components, 1):
            subgraph = tmp_graph.subgraph(component)
            if len(subgraph.edges()) == nx.diameter(subgraph): #path-tolopology, must sub_iso
                continue
            # print(subgraph.edges())
            if not rx_is_subgraph_iso(coupling_graph, subgraph):
                isIso = False
                break
        if isIso:
            if i == len(gate_layer_list) - 1:
                merge_gates = sum(gate_layer_list[last_index: i+1], [])
                partition_gates.append(merge_gates)
            continue
        else:
            merge_gates = sum(gate_layer_list[last_index: i], [])
            partition_gates.append(merge_gates)
            last_index = i
            if i == len(gate_layer_list) - 1:
                merge_gates = sum(gate_layer_list[last_index: i+1], [])
                partition_gates.append(merge_gates)

    return partition_gates

def get_2q_gates_list(circ):
    gate_2q_list = []
    instruction = circ.data
    for ins in instruction:
        if ins.operation.num_qubits == 2:
            gate_2q_list.append((ins.qubits[0]._index, ins.qubits[1]._index))
    return gate_2q_list


def get_qubits_num(gate_2q_list):
    num = max(max(gate) for gate in gate_2q_list)
    num += 1
    return num

def gates_list_to_QC(gate_list):  #default all 2-q gates circuit
    Lqubit = get_qubits_num(gate_list)
    circ = QuantumCircuit(Lqubit)
    # issue: cz
    for two_qubit_gate in gate_list:
        circ.cz(two_qubit_gate[0], two_qubit_gate[1])
    
    dag = circuit_to_dag(circ)
    return circ, dag


def euclidean_distance(node1, node2):
    x1, y1 = node1
    x2, y2 = node2
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

def generate_grid_with_Rb(n, m, Rb):
    G = nx.grid_2d_graph(n, m)  # 生成n*m的网格图
    for node1 in G.nodes():
        for node2 in G.nodes():
            if node1 != node2:
                distance = euclidean_distance(node1, node2)
                if distance <= Rb:
                    G.add_edge(node1, node2)

    return G

def extend_graph(coupling_graph, arch_size, Rb):
    coupling_graph = generate_grid_with_Rb(arch_size+1, arch_size+1, Rb)
    return coupling_graph


def map2list(mapping, num_q):
    map_list = [-1] * num_q
    for key, value in mapping.items():
        map_list[key] = value

    return map_list

def complete_mapping(i, embeddings, indices, coupling_graph):
    cur_map = embeddings[i]
    unoccupied = [value for value in coupling_graph.nodes() if value not in cur_map]
    for index in indices:
        flag = False
        if i != 0:  #If pre_map is not empty
            if embeddings[i-1][index] in unoccupied:
                cur_map[index] = embeddings[i-1][index]
                flag = True
                unoccupied.remove(cur_map[index])
        if i != len(embeddings) - 1 and flag == False:
            for j in range(i+1, len(embeddings)):
                if embeddings[j][index] != -1 and embeddings[j][index] in unoccupied:
                    cur_map[index] = embeddings[j][index]
                    unoccupied.remove(cur_map[index])
                    flag = True
                    break
        if flag == False:
            if i != 0:
                source = embeddings[i-1][index]
                node_of_shortest = dict()
                for node in unoccupied:
                    distance = nx.shortest_path_length(coupling_graph, source=source, target=node)
                    node_of_shortest[node] = distance
                min_node = min(node_of_shortest, key=node_of_shortest.get)
                cur_map[index] = min_node
                unoccupied.remove(min_node)
                flag = True
            elif i != len(embeddings) - 1:
                for j in range(i+1, len(embeddings)):
                    if embeddings[j][index] != -1:
                        source = embeddings[j][index]
                        node_of_shortest = dict()
                        for node in unoccupied:
                            distance = nx.shortest_path_length(coupling_graph, source=source, target=node)
                            node_of_shortest[node] = distance
                        min_node = min(node_of_shortest, key=node_of_shortest.get)
                        cur_map[index] = min_node
                        unoccupied.remove(min_node)
                        flag = True
                        break
        if flag == False:
            min_node = random.choice(unoccupied)
            cur_map[index] = min_node
            unoccupied.remove(min_node)
    return cur_map


def loc_to_qasm(n: int, qubit: int, loc: tuple[int, int]) -> str:
    """
    Converts a qubit location to a QASM formatted string.

    Parameters:
    n (int): The number of qubits in the quantum register.
    qubit (int): The specific qubit index.
    loc (tuple[int, int]): The location of the qubit as a tuple of two integers.

    Returns:
    str: The QASM formatted string representing the qubit location.

    Raises:
    ValueError: If the loc tuple does not have exactly two elements.
    """
    if len(loc) != 2:
        raise ValueError("Invalid loc, it must be a tuple of length 2")
    return f"Qubit(QuantumRegister({n}, 'q'), {qubit})\n({loc[0]}, {loc[1]})"

def map_to_qasm(n: int, map: list[tuple[int, int]], filename: str) -> None:
    """
    Converts a list of qubit locations to QASM format and saves it to a file.

    Parameters:
    n (int): The number of qubits in the quantum register.
    map (list[tuple[int, int]]): A list of tuples representing the locations of the qubits.
    filename (str): The name of the file to save the QASM formatted strings.

    Returns:
    None
    """
    with open(filename, 'w') as f:
        for i in range(n):
            f.write(loc_to_qasm(n, i, map[i]) + '\n')

def gate_in_layer(gate_list:list[list[int]])->list[map]:
    res = []
    for i in range(len(gate_list),-1):
        assert len(gate_list[i]) == 2
        res.append({'id':i,'q0':gate_list[i][0],'q1':gate_list[i][1]})
    return res

def check_available(graph, coupling_graph, mapping):

    for eg0, eg1 in graph.edges():
        if (mapping[eg0], mapping[eg1]) not in coupling_graph.edges():
            return False
    return True

def check_intersect(gate1, gate2, coupling_graph, mapping):
    rg1 = 1/2 * (euclidean_distance(mapping[gate1[0]], mapping[gate1[1]]))
    rg2 = 1/2 * (euclidean_distance(mapping[gate2[0]], mapping[gate2[1]]))
    dis = rg1 + rg2
    if euclidean_distance(mapping[gate1[0]], mapping[gate2[0]]) >= dis and \
        euclidean_distance(mapping[gate1[0]], mapping[gate2[1]]) >= dis and \
        euclidean_distance(mapping[gate1[1]], mapping[gate2[0]]) >= dis and \
        euclidean_distance(mapping[gate1[1]], mapping[gate2[1]]) >= dis:
        return True
    else:
        return False

def check_intersect_ver2(gate1, gate2, coupling_graph, mapping, r_re):
    if euclidean_distance(mapping[gate1[0]], mapping[gate2[0]]) > r_re and \
        euclidean_distance(mapping[gate1[0]], mapping[gate2[1]]) > r_re and \
        euclidean_distance(mapping[gate1[1]], mapping[gate2[0]]) > r_re and \
        euclidean_distance(mapping[gate1[1]], mapping[gate2[1]]) > r_re:
        return True
    else:
        return False

def get_parallel_gates(gates, coupling_graph, mapping, r_re):
    gates_list = []
    _, dag = gates_list_to_QC(gates)
    gate_layer_list = get_layer_gates(dag)

    for items in gate_layer_list:
        gates_copy = deepcopy(items)
        while(len(gates_copy) != 0):
            parallel_gates = []
            parallel_gates.append(gates_copy[0])
            for i in range(1, len(gates_copy)):
                flag = True
                for gate in parallel_gates:
                    if check_intersect_ver2(gate, gates_copy[i], coupling_graph, mapping, r_re):
                        continue
                    else:
                        flag = False
                        break
                if flag:
                    parallel_gates.append(gates_copy[i])

            for gate in parallel_gates:
                gates_copy.remove(gate)
            gates_list.append(parallel_gates)
            #print("parl:",parallel_gates)
    return gates_list

'''def set_parameters(default):
    para = {}
    if default:
        para['T_cz'] = 0.2  #us
        para['T_eff'] = 1.5e6 #us
        para['T_trans'] = 20 # us
        para['AOD_width'] = 3 #um
        para['AOD_height'] = 3 #um
        para['Move_speed'] = 0.55 #um/us
        para['F_cz'] = 0.995 

    return para'''

def set_parameters(T_cz = 0.2, T_eff = 1.5e6, T_trans=20, AOD_width=3,AOD_height=3,Move_speed=0.55,F_cz=0.995, F_trans = 1):
    para = {}
    para['T_cz'] = T_cz  #us
    para['T_eff'] = T_eff #us
    para['T_trans'] = T_trans # us
    para['AOD_width'] = AOD_width #um
    para['AOD_height'] = AOD_height #um
    para['Move_speed'] = Move_speed #um/us
    para['F_cz'] = F_cz
    para['F_trans'] = F_trans

    return para

'''def compute_fidelity(parallel_gates, all_movements, num_q, gate_num):
    para = set_parameters(True)
    t_total = 0
    t_total += (len(parallel_gates) * para['T_cz']) # cz execution time, parallel
    t_move = 0
    for move in all_movements:
        t_total += (4 * para['T_trans']) # pick/drop/pick/drop
        t_move += (4 * para['T_trans'])
        max_dis = 0
        for each_move in move:
            x1, y1 = each_move[1][0],each_move[1][1]
            x2, y2 = each_move[2][0],each_move[2][1]
            dis = (abs(x2-x1)*para['AOD_width'])**2 + (abs(y2-y1)*para['AOD_height'])**2
            if dis > max_dis:
                max_dis = dis
        max_dis = math.sqrt(max_dis)
        t_total += (max_dis/para['Move_speed'])
        t_move += (max_dis/para['Move_speed'])

    t_idle = num_q * t_total - gate_num * para['T_cz']
    Fidelity = math.exp(-t_idle/para['T_eff']) * (para['F_cz']**gate_num)
    move_fidelity = math.exp(-t_move/para['T_eff'])
    return t_idle, Fidelity, move_fidelity'''

def compute_fidelity(parallel_gates, all_movements, num_q, gate_num, para=None):
    if para is None:
        para = set_parameters()
    t_total = 0
    t_total += (len(parallel_gates) * para['T_cz']) # cz execution time, parallel
    t_move = 0
    num_trans = 0
    num_move = 0
    all_move_dis = 0
    for move_stage in all_movements:
        # 每个 move_stage 是一个移动阶段，包含多个移动步骤
        for move_step in move_stage:
            # 每个 move_step 是一个步骤，包含可以并行执行的移动
            t_total += (4 * para['T_trans']) # pick/drop/pick/drop
            t_move += (4 * para['T_trans'])
            num_trans += 4
            max_dis = 0
            for each_move in move_step:
                # 每个 each_move 是 [qubit_id, (x1,y1), (x2,y2)]
                num_move += 1
                x1, y1 = each_move[1][0], each_move[1][1]
                x2, y2 = each_move[2][0], each_move[2][1]
                dis = (abs(x2-x1)*para['AOD_width'])**2 + (abs(y2-y1)*para['AOD_height'])**2
                if dis > max_dis:
                    max_dis = dis
            max_dis = math.sqrt(max_dis)
            all_move_dis += max_dis
            t_total += (max_dis/para['Move_speed'])
            t_move += (max_dis/para['Move_speed'])

    t_idle = num_q * t_total - gate_num * para['T_cz']
    Fidelity = math.exp(-t_idle/para['T_eff']) * (para['F_cz']**gate_num) * (para['F_trans'] ** num_trans)
    move_fidelity = math.exp(-t_move/para['T_eff'])
    return t_idle, Fidelity, move_fidelity, t_total, num_trans, num_move, all_move_dis

def get_embeddings(partition_gates, coupling_graph, num_q, arch_size, Rb, 
                  initial_mapping=None, optimize_movement=True, 
                  max_candidates=50, idle_weight=0.3):
    """
    获取每个分区的嵌入映射
    
    参数:
        partition_gates: 分区门列表
        coupling_graph: 硬件拓扑图
        num_q: 量子比特数
        arch_size: 网格大小
        Rb: 交互半径
        initial_mapping: 初始映射（可选）
        optimize_movement: 是否启用移动优化（默认True）
        max_candidates: VF2 候选解数量（默认50）
        idle_weight: 闲置量子比特权重（默认0.3）
    
    返回:
        embeddings: 嵌入列表
        extend_position: 扩展位置列表
    """
    embeddings = []
    begin_index = 0
    extend_position = []
    if initial_mapping:
        embeddings.append(initial_mapping)
        begin_index = 1
    
    for i in range(begin_index, len(partition_gates)):
        tmp_graph = nx.Graph()
        tmp_graph.add_edges_from(partition_gates[i])
        if not rx_is_subgraph_iso(coupling_graph, tmp_graph):
            coupling_graph = extend_graph(coupling_graph, arch_size, Rb)
            extend_position.append(i)
        
        # === 核心优化逻辑 ===
        # 只有当开启优化、不是第一个分区、且有多于1个分区时才优化
        next_embedding = None
        if optimize_movement and i > 0 and len(partition_gates) > 1:
            try:
                next_embedding = get_best_mapping_with_inertia(
                    tmp_graph, 
                    coupling_graph, 
                    num_q,
                    prev_embedding=embeddings[i-1],
                    current_gates=partition_gates[i],
                    max_candidates=max_candidates,
                    idle_weight=idle_weight
                )
            except Exception as e:
                print(f"⚠️  优化失败于分区 {i}: {e}，回退到原版算法")
                next_embedding = None
        
        # 如果优化失败或未启用，使用原版逻辑
        if next_embedding is None:
            next_embedding = get_rx_one_mapping(tmp_graph, coupling_graph)
        
        next_embedding = map2list(next_embedding, num_q)
        embeddings.append(next_embedding)

    for i in range(begin_index, len(embeddings)):
        indices = [index for index, value in enumerate(embeddings[i]) if value == -1]
        if indices:
            embeddings[i] = complete_mapping(i, embeddings, indices, coupling_graph)

    return embeddings, extend_position

def qasm_to_map(filename):

    with open(filename, 'r') as file:
        lines = file.readlines()
    
    # 确保行数为偶数
    if len(lines) % 2 != 0:
        raise ValueError("文件内容的行数应为偶数，以便正确配对比特和映射位置。")
    qubit_pattern = re.compile(r"Qubit\(QuantumRegister\((\d+), 'q'\), (\d+)\)")
    match = qubit_pattern.search(lines[0].strip())
    num_q = int(match.group(1))
    mapping = [-1]*num_q
    # 遍历每对行
    for i in range(0, len(lines), 2):
        # 读取比特行和映射位置行
        qubit_line = lines[i].strip()
        position_line = lines[i+1].strip()
        
        # 解析比特索引
        match = qubit_pattern.search(qubit_line)
        if match:
            num_q = int(match.group(1))
            bit_index = int(match.group(2))
        else:
            raise ValueError(f"无法从比特行提取索引: {qubit_line}")
        # 解析映射位置
        try:
            position = eval(position_line)
        except Exception as e:
            raise ValueError(f"解析映射位置时出错: {position_line}") from e
        
        # 扩展列表到足够的长度
        mapping[bit_index] = position
    
    return mapping

def compute_fidelity_tetris(cycle_file, qasm_file, path):

    with open(path+cycle_file, 'r') as cyc_file:
        cyc_lines = cyc_file.readlines()

    last_line = cyc_lines[-1].strip()
    last_gate = list(map(int, last_line.split()))

    cnot_count = 0
    swap_count = 0
    circ = CreateCircuitFromQASM(qasm_file, path)
    for instruction, qargs, cargs in circ.data:
        if instruction.name == 'cx':  # CNOT 门
            cnot_count += 1
        elif instruction.name == 'swap':  # SWAP 门
            swap_count += 1

    num_q = len(circ.qubits)
    gate_num = cnot_count + 3*swap_count
    
    para = set_parameters(True)
    gate_cycle = (last_gate[0]+1)/2
    t_total = gate_cycle*para['T_cz']
    t_idle = num_q * t_total - gate_num * para['T_cz']

    Fidelity =math.exp(-t_idle/para['T_eff']) * (para['F_cz']**gate_num)
    # print(Fidelity)
    return Fidelity, swap_count, gate_cycle

def write_data(data, path, file_name):
    with open(os.path.join(path,file_name), 'w') as file:
        for sublist in data:
        # 将每个子列表转换为 JSON 格式的字符串，并写入文件
            file.write(json.dumps(sublist) + '\n')
def write_data_json(data, path, file_name):
    with open(os.path.join(path,file_name), 'w') as file:
        file.write(json.dumps(data) + '\n')

def read_data(path, file_name):
    with open(os.path.join(path,file_name), 'r') as file:
    # 逐行读取文件
        data = [json.loads(line) for line in file]

# 输出读取的数据
    return data

def get_circuit_from_json(num_qubits: int):
    """
    Load a quantum circuit from a JSON file based on the number of qubits.

    Args:
        num_qubits (int): The number of qubits for the desired circuit.

    Returns:
        QuantumCircuit: The loaded quantum circuit.

    Raises:
        ValueError: If no circuit configuration is found for the specified number of qubits.
    """
    # Path to the JSON file containing the circuits
    json_file_path = "./Enola/graphs.json"
    with open(json_file_path, "r") as file:
        data = json.load(file)
    circuit_data = data.get(str(num_qubits))
    from qiskit.qasm2.export import dump
    # Check if the circuit configuration exists
    if circuit_data:
        # Add gates to the circuit based on the data
        index = 1
        for circuits in circuit_data: 
            for gate in circuits:
                quantum_circuit = QuantumCircuit(num_qubits)
                quantum_circuit.cz(gate[0], gate[1])
            dump(quantum_circuit, 'Data/3_regular_cz/circuits/3_regular_{}_{}.qasm'.format(num_qubits, index))
            index += 1
        #return quantum_circuit
    else:
        # Raise an error if no configuration is found
        raise ValueError(f"No circuit configuration for {num_qubits} qubits in graphs.json")