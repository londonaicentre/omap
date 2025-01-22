import streamlit as st
import sys
import os
from datetime import datetime
import json

print("WARNING: Excessive directory traversal happening. Lawrence, avert your eyes.")
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.session_utils import list_saved_sessions, load_session, ProjectSession
print("It's OK you can look now.")

### Streamlit page: Mapping / confirmation
### 1) Load saved mapping session
### 2) Display paginated mapping pairs with confirmation status
### 3) Allow target concept updates through dropdown selection and track metadata
### 4) Save updated mappings to JSON on confirmation

def initialize_session_state():
    """
    Initialize all session state variables if they don't exist

    Returns:
        Session states:
            session_loaded (bool): flag to indicate if a mapping session has been loaded
            current_session (ProjectSession): currently loaded session object
            page (int): current page number to track pagination
            modified_mappings (dict): dictionary that stores modified mapping state
    """
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

def create_concept_lookups(session):
    """
    Create lookup dictionaries and list of replacement options from session concepts. Mappings are stored on unique key pairs, rather than multiple strings.

    Args:
        session (ProjectSession):
            Project session containing source / target tables, similarities, matches, and metadata

    Returns:
        tuple:
            source_lookup (dict): Maps source_key to (concept_name, concept_count)
            target_lookup (dict): Maps concept_id to concept_name
            target_options (list): List of (concept_id, concept_name) tuples for dropdown options
    """
    source_lookup = {
        concept.source_key: (concept.concept_name, concept.concept_count)
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
    """
    Configure pagination and calculate current page bounds. This is performed for active page.

    Args:
        total_items (int):
            Total number of items required to paginate across
        items_per_page (int):
            Number of items to display per page. Default as 20

    Returns:
        tuple:
            start_idx (int): Starting index for current page
            end_idx (int): Ending index for current page
            total_pages (int): Total number of pages
        Streamlit UI:
            Dsplay showing current page range
    """
    # First calculate start index based on current page number
    # e.g. page 0 -> start at 0, page 1 -> start at 20, page 2 -> start at 40
    start_idx = st.session_state.page * items_per_page

    # end index must not exceed total items
    # e.g. 45 total items and are on page 2 (start 40), end must be 45, not 60
    end_idx = min(start_idx + items_per_page, total_items)

    # Calculate total pages, rounding up
    # e.g. 45 items, 20 per page -> (45 + 19) // 20 = 3 pages
    total_pages = (total_items + (items_per_page - 1)) // items_per_page

    st.write(f"Showing mappings {start_idx + 1} to {end_idx} of {total_items}")
    return start_idx, end_idx, total_pages


def display_headings():
    """
    Creates and displays headings for below columns

    Returns:
        Streamlit UI:
            Row of column headings aligned to mapping content
    """

    with st.container():
        headings = st.columns([1, 3, 3, 1, 1, 3, 1])

        with headings[0]:
            st.write(f"Count")
        with headings[1]:
            st.write(f"Source Concepts")
        with headings[2]:
            st.write(f"Target Concepts")
        with headings[3]:
            st.write(f"Similarity")
        with headings[4]:
            st.write(f"Confirmation")
        with headings[5]:
            st.write(f"Modify Target")
        with headings[6]:
            st.write(f"")

def display_mapping_row(idx, match, source_lookup, target_lookup, target_options):
    """
    Creates and displays a single concept mapping row which includes source, target, score, confirmation status and dropdown selector for update.

    Args:
        idx (int):
            Index of the mapping row
        match (ConceptMatch):
            Concept match object (source_key to target concept_id) with similarity_score + confirmation flag
        source_lookup (dict):
            Dictionary mapping source_key to source concept_name
        target_lookup (dict):
            Dictionary mapping concept_id to target concept_name
        target_options (list):
            List of (concept_id, concept_name) tuples for target selection dropdown

    Returns:
        Session states:
            Updates modified_mappings (dict) of modified target mappings
        Streamlit UI:
            Container with 5 columns per mapping row
    """
    with st.container():
        cols = st.columns([1, 3, 3, 1, 1, 3, 1])

        source_name, source_count = source_lookup[match.source_key]

        with cols[0]:
            st.write(f"{source_count}")
        with cols[1]:
            st.write(f"{source_name}")
        with cols[2]:
            st.write(f"{target_lookup[match.target_concept_id]}")
        with cols[3]:
            st.write(f"{match.similarity_score:.2f}")
        with cols[4]:
            st.write(f"{match.confirmation_status}")
        with cols[5]:
            default_idx = 0
            target_choices = [("", "No Change")] + target_options

            selected = st.selectbox(
                "Select target",
                target_choices,
                default_idx,
                format_func=lambda x: x[1], # redundant -> if x[1] else "No Change",
                key=f"select_{idx}",
                label_visibility="collapsed"
            )

            if selected[0] is not None and selected[0] != "":
                st.session_state.modified_mappings[idx] = selected[0]
            elif idx in st.session_state.modified_mappings:
                del st.session_state.modified_mappings[idx]
        with cols[6]:
            # set confirmation flag for where unconfirmed (no intervention), or where intervention occurs (idx stored)
            needs_confirmation = not match.confirmation_status or idx in st.session_state.modified_mappings
            # activate button when confirmation task possible
            confirm_row = st.button("Confirm", key=f"confirm_{idx}", disabled=not needs_confirmation)
            if confirm_row:
                success, message = save_single_mapping(st.session_state.current_session, idx)
                if success:
                    st.rerun()
                else:
                    st.error(message)

def handle_navigation(total_pages):
    """
    Handle pagination navigation and mapping confirmation interface

    Args:
        total_pages (int):
            Total number of available pages

    Returns:
        bool:
            True if CONFIRM ALL button is clicked, False otherwise
        Session states:
            page (int) is updated on Previous/Next clicks
        Streamlit UI:
            Three columns containing previous, confiurm, next buttons
    """
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        prev = st.button("< Previous", disabled=st.session_state.page == 0)
        if prev:
            st.session_state.page -= 1
            st.rerun()

    with col2:
        confirm = st.button("CONFIRM ALL", type="primary")

    with col3:
        reject = st.button("REJECT UNCONFIRMED", type="secondary")

    with col4:
        next = st.button("Next >", disabled=st.session_state.page >= total_pages-1)
        if next:
            st.session_state.page += 1
            st.rerun()

    return confirm, reject

def save_confirmed_mappings(session, start_idx, end_idx):
    """
    Save confirmed concept mappings to JSON and update current session

    Args:
        session (ProjectSession):
            Project session containing source / target tables, similarities, matches, and metadata
        start_idx (int):
            Start index of current page
        end_idx (int):
            End index of current page

    Returns:
        bool:
            True if save successful, False otherwise
        Session states:
            current_session (ProjectSession) is updated by passing new targets from modified_mappings.
            confirmation_status is set to True, and timestamp added.
    """
    try:
        for idx, match in enumerate(session.concept_matches):

            # If idx has been updated it is in modified_mappings state -> update the target_concept_id in project session to match
            if idx in st.session_state.modified_mappings:
                if st.session_state.modified_mappings[idx] == "":  # No Change
                    match.confirmation_status = "True"
                else:
                    match.target_concept_id = st.session_state.modified_mappings[idx] # align to whichever new concept
                    match.similarity_score = -1.0
                    match.confirmation_status = "Rejected" if match.target_concept_id == 0 else "True" # handle where user selects 'no match''
                match.confirmation_timestamp = datetime.now()

            # if there are unconfirmed matches on current page that are NOT modified (i.e. No Change by default), these can be confirmed
            elif start_idx <= idx < end_idx and match.confirmation_status != "Rejected":
                match.confirmation_status = "True"  # confirm the existing mapping
                match.confirmation_timestamp = datetime.now()

        # Prepare and save JSON
        session_dir = f"sessions/{session.project_name}_{session.timestamp}"
        matches_path = f"{session_dir}/concept_matches.json"

        matches_json = [
            {
                "source_key": match.source_key,
                "target_concept_id": match.target_concept_id,
                "similarity_score": (f"{float(match.similarity_score):.2f}"),
                "confirmation_status": match.confirmation_status,
                "confirmation_timestamp": (match.confirmation_timestamp.isoformat()
                                      if match.confirmation_timestamp else None)
            }
            for match in session.concept_matches
        ]

        with open(matches_path, 'w') as f:
            json.dump(matches_json, f, indent=2)

        # clean up all modified mappings
        st.session_state.modified_mappings = {}

        return True, "Mappings saved successfully"

    except Exception as e:
        return False, f"Failed to save matches: {e}"

def save_single_mapping(session, row_idx):
    """
    Save a single confirmed concept mapping to JSON

    Args:
        session (ProjectSession):
            Project session containing source / target tables, similarities, matches, and metadata
        row_idx (int):
            Index of the row being confirmed

    Returns:
        bool:
            True if save successful, False otherwise
        Session states:
            current_session (ProjectSession) is updated by passing new target (single row) from modified_mappings.
            confirmation_status for single mapping is set to True, and timestamp added.
    """
    try:
        single_match = session.concept_matches[row_idx]

        # for particular row id only, swap in from modified_mappings, and clear entry
        if row_idx in st.session_state.modified_mappings:
            single_match.target_concept_id = st.session_state.modified_mappings[row_idx]
            single_match.similarity_score = -1.0
            del st.session_state.modified_mappings[row_idx]
            # if the target concept is 'no matching' then confirmation status should be "Rejected"
            single_match.confirmation_status = "Rejected" if single_match.target_concept_id == 0 else "True"
        else:
            single_match.confirmation_status = "True"

        single_match.confirmation_timestamp = datetime.now()

        session_dir = f"sessions/{session.project_name}_{session.timestamp}"
        matches_path = f"{session_dir}/concept_matches.json"

        # even though we have updated only a single mapping, we still dump the entire object as json
        matches_json = [
            {
                "source_key": match.source_key,
                "target_concept_id": match.target_concept_id,
                "similarity_score": (f"{float(match.similarity_score):.2f}"),
                "confirmation_status": match.confirmation_status,
                "confirmation_timestamp": (match.confirmation_timestamp.isoformat()
                                      if match.confirmation_timestamp else None)
            }
            for match in session.concept_matches
        ]

        with open(matches_path, 'w') as f:
            json.dump(matches_json, f, indent=2)

        return True, "Row confirmed successfully"

    except Exception as e:
        return False, f"Failed to save match: {e}"

def reject_unconfirmed_mappings(session, start_idx, end_idx):
    """
    Rejects all unconfirmed mappings on page. Sets target concept as 0, saves to JSON

    Args:
        session (ProjectSession):
            Project session containing source / target tables, similarities, matches, and metadata
        start_idx (int):
            Start index of current page
        end_idx (int):
            End index of current page

    Returns:
        bool:
            True if save successful, False otherwise
        Session states:
            current_session (ProjectSession) is updated by passing new targets from modified_mappings.
            confirmation_status is set to Rejected, and timestamp added.
    """
    try:
        for idx in range(start_idx, end_idx):
            match = session.concept_matches[idx]
            # reject any unconfirmed mappings
            if match.confirmation_status != "True":
                match.target_concept_id = 0
                match.similarity_score = -1.0
                match.confirmation_status = "Rejected"
                match.confirmation_timestamp = datetime.now()

        # Prepare and save JSON
        session_dir = f"sessions/{session.project_name}_{session.timestamp}"
        matches_path = f"{session_dir}/concept_matches.json"

        matches_json = [
            {
                "source_key": match.source_key,
                "target_concept_id": match.target_concept_id,
                "similarity_score": (f"{float(match.similarity_score):.2f}"),
                "confirmation_status": match.confirmation_status,
                "confirmation_timestamp": (match.confirmation_timestamp.isoformat()
                                      if match.confirmation_timestamp else None)
            }
            for match in session.concept_matches
        ]

        with open(matches_path, 'w') as f:
            json.dump(matches_json, f, indent=2)

        # clean up all modified mappings
        st.session_state.modified_mappings = {}

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
    display_headings()

    for idx, match in enumerate(session.concept_matches[start_idx:end_idx]):
        global_idx = start_idx + idx
        display_mapping_row(global_idx, match, source_lookup, target_lookup, target_options)

    # Handle navigation and saving
    confirm_clicked, reject_clicked = handle_navigation(total_pages)

    if confirm_clicked:
        success, message = save_confirmed_mappings(session, start_idx, end_idx)

        if success:
            if st.session_state.page < total_pages - 1:
                #st.session_state.page += 1
                st.success("Saved modified mappings.")
                st.rerun()
            else:
                st.success("Saved mappings. This is the last page.")
                st.rerun()
        else:
            st.error(message)

    elif reject_clicked:
        success, message = reject_unconfirmed_mappings(session, start_idx, end_idx)

        if success:
            if st.session_state.page < total_pages - 1:
                #st.session_state.page += 1
                st.success("Rejected unconfirmed mappings.")
                st.rerun()
            else:
                st.success("Rejected unconfirmed mappings. This is the last page.")
                st.rerun()
        else:
            st.error(message)

if __name__ == "__main__":
    main()