from dataclasses import dataclass
from typing import List, Optional
import pandas as pd

@dataclass
class SourceConcept:
    concept_code: str
    concept_name: str
    vocabulary_id: str
    concept_count: int

    @classmethod
    def from_row(cls, row):
        try:
            return cls(
                concept_code=str(row['source_concept_code']),
                concept_name=str(row['source_concept_name']),
                vocabulary_id=str(row['source_vocabulary_id']),
                concept_count=int(row['source_concept_count'])
            )
        ### can add other validation
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
                return False, f"Validation errors: " + "\n".join(errors)
            
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
        ### can add other validation
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
            valid_concepts = []
            errors = []
            
            for idx, row in df.iterrows():
                try:
                    concept = TargetConcept.from_row(row)
                    valid_concepts.append(concept)
                except ValueError as e:
                    errors.append(f"Row {idx}: {e}")
            
            if errors:
                return False, f"Validation errors: " + "\n".join(errors)
            
            return True, TargetConceptTable(valid_concepts)
        
        except Exception as e:
            return False, f"Error processing target concepts: {e}"
        
def read_and_validate_csv(file, tableclass):
    try:
        df = pd.read_csv(file)
        return tableclass.from_dataframe(df)
    except Exception as e:
        return False, f"Error reading CSV file: {e}"