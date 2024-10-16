import streamlit as st
import networkx as nx
import nx_altair as nxa
import altair as alt
import pandas as pd
from networkx.drawing.nx_pydot import graphviz_layout


from Ancestory.model import AncestoryModel

@st.cache_resource
def set_up_model():
    print('\n\n\n\n\n\n', 'SETTING UP NEW MODEL', '\n\n\n\n\n')
    return AncestoryModel('Data/patients.csv', 'Data/child.csv', 'Data/disease.csv', 'Data/patient_disease.csv')

model = set_up_model()

def validate_person(id, name):
    messages = []
    if id is None or len(id)==0:
        messages += ['Missing ID']
    if name is None or len(name)==0:
        messages += ['Missing name']
    return len(messages)==0, '; '.join(messages)

@st.dialog("Enter Person")
def person():
    nhs_number = st.text_input("PersonID (NHS Number)")
    name = st.text_input("Name")
    age = st.number_input("Age [if never died]", 0, 300)
    is_dead = st.toggle('Is Dead')
    valid, message = validate_person(nhs_number, name)
    if st.button("Submit"):
        if valid:
            model.update_patient(nhs_number, name, age, is_dead)
            st.rerun()
        else:
            st.error('Problem with: ' + message)


@st.dialog("Enter Child")
def child():
    all_people = model.people()

    patient_id = st.selectbox("Select Child", options=all_people, index=len(all_people)-1, format_func=model.name)

    # Mother or Father can't be itself and has to be older than patient_id
    patient_age = model.age(patient_id)

    min_age_to_have_child = 10
    all_people = [a for a in all_people if a != patient_id and model.age(a) > patient_age + min_age_to_have_child]


    # Mother or Father can't be a descendant (prevent cycles)
    descendants = model.find_descendants(patient_id)
    all_people = list(set(all_people) - set(descendants))


    mother_index, father_index = None, None
    actual_mother, actual_father = model.fetch_mother(patient_id), model.fetch_father(patient_id)

    if actual_mother is not None and pd.notna(actual_mother):
        mother_index = all_people.index(actual_mother)
        
    mother = st.selectbox("Select Mother", options=all_people, index=mother_index, format_func=model.name, help='Will only show non-descendant patients that are over a decade older than the chosen child')

    all_people = [a for a in all_people if a != mother]
    
    if actual_father is not None and pd.notna(actual_father):
        father_index = all_people.index(actual_father)

    father = st.selectbox("Select Father", options=all_people, index=father_index, format_func=model.name, help='Will only show non-descendant patients that are over a decade older than the chosen child')

    if st.button("Submit"):
        model.update_child(patient_id, mother, father)
        st.rerun()


def validate_disease(id, name):
    messages = []
    if id is None or len(id)==0:
        messages += ['Missing ID']
    if name is None or len(name)==0:
        messages += ['Missing name']
    return len(messages)==0, '; '.join(messages)


@st.dialog("Enter Disease")
def disease():
    disease_ID = st.text_input("Enter disease code")
    ddisease_name = st.text_input("Enter disease name")

    valid, message = validate_disease(disease_ID, ddisease_name)
    if st.button("Submit"):
        if valid:
            model.update_disease(disease_ID,ddisease_name)
            st.rerun()
        else:
            st.error('Problem with: ' + message)


@st.dialog("Assign Disease")
def patient_disease():
    all_people = model.people()
    patient_id = st.selectbox("Select Patient", options=all_people, index=len(all_people)-1, format_func=model.name, key='select_patient_filter')

    all_diseases = model.diseases(None)
    found_diseases = model.diseases(patient_id)
    disease_ids = st.multiselect("Select Diseases", options=all_diseases, default=found_diseases, format_func=model.disease_name, key='select_disease_filter')
    if st.button("Submit"):
        model.update_diseases_for_patient(patient_id, disease_ids)
        st.rerun()



