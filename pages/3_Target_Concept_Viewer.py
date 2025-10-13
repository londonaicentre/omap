import streamlit as st
import sys
import os
import pandas as pd

print("WARNING: Excessive directory traversal happening. Lawrence, avert your eyes.")
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.session_utils import list_saved_sessions, load_session
print("It's OK you can look now.")

def initialize_session_state():
    """
    Initialize all session state variables if they don't exist

    Returns:
        Session states:
            session_loaded (bool): flag to indicate if a mapping session has been loaded
            current_session (ProjectSession): currently loaded session object
            selected_target_id (int): currently selected target concept ID
    """
    session_states = {
        'session_loaded': False,
        'current_session': None,
        'selected_target_id': None,
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
    Create lookup dictionaries and dataframes for concepts

    Args:
        session (ProjectSession):
            Project session containing source / target tables, similarities, matches, and metadata

    Returns:
        source_lookup (dict):
            Maps source_key to (concept_name, concept_code, vocabulary_id, concept_count)
        target_lookup (dict):
            Maps concept_id to (concept_name, concept_code, vocabulary_id)
        target_mapping_counts (dict):
            Maps target_concept_id to count of mappings
        target_df (pd.DataFrame):
            DataFrame of target concepts with mapping counts
        mapping_stats (dict):
            Contains statistics about mappings
    """
    # source concept lookup
    source_lookup = {
        concept.source_key: (
            concept.concept_name,
            concept.concept_code,
            concept.vocabulary_id,
            concept.concept_count
        )
        for concept in session.source_table.concepts
    }

    # target concept lookup
    target_lookup = {
        concept.concept_id: (
            concept.concept_name,
            concept.concept_code,
            concept.vocabulary_id
        )
        for concept in session.target_table.concepts
    }

    # calculate counts
    total_source_count = sum(src[3] for src in source_lookup.values())
    total_distinct_concepts = len(source_lookup)

    target_mapping_counts = {}
    target_source_counts = {}
    mapped_source_keys = set()

    for match in session.concept_matches:
        if match.confirmation_status == "True":
            target_id = match.target_concept_id
            source_key = match.source_key
            mapped_source_keys.add(source_key)

            if target_id in target_mapping_counts:
                target_mapping_counts[target_id] += 1
            else:
                target_mapping_counts[target_id] = 1

            if source_key in source_lookup:
                source_count = source_lookup[source_key][3]
                if target_id in target_source_counts:
                    target_source_counts[target_id] += source_count
                else:
                    target_source_counts[target_id] = source_count

    # calcualte statistics
    mapped_source_count = sum(target_source_counts.values())
    mapped_distinct_concepts = len(mapped_source_keys)

    mapping_stats = {
        'total_source_count': total_source_count,
        'mapped_source_count': mapped_source_count,
        'total_distinct_concepts': total_distinct_concepts,
        'mapped_distinct_concepts': mapped_distinct_concepts
    }

    # create dataframe
    target_data = []
    for target_id, count in target_mapping_counts.items():
        if target_id in target_lookup:
            target_name, target_code, target_vocab = target_lookup[target_id]
            source_count = target_source_counts.get(target_id, 0)
            percentage = (source_count / mapped_source_count) * 100 if mapped_source_count > 0 else 0

            target_data.append({
                'concept_id': target_id,
                'concept_name': target_name,
                'concept_code': target_code,
                'vocabulary_id': target_vocab,
                'mapping_count': count,
                'source_count': source_count,
                'percentage': percentage
            })

    target_df = pd.DataFrame(target_data)
    if not target_df.empty:
        target_df = target_df.sort_values('source_count', ascending=False)

    return source_lookup, target_lookup, target_mapping_counts, target_df, mapping_stats

def display_target_summary(target_df, mapping_stats):
    """
    Display summary table of target concepts and their mapping counts

    Args:
        target_df (pd.DataFrame):
            DataFrame of target concepts with mapping counts
        mapping_stats (dict):
            Statistics about mappings
    """
    st.subheader("Target Concept Mapping Summary")

    if target_df.empty:
        st.info("No confirmed mappings found in this session.")
        return

    st.dataframe(
        target_df[['concept_name', 'mapping_count', 'source_count', 'percentage', 'concept_id', 'vocabulary_id']],
        column_config={
            "concept_name": "Target Concept",
            "mapping_count": "# Source Concepts",
            "source_count": "Total Count",
            "percentage": st.column_config.NumberColumn(
                "% of Total",
                format="%.1f%%"
            ),
            "concept_id": "Concept ID",
            "vocabulary_id": "Vocabulary"
        },
        hide_index=True,
        height=600
    )

    mapped_concepts = mapping_stats['mapped_distinct_concepts']
    total_concepts = mapping_stats['total_distinct_concepts']
    mapped_count = mapping_stats['mapped_source_count']
    total_count = mapping_stats['total_source_count']

    concept_percentage = (mapped_concepts / total_concepts * 100) if total_concepts > 0 else 0
    count_percentage = (mapped_count / total_count * 100) if total_count > 0 else 0

    st.info(
        f"Mapped: {mapped_concepts}/{total_concepts} concepts ({concept_percentage:.1f}%) | "
        f"Count: {mapped_count}/{total_count} ({count_percentage:.1f}%)"
    )

def display_mapped_sources(session, source_lookup, target_lookup, target_mapping_counts):
    """
    Display all source concepts mapped to a selected target concept

    Args:
        session (ProjectSession):
            Current session
        source_lookup (dict):
            Maps source_key to source concept details
        target_lookup (dict):
            Maps concept_id to target concept details
        target_mapping_counts (dict):
            Maps target_concept_id to count of mappings
    """
    st.subheader("Mapped Source Concepts")

    # list of target ids that have mappings
    mapped_target_ids = list(target_mapping_counts.keys())

    if not mapped_target_ids:
        st.info("No confirmed mappings found in this session.")
        return

    # dropdown options
    target_options = []
    for target_id in mapped_target_ids:
        if target_id in target_lookup:
            target_name = target_lookup[target_id][0]
            count = target_mapping_counts[target_id]
            target_options.append((target_id, f"{target_name} ({count} mappings)"))

    target_options.sort(key=lambda x: target_mapping_counts[x[0]], reverse=True)

    # default selection
    default_idx = 0
    if st.session_state.selected_target_id:
        for i, (target_id, _) in enumerate(target_options):
            if target_id == st.session_state.selected_target_id:
                default_idx = i
                break

    # target select dropdown
    selected_option = st.selectbox(
        "Select Target Concept",
        options=target_options,
        index=default_idx,
        format_func=lambda x: x[1]
    )

    selected_target_id = selected_option[0]
    st.session_state.selected_target_id = selected_target_id

    current_idx = next(i for i, (tid, _) in enumerate(target_options) if tid == selected_target_id)

    col1, col2 = st.columns(2)
    with col1:
        prev_disabled = current_idx == 0
        if st.button("← Previous Target", disabled=prev_disabled):
            st.session_state.selected_target_id = target_options[current_idx - 1][0]
            st.rerun()

    with col2:
        next_disabled = current_idx == len(target_options) - 1
        if st.button("Next Target →", disabled=next_disabled):
            st.session_state.selected_target_id = target_options[current_idx + 1][0]
            st.rerun()

    target_name, target_code, target_vocab = target_lookup[selected_target_id]
    st.write(f"### {target_name}")
    st.write(f"**Concept ID:** {selected_target_id} | **Code:** {target_code} | **Vocabulary:** {target_vocab}")

    # all source concepts that are mapped to selected target
    mapped_sources = []
    for match in session.concept_matches:
        if match.confirmation_status == "True" and match.target_concept_id == selected_target_id:
            source_key = match.source_key
            if source_key in source_lookup:
                source_name, source_code, source_vocab, source_count = source_lookup[source_key]
                mapped_sources.append({
                    'source_key': source_key,
                    'source_name': source_name,
                    'source_code': source_code,
                    'source_vocab': source_vocab,
                    'source_count': source_count
                })

    mapped_sources.sort(key=lambda x: x['source_count'], reverse=True)

    # display the mapped sources
    if mapped_sources:
        source_df = pd.DataFrame(mapped_sources)
        st.dataframe(
            source_df[['source_name', 'source_count', 'source_code', 'source_vocab']],
            column_config={
                "source_name": "Source Concept",
                "source_count": "Count",
                "source_code": "Code",
                "source_vocab": "Vocabulary"
            },
            hide_index=True
        )
    else:
        st.info(f"No source concepts are mapped to this target concept.")

def main():
    st.set_page_config(layout="wide", page_title="Target Concept Viewer")

    st.title("Target Concept Viewer")

    with st.expander("Expand here for usage guide"):
        st.write('''
            This page allows you to validate and review your concept mappings:
            1. The left panel shows a summary of all target concepts with mapping counts
            2. The right panel lets user select a target concept and view all source concepts mapped to it
            3. The summary at the bottom shows mapping completion metrics
        ''')

    initialize_session_state()

    if not st.session_state.session_loaded:
        load_mapping_session()
    else:
        session = st.session_state.current_session
        source_lookup, target_lookup, target_mapping_counts, target_df, mapping_stats = create_concept_lookups(session)

        # Two-column layout
        left_col, right_col = st.columns([1, 1])

        with left_col:
            display_target_summary(target_df, mapping_stats)

        with right_col:
            display_mapped_sources(session, source_lookup, target_lookup, target_mapping_counts)

if __name__ == "__main__":
    main()