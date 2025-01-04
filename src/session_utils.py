from dataclasses import dataclass
from datetime import datetime
import os
import json
import numpy as np
import pickle
from src.csv_utils import SourceConceptTable, TargetConceptTable

## TO DO
## Add docstrings

@dataclass
class ProjectSession:
    project_name: str
    timestamp: str
    source_table: SourceConceptTable
    target_table: TargetConceptTable
    similarity_matrix: np.ndarray

    @classmethod
    def create_and_save_session(cls, project_name, source_table, target_table, similarity_matrix):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session = cls(
                project_name=project_name,
                timestamp=timestamp,
                source_table=source_table,
                target_table=target_table,
                similarity_matrix=similarity_matrix
            )

            session_dir = f"sessions/{project_name}_{timestamp}"
            os.makedirs(session_dir)

            metadata = {
                'project_name': session.project_name,
                'timestamp': session.timestamp,
                'source_count': len(session.source_table.concepts),
                'target_count': len(session.target_table.concepts),
                'similarity_matrix_size': session.similarity_matrix.shape
            }

            with open(f"{session_dir}/metadata.json", 'w') as f:
                json.dump(metadata, f, indent=4)

            with open(f"{session_dir}/source_concepts.pkl", 'wb') as f:
                pickle.dump(session.source_table, f)

            with open(f"{session_dir}/target_concepts.pkl", 'wb') as f:
                pickle.dump(session.target_table, f)

            np.save(f"{session_dir}/similarities.npy", session.similarity_matrix)

            return True, f"Session saved successfully in {session_dir}"

        except Exception as e:
            return False, f"Failed to create session: {e}"
        
def list_saved_sessions(sessions_dir="sessions"):
    try:
        # put in to return empty list to streamlit if there are no active sessions
        if not os.path.exists(sessions_dir):
            return True, []
        
        session_list = []
        subdirs = os.listdir(sessions_dir)
        
        for session_name in subdirs:
            metadata_path = f"{sessions_dir}/{session_name}/metadata.json"
            
            if os.path.exists(metadata_path):
                try:
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                        metadata['session_name'] = session_name  # Add directory to access later
                        session_list.append(metadata)
                except Exception as e:
                    print(f"Error encountered on this json: {e}")
                    continue  # skip any corrupted metadata files
        
        session_list.sort(key=lambda x: x['timestamp'], reverse=True)
        return True, session_list
    
    except Exception as e:
        return False, f"Error listing sessions: {e}"

def load_session(session_name, sessions_dir="sessions"):
    try:
        full_path = f"{sessions_dir}/{session_name}"
        if not os.path.exists(full_path):
            return False, f"Session directory not found: {sessions_dir}"
        
        # Load metadata
        metadata_path = f"{full_path}/metadata.json"
        if not os.path.exists(metadata_path):
            return False, "Session metadata not found"
        
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        # Load source concepts
        source_path = f"{full_path}/source_concepts.pkl"
        if not os.path.exists(source_path):
            return False, "Source concepts file not found"
        
        with open(source_path, 'rb') as f:
            source_table = pickle.load(f)
        
        # Load target concepts
        target_path = f"{full_path}/target_concepts.pkl"
        if not os.path.exists(target_path):
            return False, "Target concepts file not found"
        
        with open(target_path, 'rb') as f:
            target_table = pickle.load(f)
        
        # Load similarity matrix
        similarity_path = f"{full_path}/similarities.npy"
        if not os.path.exists(similarity_path):
            return False, "Similarity matrix file not found"
        
        similarity_matrix = np.load(similarity_path)
        
        # Create ProjectSession object
        session = ProjectSession(
            project_name=metadata['project_name'],
            timestamp=metadata['timestamp'],
            source_table=source_table,
            target_table=target_table,
            similarity_matrix=similarity_matrix
        )
        
        return True, session
    
    except Exception as e:
        return False, f"Error loading session: {str(e)}"