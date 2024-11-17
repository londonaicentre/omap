import streamlit as st
import pandas as pd
import sys
import os

## TO DO
## Documented expected data structured in expander
## The sourceid:targetid mapping should be saved as .json to use in HITL  
## ??TO SET UP AS PACKAGE AGAIN TO AVOID SETTING PATH IN CODE

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.csv_utils import SourceConceptTable, TargetConceptTable, read_and_validate_csv
from src.match_utils import ModelHandler
from src.session_utils import ProjectSession 

def main():
    # header
    st.title("Source & Target Concept Upload")
    with st.expander("Expand here for usage guide"):
        st.write('''
                 Functionality:
                 (1) Upload table as CSV containing distinct Source Concepts
                 (2) Upload table as CSV containing distinct Target Concepts
                 (3) Bootstrap matching using BioLord embeddings and cosine similarity
                 (4) Session is automatically saved 
                 ''') 

    # set session states
    # (note that streamlit re-runs per interaction)
    if 'source_table' not in st.session_state:
        st.session_state.source_table = None
    if 'target_table' not in st.session_state:
        st.session_state.target_table = None
    if 'project_name' not in st.session_state:
        st.session_state.project_name = None
    if 'session_saved' not in st.session_state:
        st.session_state.session_saved = False
    if 'similarities' not in st.session_state:
        st.session_state.similarities = None        

    # source file uploader
    source_file = st.file_uploader("Upload Source Concepts CSV", type=['csv'])
    
    if source_file is not None:
        success, result = read_and_validate_csv(source_file, SourceConceptTable)
        if success:
            st.session_state.source_table = result
            st.success("Source CSV loaded successfully!")
            
            source_df = pd.DataFrame([
                {
                    'source_concept_code': sc.concept_code,
                    'source_concept_name': sc.concept_name,
                    'source_vocabulary_id': sc.vocabulary_id,
                    'source_concept_count': sc.concept_count
                } for sc in result.concepts
            ])
            
            st.write(f"Total source concepts: {len(source_df)}")
            st.dataframe(source_df.head())

        else:
            st.error(result)

    # target file uploader
    target_file = st.file_uploader("Upload Target Concepts CSV", type=['csv'])

    if target_file is not None:
        success, result = read_and_validate_csv(target_file, TargetConceptTable)
        if success:
            st.session_state.target_table = result
            st.success("Target CSV loaded successfully!")
            
            target_df = pd.DataFrame([
                {
                    'concept_id': tc.concept_id,
                    'concept_code': tc.concept_code,
                    'concept_name': tc.concept_name,
                    'vocabulary_id': tc.vocabulary_id
                } for tc in result.concepts
            ])
            
            st.write(f"Total target concepts: {len(target_df)}")
            st.dataframe(target_df.head())         

        else:
            st.error(result)

    # generate cosine similarity
    # only display if both source and target files are uploaded and validated
    if st.session_state.source_table is not None and st.session_state.target_table is not None:
        st.divider()
        st.subheader("Generate Concept Similarities")
    
        if 'similarities' not in st.session_state:
            st.session_state.similarities = None
            
        if st.button("Perform Concept Matching"):
            with st.spinner("Loading BioLORD model..."):
                model_handler = ModelHandler()
                success, message = model_handler.load_model()
                
                if not success:
                    st.error(f"Failed to load model: {message}")
                else:
                    st.info("Model loaded successfully. Calculating similarities...")
                    
                    success, result = model_handler.get_concept_similarities(
                        st.session_state.source_table,
                        st.session_state.target_table
                    )
                    
                    if success:
                        st.session_state.similarities = result
                        st.success(f"Similarity matrix generated successfully")
                        
                    else:
                        st.error(f"Failed to calculate similarities: {result}")
                        
        elif st.session_state.similarities is not None:
            st.success("Similarity matrix already generated and stored in session state.")
            st.write(f"Matrix shape: {st.session_state.similarities.shape}")
            
    # save session
    if st.session_state.similarities is not None and not st.session_state.session_saved:
        st.divider()
        st.subheader("Save Project Session")
        
        project_name = st.text_input(
            "Enter project name",
            key="project_name_input",
            help="Enter a name to identify this mapping project"
        )
        
        if project_name and st.button("Save Session"):
            with st.spinner("Saving session..."):
                success, message = ProjectSession.create_and_save_session(
                    project_name=project_name,
                    source_table=st.session_state.source_table,
                    target_table=st.session_state.target_table,
                    similarity_matrix=st.session_state.similarities
                )
                
                if success:
                    st.session_state.session_saved = True
                    st.session_state.project_name = project_name
                    st.success(message)
                else:
                    st.error(message)
    
    elif st.session_state.similarities is not None and st.session_state.session_saved:
        st.info(f"Session already saved as project: {st.session_state.project_name}")

if __name__ == "__main__":
    main()