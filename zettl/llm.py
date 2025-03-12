# llm.py
import os
import re
from typing import List, Dict, Any, Optional, Union
from zettl.database import Database
from zettl.config import CLAUDE_API_KEY

class LLMHelper:
    def __init__(self):
        self.db = Database()
        self.api_key = CLAUDE_API_KEY
        self.model = "claude-3-7-sonnet-20250219"  # Using the latest model
        self._client = None  # Lazy-loaded client
        
    @property
    def client(self):
        """Lazy-load the Anthropic client."""
        if self._client is None:
            try:
                import anthropic
            except ImportError:
                raise ImportError(
                    "The anthropic package is not installed. "
                    "Install it with: pip install anthropic"
                )
                
            if not self.api_key:
                raise ValueError("Claude API key not found. Check the configuration.")
                
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client
        
    def _prepare_note_context(self, note_ids: List[str]) -> str:
        """Prepare a context string from multiple notes."""
        context = ""
        
        for note_id in note_ids:
            try:
                note = self.db.get_note(note_id)
                context += f"Note #{note_id}:\n{note['content']}\n\n"
            except Exception as e:
                print(f"Warning: Could not retrieve note {note_id}: {str(e)}")
                continue
                
        return context
        
    def _call_llm_api(self, prompt: str, system_message: str = None, max_tokens: int = 1000) -> str:
        """
        Call Claude API to generate a response using the Anthropic package.
        
        Args:
            prompt: The user message to send to Claude
            system_message: Optional system message to guide Claude's behavior
            max_tokens: Maximum number of tokens in the response
            
        Returns:
            String response from Claude
            
        Raises:
            Exception: If the API call fails or returns an invalid response
        """
        # Default system message if none provided
        if not system_message:
            system_message = "You are a helpful assistant for a Zettelkasten note-taking system."
            
        try:
            # Call the API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_message,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract text from response
            text_blocks = []
            for content_block in response.content:
                if hasattr(content_block, 'text'):
                    text_blocks.append(content_block.text)
            
            if text_blocks:
                return "\n".join(text_blocks)
            else:
                raise Exception("No text content in Claude's response")
                
        except Exception as e:
            # Handle API errors with clear messages
            error_msg = str(e)
            
            # Add context based on error type
            if "rate limit" in error_msg.lower():
                error_msg = f"Rate limit exceeded: {error_msg}. Try again in a moment."
            elif "authentication" in error_msg.lower() or "auth" in error_msg.lower():
                error_msg = f"Authentication error: {error_msg}. Check your API key."
            elif "content policy" in error_msg.lower() or "harmful" in error_msg.lower():
                error_msg = f"Content policy violation: {error_msg}. Try with different input."
            
            raise Exception(f"API request failed: {error_msg}")
        
    def summarize_note(self, note_id: str) -> str:
        """
        Summarize a single note using Claude.
        
        Args:
            note_id: ID of the note to summarize
            
        Returns:
            A concise summary of the note
        """
        try:
            note = self.db.get_note(note_id)
            
            system_message = """You are an expert assistant for a Zettelkasten note-taking system. 
Your task is to provide clear, concise summaries of notes while preserving the key ideas.
Focus on extracting the core concepts, and present them in well-structured format.
Your summary should be significantly shorter than the original note but capture its essence."""
            
            prompt = f"""Please summarize the following note concisely, preserving the main ideas and their relationships:

## Note #{note_id}
{note['content']}

Provide a summary that captures the essence of this note in 2-3 sentences."""
            
            return self._call_llm_api(prompt, system_message, max_tokens=300)
            
        except Exception as e:
            return f"Error summarizing note: {str(e)}"
        
    def generate_connections(self, note_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Find potential connections between this note and others.
        
        Args:
            note_id: ID of the note to find connections for
            limit: Maximum number of connections to return
            
        Returns:
            List of dictionaries containing note_id and explanation of the connection
        """
        try:
            note = self.db.get_note(note_id)
            
            # Get tags for the source note
            source_tags = self.db.get_tags(note_id)
            
            # Get other notes to compare with
            other_notes = self.db.list_notes(30)
            other_notes = [n for n in other_notes if n['id'] != note_id]
            
            if not other_notes:
                return []
                
            system_message = """You are an expert assistant for a Zettelkasten note-taking system.
    Your specialized skill is finding meaningful conceptual connections between ideas across different notes.
    Focus on identifying substantial relationships based on:
    1. Shared concepts or themes
    2. Complementary or contradictory ideas
    3. Potential cause-effect relationships
    4. Applications of one idea to another domain
    5. Shared or related tags

    For each connection, provide a clear, specific explanation of how the notes relate to each other.
    Pay special attention to the tags associated with each note, as they often indicate key concepts or themes."""
            
            # Prepare prompt with the target note
            prompt = f"""I need to find meaningful connections between notes in my Zettelkasten system.

    Here is the source note I want to connect to other notes:

    ## Note #{note_id}
    {note['content']}
    Tags: {', '.join(source_tags) if source_tags else 'None'}

    Here are other notes in my system. Please identify the top {limit} notes that have the strongest conceptual connection to Note #{note_id}:

    """
            
            # Add a reasonable number of other notes to the prompt
            # We'll only include first 300 chars of each note to keep the prompt size manageable
            for i, other_note in enumerate(other_notes):
                # Get tags for this note
                try:
                    note_tags = self.db.get_tags(other_note['id'])
                except Exception:
                    note_tags = []
                    
                note_preview = other_note['content']
                if len(note_preview) > 300:
                    note_preview = note_preview[:300] + "..."
                
                # Include tags in the prompt
                prompt += f"## Note #{other_note['id']}\n{note_preview}\n"
                prompt += f"Tags: {', '.join(note_tags) if note_tags else 'None'}\n\n"
                
                # Limit number of notes to avoid exceeding token limits
                if i >= 15:  # Limited to 15 notes to avoid token limits
                    break
                    
            prompt += f"""For each of the top {limit} most related notes, provide:
    1. The note ID (in the format: "Note #ID")
    2. A clear explanation of the conceptual connection to the source note
    3. Mention any shared or related tags that contribute to the connection

    Format your response as a structured list with one connection per item. Include only notes with meaningful connections."""

            response = self._call_llm_api(prompt, system_message, max_tokens=1500)
            
            # Process the results with improved parsing
            results = []
            current_id = None
            current_explanation = ""
            
            # Split response into lines and process
            lines = response.split('\n')
            for i, line in enumerate(lines):
                line = line.strip()
                
                # Skip empty lines
                if not line:
                    continue
                    
                # Look for note IDs in various formats
                id_patterns = [
                    r'Note #([a-zA-Z0-9]+)',  # Note #abc123
                    r'#([a-zA-Z0-9]+):',      # #abc123:
                    r'#([a-zA-Z0-9]+) -',     # #abc123 -
                    r'^\s*([0-9]+)\.\s+#([a-zA-Z0-9]+)', # 1. #abc123
                    r'^\s*([0-9]+)\.\s+Note #([a-zA-Z0-9]+)', # 1. Note #abc123
                ]
                
                found_id = False
                for pattern in id_patterns:
                    import re
                    match = re.search(pattern, line)
                    if match:
                        # Save previous note if exists
                        if current_id and current_explanation:
                            results.append({
                                "note_id": current_id,
                                "explanation": current_explanation.strip()
                            })
                        
                        # Extract the ID from the appropriate capture group
                        if len(match.groups()) == 1:
                            current_id = match.group(1)
                        else:
                            current_id = match.group(2)  # For numbered list pattern
                            
                        # Extract explanation from the current line
                        parts = re.split(r'[:-] ', line, 1)
                        current_explanation = parts[1] if len(parts) > 1 else ""
                        found_id = True
                        break
                
                # If no ID was found, add to the current explanation
                if not found_id and current_id:
                    current_explanation += " " + line
            
            # Add the last result if exists
            if current_id and current_explanation:
                results.append({
                    "note_id": current_id,
                    "explanation": current_explanation.strip()
                })
                
            # Filter out any invalid note IDs
            valid_ids = {note['id'] for note in other_notes}
            results = [r for r in results if r['note_id'] in valid_ids]
                
            return results[:limit]  # Ensure we return at most 'limit' results
            
        except Exception as e:
            print(f"Error generating connections: {str(e)}")
            return []
        
    def suggest_tags(self, note_id: str, count: int = 3) -> List[str]:
        """
        Suggest tags for a note using Claude.
        
        Args:
            note_id: ID of the note to suggest tags for
            count: Number of tags to suggest
            
        Returns:
            List of suggested tags
        """
        try:
            note = self.db.get_note(note_id)
            
            system_message = """You are an expert assistant for a Zettelkasten note-taking system.
Your task is to suggest relevant, precise tags for notes.
Tags should be specific enough to be useful for categorization but general enough to connect multiple notes.
Prefer lowercase, single-word tags or short hyphenated phrases that capture key concepts."""
            
            prompt = f"""Please suggest exactly {count} appropriate tags for the following note:

## Note #{note_id}
{note['content']}

Consider:
1. Key concepts in the note
2. Academic fields or domains relevant to the content
3. Methodologies or approaches mentioned
4. Potential use cases or applications

Format your response as a simple list with exactly {count} tags, each on a new line.
Start each line with "Tag: " followed by the tag.
Each tag should be a single lowercase word or hyphenated phrase without the # symbol.

For example:
Tag: productivity
Tag: memory-techniques
Tag: learning

Please provide exactly {count} tags in this format."""
            
            response = self._call_llm_api(prompt, system_message, max_tokens=200)
            
            # Process and clean up tags
            tags = []
            
            # First look for the "Tag: " format
            for line in response.strip().split('\n'):
                line = line.strip().lower()
                
                # Skip empty lines
                if not line:
                    continue
                    
                # Check for "Tag: " prefix
                if line.lower().startswith('tag:'):
                    tag = line[4:].strip()  # Remove "Tag: " prefix
                    if tag:
                        tags.append(tag)
                    
            # If we didn't find any tags with that format, try other formats
            if not tags:
                for line in response.strip().split('\n'):
                    line = line.strip().lower()
                    
                    # Skip empty lines or numbered lines without content
                    if not line or re.match(r'^\d+\.\s*$', line):
                        continue
                        
                    # Remove numbered prefixes (1., 2., etc.)
                    line = re.sub(r'^\d+\.\s*', '', line)
                    
                    # Remove any # symbols if present
                    if line.startswith('#'):
                        line = line[1:].strip()
                        
                    # Remove any bullet points or symbols
                    line = line.lstrip('*-•⁃➢➤› ').strip()
                    
                    # Only add non-empty tags
                    if line:
                        tags.append(line)
            
            # If still no tags, split the response and take words that look like tags
            if not tags:
                words = response.lower().split()
                for word in words:
                    # Clean the word (remove punctuation)
                    word = re.sub(r'[^\w\-]', '', word)
                    
                    # Only consider words of reasonable length
                    if len(word) >= 3 and word not in tags:
                        tags.append(word)
                        
                        # Stop once we have enough tags
                        if len(tags) >= count:
                            break
            
            # Deduplicate tags
            tags = list(dict.fromkeys(tags))
            
            # Return only the requested number of tags
            return tags[:count]
            
        except Exception as e:
            print(f"Error suggesting tags: {str(e)}")
            return []
    
    def extract_key_concepts(self, note_id: str, count: int = 5) -> List[Dict[str, str]]:
        """
        Extract key concepts from a note with explanations.
        
        Args:
            note_id: ID of the note to extract concepts from
            count: Number of concepts to extract
            
        Returns:
            List of dictionaries with concept and explanation keys
        """
        try:
            note = self.db.get_note(note_id)
            
            system_message = """You are an expert assistant for a Zettelkasten note-taking system.
Your task is to identify the most important concepts in a note and provide a brief explanation for each.
Focus on extracting core ideas that could form the basis of new notes in a Zettelkasten system."""
            
            prompt = f"""Please identify the {count} most important concepts in this note:

## Note #{note_id}
{note['content']}

For each concept:
1. Start with "Concept: " followed by a short, clear name for the concept (3-5 words maximum)
2. On the next line, start with "Explanation: " followed by a 1-2 sentence explanation

Format your response precisely as follows:

Concept: [First concept name]
Explanation: [Your explanation of the first concept]

Concept: [Second concept name]
Explanation: [Your explanation of the second concept]

Follow this exact format for all {count} concepts, with each concept-explanation pair separated by a blank line."""
            
            response = self._call_llm_api(prompt, system_message, max_tokens=800)
            
            # Process and extract concepts using the "Concept: " format
            concepts = []
            current_concept = None
            current_explanation = None
            
            # Split response into lines
            lines = response.strip().split('\n')
            
            # First parsing approach: Look for Concept:/Explanation: format
            for line in lines:
                line = line.strip()
                
                # Skip empty lines
                if not line:
                    continue
                    
                if line.lower().startswith('concept:'):
                    # If we already have a concept-explanation pair, add it to results
                    if current_concept and current_explanation:
                        concepts.append({
                            "concept": current_concept.strip(),
                            "explanation": current_explanation.strip()
                        })
                    
                    # Start a new concept
                    current_concept = line[8:].strip()  # Remove "Concept: " prefix
                    current_explanation = None
                elif line.lower().startswith('explanation:'):
                    # Start the explanation for the current concept
                    current_explanation = line[12:].strip()  # Remove "Explanation: " prefix
                elif current_explanation is not None and line:
                    # Continue adding to the current explanation
                    current_explanation += " " + line
                elif current_concept is not None and current_explanation is None and line:
                    # Continue adding to the current concept if explanation hasn't started yet
                    current_concept += " " + line
            
            # Add the last concept-explanation pair
            if current_concept and current_explanation:
                concepts.append({
                    "concept": current_concept.strip(),
                    "explanation": current_explanation.strip()
                })
                
            # If no concepts found with first method, try alternative parsing
            if not concepts:
                # Try to find numbered items
                for i, line in enumerate(lines):
                    line = line.strip()
                    
                    # Look for numbered items (1., 2., etc.)
                    match = re.match(r'^(\d+)\.\s+(.+)', line)
                    if match:
                        concept_text = match.group(2)
                        
                        # Look for explanation in the next lines
                        explanation_lines = []
                        j = i + 1
                        while j < len(lines) and not re.match(r'^\d+\.', lines[j].strip()):
                            if lines[j].strip():  # Only add non-empty lines
                                explanation_lines.append(lines[j].strip())
                            j += 1
                        
                        explanation = " ".join(explanation_lines).strip()
                        
                        # If no explanation found, use a placeholder
                        if not explanation:
                            explanation = "This is a key concept from the note."
                        
                        concepts.append({
                            "concept": concept_text.strip(),
                            "explanation": explanation
                        })
                
                # If still no concepts, try to extract them from paragraphs
                if not concepts:
                    paragraphs = []
                    current_paragraph = []
                    
                    # Split into paragraphs
                    for line in lines:
                        if line.strip():
                            current_paragraph.append(line.strip())
                        elif current_paragraph:  # Empty line and we have content
                            paragraphs.append(" ".join(current_paragraph))
                            current_paragraph = []
                    
                    # Add the last paragraph if it exists
                    if current_paragraph:
                        paragraphs.append(" ".join(current_paragraph))
                    
                    # Use paragraphs as concepts and explanations
                    for i, paragraph in enumerate(paragraphs[:count]):
                        # Try to extract a concept name from the first sentence
                        sentences = re.split(r'[.!?]', paragraph)
                        concept_name = sentences[0].strip()
                        
                        # Limit concept name length
                        if len(concept_name.split()) > 8:
                            concept_name = " ".join(concept_name.split()[:8]) + "..."
                        
                        # Use the rest as explanation or the full paragraph
                        explanation = paragraph
                        
                        concepts.append({
                            "concept": concept_name,
                            "explanation": explanation
                        })
            
            return concepts[:count]  # Ensure we return at most 'count' concepts
            
        except Exception as e:
            print(f"Error extracting concepts: {str(e)}")
            return []
    
    def generate_question_note(self, note_id: str, count: int = 3) -> List[Dict[str, str]]:
        """
        Generate thought-provoking questions based on a note.
        
        Args:
            note_id: ID of the note to generate questions from
            count: Number of questions to generate
            
        Returns:
            List of dictionaries with question and explanation keys
        """
        try:
            note = self.db.get_note(note_id)
            
            system_message = """You are an expert assistant for a Zettelkasten note-taking system.
Your task is to generate thought-provoking questions that extend the ideas in a note.
Each question should explore implications, applications, or connections that aren't explicitly covered in the original note."""
            
            prompt = f"""Based on the following note, generate exactly {count} thought-provoking questions that extend its ideas:

## Note #{note_id}
{note['content']}

For each question:
1. Start with 'Question: ' followed by your clear, focused question
2. Then on a new line, start with 'Explanation: ' followed by why this question is interesting or important
3. Use this exact format for each of the {count} questions, with a blank line between each question-explanation pair

Format your response precisely as follows:

Question: [Your first question here]
Explanation: [Your explanation here]

Question: [Your second question here]
Explanation: [Your explanation here]

Question: [Your third question here]
Explanation: [Your explanation here]

Follow this format exactly, with the labels 'Question:' and 'Explanation:' at the start of their respective lines."""
            
            response = self._call_llm_api(prompt, system_message, max_tokens=800)
            
            # Simplified parsing with explicit markers
            questions = []
            current_question = None
            current_explanation = None
            
            # Split the response into lines
            lines = response.strip().split('\n')
            
            # First parsing method: Look for Question:/Explanation: markers
            for line in lines:
                line = line.strip()
                
                if line.lower().startswith('question:'):
                    # If we already have a question-explanation pair, add it to results
                    if current_question and current_explanation:
                        questions.append({
                            "question": current_question.strip(),
                            "explanation": current_explanation.strip()
                        })
                    
                    # Start a new question
                    current_question = line[9:].strip()  # Remove 'Question: ' prefix
                    current_explanation = None
                elif line.lower().startswith('explanation:'):
                    # Start the explanation for the current question
                    current_explanation = line[12:].strip()  # Remove 'Explanation: ' prefix
                elif current_explanation is not None and line:
                    # Continue adding to the current explanation
                    current_explanation += " " + line
                elif current_question is not None and current_explanation is None and line:
                    # Continue adding to the current question if explanation hasn't started yet
                    current_question += " " + line
            
            # Add the last question-explanation pair
            if current_question and current_explanation:
                questions.append({
                    "question": current_question.strip(),
                    "explanation": current_explanation.strip()
                })
            
            # If no questions found with the first method, try alternative parsing
            if not questions:
                # Try to parse questions based on numbered format (1. Question...)
                for i, line in enumerate(lines):
                    line = line.strip()
                    
                    # Look for numbered items
                    match = re.match(r'^(\d+)\.\s+(.+)', line)
                    if match:
                        question_line = match.group(2)
                        
                        # Look for explanation in the next lines
                        explanation_lines = []
                        j = i + 1
                        while j < len(lines) and not re.match(r'^\d+\.', lines[j].strip()):
                            explanation_lines.append(lines[j].strip())
                            j += 1
                        
                        explanation = " ".join(explanation_lines).strip()
                        
                        # Add to questions
                        questions.append({
                            "question": question_line.strip(),
                            "explanation": explanation if explanation else "This question explores an important aspect of the note."
                        })
                
                # If still no questions, try to split the response into equal parts
                if not questions:
                    # Split the full response into roughly equal chunks for each question
                    full_text = response.strip()
                    chunk_size = len(full_text) // count
                    
                    for i in range(count):
                        start = i * chunk_size
                        end = start + chunk_size if i < count - 1 else len(full_text)
                        chunk = full_text[start:end].strip()
                        
                        # Try to extract a question from this chunk
                        question_match = re.search(r'([^.!?]+\?)', chunk)
                        if question_match:
                            question = question_match.group(1).strip()
                        else:
                            # If no question mark found, use the first sentence
                            sentences = re.split(r'[.!?]', chunk)
                            question = sentences[0].strip() + "?"
                        
                        # Use the rest as explanation or a default
                        explanation = chunk.replace(question, "").strip()
                        if not explanation:
                            explanation = "This question relates to concepts in the note."
                        
                        questions.append({
                            "question": question,
                            "explanation": explanation
                        })
            
            # Ensure all questions end with a question mark
            for question in questions:
                if not question["question"].endswith('?'):
                    question["question"] += '?'
            
            return questions[:count]  # Ensure we return at most 'count' questions
            
        except Exception as e:
            print(f"Error generating questions: {str(e)}")
            return []
            
    def expand_note(self, note_id: str) -> str:
        """
        Expand a note with additional details and insights.
        
        Args:
            note_id: ID of the note to expand
            
        Returns:
            Expanded version of the note
        """
        try:
            note = self.db.get_note(note_id)
            
            system_message = """You are an expert assistant for a Zettelkasten note-taking system.
Your task is to thoughtfully expand a note with additional context, examples, and insights.
Preserve the original meaning while adding depth and connections to other potential ideas.
You should aim to roughly double the length of the original note."""
            
            prompt = f"""Please expand the following note with additional context, examples, and insights:

## Note #{note_id}
{note['content']}

Please:
1. Preserve the original meaning and intent of the note
2. Add relevant examples or applications
3. Explore potential implications or extensions of the ideas
4. Suggest connections to related concepts
5. Maintain a clear, concise writing style appropriate for a Zettelkasten system"""
            
            return self._call_llm_api(prompt, system_message, max_tokens=1500)
            
        except Exception as e:
            return f"Error expanding note: {str(e)}"
        
    def critique_note(self, note_id: str) -> Dict[str, Any]:
        """
        Provide constructive critique for a note.
        
        Args:
            note_id: ID of the note to critique
            
        Returns:
            Dictionary with strengths, weaknesses, and suggestions
        """
        try:
            note = self.db.get_note(note_id)
            
            system_message = """You are an expert assistant for a Zettelkasten note-taking system.
Your task is to provide a constructive critique of a note to help improve its quality.
Focus on clarity, atomicity (one idea per note), and potential for connections."""
            
            prompt = f"""Please provide a constructive critique of the following note:

## Note #{note_id}
{note['content']}

Analyze the note for:
1. Clarity and precision of expression
2. Atomicity (does it focus on a single idea?)
3. Potential for connections to other ideas
4. Completeness of the thought

Format your response with these clearly labeled sections:
- Strengths: [List the note's strengths]
- Areas for Improvement: [List areas that could be improved]
- Suggestions: [Provide specific actionable suggestions]

Use this exact format with these three section headings."""
            
            response = self._call_llm_api(prompt, system_message, max_tokens=800)
            
            # Process the response into structured feedback
            lines = response.strip().split('\n')
            
            # Initialize sections
            strengths = []
            weaknesses = []
            suggestions = []
            current_section = None
            
            for line in lines:
                line = line.strip()
                
                # Skip empty lines
                if not line:
                    continue
                
                # Detect section headers
                lower_line = line.lower()
                if "strength" in lower_line:
                    current_section = "strengths"
                    continue
                elif "area" in lower_line and "improve" in lower_line or "weakness" in lower_line:
                    current_section = "weaknesses"
                    continue
                elif "suggestion" in lower_line or "recommend" in lower_line:
                    current_section = "suggestions"
                    continue
                
                # Add content to appropriate section
                if current_section == "strengths" and line:
                    # Clean up bullet points and numbering
                    item = re.sub(r'^\s*[\*•\-\d.]+\s*', '', line)
                    if item:
                        strengths.append(item)
                elif current_section == "weaknesses" and line:
                    item = re.sub(r'^\s*[\*•\-\d.]+\s*', '', line)
                    if item:
                        weaknesses.append(item)
                elif current_section == "suggestions" and line:
                    item = re.sub(r'^\s*[\*•\-\d.]+\s*', '', line)
                    if item:
                        suggestions.append(item)
            
            # If we couldn't detect clear sections, try to determine them from the content
            if not (strengths or weaknesses or suggestions):
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                        
                    # Clean up line
                    item = re.sub(r'^\s*[\*•\-\d.]+\s*', '', line)
                    
                    lower_item = item.lower()
                    if any(word in lower_item for word in ["good", "strong", "clear", "well", "excellent"]):
                        strengths.append(item)
                    elif any(word in lower_item for word in ["weak", "issue", "problem", "lack", "missing", "could", "should"]):
                        if "consider" in lower_item or "try" in lower_item or "add" in lower_item:
                            suggestions.append(item)
                        else:
                            weaknesses.append(item)
                    elif any(word in lower_item for word in ["suggest", "consider", "try", "add", "improve"]):
                        suggestions.append(item)
            
            return {
                "strengths": strengths,
                "weaknesses": weaknesses,
                "suggestions": suggestions
            }
            
        except Exception as e:
            print(f"Error critiquing note: {str(e)}")
            return {
                "strengths": [],
                "weaknesses": [],
                "suggestions": [f"Error analyzing note: {str(e)}"]
            }