from collections import deque
import random
import numpy as np
import pytest
from src.components.optical_channel import QuantumChannel, ClassicalChannel

from src.kernel.timeline import Timeline
from src.qkd.three_stage import pair_3stage_protocols
from src.protocol import Protocol
from src.topology.node import QKDNode

import matplotlib

matplotlib.use('Agg')  # Use a non-GUI backend to prevent Tkinter errors
import matplotlib.pyplot as plt
import networkx as nx


# Global variables to hold the quantum channels and nodes
quantum_channels = []
qkd_nodes = []
tl = Timeline(1e12)
tl.seed(1)
counter = 0

class Parent(Protocol):
    def __init__(self, own, length, name):
        super().__init__(own, name)
        self.upper_protocols = []
        self.lower_protocols = []
        self.length = length

    def received_message(self):
        pass


def generate_adjacency_matrix(topology, m):
    n = m;
    size = n * n

    if (topology == 'Grid') or (topology == 'grid'):
        adj_matrix = np.zeros((size, size))
        for row in range(n):
            for col in range(n):
                index = row * n + col

                # Connect to the right
                if col < n - 1:
                    adj_matrix[index][index + 1] = 1
                    adj_matrix[index + 1][index] = 1

                # Connect downwards
                if row < n - 1:
                    adj_matrix[index][index + n] = 1
                    adj_matrix[index + n][index] = 1
        return adj_matrix

    elif (topology == 'ring') or (topology == 'Ring'):
        adjacency_matrix = np.zeros((n, n))
        for i in range(n):
            adjacency_matrix[i][(i - 1) % n] = 1  # Connect to previous node
            adjacency_matrix[i][(i + 1) % n] = 1  # Connect to next node
        return adjacency_matrix

    elif (topology == 'star') or (topology == 'Star'):
        adjacency_matrix = np.zeros((n + 1, n + 1))
        for i in range(1, n + 1):
            adjacency_matrix[i][0] = adjacency_matrix[0][i] = 1
        return adjacency_matrix

    elif (topology == 'torus') or (topology == 'Torus'):
        totalNodes = size
        totalNodesX = n
        totalNodesY = n
        adjacencyMatrix = np.zeros((totalNodes, totalNodes))

        for i in range(totalNodesX):
            for j in range(totalNodesY):
                node = i * totalNodesY + j

                # Calculate the left neighbor
                if j == 0:
                    leftNeighbor = node + (totalNodesY - 1)
                else:
                    leftNeighbor = node - 1

                # Calculate the upper neighbor
                if i == 0:
                    upperNeighbor = node + (totalNodesX - 1) * totalNodesY
                else:
                    upperNeighbor = node - totalNodesY

                # Update the adjacency matrix
                adjacencyMatrix[node, leftNeighbor] = 1
                adjacencyMatrix[leftNeighbor, node] = 1
                adjacencyMatrix[node, upperNeighbor] = 1
                adjacencyMatrix[upperNeighbor, node] = 1

        return adjacencyMatrix

def get_nodes(topology, n):
    topology = topology.lower()
    if topology in ['ring', 'grid', 'torus']:
        if topology == 'ring':
            adj_matrix = generate_adjacency_matrix('Ring', n)
            start_node = 0
            end_node = n // 2
        elif topology == 'grid':
            adj_matrix = generate_adjacency_matrix('Grid', n)
            start_node = 0
            end_node = n * n - 1
        elif topology == 'torus':
            adj_matrix = generate_adjacency_matrix('Torus', n)
            start_node = 0
            end_node = n * n - 1
        nodes_in_between = shortest_path_length_bfs(adj_matrix, start_node, end_node)
        return nodes_in_between
    else:
        raise ValueError('Error in topology: use either of ring, grid, or torus topology')

