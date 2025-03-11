# graph.py
from typing import List, Dict, Any
import json
from zettl.database import Database

class NoteGraph:
    def __init__(self):
        self.db = Database()
    
    def generate_graph_data(self, center_note_id: str = None, depth: int = 1) -> Dict[str, Any]:
        """Generate a graph representation of notes and their connections."""
        nodes = []
        edges = []
        processed_note_ids = set()
        
        # Process each note only once
        def process_note(note_id: str, current_depth: int):
            if current_depth > depth or note_id in processed_note_ids:
                return
                
            processed_note_ids.add(note_id)
            
            try:
                # Get the note from the cached method
                note = self.db.get_note(note_id)
                
                # Add node
                title = note['content'][:30] + "..." if len(note['content']) > 30 else note['content']
                nodes.append({
                    "id": note_id,
                    "label": note_id,
                    "title": title
                })
                
                # Get connections - ideally, this would be cached too
                outgoing_result = self.db.client.table('links').select('*').eq('source_id', note_id).execute()
                
                # Add edges for outgoing connections
                if outgoing_result.data:
                    for link in outgoing_result.data:
                        target_id = link['target_id']
                        edges.append({
                            "from": note_id,
                            "to": target_id
                        })
                        
                        # Process the connected note recursively
                        if current_depth < depth:
                            process_note(target_id, current_depth + 1)
            except Exception:
                # Skip notes that can't be processed
                pass
        
        # If center_note_id is provided, start from that note
        if center_note_id:
            process_note(center_note_id, 1)
        else:
            # Otherwise, get all notes
            notes_result = self.db.client.table('notes').select('id').execute()
            if notes_result.data:
                for note_data in notes_result.data:
                    process_note(note_data['id'], 1)
        
        return {
            "nodes": nodes,
            "edges": edges
        }
        
    def export_graph(self, file_path: str, center_note_id: str = None, depth: int = 1) -> None:
        """Export the graph data to a JSON file."""
        graph_data = self.generate_graph_data(center_note_id, depth)
        
        with open(file_path, 'w') as f:
            json.dump(graph_data, f, indent=2)
            
        return file_path