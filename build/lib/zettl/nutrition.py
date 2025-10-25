# nutrition.py
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import sys
from zettl.notes import Notes
from zettl.formatting import ZettlFormatter

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
    
    def add_entry(self, content: str, past_date: Optional[str] = None) -> str:
        """
        Add a new nutrition entry.
        
        Args:
            content: The nutrition entry content
            past_date: Optional date string in YYYY-MM-DD format for backdating the entry
        
        Returns:
            The ID of the created note
        """
        # Validate format
        data = self.parse_nutrition_data(content)
        if not data:
            raise ValueError("Invalid nutrition data format. Use 'cal: XXX prot: YYY'")
        
        # Create the note with optional past date
        if past_date:
            try:
                # Validate the date format
                datetime.strptime(past_date, '%Y-%m-%d')
                # Create timestamp at noon on the specified date (to avoid timezone issues)
                timestamp = f"{past_date}T12:00:00Z"
                note_id = self.notes_manager.create_note_with_timestamp(content, timestamp)
            except ValueError:
                raise ValueError(f"Invalid date format: {past_date}. Use YYYY-MM-DD format.")
        else:
            # Create with current timestamp
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
        
        # Filter by date range
        filtered_notes = []
        for note in nutrition_notes:
            created_at = note.get('created_at', '')
            if not created_at:
                continue
                            
            try:
                # Fix for fractional seconds with less than 6 digits
                if '.' in created_at:
                    # Split into parts
                    timestamp_parts = created_at.split('.')
                    date_time = timestamp_parts[0]  # Part before decimal
                    
                    # Handle the fractional part
                    fractional = timestamp_parts[1]
                    
                    # Separate the timezone part if any
                    tz_part = ""
                    for tz_char in ['+', '-', 'Z']:
                        if tz_char in fractional:
                            fractional_parts = fractional.split(tz_char, 1)
                            fractional = fractional_parts[0]
                            tz_part = tz_char + fractional_parts[1] if len(fractional_parts) > 1 else tz_char
                            break
                    
                    # Ensure exactly 6 digits for microseconds (padding with zeros if needed)
                    fractional = fractional.ljust(6, '0')[:6]
                    
                    # Reconstruct the timestamp
                    normalized_timestamp = f"{date_time}.{fractional}{tz_part}"
                else:
                    normalized_timestamp = created_at
                    
                # Handle timezone for parsing
                if 'Z' in normalized_timestamp:
                    normalized_timestamp = normalized_timestamp.replace('Z', '+00:00')
                elif 'T' in normalized_timestamp and not any(x in normalized_timestamp[10:] for x in ['+', '-']):
                    # No timezone info - assume UTC
                    normalized_timestamp = normalized_timestamp + '+00:00'
                    
                # Parse the date with timezone awareness
                note_date = datetime.fromisoformat(normalized_timestamp)
                
                # Continue with date comparison
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
                print(f"Error processing entry {note.get('id', 'unknown')}: {str(e)}", file=sys.stderr)
                continue
        
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
                # Fix for fractional seconds with less than 6 digits
                if '.' in created_at:
                    # Split into parts
                    timestamp_parts = created_at.split('.')
                    date_time = timestamp_parts[0]  # Part before decimal
                    
                    # Handle the fractional part
                    fractional = timestamp_parts[1]
                    
                    # Separate the timezone part if any
                    tz_part = ""
                    for tz_char in ['+', '-', 'Z']:
                        if tz_char in fractional:
                            fractional_parts = fractional.split(tz_char, 1)
                            fractional = fractional_parts[0]
                            tz_part = tz_char + fractional_parts[1] if len(fractional_parts) > 1 else tz_char
                            break
                    
                    # Ensure exactly 6 digits for microseconds (padding with zeros if needed)
                    fractional = fractional.ljust(6, '0')[:6]
                    
                    # Reconstruct the timestamp
                    normalized_timestamp = f"{date_time}.{fractional}{tz_part}"
                else:
                    normalized_timestamp = created_at
                
                # Handle timezone for parsing
                if 'Z' in normalized_timestamp:
                    normalized_timestamp = normalized_timestamp.replace('Z', '+00:00')
                elif 'T' in normalized_timestamp and not any(x in normalized_timestamp[10:] for x in ['+', '-']):
                    # No timezone info - assume UTC
                    normalized_timestamp = normalized_timestamp + '+00:00'
                
                # Parse the date with timezone awareness
                note_date = datetime.fromisoformat(normalized_timestamp)
                
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
        result += f"Total Calories: [green]{total_calories:.1f}[/green]\n"
        result += f"Total Protein: [blue]{total_protein:.1f}g[/blue]\n"
        
        if entries:
            result += "\nEntries:\n"
            for entry in entries:
                created_at = entry.get('created_at', '')
                if not created_at:
                    continue
                    
                try:
                    # Fix for fractional seconds with less than 6 digits
                    if '.' in created_at:
                        # Split into parts
                        timestamp_parts = created_at.split('.')
                        date_time = timestamp_parts[0]  # Part before decimal
                        
                        # Handle the fractional part
                        fractional = timestamp_parts[1]
                        
                        # Separate the timezone part if any
                        tz_part = ""
                        for tz_char in ['+', '-', 'Z']:
                            if tz_char in fractional:
                                fractional_parts = fractional.split(tz_char, 1)
                                fractional = fractional_parts[0]
                                tz_part = tz_char + fractional_parts[1] if len(fractional_parts) > 1 else tz_char
                                break
                        
                        # Ensure exactly 6 digits for microseconds (padding with zeros if needed)
                        fractional = fractional.ljust(6, '0')[:6]
                        
                        # Reconstruct the timestamp
                        normalized_timestamp = f"{date_time}.{fractional}{tz_part}"
                    else:
                        normalized_timestamp = created_at
                    
                    # Handle timezone for parsing
                    if 'Z' in normalized_timestamp:
                        normalized_timestamp = normalized_timestamp.replace('Z', '+00:00')
                    elif 'T' in normalized_timestamp and not any(x in normalized_timestamp[10:] for x in ['+', '-']):
                        # No timezone info - assume UTC
                        normalized_timestamp = normalized_timestamp + '+00:00'
                    
                    time_str = datetime.fromisoformat(normalized_timestamp).strftime('%H:%M')
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
                    
                    result += f"[{time_str}] {ZettlFormatter.note_id(note_id)} Cal: [green]{cal:.1f}[/green], "
                    result += f"Prot: [blue]{prot:.1f}g[/blue]{description}\n"
                except Exception as e:
                    # Skip entries with formatting issues
                    import sys
                    print(f"Error formatting entry {entry.get('id', 'unknown')}: {str(e)}", file=sys.stderr)
                    continue
        
        return result
    



    def format_history(self, days: int = 7) -> str:
        """Format nutrition history with fixed-scale bars and proper alignment."""
        daily_summary = self.get_daily_summary(days=days)
        
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
        
        result += f"Average Daily Calories: [green]{avg_calories:.1f}[/green]\n"
        result += f"Average Daily Protein: [blue]{avg_protein:.1f}g[/blue]\n\n"
        
        # Show daily breakdown
        result += "Daily Breakdown:\n"
        
        for day in daily_summary:
            date_str = day['date']
            cal_value = day['calories']
            prot_value = day['protein']
            entry_count = len(day['entries'])
            
            # FIXED SCALE: 1 character = 100 calories (max 30 chars)
            cal_bar_len = min(int(cal_value / 100), 30)
            
            # FIXED SCALE: 1 character = 10g protein (max 25 chars)
            prot_bar_len = min(int(prot_value / 10), 25)
            
            # Handle special padding for values < 1000 calories
            if cal_value < 1000:
                cal_padding = 1  # One extra space for values < 1000
            else:
                cal_padding = 0
                
            # Format the calorie part with padding
            cal_part = f"{date_str}: Cal: "
            cal_value_part = f"[green]{cal_value:.1f}[/green]"

            # Create the calorie bar
            cal_bar = f"[green]{'█' * cal_bar_len}[/green]"
            
            # Add the calorie padding AFTER the value before the bar
            cal_with_padding = cal_value_part + " " * cal_padding
            
            # We want "Prot:" to be at a fixed position
            # First calculate how many visible characters we have so far
            visible_len = len(date_str) + len(": Cal: ") + len(f"{cal_value:.1f}") + cal_padding + cal_bar_len
            
            # Target position for "Prot:" - adjust as needed 
            prot_pos = 50
            
            # Calculate padding needed before "Prot:"
            prot_padding = max(0, prot_pos - visible_len)
            
            # Create protein part
            prot_label = "Prot: "
            prot_value_part = f"[blue]{prot_value:.1f}g[/blue]"

            # Add padding for protein < 100g
            if prot_value < 100:
                prot_value_padding = 1  # One extra space for values < 100g
            else:
                prot_value_padding = 0

            # Create protein bar
            prot_bar = f"[blue]{'█' * prot_bar_len}[/blue]"
            
            # Build the final line with all components and proper spacing
            line = cal_part + cal_with_padding + cal_bar
            line += " " * prot_padding + prot_label
            line += prot_value_part + " " * prot_value_padding + prot_bar
            line += f" ({entry_count} entries)"
            
            result += line + "\n"
        
        return result