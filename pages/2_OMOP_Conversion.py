import streamlit as st
import sys
import os

print("WARNING: Excessive directory traversal happening. Lawrence, avert your eyes.")
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.session_utils import list_saved_sessions, load_session
from src.omop_utils import (is_fully_mapped, assign_concept_ids, generate_concept_table, generate_relationship_table, save_tables)
print("It's OK you can look now.")

def display_header():
    """
    Display page title and usage guide in expander panel

    Returns:
        Streamlit UI:
            Expander panel for general instructions
    """
    st.title("OMOP CDM Conversion")

    with st.expander("Expand here for usage guide"):
        st.write('''
                 Functionality:
                 1) Review list of sessions that are completely mapped
                 2) Turn all sessions into OMOP CONCEPT and CONCEPT_RELATIONSHIP tables
                 3) Uses timestamp ordering of first mapping to ensure incremental source concept_ids that remain consistent across generations
                 ''')
    st.divider()

def main():
    display_header()

    success, sessions = list_saved_sessions()
    if not success:
        st.error("Failed to list sessions")
        return

    mapped_sessions = []
    for session_info in sessions:
        success, session = load_session(session_info['session_name'])
        if success and is_fully_mapped(session.concept_matches):
            mapped_sessions.append(session)

    if not mapped_sessions:
        st.warning("No fully mapped sessions found. Please complete concept mapping first.")
        return

    st.subheader("Completed Sessions")
    st.write("All concepts in these sessions are either mapped or rejected:")
    for session in mapped_sessions:
        confirmed_count = sum(1 for match in session.concept_matches if match.confirmation_status == "True")
        total_count = len(session.concept_matches)
        diff = int(total_count - confirmed_count)
        st.write(f"- {session.project_name} ({session.timestamp}), Mapped: {confirmed_count}, Rejected: {diff}")

    st.divider()

    if st.button("Generate OMOP Vocab Tables"):
        try:
            # generate concept ids
            source_key_to_id = assign_concept_ids(mapped_sessions)

            # generate tables
            concept_rows = generate_concept_table(mapped_sessions, source_key_to_id)
            relationship_rows = generate_relationship_table(mapped_sessions, source_key_to_id)
            output_dir="omop"

            # save files
            save_tables(concept_rows, relationship_rows, output_dir)

            st.success("OMOP tables generatedL")
            st.write(f"{output_dir}/CONCEPT.csv")
            st.write(f"{output_dir}/CONCEPT_RELATIONSHIP.csv")

        except Exception as e:
            st.error(f"Error during OMOP conversion: {e}")

if __name__ == "__main__":
    main()