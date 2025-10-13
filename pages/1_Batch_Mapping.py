import streamlit as st
import sys
import os
import pandas as pd
from datetime import datetime

print("WARNING: Excessive directory traversal happening. Lawrence, avert your eyes.")
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.session_utils import list_saved_sessions, load_session, ProjectSession
print("It's OK you can look now.")

### Streamlit page: Batch Mapping
### 1) Load saved mapping session
### 2) Filter source concepts by string
### 3) Select a target concept to map to
### 4) Select multiple source concepts via checkboxes
### 5) Confirm mapping for all selected source concepts

### TO DO
### 1. Optimisation. At moment relies on list load/check against state on each tick/untick!!
### 2. Refactor. Most functions are recycled from 0_Concept_Auto-Match and 2_Mapping_And_Validation.
### 3. Bug. In confirm_selected_mappings, selected_sources state fails to clear all checkboxes
### 4. Bug. Per 3, clear checkboxes button fails to clear all.

def initialize_session_state():
    """
    Returns:
        Session states:
            session_loaded (bool): flag to indicate if a mapping session loaded
            current_session (ProjectSession): currently loaded session object
            search_term (str): current search term for filtering source concepts
            selected_target_id (int): currently selected target concept
            selected_sources (list): list of selected source concept keys
            show_unconfirmed_only (bool): flag to show only unconfirmed mappings
    """
    session_states = {
        'session_loaded': False,
        'current_session': None,
        'search_term': '',
        'selected_target_id': None,
        'selected_sources': [],
        'show_unconfirmed_only': False,
    }

    for key, default_value in session_states.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

def display_header():
    st.title("Batch Concept Mapping")

    with st.expander("Expand here for usage guide"):
        st.write('''
                 Functionality:
                 1) Load a saved mapping session
                 2) Filter source concepts by a search string (case-insensitive)
                 3) Select a target concept for mapping
                 4) Use checkboxes to select multiple source concepts
                 5) Confirm mappings for all selected source concepts at once
                 6) Unselected concepts remain unchanged
                 ''')
    st.divider()

def load_mapping_session():
    """
    Handle session selection and loading

    Returns:
        bool:
            False if session loading fails or is not yet complete
        Session states:
            Updates current_session (ProjectSession) on load, and session_loaded (bool) flag
        Streamlit UI:
            Selectbox for choosing saved session
    """
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

def create_concept_lookups(session):
    """
    Create lookup dictionaries from session concepts.

    Args:
        session (ProjectSession):
            Project session containing source / target tables, similarities, matches, and metadata

    Returns:
        tuple:
            source_df (pd.DataFrame):
                df of source concepts
            target_df (pd.DataFrame):
                df of target concepts
            source_key_to_idx (dict):
                maps source_key to index in concept_matches
    """
    source_df = create_concept_dataframe(session.source_table.concepts, is_source=True)
    target_df = create_concept_dataframe(session.target_table.concepts, is_source=False)

    source_key_to_idx = {}
    for idx, match in enumerate(session.concept_matches):
        source_key_to_idx[match.source_key] = idx

    return source_df, target_df, source_key_to_idx

def display_top_unmapped_concepts(source_df, source_key_to_idx, session):
    """
    Display the top 20 most common source concepts that are not yet confirmed.
    This helps users choose what keywords to search.

    Args:
        source_df (pd.DataFrame):
            df of source concepts
        source_key_to_idx (dict):
            Maps source_key to index in concept_matches
        session (ProjectSession):
            Current session

    Returns:
        Streamlit UI:
            Expander showing unmapped concepts
    """
    unmapped_concepts = []

    for _, row in source_df.iterrows():
        source_key = row['source_key']
        idx = source_key_to_idx.get(source_key)

        if idx is not None:
            match = session.concept_matches[idx]
            # check if concepts are confirmed or not
            if str(match.confirmation_status).lower() != "true" and match.confirmation_status != "Rejected":
                unmapped_concepts.append({
                    'source_key': source_key,
                    'concept_name': row['source_concept_name'],
                    'concept_count': row['source_concept_count']
                })

    # sort by count
    top_unmapped = sorted(unmapped_concepts, key=lambda x: x['concept_count'], reverse=True)[:20]

    # expander to take up less space
    with st.expander("Top 20 Unmapped Concepts"):
        if not top_unmapped:
            st.info("All concepts have been mapped.")
        else:
            data_rows = []
            for concept in top_unmapped:
                data_rows.append([concept['concept_count'], concept['concept_name']])

            st.table({
                'Count': [row[0] for row in data_rows],
                'Concept Name': [row[1] for row in data_rows]
            })


