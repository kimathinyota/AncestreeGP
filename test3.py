#***********************************************************
#                                                          *
#                                                          *
#               ALTERNATIVE SOLUTION                       *
#                                                          *
#                                                          *
# **********************************************************

import random
import networkx as nx
import matplotlib.pyplot as plt
import streamlit as st

test = st.tab(['test'])

with test:
    if st.toggle('See old version'):
        # Initialize Streamlit state for the selected patient
        if "selected_node" not in st.session_state:
            st.session_state.selected_node = None

        # Sample family graph creation
        G = nx.Graph()

        # Define relationships (parents -> children, 'marriage' -> represents "-")
        relationships = {
            (1, 2): [3, 4, 5],  # 1 and 2 are parents, 3, 4, 5 are children
            (3, 6): [7],         # 3 and 6 are parents, 7 is their child
            (4, 8): [],          # 4 and 8 are parents, no children
            (5,): []             # 5 has no children
        }

        # Add edges to the graph based on relationships
        for parents, children in relationships.items():
            for child in children:
                G.add_edge(parents[0], child)  # Parent to child

        # Add 'marriage' connections (e.g., between 1 and 2)
        for parents in relationships:
            if len(parents) == 2:  # It's a pair of parents
                G.add_edge(parents[0], parents[1])  # Marriage connection

        # Generate random patient data
        random.seed(42)  # For reproducibility
        patient_names = [f"Patient_{i}" for i in range(1, 9)]
        disease_presence = [random.choice([True, False]) for _ in range(8)]

        # Store node information in a DataFrame
        node_data = pd.DataFrame({
            'node': list(G.nodes),
            'patient_name': patient_names,
            'has_disease': disease_presence
        })

        # Layout for graph drawing
        pos = nx.spring_layout(G)

        def draw_graph(selected_node=None):
            """Draw the graph with highlights based on the selected node."""
            fig, ax = plt.subplots(figsize=(8, 6))
            
            # Draw the entire graph with default node colors
            nx.draw(G, pos, with_labels=True, node_color='lightgray', node_size=500, font_size=10, ax=ax)

            # Highlight nodes with disease
            diseased_nodes = node_data[node_data['has_disease'] == True]['node'].tolist()
            nx.draw_networkx_nodes(G, pos, nodelist=diseased_nodes, node_color='black', node_size=700, ax=ax)

            if selected_node is not None:
                # First generation (direct neighbors)
                gen_1_nodes = set(G.neighbors(selected_node))

                # Second generation (neighbors of neighbors)
                gen_2_nodes = set()
                for node in gen_1_nodes:
                    gen_2_nodes.update(G.neighbors(node))
                gen_2_nodes.difference_update({selected_node}, gen_1_nodes)

                # Draw nodes with generation-based highlighting
                nx.draw_networkx_nodes(G, pos, nodelist=[selected_node], node_color='yellow', node_size=700, ax=ax)
                nx.draw_networkx_nodes(G, pos, nodelist=gen_1_nodes, node_color='none', edgecolors='blue', linewidths=2, ax=ax)
                nx.draw_networkx_nodes(G, pos, nodelist=gen_2_nodes, node_color='none', edgecolors='green', linewidths=2, ax=ax)

                # Add legend with patient details
                patient_name = node_data[node_data['node'] == selected_node]['patient_name'].values[0]
                has_disease = node_data[node_data['node'] == selected_node]['has_disease'].values[0]
                legend_text = f"Selected Patient: {patient_name}\nDisease: {'Yes' if has_disease else 'No'}\n"
                ax.text(0.95, 0.05, legend_text, transform=ax.transAxes, fontsize=9, verticalalignment='bottom',
                        horizontalalignment='right', bbox=dict(facecolor='white', alpha=0.7))

            st.pyplot(fig)  # Display the graph in Streamlit

        # Streamlit UI
        st.title("Interactive Family Tree Viewer")

        # Dropdown to select a patient node
        selected_patient = st.selectbox("Select a Patient:", options=list(G.nodes), format_func=lambda x: f"Patient {x}")

        # Update the selected node in the session state
        if selected_patient:
            st.session_state.selected_node = selected_patient

        # Draw the graph with the selected node highlighted
        draw_graph(st.session_state.selected_node)
