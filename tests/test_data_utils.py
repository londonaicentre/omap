import pytest
import data_utils
import session_utils

@pytest.fixture
def sample_mappings():
    """Returns a list of sample concept mappings for testing."""
    return [
        session_utils.ConceptMatch(source_key=1, target_concept_id=1001, similarity_score=0.9, confirmation_status="False", first_confirmation_timestamp=None, last_update_timestamp=None),
        session_utils.ConceptMatch(source_key=2, target_concept_id=1002, similarity_score=0.8, confirmation_status="True", first_confirmation_timestamp=None, last_update_timestamp=None),
        session_utils.ConceptMatch(source_key=3, target_concept_id=1003, similarity_score=0.85, confirmation_status="Rejected", first_confirmation_timestamp=None, last_update_timestamp=None),
        session_utils.ConceptMatch(source_key=4, target_concept_id=1004, similarity_score=0.7, confirmation_status="False", first_confirmation_timestamp=None, last_update_timestamp=None),
    ]

@pytest.fixture
def sample_source_lookup():
    """Returns a dictionary to mock source concept names."""
    return {
        1: "Buprenorphine",
        2: "Paracetamol",
        3: "Ibuprofen",
        4: "Clopidogrel",
    }

# TEST 1: Filtering works correctly
def test_filter_for_unconfirmed_mappings(sample_mappings):
    filtered = data_utils.filter_for_unconfirmed_mappings(sample_mappings)
    assert len(filtered) == 2  # Only the two "False" ones should remain
    assert all(match.confirmation_status == "False" for match in filtered)

# TEST 2: Sorting by A-Z works
def test_sort_concepts_alphabetical(sample_mappings, sample_source_lookup):
    sorted_mappings = data_utils.sort_concepts(sample_mappings, sample_source_lookup, sort_option="Alphabetical (A-Z)")
    sorted_names = [sample_source_lookup[m.source_key] for m in sorted_mappings]
    assert sorted_names == sorted(sorted_names)  # Should be sorted alphabetically

# TEST 3: Sorting by confidence works
def test_sort_concepts_highest_confidence(sample_mappings, sample_source_lookup):
    sorted_mappings = data_utils.sort_concepts(sample_mappings, sample_source_lookup, sort_option="Highest Confidence")
    sorted_scores = [m.similarity_score for m in sorted_mappings]
    assert sorted_scores == sorted(sorted_scores, reverse=True)  # Should be sorted highest to lowest