def filter_source_concepts(source_df, search_term):
    """
    Filter source concepts by search term (case-insensitive)
    Supports multiple words with AND logic

    Args:
        source_df (pd.DataFrame):
            df of source concepts
        search_term (str):
            Search term to filter by

    Returns:
        pd.DataFrame: Filtered DataFrame of source concepts
    """
    if not search_term or len(search_term) < 2:
        return pd.DataFrame(columns=source_df.columns)  # return empty if char length

    # split and lowercase...
    search_words = search_term.lower().split()

    # filter on each word
    filtered_df = source_df.copy()
    for word in search_words:
        if len(word) >= 2:
            filtered_df = filtered_df[filtered_df['source_concept_name'].str.lower().str.contains(word)]

    return filtered_df

def display_search_and_target_selection(source_df, target_df):
    """
    Display search box and target concept selection dropdown

    Args:
        source_df (pd.DataFrame):
            df of source concepts
        target_df (pd.DataFrame):
            ff of target concepts

    Returns:
        Streamlit UI:
            search box, target concept list
        Session states:
            Updates states for search_term and selected_target_id
    """
    col1, col2 = st.columns(2)

    with col1:
        search_term = st.text_input(
            "Filter source concepts (case-insensitive, multiple words = AND)",
            value=st.session_state.search_term,
            key="search_input",
            placeholder="Enter search terms (min 2 characters per word)"
        )
        if search_term != st.session_state.search_term:
            st.session_state.search_term = search_term
            st.rerun()

        show_unconfirmed = st.checkbox(
            "Show unconfirmed mappings only",
            value=st.session_state.show_unconfirmed_only,
            key="unconfirmed_filter"
        )
        if show_unconfirmed != st.session_state.show_unconfirmed_only:
            st.session_state.show_unconfirmed_only = show_unconfirmed
            st.rerun()

    with col2:
        # target dropdown
        target_options = [(row['concept_id'], f"{row['concept_name']} ({row['concept_id']})")
                          for _, row in target_df.iterrows()]

        if len(target_options) > 0 and target_options[0][0] != 0:
            target_options.insert(0, (0, "No matching concept (0)"))

        selected_target = st.selectbox(
            "Select target concept",
            options=target_options,
            format_func=lambda x: x[1],
            key="target_selection"
        )

        if selected_target[0] != st.session_state.selected_target_id:
            st.session_state.selected_target_id = selected_target[0]

    filtered_df = filter_source_concepts(source_df, st.session_state.search_term)

    # stop search term being 1 letter
    if len(st.session_state.search_term) < 2:
        st.info("Please enter at least 2 characters to search.")
    else:
        st.write(f"Found {len(filtered_df)} source concepts matching your search criteria")

    return filtered_df

def display_source_concepts_with_checkboxes(filtered_df, source_key_to_idx, session):
    """
    Display filtered source concepts with checkboxes and current mapping status.

    Args:
        filtered_df (pd.DataFrame):
            Filtered df of source concepts
        source_key_to_idx (dict):
            Maps source_key to index in concept_matches
        session (ProjectSession):
            Current session

    Returns:
        Streamlit UI:
            Table of source concepts, checkboxes, current status
        Session states:
            Updates selected_sources
    """
    if st.session_state.selected_sources is None or len(st.session_state.selected_sources) == 0:
        st.session_state.selected_sources = []

    display_data = []
    for _, row in filtered_df.iterrows():
        source_key = row['source_key']
        idx = source_key_to_idx.get(source_key)
        if idx is not None:
            match = session.concept_matches[idx]

            # skip confirmed if filter is active
            if st.session_state.show_unconfirmed_only and str(match.confirmation_status).lower() == "true":
                continue

            target_name = "Unknown"
            for concept in session.target_table.concepts:
                if concept.concept_id == match.target_concept_id:
                    target_name = concept.concept_name
                    break

            display_data.append({
                'source_key': source_key,
                'concept_name': row['source_concept_name'],
                'concept_count': row['source_concept_count'],
                'current_target': f"{target_name} ({match.target_concept_id})",
                'status': match.confirmation_status
            })

    if display_data:
        display_df = pd.DataFrame(display_data)

        st.write("Select source concepts to map:")

        # # causing selection bugs
        # all_selected = st.checkbox("Select All Displayed Results", key="select_all")
        # if all_selected:
        #     for _, row in display_df.iterrows():
        #         if row['source_key'] not in st.session_state.selected_sources:
        #             st.session_state.selected_sources.append(row['source_key'])

        with st.container():
            headings = st.columns([0.5, 3, 1, 3, 1])
            with headings[0]:
                st.write("Select")
            with headings[1]:
                st.write("Source Concept")
            with headings[2]:
                st.write("Count")
            with headings[3]:
                st.write("Current Target")
            with headings[4]:
                st.write("Status")

        for i, row in display_df.iterrows():
            with st.container():
                cols = st.columns([0.5, 3, 1, 3, 1])
                with cols[0]:
                    # checkbox if source already selected populate key
                    is_selected = row['source_key'] in st.session_state.selected_sources
                    checkbox = st.checkbox("", value=is_selected, key=f"cb_{row['source_key']}")

                    # update session state oneach iteration
                    # This is VERY SLOW. Likely better way to do this.
                    if checkbox and row['source_key'] not in st.session_state.selected_sources:
                        st.session_state.selected_sources.append(row['source_key'])
                    elif not checkbox and row['source_key'] in st.session_state.selected_sources:
                        st.session_state.selected_sources.remove(row['source_key'])

                with cols[1]:
                    st.write(row['concept_name'])
                with cols[2]:
                    st.write(row['concept_count'])
                with cols[3]:
                    st.write(row['current_target'])
                with cols[4]:
                    st.write(row['status'])

    elif len(st.session_state.search_term) >= 2:
        if st.session_state.show_unconfirmed_only:
            st.info("No unconfirmed source concepts found matching search criteria.")
        else:
            st.info("No source concepts found matching search criteria.")