def shortest_path_length_bfs(adjacency_matrix, start_node, end_node):
    """
    Find the length of the shortest path in an unweighted graph using BFS.

    Args:
    adjacency_matrix (numpy.ndarray): The adjacency matrix of the graph.
    start_node (int): The starting node index.
    end_node (int): The ending node index.

    Returns:
    int: The number of nodes in between the start_node and end_node in the shortest path.
    """
    num_nodes = adjacency_matrix.shape[0]
    visited = [False] * num_nodes
    prev = [None] * num_nodes

    # BFS
    queue = deque([start_node])
    visited[start_node] = True

    while queue:
        node = queue.popleft()

        # Visit the neighbors
        for neighbor, connected in enumerate(adjacency_matrix[node]):
            if connected and not visited[neighbor]:
                queue.append(neighbor)
                visited[neighbor] = True
                prev[neighbor] = node

    # Reconstruct the path
    path = []
    at = end_node
    while at is not None:
        path.append(at)
        at = prev[at]
    path.reverse()

    # Return the number of nodes in between start and end, excluding start and end
    nonodes = len(path) - 2 if path[0] == start_node and len(path) > 1 else 0
    return nonodes


def clear_file_contents(file_name):
    with open(file_name, 'w') as file:
        file.write('')


@pytest.fixture(scope="module", autouse=True)
def clear_files():
    clear_file_contents('result_3stage.txt')

@pytest.fixture(scope="module")
def setup_network():
    global quantum_channels, qkd_nodes, tl, counter

    topology = 'grid'
    matrix_size = 4
    nodes_count = get_nodes(topology, matrix_size)

    if not qkd_nodes:
        qkd_nodes = [QKDNode(f"Node{i}", tl, stack_size=4) for i in range(nodes_count)]
        qkd_nodes.insert(0, QKDNode("Alice", tl, stack_size=4))
        qkd_nodes.append(QKDNode("Bob", tl, stack_size=4))

    channel_counter = 0  # Initialize a counter for channel naming

    # Assuming quantum_channels is a list that will store all the created channels
    if not quantum_channels:
        # First pass: Alice to Bob
        for i in range(len(qkd_nodes) - 1):
            channel_name = f"qc_{qkd_nodes[i].name}_{qkd_nodes[i + 1].name}_{channel_counter}"
            channel = QuantumChannel(channel_name, tl, distance=10, attenuation=0.1, polarization_fidelity=0.8)
            quantum_channels.append(channel)
            channel.set_ends(qkd_nodes[i], qkd_nodes[i + 1].name)
            channel_counter += 1

        # Second pass: Bob to Alice
        for i in range(len(qkd_nodes) - 1, 0, -1):
            channel_name = f"qc_{qkd_nodes[i].name}_{qkd_nodes[i - 1].name}_{channel_counter}"
            channel = QuantumChannel(channel_name, tl, distance=10, attenuation=0.1, polarization_fidelity=0.8)
            quantum_channels.append(channel)
            channel.set_ends(qkd_nodes[i], qkd_nodes[i - 1].name)
            print(channel_name)
            channel_counter += 1

        # Third pass: Alice to Bob again
        for i in range(len(qkd_nodes) - 1):
            channel_name = f"qc_{qkd_nodes[i].name}_{qkd_nodes[i + 1].name}_{channel_counter}"
            channel = QuantumChannel(channel_name, tl, distance=10, attenuation=0.1, polarization_fidelity=0.8)
            quantum_channels.append(channel)
            channel.set_ends(qkd_nodes[i], qkd_nodes[i + 1].name)
            print(channel_name)
            channel_counter += 1


def draw_network_diagram(nodes, edges, title, file_name):
    # Create a directed graph
    G = nx.DiGraph()
    G.add_nodes_from(nodes)
    G.add_edges_from(edges)

    # Position the nodes using the shell layout for better spacing
    pos = nx.shell_layout(G)

    # Set figure size to accommodate the graph
    plt.figure(figsize=(12, 8))

    # Draw the nodes
    nx.draw_networkx_nodes(G, pos, node_size=3000, node_color='skyblue', alpha=0.6)

    # Draw the edges with arrows
    nx.draw_networkx_edges(G, pos, edge_color='gray', arrowstyle='->', arrowsize=20)

    # Draw the node labels
    nx.draw_networkx_labels(G, pos, font_size=12, font_family="sans-serif")

    # Define and draw the edge labels
    edge_labels = {edge: 'Quantum Channel' for edge in edges}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, label_pos=0.5, font_size=9)

    # Set the title of the plot
    plt.title(title)

    # Remove the axes
    plt.axis('off')

    # Save the diagram to a file
    plt.savefig(file_name, format='PNG', bbox_inches='tight')
    plt.close()


