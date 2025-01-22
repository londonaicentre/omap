from datetime import datetime, date
from dataclasses import dataclass
import pandas as pd
import os

@dataclass
class ConceptRow:
    concept_id: int
    concept_name: str
    domain_id: str
    vocabulary_id: str
    concept_class_id: str
    standard_concept: str
    concept_code: str
    valid_start_date: date
    valid_end_date: date
    invalid_reason: str

@dataclass
class ConceptRelationshipRow:
    concept_id_1: int
    concept_id_2: int
    relationship_id: str
    valid_start_date: date
    valid_end_date: date
    invalid_reason: str

def is_fully_mapped(concept_matches):
    """
    Check if all concepts in session are confirmed or rejected
    """
    fully_mapped = all(match.confirmation_status in ["True", "Rejected"] for match in concept_matches)

    return fully_mapped

def assign_concept_ids(sessions, base_id=2000000001):
    """
    Assign incremental concept IDs to source concepts across all sessions
    Ensures that if there is a duplicate source_key (i.e. same concept across multiple sessions) then this is flagged
    """
    source_concepts = []

    # collect all concepts
    # there is probably a way to do this more cleanly, instead of nested loops
    for session in sessions:
        for match in session.concept_matches:
            if match.confirmation_status == "True" or match.confirmation_status == "Rejected":
                # grab source concept details
                source = None
                for concept in session.source_table.concepts:
                    if concept.source_key == match.source_key:
                        source = concept
                        break
                source_concepts.append({
                    'source_key': source.source_key,
                    'timestamp': match.first_confirmation_timestamp,
                    'concept_name': source.concept_name,
                    'concept_code': source.concept_code
                })

    # CHECK FOR DUPLICATES
    source_keys = [c['source_key'] for c in source_concepts]
    if len(source_keys) != len(set(source_keys)):
        duplicate_keys = [k for k in set(source_keys) if source_keys.count(k) > 1]
        duplicates = [c for c in source_concepts if c['source_key'] in duplicate_keys]
        raise ValueError(f"Duplicate source keys found: {duplicates}")

    # sort and assign incremental OMOP concept_ids per method discussed @LAdams/@drjzhn
    sorted_concepts = sorted(source_concepts,
                           key=lambda x: (x['timestamp'], x['concept_name'], x['concept_code']))

    source_key_to_id = {}
    current_id = base_id

    for concept in sorted_concepts:
        if concept['source_key'] not in source_key_to_id:
            source_key_to_id[concept['source_key']] = current_id
            current_id += 1

    return source_key_to_id

def generate_concept_table(sessions, source_key_to_id):
    """
    Generate OMOP.CONCEPT table rows
    """
    concept_rows = []

    for session in sessions:
        for match in session.concept_matches:
            if match.source_key in source_key_to_id:
                # grab source concept details
                source = None
                for concept in session.source_table.concepts:
                    if concept.source_key == match.source_key:
                        source = concept
                        break
                # append to OMOP
                concept_rows.append(ConceptRow(
                    concept_id=source_key_to_id[match.source_key],
                    concept_name=source.concept_name,
                    domain_id='',
                    vocabulary_id=source.vocabulary_id,
                    concept_class_id='',
                    standard_concept='N',
                    concept_code=source.concept_code,
                    valid_start_date=match.last_update_timestamp.date(),
                    valid_end_date=date(2099, 12, 31),
                    invalid_reason=None
                ))

    return concept_rows

def generate_relationship_table(sessions, source_key_to_id):
    """
    Generate OMOP.CONCEPT_RELATIONSHIP table rows
    """
    relationship_rows = []

    for session in sessions:
        for match in session.concept_matches:
            if match.source_key in source_key_to_id:
                relationship_rows.append(ConceptRelationshipRow(
                    concept_id_1=source_key_to_id[match.source_key],
                    concept_id_2=match.target_concept_id,
                    relationship_id='Maps to',
                    valid_start_date=match.last_update_timestamp.date(),
                    valid_end_date=date(2099, 12, 31),
                    invalid_reason=None
                ))
                relationship_rows.append(ConceptRelationshipRow(
                    concept_id_1=match.target_concept_id,
                    concept_id_2=source_key_to_id[match.source_key],
                    relationship_id='Maps from',
                    valid_start_date=match.last_update_timestamp.date(),
                    valid_end_date=date(2099, 12, 31),
                    invalid_reason=None
                ))

    return relationship_rows

def save_tables(concept_rows, relationship_rows, output_dir="omop"):
    """
    Save tables as CSV files
    """
    os.makedirs(output_dir, exist_ok=True)

    concept_df = pd.DataFrame([vars(row) for row in concept_rows])
    concept_df.to_csv(f"{output_dir}/CONCEPT.csv", index=False)

    relationship_df = pd.DataFrame([vars(row) for row in relationship_rows])
    relationship_df.to_csv(f"{output_dir}/CONCEPT_RELATIONSHIP.csv", index=False)