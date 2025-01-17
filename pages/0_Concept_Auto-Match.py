import streamlit as st
import pandas as pd
import sys
import os

print("WARNING: Excessive directory traversal happening. Lawrence, avert your eyes.")
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.data_utils import SourceConceptTable, TargetConceptTable, read_and_validate_csv
from src.match_utils import ModelHandler
from src.session_utils import ProjectSession
print("It's OK you can look now.")

### Streamlit page: Concept Auto-Match
### 1) Upload source concept CSV file
### 2) Upload target concept CSV file
### 3) NLP + cosine similarity (presently hard-coded to BioLord)
### 4) Save session

def initialize_session_state():
    """
    Initialize all session states if they don't exist.

    Returns:
        Session states:
            source_table (SourceConceptTable): source concept table loaded from CSV
            target_table (TargetConceptTable): target concept table loaded from CSV
            project_name (str): Manually entered identifier for current project
            session_saved (bool): indicates if session has been saved
            similarities (numpy.ndarray): similarity score matrix
            concept_matches (List[ConceptMatch]): highest scoring matches
    """
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
    """
    Display page title and usage guide in expander panel

    Returns:
        Streamlit UI:
            Expander panel for general instructions
    """
    st.title("Concept Auto-Matching")

    with st.expander("Expand here for usage guide"):
        st.write('''
                 Functionality:
                 1) Upload table as CSV containing distinct Source Concepts
                 2) Upload table as CSV containing distinct Target Concepts
                 3) Bootstrap matching using BioLord embeddings and cosine similarity
                 4) Session is automatically saved
                 ''')
    st.divider()
    st.subheader("Upload Files For Matching")

def create_concept_dataframe(concepts, is_source=True):
    """
    Create a DataFrame from concept objects.

    Args:
        concepts (List):
            List of concept objects, either SourceConcept or TargetConcept instances
        is_source (bool):
            Indicates whether the input concepts are source (True) or target (False). Default is True.

    Returns:
        pd.DataFrame:
            Pandas dataframe containing source concept data (including new source keys) or target concept data
    """
    if is_source:
        return pd.DataFrame([
            {
                'source_key': sc.source_key,
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
    """
    Handles file upload and validation for source and target concepts.

    Args:
        filetype (str):
            Type of concept file to upload, 'source' or 'target'. Default is source.

    Returns:
        bool:
            Success state
        Session states:
            Updates source_table (SourceConceptTable) or target_table (TargetConceptTable) with uploaded concepts
        Streamlit UI:
            Expander panel to preview top 5 rows of concept dataframe
    """

    label = "Source" if file_type == 'source' else "Target"
    table_class = SourceConceptTable if file_type == 'source' else TargetConceptTable

    uploaded_file = st.file_uploader(f"Upload {label} Concepts CSV", type=['csv'])

    if uploaded_file is not None:
        read_success, result = read_and_validate_csv(uploaded_file, table_class)
        if read_success:
            state_key = f"{file_type}_table"
            st.session_state[state_key] = result
            st.success(f"{label} CSV loaded successfully!")

            with st.expander(f"Preview {file_type} concepts:"):
                df = create_concept_dataframe(result.concepts, is_source=(file_type == 'source'))
                st.dataframe(df.head())
                st.write(f"Total {file_type} concepts: {len(df)}")
            return True
        else:
            st.error(result)
            return False

    return False

def perform_concept_matching():
    """
    Generate concept similarities using BioLord model

    Returns:
        bool:
            Success state
        Session states:
            Updates similarities (numpy.ndarray) and concept_matches (List[ConceptMatch]) with outputs of NLP embedding and similarity matching
    """
    with st.spinner("Loading BioLORD model and calculating similarities..."):
        model_handler = ModelHandler()
        load_success, message = model_handler.load_model()

        if not load_success:
            st.error(f"Failed to load model: {message}")
            return False

        similarity_success, result = model_handler.get_concept_similarities(
            st.session_state.source_table,
            st.session_state.target_table
        )

        if similarity_success:
            st.session_state.similarities = result
            try:
                matches = model_handler.generate_initial_matches(
                    st.session_state.source_table,
                    st.session_state.target_table,
                    result
                )
                st.session_state.concept_matches = matches
                st.success("Similarity matrix and matches generated")
                return True
            except Exception as e:
                st.error(f"Failed to generate matches: {e}")
                return False
        else:
            st.error(f"Failed to calculate similarities: {result}")
            return False

def handle_session_save():
    """
    Handle session saving logic

    Returns:
        bool:
            Success state
        Session states:
            Updates session_saved (bool) and project_name (str) states
        Streamlit UI:
            Creates text input box for project name

    """
    project_name = st.text_input(
        "Enter a descriptive project name (no spaces)",
        key="project_name_input",
        help="Enter a nice, descriptive name to identify this mapping project"
    )

    # not currently allowing overwriting
    save_button = st.button("Save Session", disabled=not project_name or st.session_state.session_saved)

    if st.session_state.session_saved:
        st.info(f"Session already saved as project: {st.session_state.project_name}")
        return True

    if save_button:
        with st.spinner("Saving session..."):
            try:
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
                    return True
                else:
                    st.error(message)
                    return False
            except Exception as e:
                st.error(f"Error while saving session: {e}")
                return False
def main():
    initialize_session_state()
    display_header()

    # upload source and target files
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

    # Users can move onto next page to load session and perform matching
if __name__ == "__main__":
    main()