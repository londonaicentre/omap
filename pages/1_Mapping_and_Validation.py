import streamlit as st
import sys
import os
from datetime import datetime
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.session_utils import list_saved_sessions, load_session, ProjectSession

def initialize_session_state():
    """Initialize all session state variables if they don't exist."""
    session_states = {
        'session_loaded': False,
        'current_session': None,
        'page': 0,
        'modified_mappings': {},
    }

    for key, default_value in session_states.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

def load_mapping_session():
    """Handle session selection and loading."""
    success, sessions = list_saved_sessions()

    if not success:
        st.error("Failed to list sessions. Please check the sessions directory.")
        return False
    if not sessions:
        st.warning("No saved sessions found. Please create a new mapping session first.")
        return False

    session_names = [session['session_name'] for session in sessions]

    selected_session = st.selectbox(
        "Select a session to load",
        options=session_names,
        help="Choose a saved mapping session to continue"
    )

    if st.button("Load Selected Session"):
        with st.spinner("Loading session..."):
            success, result = load_session(selected_session)

            if success:
                st.session_state.current_session = result
                st.session_state.session_loaded = True
                st.rerun()
            else:
                st.error(f"Failed to load session: {result}")
                return False
    return False

def create_concept_lookups(session):
    """Create lookup dictionaries for source and target concepts."""
    source_lookup = {
        concept.source_key: concept.concept_name
        for concept in session.source_table.concepts
    }
    target_lookup = {
        concept.concept_id: concept.concept_name
        for concept in session.target_table.concepts
    }
    target_options = [
        (concept.concept_id, concept.concept_name)
        for concept in session.target_table.concepts
    ]
    return source_lookup, target_lookup, target_options

def setup_pagination(total_items, items_per_page=20):
    """Configure pagination and return current page bounds."""
    start_idx = st.session_state.page * items_per_page
    end_idx = min(start_idx + items_per_page, total_items)
    total_pages = (total_items + (items_per_page - 1)) // items_per_page

    st.write(f"Showing mappings {start_idx + 1} to {end_idx} of {total_items}")
    return start_idx, end_idx, total_pages

def display_mapping_row(idx, match, source_lookup, target_lookup, target_options):
    """Display a single mapping row with all its components."""
    with st.container():
        cols = st.columns([3, 3, 1, 1, 4])

        with cols[0]:
            st.write(f"Source: {source_lookup[match.source_key]}")
        with cols[1]:
            st.write(f"Target: {target_lookup[match.target_concept_id]}")
        with cols[2]:
            st.write(f"Score: {match.similarity_score:.3f}")
        with cols[3]:
            st.write(f"Validated: {match.validation_status}")
        with cols[4]:
            default_idx = 0
            target_choices = [("", "No Change")] + target_options

            selected = st.selectbox(
                "Update target",
                target_choices,
                default_idx,
                format_func=lambda x: x[1] if x[1] else "No Change",
                key=f"select_{idx}"
            )

            if selected[0]:
                st.session_state.modified_mappings[idx] = selected[0]
            elif idx in st.session_state.modified_mappings:
                del st.session_state.modified_mappings[idx]

def handle_navigation(total_pages):
    """Handle pagination navigation."""
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("< Previous", disabled=st.session_state.page == 0):
            st.session_state.page -= 1
            st.rerun()

    with col2:
        return st.button("CONFIRM ALL", type="primary")

    with col3:
        if st.button("Next >", disabled=st.session_state.page >= total_pages - 1):
            st.session_state.page += 1
            st.rerun()

def save_validated_mappings(session, start_idx, end_idx):
    """Save validated mappings to JSON and update session state."""
    try:
        # Update the concept matches in current session
        for idx, match in enumerate(session.concept_matches):
            if idx in st.session_state.modified_mappings:
                match.target_concept_id = st.session_state.modified_mappings[idx]
            if start_idx <= idx < end_idx:
                match.validation_status = True
                match.validation_timestamp = datetime.now()

        # Prepare and save JSON
        session_dir = f"sessions/{session.project_name}_{session.timestamp}"
        matches_path = f"{session_dir}/concept_matches.json"

        matches_json = [
            {
                "source_key": match.source_key,
                "target_concept_id": match.target_concept_id,
                "similarity_score": ("NA" if match.similarity_score == "NA"
                                  else f"{float(match.similarity_score):.3f}"),
                "validation_status": match.validation_status,
                "validation_timestamp": (match.validation_timestamp.isoformat()
                                      if match.validation_timestamp else None)
            }
            for match in session.concept_matches
        ]

        with open(matches_path, 'w') as f:
            json.dump(matches_json, f, indent=2)

        return True, "Mappings saved successfully"

    except Exception as e:
        return False, f"Failed to save matches: {e}"

def main():
    st.set_page_config(layout="wide")

    st.title("Validate Mappings")
    initialize_session_state()

    if not st.session_state.session_loaded:
        return load_mapping_session()

    session = st.session_state.current_session
    source_lookup, target_lookup, target_options = create_concept_lookups(session)
    start_idx, end_idx, total_pages = setup_pagination(len(session.concept_matches))

    # Display mappings
    for idx, match in enumerate(session.concept_matches[start_idx:end_idx]):
        global_idx = start_idx + idx
        display_mapping_row(global_idx, match, source_lookup, target_lookup, target_options)

    # Handle navigation and saving
    if handle_navigation(total_pages):
        success, message = save_validated_mappings(session, start_idx, end_idx)

        if success:
            st.session_state.modified_mappings = {}
            if st.session_state.page < total_pages - 1:
                st.session_state.page += 1
                st.success("Saved modified mappings. Moving to next page...")
                st.rerun()
            else:
                st.success("Saved mappings. This is the last page.")
                st.rerun()
        else:
            st.error(message)

if __name__ == "__main__":
    main()