@pytest.mark.parametrize("distance", range(1, 52, 5))
def test_3stage_protocol(distance, setup_network):
    global quantum_channels, qkd_nodes, tl, counter
    clear_file_contents('round_details_3stage.txt')
    num_rounds = 100
    num_of_bits = 100

    # Assuming quantum_channels is already populated with QuantumChannel objects
    for channel in quantum_channels:
        print(channel.name)  # or use the appropriate attribute/method to get the channel's name

    # Assuming qkd_nodes contains all the nodes, including Alice and Bob
    for i, node in enumerate(qkd_nodes):
        # Set seed for each node
        node.set_seed(i)

    # Pair nodes sequentially
    for i in range(len(qkd_nodes) - 1):
        pair_3stage_protocols(qkd_nodes[i].protocol_stack[0], qkd_nodes[i + 1].protocol_stack[0])
        print(f"Paired {qkd_nodes[i].name} with {qkd_nodes[i + 1].name}")

    # Pairing back from Bob to Alice through the intermediate nodes
    for i in range(len(qkd_nodes) - 1, 0, -1):
        pair_3stage_protocols(qkd_nodes[i].protocol_stack[0], qkd_nodes[i - 1].protocol_stack[0])
        print(f"Paired {qkd_nodes[i].name} with {qkd_nodes[i - 1].name}")

    # Pair nodes sequentially
    for i in range(len(qkd_nodes) - 1):
        pair_3stage_protocols(qkd_nodes[i].protocol_stack[0], qkd_nodes[i + 1].protocol_stack[0])
        print(f"Paired {qkd_nodes[i].name} with {qkd_nodes[i + 1].name}")

    print("\n")
    print("\n")

    for channel in quantum_channels:
        qc = tl.get_entity_by_name(channel.name)
        if qc:
            # Set distance for all the channels
            qc.__setattr__("distance", distance)

    if counter == 0:
        # Now, handle the attenuation separately for 2nd to last channels
        for channel in quantum_channels[1:]:
            qc = tl.get_entity_by_name(channel.name)
            if qc and random.random() < 0.75 and random.random() < 0.75:
                # Apply quantum repeater logic for 2nd to last channels
                qc.__setattr__("attenuation", 0.0)
                qc.__setattr__("isQr", True)

    counter += 1
    parent_protocols = []
    for i, node in enumerate(qkd_nodes):
        parent_protocol = Parent(node, 128, f"parent_{node.name}")
        parent_protocols.append(parent_protocol)
        node.protocols[0].upper_protocols.append(parent_protocol)
        parent_protocol.lower_protocols.append(node.protocol_stack[0])

    tl.init()
    alice = qkd_nodes[0]
    alice.protocols[0].generate_sequences(num_of_bits, num_rounds)
    alice.protocols[0].send_pulse()
    for round in range(1, num_rounds + 1):
        print(f"Round {round} in progress")
        for i, node in enumerate(qkd_nodes[:-1]):  # Exclude the last node as it will not initiate a push
            node.protocols[0].push(1, round)
            tl.run()
            while not tl.events.isempty():
                tl.run()
            # Check for quantum repeater presence in the channel connected to the current node
            if "qr" in quantum_channels[i].name:
                print(f"Quantum Repeaters are attached between {node.name} and {qkd_nodes[i + 1].name} in round {round}")
            print(f"{node.name} run done")

        alice.protocols[0].decoding()
        alice.protocols[0].begin_classical_communication()

    alice.protocols[0].end_of_round(distance * 6, num_rounds)