def confirm_selected_mappings(session, source_key_to_idx):
    """
    Save confirmed mappings for selected source concepts

    Args:
        session (ProjectSession):
            Current session
        source_key_to_idx (dict):
            Maps source_key to index in concept_matches

    Returns:
        bool:
            True if save successful, False otherwise
    """
    if not st.session_state.selected_sources:
        st.warning("No source concepts selected. Please select at least one source concept.")
        return False

    if st.session_state.selected_target_id is None:
        st.warning("No target concept selected. Please select a target concept.")
        return False

    try:
        # update for selected sources
        updated_count = 0
        for source_key in st.session_state.selected_sources:
            idx = source_key_to_idx.get(source_key)
            if idx is not None:
                match = session.concept_matches[idx]
                match.target_concept_id = st.session_state.selected_target_id
                match.similarity_score = -1.0
                match.confirmation_status = "True" if st.session_state.selected_target_id != 0 else "Rejected"

                # update timestamps
                if match.first_confirmation_timestamp is None:
                    match.first_confirmation_timestamp = datetime.now()
                match.last_update_timestamp = datetime.now()

                updated_count += 1

        # save to file
        session_dir = f"sessions/{session.project_name}_{session.timestamp}"
        matches_path = f"{session_dir}/concept_matches.json"

        matches_json = [
            {
                "source_key": match.source_key,
                "target_concept_id": match.target_concept_id,
                "similarity_score": (f"{float(match.similarity_score):.2f}"),
                "confirmation_status": match.confirmation_status,
                "first_confirmation_timestamp": (match.first_confirmation_timestamp.isoformat()
                                            if match.first_confirmation_timestamp else None),
                "last_update_timestamp": (match.last_update_timestamp.isoformat()
                                      if match.last_update_timestamp else None)
            }
            for match in session.concept_matches
        ]

        import json
        with open(matches_path, 'w') as f:
            json.dump(matches_json, f, indent=2)

        # clear selections on save
        # this sometimes fails to clear, unclear why
        st.session_state.selected_sources = []

        return True, f"Successfully updated {updated_count} mappings"

    except Exception as e:
        return False, f"Failed to save mappings: {e}"

def display_buttons():
    col1, col2 = st.columns(2)

    with col1:
        confirm_button = st.button("CONFIRM SELECTED", type="primary")

    # with col2:
    #     # clear_button = st.button("Clear Selections")
    #     # if clear_button:
    #     #     st.session_state.selected_sources = []
    #     #     st.rerun()

    with col2:
        selected_count = len(st.session_state.selected_sources) if st.session_state.selected_sources else 0
        st.write(f"Selected: {selected_count} concept(s)")

    return confirm_button

def main():
    st.set_page_config(layout="wide")

    initialize_session_state()
    display_header()

    if not st.session_state.session_loaded:
        return load_mapping_session()

    session = st.session_state.current_session
    source_df, target_df, source_key_to_idx = create_concept_lookups(session)

    display_top_unmapped_concepts(source_df, source_key_to_idx, session)

    st.subheader("Search and Select")
    filtered_df = display_search_and_target_selection(source_df, target_df)

    st.divider()
    display_source_concepts_with_checkboxes(filtered_df, source_key_to_idx, session)

    st.divider()
    confirm_button = display_buttons()

    if confirm_button:
        success, message = confirm_selected_mappings(session, source_key_to_idx)
        if success:
            st.success(message)
            st.rerun()
        else:
            st.error(message)

if __name__ == "__main__":
    main()