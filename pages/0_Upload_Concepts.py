import streamlit as st
import pandas as pd
import sys
import os

## TO DO
## ADD CACHING OF CSV/DF + BUTTON TO CLEAR STATE AND CACHE
## TO ADD INSTRUCTIONS TO EXPANDER
## ??TO SET UP AS PACKAGE AGAIN TO AVOID SETTING PATH IN CODE

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.csv_utils import SourceConceptTable, TargetConceptTable, read_and_validate_csv

def main():
    st.title("Source & Target Concept Upload")
    with st.expander("Expand here for usage guide"):
        st.write('''
                 ...Add expected structured and types here.
                 ''') 

    ## set session state
    if 'source_table' not in st.session_state:
        st.session_state.source_table = None
    if 'target_table' not in st.session_state:
        st.session_state.target_table = None

    ## source file uploader
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

    ## target file uploader
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

if __name__ == "__main__":
    main()