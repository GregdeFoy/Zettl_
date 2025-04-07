# nutrition.py
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import sys
from zettl.notes import Notes
from zettl.formatting import ZettlFormatter, Colors

class NutritionTracker:
    def __init__(self):
        self.notes_manager = Notes()
    
    def parse_nutrition_data(self, content: str) -> Dict[str, float]:
        """Parse nutrition data from note content."""
        result = {}
        
        # Extract calories
        cal_match = re.search(r'cal\s*:\s*(\d+\.?\d*)', content.lower())
        if cal_match:
            result['calories'] = float(cal_match.group(1))
        
        # Extract protein
        prot_match = re.search(r'prot\s*:\s*(\d+\.?\d*)', content.lower())
        if prot_match:
            result['protein'] = float(prot_match.group(1))
        
        return result
    
    def add_entry(self, content: str) -> str:
        """Add a new nutrition entry."""
        # Validate format
        data = self.parse_nutrition_data(content)
        if not data:
            raise ValueError("Invalid nutrition data format. Use 'cal: XXX prot: YYY'")
        
        # Create the note
        note_id = self.notes_manager.create_note(content)
        
        # Tag it with 'nutrition'
        self.notes_manager.add_tag(note_id, "nutrition")
        
        return note_id
    
    def get_entries_for_date_range(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get nutrition entries for a date range."""
        # Force invalidate any relevant caches to ensure fresh data
        self.notes_manager.db.invalidate_cache("tags:nutrition")
        
        # Get all nutrition notes - force a fresh query
        nutrition_notes = self.notes_manager.get_notes_by_tag("nutrition")
        
        # Make start_date and end_date timezone-aware if they aren't already
        import sys
        from datetime import timezone
        
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        
        # Debug info
        # print(f"Start date: {start_date}, End date: {end_date}", file=sys.stderr)
        
        # Filter by date range
        filtered_notes = []
        for note in nutrition_notes:
            created_at = note.get('created_at', '')
            if not created_at:
                continue
                
            try:
                # Normalize the datetime string
                if 'Z' in created_at:
                    created_at = created_at.replace('Z', '+00:00')
                elif 'T' in created_at and not ('+' in created_at or '-' in created_at[10:]):
                    # No timezone info - assume UTC
                    created_at = created_at + '+00:00'
                
                # Parse the date
                note_date = datetime.fromisoformat(created_at)
                
                # Ensure note_date is timezone-aware
                if note_date.tzinfo is None:
                    note_date = note_date.replace(tzinfo=timezone.utc)
                
                # Debug info
                # print(f"Note: {note['id']}, Date: {note_date}", file=sys.stderr)
                
                # Compare only the date parts, ignoring time
                note_date_only = note_date.date()
                start_date_only = start_date.date()
                end_date_only = end_date.date()
                
                if start_date_only <= note_date_only <= end_date_only:
                    # Parse the nutrition data
                    note_data = self.parse_nutrition_data(note['content'])
                    if note_data:  # Only include if it has valid nutrition data
                        note['nutrition_data'] = note_data
                        filtered_notes.append(note)
            except Exception as e:
                # Log the error with the note ID for debugging
                import sys
                print(f"Error processing note {note.get('id', 'unknown')}: {str(e)}", file=sys.stderr)
                continue
        
        # Debug info
        # print(f"Found {len(filtered_notes)} filtered notes", file=sys.stderr)
        
        return filtered_notes
    
    def get_today_entries(self) -> List[Dict]:
        """Get nutrition entries for today."""
        from datetime import timezone
        
        # Make both dates timezone-aware with UTC
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
        tomorrow = today + timedelta(days=1)
        
        return self.get_entries_for_date_range(today, tomorrow)
    
    def get_daily_summary(self, start_date: Optional[datetime] = None, 
                        end_date: Optional[datetime] = None, 
                        days: int = 7) -> List[Dict]:
        """Get daily summary of nutrition for a date range."""
        from datetime import timezone
        
        # Make sure we work with timezone-aware datetimes consistently
        if not start_date:
            end_date = datetime.now().replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
            start_date = end_date - timedelta(days=days-1)
            start_date = start_date.replace(hour=0, minute=0, second=0)
        elif not end_date:
            end_date = start_date + timedelta(days=days)
        
        # Ensure timezone awareness for both dates
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        
        # Get all entries in the date range
        entries = self.get_entries_for_date_range(start_date, end_date)
        
        # Group by date
        daily_summaries = {}
        for entry in entries:
            created_at = entry.get('created_at', '')
            if not created_at:
                continue
                
            try:
                # Normalize the datetime string
                if 'Z' in created_at:
                    created_at = created_at.replace('Z', '+00:00')
                elif 'T' in created_at and not ('+' in created_at or '-' in created_at[10:]):
                    # No timezone info - assume UTC
                    created_at = created_at + '+00:00'
                
                # Parse the date with timezone awareness
                note_date = datetime.fromisoformat(created_at)
                
                # Ensure note_date is timezone-aware
                if note_date.tzinfo is None:
                    note_date = note_date.replace(tzinfo=timezone.utc)
                
                # Use date without time as key - converted to string for dictionary key
                note_date_only = note_date.date()
                date_key = note_date_only.isoformat()
                
                # Initialize if needed
                if date_key not in daily_summaries:
                    daily_summaries[date_key] = {
                        'date': date_key,
                        'calories': 0,
                        'protein': 0,
                        'entries': []
                    }
                
                # Add this entry's data
                data = entry['nutrition_data']
                daily_summaries[date_key]['calories'] += data.get('calories', 0)
                daily_summaries[date_key]['protein'] += data.get('protein', 0)
                daily_summaries[date_key]['entries'].append(entry)
            except Exception as e:
                # Skip entries with date parsing issues
                import sys
                print(f"Error processing entry {entry.get('id', 'unknown')}: {str(e)}", file=sys.stderr)
                continue
        
        # Convert to list and sort by date
        result = list(daily_summaries.values())
        result.sort(key=lambda x: x['date'])
        
        return result
    
    def format_today_summary(self) -> str:
        """Format today's nutrition summary for display."""
        entries = self.get_today_entries()
        
        # Calculate totals
        total_calories = sum(entry['nutrition_data'].get('calories', 0) for entry in entries)
        total_protein = sum(entry['nutrition_data'].get('protein', 0) for entry in entries)
        
        # Fix for nested f-strings - separate them
        header_text = f"Today's Nutrition Summary ({len(entries)} entries)"
        header = ZettlFormatter.header(header_text)
        result = f"{header}\n"
        result += f"Total Calories: {Colors.GREEN}{total_calories:.1f}{Colors.RESET}\n"
        result += f"Total Protein: {Colors.BLUE}{total_protein:.1f}g{Colors.RESET}\n"
        
        if entries:
            result += "\nEntries:\n"
            for entry in entries:
                created_at = entry.get('created_at', '')
                if not created_at:
                    continue
                    
                try:
                    # Handle different ISO formats
                    if 'Z' in created_at:
                        created_at = created_at.replace('Z', '+00:00')
                    elif 'T' in created_at and not ('+' in created_at or '-' in created_at[10:]):
                        # No timezone info - assume UTC
                        created_at = created_at + '+00:00'
                    
                    time_str = datetime.fromisoformat(created_at).strftime('%H:%M')
                    cal = entry['nutrition_data'].get('calories', 0)
                    prot = entry['nutrition_data'].get('protein', 0)
                    note_id = entry['id']
                    
                    # Get full content but remove the cal/prot parts for display
                    content = entry['content']
                    content = re.sub(r'cal\s*:\s*\d+\.?\d*', '', content, flags=re.IGNORECASE)
                    content = re.sub(r'prot\s*:\s*\d+\.?\d*', '', content, flags=re.IGNORECASE)
                    content = content.strip()
                    
                    # Add description if present
                    description = f" - {content}" if content else ""
                    
                    result += f"[{time_str}] {ZettlFormatter.note_id(note_id)} Cal: {Colors.GREEN}{cal:.1f}{Colors.RESET}, "
                    result += f"Prot: {Colors.BLUE}{prot:.1f}g{Colors.RESET}{description}\n"
                except Exception:
                    # Skip entries with formatting issues
                    continue
        
        return result
    
    def format_history(self, days: int = 7) -> str:
        """Format nutrition history for display."""
        daily_summary = self.get_daily_summary(days=days)
        
        # Fix for nested f-strings - separate them
        header_text = f"Nutrition History ({days} days)"
        header = ZettlFormatter.header(header_text)
        result = f"{header}\n"
        
        if not daily_summary:
            result += "No nutrition entries found for this period.\n"
            return result
        
        # Calculate overall stats
        total_days = len(daily_summary)
        total_calories = sum(day['calories'] for day in daily_summary)
        total_protein = sum(day['protein'] for day in daily_summary)
        avg_calories = total_calories / total_days if total_days > 0 else 0
        avg_protein = total_protein / total_days if total_days > 0 else 0
        
        result += f"Average Daily Calories: {Colors.GREEN}{avg_calories:.1f}{Colors.RESET}\n"
        result += f"Average Daily Protein: {Colors.BLUE}{avg_protein:.1f}g{Colors.RESET}\n\n"
        
        # Show daily breakdown
        result += "Daily Breakdown:\n"
        
        # Find maximum values for visual scaling
        max_calories = max((day['calories'] for day in daily_summary), default=1)
        max_protein = max((day['protein'] for day in daily_summary), default=1)
        
        for day in daily_summary:
            date_str = day['date']
            
            # Create simple bar charts using characters
            cal_bar_len = int(20 * (day['calories'] / max_calories)) if max_calories > 0 else 0
            prot_bar_len = int(10 * (day['protein'] / max_protein)) if max_protein > 0 else 0
            
            cal_bar = Colors.GREEN + "█" * cal_bar_len + Colors.RESET
            prot_bar = Colors.BLUE + "█" * prot_bar_len + Colors.RESET
            
            result += f"{date_str}: Cal: {Colors.GREEN}{day['calories']:.1f}{Colors.RESET} {cal_bar}, "
            result += f"Prot: {Colors.BLUE}{day['protein']:.1f}g{Colors.RESET} {prot_bar} "
            result += f"({len(day['entries'])} entries)\n"
        
        return result