def generate_family_tree(selected_disease=None, selected_patient=None, highlighted_diseases=None, contains_all=False):

    if selected_patient is None:
        linking_df = model.get_edge_list()
    else:
        linking_df = model.filter_family_tree(selected_patient, True)

    if linking_df.empty:
        st.error('No tree can be displayed for {0}'.format(model.name(selected_patient)), icon="🚨")
        return None


    G = nx.from_pandas_edgelist(linking_df, 'source', 'target', ['relationship'], create_using=nx.DiGraph())

    pos = graphviz_layout(G, prog="dot")

    if selected_disease is not None:
        selected_disease_name = model.disease_name(selected_disease)
    
    if highlighted_diseases is None:
        highlighted_diseases = []

    highlighted_disease_text = 'Carries at least one?' if not contains_all else 'Carries all?'

    # Add attributes to nodes
    for n in G.nodes():
        G.nodes[n]['id'] = n
        G.nodes[n]['name'] = model.name(n, 'Unknown')
        G.nodes[n]['is_dead'] = 'Yes' if model.is_dead(n) else 'No'
        G.nodes[n]['age'] = model.age(n)
        G.nodes[n]['mother'] = model.fetch_parent_name(n, True)
        G.nodes[n]['father'] = model.fetch_parent_name(n, False)

        all_diseases = model.diseases(n)
        disease_str = ', '.join(map(model.disease_name, all_diseases))
        G.nodes[n]['diseases'] = disease_str

        if selected_disease is not None:
            G.nodes[n][selected_disease_name] = 'Yes' if selected_disease in all_diseases else 'No'
        
        intersection = set(all_diseases) & set(highlighted_diseases)

        
        
        if contains_all:
            condition = len(set(highlighted_diseases) - set(all_diseases))==0

        else:
            condition = len(set(all_diseases) & set(highlighted_diseases)) > 0

        G.nodes[n][highlighted_disease_text] = 'Yes' if condition else 'No'

        G.nodes[n]['selected'] = n==selected_patient
    
    for e in G.edges():
        if selected_patient is not None and (e[0]==selected_patient or e[1]==selected_patient):
            G.edges[e[0], e[1]]['selected'] = True

    

    if selected_disease is not None:
        chart = nxa.draw_networkx(
            G=G,
            pos=pos,
            width=5,
            node_color=selected_disease_name,
            cmap='set2',
            node_tooltip=['id', 'name', 'age', 'is_dead', 'father', 'mother', selected_disease_name],
            edge_color='selected',
            node_size=600)
        
        chart_edges = chart.layer[0]
        chart_b = chart.layer[1]
        chart_nodes = chart.layer[2]


        # st.write('Layer' + str(len(chart.layer)))

        chart_nodes = chart_nodes.encode(
            opacity = alt.when(alt.datum.id == selected_patient).then(alt.value(1)).otherwise(alt.value(0.9)),
            stroke=alt.when(alt.datum.id == selected_patient).then(alt.value('white')).otherwise(alt.value('black')),
            strokeWidth=alt.when(alt.datum.id == selected_patient).then(alt.value(4)).otherwise(alt.value(2)),
        )

        chart_edges = chart_edges.encode(
            opacity = alt.value(0.6)
        )

        chart = (chart_edges + chart_nodes).interactive()


    else:
        chart = nxa.draw_networkx(
            G=G,
            pos=pos,
            width=5,
            node_color=highlighted_disease_text if len(highlighted_diseases) > 0 else 'cyan',
            cmap='set2' if len(highlighted_diseases) > 0 else None,
            node_tooltip=['id', 'name', 'age', 'is_dead', 'father', 'mother', 'diseases'],
            edge_color='cyan',
            node_size=600)
        
        chart_edges = chart.layer[0]
        chart_b = chart.layer[1]
        chart_nodes = chart.layer[2]

        chart_nodes = chart_nodes.encode(
            opacity = alt.when(alt.datum.is_dead == 'Yes').then(alt.value(0.9)).otherwise(alt.value(1)),
            stroke=alt.when(alt.datum.is_dead == 'Yes').then(alt.value('gold')).otherwise(alt.value('cyan')),
            strokeWidth=alt.when(alt.datum.is_dead == 'Yes').then(alt.value(4)).otherwise(alt.value(2)),
          
        )

        chart_edges = chart_edges.encode(
            opacity = alt.value(0.6)
        )

        chart = (chart_edges + chart_nodes).interactive()
        

    return chart



st.title("AncestreeGP: Demo")
tree, raw = st.tabs(["Tree Viz", "Raw"])


with st.sidebar:

    risks = st.container(border=True)
    risks.header('Hereditary Risk')
    filter_on = risks.toggle('Determine the risk', help='When toggled it will estimate the hereditary risk and change the family tree visual for the given disease and patient')
    all_diseases = model.diseases(None)
    selected_disease = risks.selectbox('Select Disease', all_diseases, format_func=model.disease_name)
    all_people = model.people()
    selected_patient = risks.selectbox("Select Patient", options=all_people, index=len(all_people)-1, format_func=model.name)
    if not filter_on:
        selected_disease, selected_patient = None, None
    else:
        result, verdict = model.count_relatives_with_disease(selected_patient, selected_disease)
        risks.write(result.to_frame('Answer'))
        risks.markdown('Suggestion: ' + verdict)

    # manual_entry = st.toggle("Manually Enter Data")
    with  st.expander('Manual Entry'):
        if st.button("Person"):
            person()
        if st.button('Child'):
            child()
        if st.button('Disease'):
            disease()
        if st.button('Assign diseases'):
            patient_disease()
    
    cond_map = {1: 'Exclusive: carry every disease', 
                0: 'Inclusive: carry at least one disease'}
    
    highlight_diseases_condition = st.selectbox('Select disease-highlighting condition', [0, 1], 0, format_func=lambda o: cond_map[o], disabled=filter_on)


    
with tree:

    
    
    # include_disease = st.toggle('Highlight Diseases',disabled=selected_disease is not None)

    diseases = model.diseases(None)
    highlight_diseases = []

    contains_all = highlight_diseases_condition == 1
    if len(diseases) > 0:
        with st.expander('Highlight diseases'):

            # help_condtion = False

            lab='Select diseases: to highlight the patients that carry {0} of the following:'.format('all' if contains_all else 'at least one')
            highlight_diseases = st.multiselect(lab, diseases, [], format_func=model.disease_name, disabled=selected_disease is not None, )
            # contains_all = st.toggle('Highlighted nodes must carry every single disease', disabled=selected_disease is not None)
            # help_condtion = contains_all
    family_tree_chart = generate_family_tree(selected_disease, selected_patient, highlight_diseases, contains_all)
    if family_tree_chart is not None:
        st.altair_chart(family_tree_chart, use_container_width=True)


with raw:

    with st.expander('Advanced'):
        display_table = model.create_patient_summary_table()
        cols = display_table.columns
        default = ['Patient_ID', 'Name', 'Age', 'Is_Dead', 'Mother_name', 'Father_name', 'Diseases_names']
        columns = st.multiselect('Select columns', cols, default)

    st.write(display_table[columns])




