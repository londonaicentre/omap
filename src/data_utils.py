from dataclasses import dataclass
import hashlib
import pandas as pd
from datetime import datetime

## TO DO
## Add docstrings

def generate_source_key(concept_code, concept_name, vocabulary_id):
    """
    Each distinct source concept is given a 'source_key' as a unique identifier
    This is used to track concepts during mapping
    """
    concat_string = f"{concept_code}_{concept_name}_{vocabulary_id}"
    hash_obj = hashlib.sha256(concat_string.encode())
    # Get first 8 bytes of hash, modulo to 9 digit key
    hash_int = int.from_bytes(hash_obj.digest()[:8], 'big')
    return hash_int % 1000000000

@dataclass
class SourceConcept:
    source_key: int
    concept_code: str
    concept_name: str
    vocabulary_id: str
    concept_count: int

    @classmethod
    def from_row(cls, row):
        try:
            source_key = generate_source_key(
                str(row['source_concept_code']),
                str(row['source_concept_name']),
                str(row['source_vocabulary_id'])
            )
            return cls(
                source_key = source_key,
                concept_code=str(row['source_concept_code']),
                concept_name=str(row['source_concept_name']),
                vocabulary_id=str(row['source_vocabulary_id']),
                concept_count=int(row['source_concept_count'])
            )
        except ValueError as e:
            raise ValueError(f"Type conversion failed: {e}")

class SourceConceptTable:
    source_columns = ['source_concept_code', 'source_concept_name', 'source_vocabulary_id', 'source_concept_count']

    def __init__(self, concepts):
       self.concepts = concepts

    def from_dataframe(df):
        if not all(col in df.columns for col in SourceConceptTable.source_columns):
            return False, f"Missing required columns. Expected: {SourceConceptTable.source_columns}"

        try:
            valid_concepts = []
            errors = []

            for idx, row in df.iterrows():
                try:
                    concept = SourceConcept.from_row(row)
                    valid_concepts.append(concept)
                except ValueError as e:
                    errors.append(f"Row {idx}: {e}")

            if errors:
                return False, f"confirmation errors: " + "\n".join(errors)

            return True, SourceConceptTable(valid_concepts)

        except Exception as e:
            return False, f"Error processing source concepts: {e}"

@dataclass
class TargetConcept:
    concept_id: int
    concept_code: str
    concept_name: str
    vocabulary_id: str

    @classmethod
    def from_row(cls, row):
        try:
            return cls(
                concept_id=int(row['concept_id']),
                concept_code=str(row['concept_code']),
                concept_name=str(row['concept_name']),
                vocabulary_id=str(row['vocabulary_id'])
            )
        ### can add other confirmation
        except ValueError as e:
            raise ValueError(f"Type conversion failed: {e}")

class TargetConceptTable:
    target_columns = ['concept_id','concept_code', 'concept_name', 'vocabulary_id']

    def __init__(self, concepts):
        self.concepts = concepts

    def from_dataframe(df):
        if not all(col in df.columns for col in TargetConceptTable.target_columns):
            return False, f"Missing required columns. Expected: {TargetConceptTable.target_columns}"

        try:
            # target concepts must always has a 'no match' option
            # this is the official OMOP representation of 'no matchign concept'
            valid_concepts = [
                TargetConcept(
                    concept_id=0,
                    concept_code='No matching concept',
                    concept_name='No matching concept',
                    vocabulary_id='None'
                )
            ]
            errors = []

            for idx, row in df.iterrows():
                try:
                    concept = TargetConcept.from_row(row)
                    valid_concepts.append(concept)
                except ValueError as e:
                    errors.append(f"Row {idx}: {e}")

            if errors:
                return False, f"confirmation errors: " + "\n".join(errors)

            return True, TargetConceptTable(valid_concepts)

        except Exception as e:
            return False, f"Error processing target concepts: {e}"


def get_source_concept_name(match, source_lookup):
    """Fetches the source concept name for a given match from the source lookup dictionary."""
    return source_lookup.get(match.source_key, ("", 0))[0].lower()  # Extract name, ignore count

def sort_concepts(concept_matches, source_lookup, sort_option="None"):
    """Sorts the list of concept matches based on user choice."""
    if sort_option == "Alphabetical (A-Z)":
        return sorted(concept_matches, key=lambda match: get_source_concept_name(match, source_lookup))
    elif sort_option == "Alphabetical (Z-A)":
        return sorted(concept_matches, key=lambda match: get_source_concept_name(match, source_lookup), reverse=True)
    elif sort_option == "Highest Confidence":
        return sorted(concept_matches, key=lambda match: match.similarity_score, reverse=True)
    elif sort_option == "Lowest Confidence":
        return sorted(concept_matches, key=lambda match: match.similarity_score)
    return concept_matches  # Default: return unsorted list


def filter_for_unconfirmed_mappings(concept_matches):
    """
    Filters out confirmed mappings, keeping only those where confirmation_status is 'False'.
    """
    # Filter only mappings where confirmation_status is exactly False
    filtered_matches = [match for match in concept_matches if str(match.confirmation_status).lower() == "false"]
    return filtered_matches


@dataclass
class ConceptMatch:
    source_key: int
    target_concept_id: int
    similarity_score: float
    confirmation_status: str #"True", "False", "Rejected" -> to define w/ enum
    first_confirmation_timestamp: datetime | None
    last_update_timestamp: datetime | None

def read_and_validate_csv(file, tableclass):
    try:
        df = pd.read_csv(file)
        return tableclass.from_dataframe(df)
    except Exception as e:
        return False, f"Error reading CSV file: {e}"

