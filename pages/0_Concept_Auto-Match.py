import streamlit as st
import pandas as pd
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.data_utils import SourceConceptTable, TargetConceptTable, read_and_validate_csv
from src.match_utils import ModelHandler
from src.session_utils import ProjectSession 

def initialize_session_state():
    """Initialize all session state variables if they don't exist."""
    session_states = {
        'source_table': None,
        'target_table': None,
        'project_name': None,
        'session_saved': False,
        'similarities': None,
        'concept_matches': None
    }
    
    for key, default_value in session_states.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

def display_header():
    """Display page title and usage guide."""
    st.title("Concept Auto-Matching")
    
    with st.expander("Expand here for usage guide"):
        st.write('''
                 Functionality:
                 (1) Upload table as CSV containing distinct Source Concepts
                 (2) Upload table as CSV containing distinct Target Concepts
                 (3) Bootstrap matching using BioLord embeddings and cosine similarity
                 (4) Session is automatically saved 
                 ''')
    st.divider()
    st.subheader("Upload Files For Matching")

def create_concept_dataframe(concepts, is_source=True):
    """Create a DataFrame from concept objects."""
    if is_source:
        return pd.DataFrame([
            {
                'source_concept_id': sc.concept_id,                        
                'source_concept_code': sc.concept_code,
                'source_concept_name': sc.concept_name,
                'source_vocabulary_id': sc.vocabulary_id,
                'source_concept_count': sc.concept_count
            } for sc in concepts
        ])
    else:
        return pd.DataFrame([
            {
                'concept_id': tc.concept_id,
                'concept_code': tc.concept_code,
                'concept_name': tc.concept_name,
                'vocabulary_id': tc.vocabulary_id
            } for tc in concepts
        ])

def handle_file_upload(file_type='source'):
    """Handle file upload and validation for source or target concepts."""
    label = "Source" if file_type == 'source' else "Target"
    table_class = SourceConceptTable if file_type == 'source' else TargetConceptTable
    
    uploaded_file = st.file_uploader(f"Upload {label} Concepts CSV", type=['csv'])
    
    if uploaded_file is not None:
        success, result = read_and_validate_csv(uploaded_file, table_class)
        if success:
            state_key = f"{file_type}_table"
            st.session_state[state_key] = result
            st.success(f"{label} CSV loaded successfully!")
            
            with st.expander(f"Preview {file_type} concepts:"):
                df = create_concept_dataframe(result.concepts, is_source=(file_type == 'source'))
                st.dataframe(df.head())
                st.write(f"Total {file_type} concepts: {len(df)}")
        else:
            st.error(result)

def perform_concept_matching():
    """Generate concept similarities using the model."""
    with st.spinner("Loading BioLORD model and calculating similarities..."):
        model_handler = ModelHandler()
        success, message = model_handler.load_model()
        
        if not success:
            st.error(f"Failed to load model: {message}")
            return
            
        success, result = model_handler.get_concept_similarities(
            st.session_state.source_table,
            st.session_state.target_table
        )
        
        if success:
            st.session_state.similarities = result
            matches = model_handler.generate_initial_matches(
                st.session_state.source_table,
                st.session_state.target_table,
                result
            )
            st.session_state.concept_matches = matches
            st.success("Similarity matrix and matches generated")
        else:
            st.error(f"Failed to calculate similarities: {result}")

def handle_session_save():
    """Handle session saving logic."""
    project_name = st.text_input(
        "Enter a descriptive project name (no spaces)",
        key="project_name_input",
        help="Enter a nice, descriptive name to identify this mapping project"
    )
    
    save_button = st.button("Save Session", disabled=not project_name or st.session_state.session_saved)
    
    if st.session_state.session_saved:
        st.info(f"Session already saved as project: {st.session_state.project_name}")
        return
        
    if save_button:
        with st.spinner("Saving session..."):
            success, message = ProjectSession.create_and_save_session(
                project_name=project_name,
                source_table=st.session_state.source_table,
                target_table=st.session_state.target_table,
                similarity_matrix=st.session_state.similarities,
                concept_matches=st.session_state.concept_matches
            )
            
            if success:
                st.session_state.session_saved = True
                st.session_state.project_name = project_name
                st.success(message)
                st.info("Concept matches saved for HITL validation")
            else:
                st.error(message)

def main():
    initialize_session_state()
    display_header()
    
    # Handle file uploads
    handle_file_upload('source')
    handle_file_upload('target')
    
    # Generate similarities if both files are loaded
    if st.session_state.source_table is not None and st.session_state.target_table is not None:
        st.divider()
        st.subheader("Generate Concept Similarities")
        
        if st.button("Perform Concept Matching"):
            perform_concept_matching()
        elif st.session_state.similarities is not None:
            st.success("Similarity matrix and matches generated")
    
    # Save session if similarities are generated
    if st.session_state.similarities is not None and st.session_state.concept_matches is not None:
        st.divider()
        st.subheader("Save Project Session")
        handle_session_save()

if __name__ == "__main__":
    main()