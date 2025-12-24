from typing import List, Dict, Optional, Any
from app.config.settings import settings
from app.utils.openai_factory import get_openai_client
import json
import re
import logging

logger = logging.getLogger(__name__)

class CodingInterviewEngine:
    """Engine for managing coding interview sessions"""
    
    def __init__(self):
        self.client = get_openai_client("coding")
        self.openai_available = self.client is not None
    
    def start_coding_session(
        self,
        user_id: str,
        resume_skills: Optional[List[str]] = None,
        resume_context: Optional[Dict[str, Any]] = None,
        experience_level: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Start a new coding interview session
        Extracts coding-related skills from resume
        """
        # Extract coding-related skills
        coding_skills = []
        resume_projects: List[str] = []
        resume_domains: List[str] = []

        if resume_skills:
            # Filter for programming languages and DSA-related skills
            coding_keywords = ['python', 'java', 'javascript', 'c++', 'c', 'cpp', 'sql', 
                             'mysql', 'postgresql', 'postgres', 'database', 'oracle', 'sqlite',
                             'algorithm', 'data structure', 'dsa', 'leetcode', 'hackerrank',
                             'programming', 'coding', 'software development', 'web development']
            for skill in resume_skills:
                skill_lower = skill.lower()
                if any(keyword in skill_lower for keyword in coding_keywords):
                    coding_skills.append(skill)
        
        if resume_context:
            extra_skills = resume_context.get("skills", []) or []
            for skill in extra_skills:
                if skill and skill not in coding_skills:
                    coding_skills.append(skill)
            resume_projects = resume_context.get("projects", []) or []
            resume_domains = resume_context.get("domains", []) or []
            if not experience_level:
                experience_level = resume_context.get("experience_level")
            keywords = resume_context.get("keywords", {}) or {}
            if not resume_projects and keywords:
                resume_projects = keywords.get("projects", []) or []
        
        # If no coding skills found, use default
        if not coding_skills:
            coding_skills = ["Python", "Data Structures", "Algorithms"]
        
        # Remove duplicates and limit
        coding_skills = list(dict.fromkeys(coding_skills))[:15]
        
        return {
            "session_id": None,  # Will be set by the router
            "coding_skills": coding_skills,
            "current_question_index": 0,
            "questions_asked": [],
            "solutions_submitted": [],
            "experience_level": experience_level,
            "resume_projects": resume_projects,
            "domains": resume_domains
        }
    
    def _get_question_types_asked(self, previous_questions: List[str]) -> Dict[str, bool]:
        """✅ FIX: Analyze previous questions to determine which types have been asked"""
        question_types = {
            "array": False,
            "string": False,
            "oop": False,
            "sql": False,
            "api": False,
            "debugging": False,
            "logic": False,
            "dsa_pattern": False,
            "real_world": False
        }
        
        for q in previous_questions:
            q_lower = q.lower()
            if any(word in q_lower for word in ["array", "list", "index", "element"]):
                question_types["array"] = True
            if any(word in q_lower for word in ["string", "substring", "character", "text"]):
                question_types["string"] = True
            if any(word in q_lower for word in ["class", "object", "method", "inheritance", "polymorphism", "encapsulation"]):
                question_types["oop"] = True
            if any(word in q_lower for word in ["sql", "database", "table", "query", "select", "join"]):
                question_types["sql"] = True
            if any(word in q_lower for word in ["api", "endpoint", "request", "response", "http", "rest"]):
                question_types["api"] = True
            if any(word in q_lower for word in ["bug", "debug", "error", "fix", "issue"]):
                question_types["debugging"] = True
            if any(word in q_lower for word in ["logic", "condition", "if", "loop", "algorithm"]):
                question_types["logic"] = True
            if any(word in q_lower for word in ["graph", "tree", "dynamic programming", "dp", "backtracking", "dijkstra", "bfs", "dfs"]):
                question_types["dsa_pattern"] = True
            if any(word in q_lower for word in ["project", "application", "system", "feature", "user", "real"]):
                question_types["real_world"] = True
        
        return question_types
    
    def _suggest_question_type(self, question_types_asked: Dict[str, bool], experience_level: Optional[str], question_number: int) -> str:
        """✅ FIX: Suggest which question type to generate next to ensure variety"""
        years = self._parse_experience_years(experience_level) or 0
        
        # For freshers (0-1 years), prioritize basic types and avoid heavy DSA
        if years < 1:
            # Prioritize: array, string, logic, real_world, debugging
            # Avoid: complex DSA patterns, heavy OOP
            priority_types = ["array", "string", "logic", "real_world", "debugging"]
            for qtype in priority_types:
                if not question_types_asked.get(qtype, False):
                    return qtype
            # If all basic types asked, allow simple OOP or API
            if not question_types_asked.get("oop", False):
                return "oop"
            if not question_types_asked.get("api", False):
                return "api"
            # Last resort: return any unasked type
            for qtype, asked in question_types_asked.items():
                if not asked:
                    return qtype
            return "array"  # Default for freshers
        
        # For junior (1-3 years), balanced mix
        elif years < 3:
            # Rotate through all types
            all_types = ["array", "string", "oop", "sql", "api", "debugging", "logic", "dsa_pattern", "real_world"]
            for qtype in all_types:
                if not question_types_asked.get(qtype, False):
                    return qtype
            # If all types asked, return least recently asked
            return "array"  # Default rotation
        
        # For senior (3+ years), all types including advanced DSA
        else:
            all_types = ["array", "string", "oop", "sql", "api", "debugging", "logic", "dsa_pattern", "real_world"]
            for qtype in all_types:
                if not question_types_asked.get(qtype, False):
                    return qtype
            return "dsa_pattern"  # Default for seniors
    
    def generate_coding_question(
        self,
        session_data: Dict[str, Any],
        previous_questions: List[str]
    ) -> Dict[str, Any]:
        """
        ✅ FIX: Generate a coding question based on resume skills
        Ensures ALL types of questions are generated (array, string, OOP, SQL, API, debugging, logic, DSA, real-world)
        Difficulty scales with experience: 0-1 years (basic), 1-3 years (medium), 3+ years (advanced)
        Prevents question repeats
        """
        coding_skills = session_data.get("coding_skills", [])
        experience_level = session_data.get("experience_level")
        resume_projects = session_data.get("resume_projects", [])
        resume_domains = session_data.get("domains", [])
        skills_context = ", ".join(coding_skills[:10]) if coding_skills else "general programming"
        
        # ✅ FIX: Track question types to ensure variety
        question_types_asked = self._get_question_types_asked(previous_questions)
        question_number = len(previous_questions) + 1
        suggested_type = self._suggest_question_type(question_types_asked, experience_level, question_number)
        
        # Check if SQL skills are present and SQL question type is suggested
        sql_skills = ['sql', 'mysql', 'postgresql', 'postgres', 'database', 'oracle', 'sqlite']
        has_sql_skills = any(skill.lower() in sql_skills for skill in coding_skills)
        
        # If SQL type suggested and skills present, generate SQL question
        if suggested_type == "sql" and has_sql_skills:
            sql_question_asked = question_types_asked.get("sql", False)
            if not sql_question_asked:
                return self._generate_sql_question(session_data, previous_questions)
        
        # Fallback questions if OpenAI is not available
        if not self.openai_available or self.client is None:
            return self._get_fallback_coding_question(session_data, previous_questions, suggested_type)
        
        try:
            # ✅ FIX: Enhanced system prompt with difficulty guidance
            years_for_prompt = self._parse_experience_years(experience_level) or 0
            difficulty_guidance = ""
            if years_for_prompt < 1:
                difficulty_guidance = """
FOR FRESHERS (0-1 years experience):
- Generate BASIC level problems only
- Focus on: simple array/string manipulation, basic loops & conditions, simple logic building
- Include: basic SQL queries, simple API/CRUD tasks, basic debugging questions
- Include: small real-world practical tasks (e.g., "Write a function to validate email")
- AVOID: Heavy DSA (graphs, DP, backtracking, complex trees)
- AVOID: Complex OOP design patterns
- Problem statements should be simple and easy to understand
- Examples should be clear and straightforward"""
            elif years_for_prompt < 3:
                difficulty_guidance = """
FOR JUNIOR DEVELOPERS (1-3 years experience):
- Generate MEDIUM level problems
- Include balanced mix of: DSA, OOP, SQL, API tasks, real-world project-based questions
- Include: array/string problems, logic building, debugging scenarios
- Moderate complexity only
- NO heavy system-design-level problems"""
            else:
                difficulty_guidance = """
FOR SENIOR DEVELOPERS (3+ years experience):
- Generate HARD/ADVANCED level problems
- Include all types: complex DSA patterns, advanced OOP, complex SQL, API design, system-level debugging
- Include: advanced algorithms, optimization problems, real-world system challenges
- High complexity and depth expected"""
            
            system_prompt = f"""You are a coding interview question generator. Generate coding problems suitable for online coding tests.

✅ CRITICAL REQUIREMENTS:
1. Generate ALL TYPES of coding problems to ensure variety:
   - Array manipulation problems
   - String processing problems
   - Object-Oriented Programming (OOP) design questions
   - SQL/database query problems
   - API/CRUD task problems
   - Debugging and error-fixing problems
   - Logic building and algorithmic thinking problems
   - DSA pattern problems (trees, graphs, DP, etc.)
   - Real-world practical coding tasks

2. {difficulty_guidance}

3. Each question must:
   - Have clear problem statement
   - Include example input/output
   - Include test cases (at least 2-3)
   - Specify constraints
   - Be appropriate for the candidate's experience level
   - NEVER repeat any previous question (check the previous questions list)

4. **Question Type Variety:**
   - Ensure you generate different types of problems across the interview
   - Mix array, string, OOP, SQL, API, debugging, logic, DSA patterns, and real-world tasks
   - Suggested question type for this round: {suggested_type}

Return JSON with this structure:
{{
  "problem": "Problem statement",
  "examples": [{{"input": "...", "output": "...", "explanation": "..."}}],
  "test_cases": [{{"input": "...", "output": "..."}}],
  "constraints": "...",
  "difficulty": "Easy/Medium/Hard",
  "topics": ["array", "string", "OOP", "SQL", "API", "debugging", "logic", "DSA", "real-world"],
  "question_type": "{suggested_type}"
}}"""

            # ✅ FIX: Calculate years for difficulty guidance
            years = self._parse_experience_years(experience_level) or 0
            
            # Get past performance for adaptive difficulty
            past_performance = session_data.get("past_performance")
            difficulty_label = self._determine_difficulty(experience_level, coding_skills, past_performance)
            project_context = ", ".join(resume_projects[:2]) if resume_projects else "recent real-world projects"
            domain_context = ", ".join(resume_domains[:2]) if resume_domains else "software engineering"

            # ✅ FIX: Enhanced duplicate detection
            previous_questions_summary = ""
            if previous_questions:
                previous_questions_summary = "\n".join([
                    f"{i+1}. {q[:150]}..." if len(q) > 150 else f"{i+1}. {q}"
                    for i, q in enumerate(previous_questions[:10])  # Show up to 10 previous questions
                ])
            else:
                previous_questions_summary = "None - this is the first question"

            user_prompt = f"""Generate a coding problem for a candidate with these details:

CANDIDATE PROFILE:
- Key skills: {skills_context}
- Experience level: {experience_level or 'Not specified'} ({years} years)
- Projects/domains: {project_context} | {domain_context}
- Question number: {question_number}

PREVIOUS QUESTIONS (DO NOT REPEAT ANY OF THESE):
{previous_questions_summary}

QUESTION TYPE TO GENERATE: {suggested_type}

REQUIREMENTS:
1. Generate a {difficulty_label} level coding problem
2. Question type should be: {suggested_type}
3. Reference at least one skill or project context from the candidate's profile
4. **CRITICAL: The problem must be COMPLETELY DIFFERENT from all previous questions listed above**
5. Do NOT repeat any problem statement, concept, approach, or pattern from previous questions
6. Ensure the problem matches the experience level ({years} years) and difficulty ({difficulty_label})
7. Include clear examples and test cases

Generate a unique, personalized coding problem now."""

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.8,  # Slightly higher for more variety
                response_format={"type": "json_object"},
                timeout=30
            )
            
            content = response.choices[0].message.content
            question_data = json.loads(content)
            
            # ✅ FIX: Strict duplicate detection - check exact matches and similarity
            new_problem = question_data.get("problem", "")
            if new_problem:
                # Normalize new problem for comparison
                new_problem_normalized = " ".join(new_problem.strip().lower().split())
                
                # Check against normalized set if available (faster)
                questions_normalized = session_data.get("questions_asked_normalized", set())
                if questions_normalized and new_problem_normalized in questions_normalized:
                    # Exact duplicate detected - regenerate immediately
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"[CODING ENGINE] ⚠️ Exact duplicate detected for question: {new_problem[:80]}...")
                    return self._regenerate_with_duplicate_warning(
                        session_data, previous_questions, suggested_type, difficulty_label, skills_context
                    )
                
                # Also check against full list for similarity
                for prev_q in previous_questions:
                    if not prev_q:
                        continue
                    prev_q_normalized = " ".join(prev_q.strip().lower().split())
                    
                    # Exact match check
                    if new_problem_normalized == prev_q_normalized:
                        # Exact duplicate - regenerate
                        return self._regenerate_with_duplicate_warning(
                            session_data, previous_questions, suggested_type, difficulty_label, skills_context
                        )
                    
                    # Similarity check: if >40% words match, flag as potential duplicate
                    new_words = set(new_problem_normalized.split())
                    prev_words = set(prev_q_normalized.split())
                    if len(new_words) > 0 and len(prev_words) > 0:
                        # Remove common stop words for better comparison
                        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were", "be", "been", "have", "has", "had", "do", "does", "did", "will", "would", "should", "could", "may", "might", "must", "can"}
                        new_words_filtered = new_words - stop_words
                        prev_words_filtered = prev_words - stop_words
                        
                        if len(new_words_filtered) > 0 and len(prev_words_filtered) > 0:
                            similarity = len(new_words_filtered & prev_words_filtered) / len(new_words_filtered | prev_words_filtered)
                            if similarity > 0.4:  # More than 40% similarity (lowered threshold for stricter detection)
                                # Similar question detected - regenerate
                                import logging
                                logger = logging.getLogger(__name__)
                                logger.warning(f"[CODING ENGINE] ⚠️ Similar question detected (similarity: {similarity:.2%}): {new_problem[:80]}...")
                                return self._regenerate_with_duplicate_warning(
                                    session_data, previous_questions, suggested_type, difficulty_label, skills_context
                                )
            
            return {
                "problem": question_data.get("problem", ""),
                "examples": question_data.get("examples", []),
                "test_cases": question_data.get("test_cases", []),
                "constraints": question_data.get("constraints", ""),
                "difficulty": question_data.get("difficulty", difficulty_label),
                "topics": question_data.get("topics", [suggested_type]),
                "question_type": question_data.get("question_type", suggested_type)
            }
            
        except Exception as e:
            return self._get_fallback_coding_question(session_data, previous_questions, suggested_type)
    
    def _regenerate_with_duplicate_warning(
        self,
        session_data: Dict[str, Any],
        previous_questions: List[str],
        suggested_type: str,
        difficulty_label: str,
        skills_context: str
    ) -> Dict[str, Any]:
        """✅ FIX: Regenerate question with stronger duplicate warning - try up to 3 times"""
        if not self.openai_available or self.client is None:
            return self._get_fallback_coding_question(session_data, previous_questions, suggested_type)
        
        # Try up to 3 regeneration attempts
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                # Build comprehensive list of previous questions
                previous_questions_summary = "\n".join([
                    f"{i+1}. {q[:200]}..." if len(q) > 200 else f"{i+1}. {q}"
                    for i, q in enumerate(previous_questions[:10])
                ])
                
                user_prompt = f"""⚠️ CRITICAL: DUPLICATE DETECTED - Generate a COMPLETELY NEW and DIFFERENT coding problem.

PREVIOUS QUESTIONS (DO NOT REPEAT OR SIMILAR TO ANY OF THESE):
{previous_questions_summary}

REQUIREMENTS:
- Generate a {difficulty_label} level {suggested_type} problem
- Skills context: {skills_context}
- The new problem must be:
  * COMPLETELY DIFFERENT from all previous questions
  * Use a different problem statement, approach, and examples
  * NOT a variant or rephrasing of any previous question
  * Unique in concept and solution approach

Generate a truly unique coding problem now (attempt {attempt + 1}/{max_attempts})."""
                
                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a coding interview question generator. You MUST generate completely unique questions that are NOT duplicates or variants of previous questions. Each question must have a distinct problem statement, approach, and solution."},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.95,  # Very high temperature for maximum variety
                    response_format={"type": "json_object"},
                    timeout=30
                )
                
                content = response.choices[0].message.content
                question_data = json.loads(content)
                new_problem = question_data.get("problem", "")
                
                if not new_problem:
                    continue  # Try again
                
                # Validate the regenerated question is not a duplicate
                new_problem_normalized = " ".join(new_problem.strip().lower().split())
                questions_normalized = session_data.get("questions_asked_normalized", set())
                
                # Check exact match
                if questions_normalized and new_problem_normalized in questions_normalized:
                    if attempt < max_attempts - 1:
                        continue  # Try again
                    else:
                        # Last attempt failed, use fallback
                        return self._get_fallback_coding_question(session_data, previous_questions, suggested_type)
                
                # Check similarity with previous questions
                is_duplicate = False
                for prev_q in previous_questions:
                    if not prev_q:
                        continue
                    prev_q_normalized = " ".join(prev_q.strip().lower().split())
                    if new_problem_normalized == prev_q_normalized:
                        is_duplicate = True
                        break
                    
                    # Similarity check
                    new_words = set(new_problem_normalized.split())
                    prev_words = set(prev_q_normalized.split())
                    stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
                    new_words_filtered = new_words - stop_words
                    prev_words_filtered = prev_words - stop_words
                    if len(new_words_filtered) > 0 and len(prev_words_filtered) > 0:
                        similarity = len(new_words_filtered & prev_words_filtered) / len(new_words_filtered | prev_words_filtered)
                        if similarity > 0.4:
                            is_duplicate = True
                            break
                
                if is_duplicate:
                    if attempt < max_attempts - 1:
                        continue  # Try again
                    else:
                        # Last attempt failed, use fallback
                        return self._get_fallback_coding_question(session_data, previous_questions, suggested_type)
                
                # Question is unique, return it
                return {
                    "problem": new_problem,
                    "examples": question_data.get("examples", []),
                    "test_cases": question_data.get("test_cases", []),
                    "constraints": question_data.get("constraints", ""),
                    "difficulty": question_data.get("difficulty", difficulty_label),
                    "topics": question_data.get("topics", [suggested_type]),
                    "question_type": suggested_type
                }
            except Exception as e:
                if attempt < max_attempts - 1:
                    continue  # Try again
                else:
                    # All attempts failed, use fallback
                    return self._get_fallback_coding_question(session_data, previous_questions, suggested_type)
        
        # If we get here, all attempts failed
        return self._get_fallback_coding_question(session_data, previous_questions, suggested_type)
    
    def _determine_difficulty(
        self, 
        experience_level: Optional[str], 
        skills: List[str],
        past_performance: Optional[Dict[str, Any]] = None
    ) -> str:
        """✅ FIX: Determine difficulty based on experience level with proper scaling:
        - Fresher (0-1 years) → Easy (basic problems only)
        - Junior (1-3 years) → Medium (balanced mix)
        - Senior (3+ years) → Hard (advanced problems)
        
        Adaptive adjustment based on past performance:
        - If solved most questions correctly → increase difficulty slightly
        - If struggled → decrease difficulty
        """
        import random
        
        # ✅ FIX: Base difficulty from experience with proper scaling
        base_difficulty = None
        years = self._parse_experience_years(experience_level)
        if years is not None:
            if years < 1:  # Fresher (0-1 years) - Basic level only
                base_difficulty = "Easy"
            elif years < 3:  # Junior (1-3 years) - Medium level
                base_difficulty = "Medium"
            else:  # Senior (3+ years) - Hard level
                base_difficulty = "Hard"
        else:
            # Fallback to skills-based difficulty if experience level not available
            if len(skills) >= 10:
                base_difficulty = "Hard"
            elif len(skills) >= 5:
                base_difficulty = "Medium"
            else:
                base_difficulty = "Easy"
        
        # Adaptive adjustment based on past performance (slight adjustments only)
        if past_performance:
            accuracy = past_performance.get("accuracy", 0)
            average_score = past_performance.get("average_score", 0)
            
            # If user performed very well (accuracy > 80% or average score > 80), increase difficulty slightly
            if accuracy > 80 or average_score > 80:
                if base_difficulty == "Easy":
                    return "Medium"
                elif base_difficulty == "Medium":
                    return "Hard"
                # Already Hard, keep it
                return "Hard"
            # If user struggled significantly (accuracy < 30% or average score < 30), decrease difficulty
            elif accuracy < 30 or average_score < 30:
                if base_difficulty == "Hard":
                    return "Medium"
                elif base_difficulty == "Medium":
                    return "Easy"
                # Already Easy, keep it
                return "Easy"
        
        return base_difficulty

    @staticmethod
    def _parse_experience_years(experience_level: Optional[str]) -> Optional[float]:
        """
        Parse years of experience from experience level string.
        Returns 0 for Fresher, None if cannot determine.
        """
        if not experience_level:
            return 0  # Default to 0 (Fresher) if not specified
        exp = experience_level.lower()
        if "fresher" in exp or "not specified" in exp or "unknown" in exp:
            return 0
        match = re.search(r'(\d+)\s*(?:\+|years|yrs|y)?', exp)
        if match:
            return float(match.group(1))
        range_match = re.search(r'(\d+)\s*-\s*(\d+)', exp)
        if range_match:
            return (float(range_match.group(1)) + float(range_match.group(2))) / 2
        # If we can't parse it, default to 0 (Fresher)
        return 0
    
    def _get_fallback_coding_question(
        self,
        session_data: Dict[str, Any],
        previous_questions: List[str],
        suggested_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fallback coding questions that remain resume-aware"""
        coding_skills = session_data.get("coding_skills", []) or []
        resume_projects = session_data.get("resume_projects", []) or []
        experience_level = session_data.get("experience_level")
        difficulty = self._determine_difficulty(experience_level, coding_skills)

        primary_skill = coding_skills[len(previous_questions) % len(coding_skills)] if coding_skills else "your preferred language"
        project_reference = resume_projects[len(previous_questions) % len(resume_projects)] if resume_projects else "a recent project"
        
        fallback_questions = [
            {
                "problem": "Given an array of integers, find the maximum sum of a contiguous subarray. Example: For array [-2, 1, -3, 4, -1, 2, 1, -5, 4], the maximum sum is 6 (subarray [4, -1, 2, 1]).",
                "examples": [
                    {
                        "input": "[-2, 1, -3, 4, -1, 2, 1, -5, 4]",
                        "output": "6",
                        "explanation": "The maximum sum subarray is [4, -1, 2, 1]"
                    }
                ],
                "test_cases": [
                    {"input": "[-2, 1, -3, 4, -1, 2, 1, -5, 4]", "output": "6"},
                    {"input": "[1, 2, 3, 4, 5]", "output": "15"},
                    {"input": "[-1, -2, -3]", "output": "-1"}
                ],
                "constraints": "1 <= array.length <= 10^5, -10^4 <= array[i] <= 10^4",
                "difficulty": "Medium",
                "topics": ["array", "dynamic programming"]
            },
            {
                "problem": "Given a string, find the length of the longest substring without repeating characters.\n\nExample: For 'abcabcbb', the answer is 3 (substring 'abc').",
                "examples": [
                    {
                        "input": "'abcabcbb'",
                        "output": "3",
                        "explanation": "The longest substring without repeating characters is 'abc'"
                    }
                ],
                "test_cases": [
                    {"input": "'abcabcbb'", "output": "3"},
                    {"input": "'bbbbb'", "output": "1"},
                    {"input": "'pwwkew'", "output": "3"}
                ],
                "constraints": "0 <= s.length <= 5 * 10^4",
                "difficulty": "Medium",
                "topics": ["string", "sliding window", "hash table"]
            },
            {
                "problem": "Given two sorted arrays, merge them into a single sorted array.\n\nExample: Merge [1, 3, 5] and [2, 4, 6] to get [1, 2, 3, 4, 5, 6].",
                "examples": [
                    {
                        "input": "[1, 3, 5] and [2, 4, 6]",
                        "output": "[1, 2, 3, 4, 5, 6]",
                        "explanation": "Merge the two sorted arrays maintaining sorted order"
                    }
                ],
                "test_cases": [
                    {"input": "[1, 3, 5], [2, 4, 6]", "output": "[1, 2, 3, 4, 5, 6]"},
                    {"input": "[1, 2, 3], [4, 5, 6]", "output": "[1, 2, 3, 4, 5, 6]"},
                    {"input": "[], [1, 2]", "output": "[1, 2]"}
                ],
                "constraints": "0 <= arr1.length, arr2.length <= 10^4",
                "difficulty": "Easy",
                "topics": ["array", "two pointers"]
            },
            {
                "problem": "Given a binary tree, find its maximum depth.\n\nThe maximum depth is the number of nodes along the longest path from the root node down to the farthest leaf node.",
                "examples": [
                    {
                        "input": "Tree: [3,9,20,null,null,15,7]",
                        "output": "3",
                        "explanation": "The tree has depth 3"
                    }
                ],
                "test_cases": [
                    {"input": "[3,9,20,null,null,15,7]", "output": "3"},
                    {"input": "[1,null,2]", "output": "2"}
                ],
                "constraints": "The number of nodes in the tree is in the range [0, 10^4]",
                "difficulty": "Easy",
                "topics": ["tree", "depth-first search", "breadth-first search"]
            },
            {
                "problem": "Given an array of integers, return indices of the two numbers such that they add up to a specific target.\n\nYou may assume that each input would have exactly one solution.",
                "examples": [
                    {
                        "input": "nums = [2, 7, 11, 15], target = 9",
                        "output": "[0, 1]",
                        "explanation": "nums[0] + nums[1] = 2 + 7 = 9"
                    }
                ],
                "test_cases": [
                    {"input": "[2, 7, 11, 15], 9", "output": "[0, 1]"},
                    {"input": "[3, 2, 4], 6", "output": "[1, 2]"},
                    {"input": "[3, 3], 6", "output": "[0, 1]"}
                ],
                "constraints": "2 <= nums.length <= 10^4, -10^9 <= nums[i] <= 10^9",
                "difficulty": "Easy",
                "topics": ["array", "hash table"]
            }
        ]
        
        # ✅ FIX: Select a question that hasn't been asked - use normalized comparison
        available = []
        questions_normalized = session_data.get("questions_asked_normalized", set())
        
        for q in fallback_questions:
            q_problem = q.get("problem", "")
            if not q_problem:
                continue
            
            # Normalize for comparison
            q_normalized = " ".join(q_problem.strip().lower().split())
            
            # Check if this question was already asked
            is_duplicate = False
            if questions_normalized and q_normalized in questions_normalized:
                is_duplicate = True
            else:
                # Also check against full list
                for prev_q in previous_questions:
                    if not prev_q:
                        continue
                    prev_q_normalized = " ".join(prev_q.strip().lower().split())
                    if q_normalized == prev_q_normalized:
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                available.append(q)
        
        # If all questions have been asked, cycle through them but skip exact duplicates
        if not available:
            # Find questions that are least similar to previous ones
            available = fallback_questions
        
        # Select question using round-robin to ensure variety
        question_index = len(previous_questions) % len(available) if available else 0
        base_question = available[question_index] if available else fallback_questions[0]
        contextual_problem = f"While enhancing your '{project_reference}' work using {primary_skill}, you now need to solve the following challenge. {base_question['problem']}"
        return {
            "problem": contextual_problem,
            "examples": base_question.get("examples", []),
            "test_cases": base_question.get("test_cases", []),
            "constraints": base_question.get("constraints", ""),
            "difficulty": difficulty,
            "topics": base_question.get("topics", [])
        }
    
    def _generate_sql_question(
        self,
        session_data: Dict[str, Any],
        previous_questions: List[str]
    ) -> Dict[str, Any]:
        """
        Generate a SQL coding question with table setup
        Returns question with table definitions and sample data
        """
        coding_skills = session_data.get("coding_skills", [])
        experience_level = session_data.get("experience_level")
        difficulty = self._determine_difficulty(experience_level, coding_skills)
        
        # Fallback SQL questions if OpenAI is not available
        if not self.openai_available or self.client is None:
            return self._get_fallback_sql_question(session_data, previous_questions)
        
        try:
            system_prompt = """You are a SQL interview question generator. Generate SQL problems suitable for coding interviews.
Each SQL question must include:
1. A clear problem statement describing what query needs to be written
2. Table definitions (CREATE TABLE statements) with appropriate columns and data types
3. Sample data (INSERT statements) to populate the tables
4. Expected output format
5. At least 2-3 example queries showing expected results
6. Appropriate difficulty level (Easy/Medium/Hard)

Return JSON with this structure:
{
  "problem": "Problem statement describing the SQL query to write",
  "table_setup": "CREATE TABLE statements and INSERT statements separated by semicolons",
  "examples": [{"query": "SELECT example", "output": "Expected result", "explanation": "..."}],
  "constraints": "Any constraints or requirements",
  "difficulty": "Easy/Medium/Hard",
  "topics": ["SELECT", "JOIN", "GROUP BY", etc.]
}

IMPORTANT: The table_setup field must contain valid SQLite-compatible SQL statements.
Use semicolons to separate multiple statements."""

            skills_context = ", ".join(coding_skills[:10]) if coding_skills else "SQL and database management"
            user_prompt = f"""Generate a SQL coding problem for a candidate with these skills: {skills_context}
Experience level: {experience_level or 'Not specified'}
Difficulty: {difficulty}

Create a realistic SQL problem with:
- 2-3 related tables (e.g., employees and departments, orders and customers, etc.)
- Sample data (5-10 rows per table)
- A query that requires JOIN, WHERE, GROUP BY, or other SQL features appropriate for {difficulty} level
- Clear problem statement and expected output format"""

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"},
                timeout=30
            )
            
            content = response.choices[0].message.content
            question_data = json.loads(content)
            
            return {
                "problem": question_data.get("problem", ""),
                "table_setup": question_data.get("table_setup", ""),
                "examples": question_data.get("examples", []),
                "test_cases": question_data.get("examples", []),  # Use examples as test cases
                "constraints": question_data.get("constraints", ""),
                "difficulty": question_data.get("difficulty", "Medium"),
                "topics": question_data.get("topics", ["SQL"]),
                "language": "sql"  # Mark as SQL question
            }
            
        except Exception as e:
            return self._get_fallback_sql_question(session_data, previous_questions)
    
    def _get_fallback_sql_question(
        self,
        session_data: Dict[str, Any],
        previous_questions: List[str]
    ) -> Dict[str, Any]:
        """Fallback SQL questions with table setup"""
        difficulty = self._determine_difficulty(
            session_data.get("experience_level"),
            session_data.get("coding_skills", [])
        )
        
        fallback_sql_questions = [
            {
                "problem": "Given the following database schema, write a SQL query to find all employees who work in the 'Engineering' department along with their manager's name.\n\nYou need to:\n1. Join the employees and departments tables\n2. Filter by department name 'Engineering'\n3. Include the employee's name and their manager's name in the result",
                "table_setup": """CREATE TABLE departments (
    dept_id INTEGER PRIMARY KEY,
    dept_name TEXT NOT NULL
);

CREATE TABLE employees (
    emp_id INTEGER PRIMARY KEY,
    emp_name TEXT NOT NULL,
    dept_id INTEGER,
    manager_id INTEGER,
    salary REAL,
    FOREIGN KEY (dept_id) REFERENCES departments(dept_id),
    FOREIGN KEY (manager_id) REFERENCES employees(emp_id)
);

INSERT INTO departments (dept_id, dept_name) VALUES (1, 'Engineering');
INSERT INTO departments (dept_id, dept_name) VALUES (2, 'Sales');
INSERT INTO departments (dept_id, dept_name) VALUES (3, 'Marketing');

INSERT INTO employees (emp_id, emp_name, dept_id, manager_id, salary) VALUES (1, 'Alice', 1, NULL, 100000);
INSERT INTO employees (emp_id, emp_name, dept_id, manager_id, salary) VALUES (2, 'Bob', 1, 1, 80000);
INSERT INTO employees (emp_id, emp_name, dept_id, manager_id, salary) VALUES (3, 'Charlie', 1, 1, 75000);
INSERT INTO employees (emp_id, emp_name, dept_id, manager_id, salary) VALUES (4, 'David', 2, NULL, 90000);
INSERT INTO employees (emp_id, emp_name, dept_id, manager_id, salary) VALUES (5, 'Eve', 2, 4, 70000);""",
                "examples": [
                    {
                        "query": "SELECT e.emp_name, m.emp_name AS manager_name FROM employees e JOIN departments d ON e.dept_id = d.dept_id LEFT JOIN employees m ON e.manager_id = m.emp_id WHERE d.dept_name = 'Engineering';",
                        "output": "emp_name | manager_name\nBob | Alice\nCharlie | Alice",
                        "explanation": "Join employees with departments, then self-join to get manager names"
                    }
                ],
                "constraints": "Use JOIN operations. Handle NULL manager_id (employees without managers).",
                "difficulty": "Medium",
                "topics": ["JOIN", "WHERE", "SQL"],
                "language": "sql"
            },
            {
                "problem": "Write a SQL query to find the department with the highest average salary. Return the department name and average salary.",
                "table_setup": """CREATE TABLE departments (
    dept_id INTEGER PRIMARY KEY,
    dept_name TEXT NOT NULL
);

CREATE TABLE employees (
    emp_id INTEGER PRIMARY KEY,
    emp_name TEXT NOT NULL,
    dept_id INTEGER,
    salary REAL,
    FOREIGN KEY (dept_id) REFERENCES departments(dept_id)
);

INSERT INTO departments (dept_id, dept_name) VALUES (1, 'Engineering');
INSERT INTO departments (dept_id, dept_name) VALUES (2, 'Sales');
INSERT INTO departments (dept_id, dept_name) VALUES (3, 'Marketing');

INSERT INTO employees (emp_id, emp_name, dept_id, salary) VALUES (1, 'Alice', 1, 100000);
INSERT INTO employees (emp_id, emp_name, dept_id, salary) VALUES (2, 'Bob', 1, 80000);
INSERT INTO employees (emp_id, emp_name, dept_id, salary) VALUES (3, 'Charlie', 2, 70000);
INSERT INTO employees (emp_id, emp_name, dept_id, salary) VALUES (4, 'David', 2, 75000);
INSERT INTO employees (emp_id, emp_name, dept_id, salary) VALUES (5, 'Eve', 3, 65000);""",
                "examples": [
                    {
                        "query": "SELECT d.dept_name, AVG(e.salary) AS avg_salary FROM departments d JOIN employees e ON d.dept_id = e.dept_id GROUP BY d.dept_id, d.dept_name ORDER BY avg_salary DESC LIMIT 1;",
                        "output": "dept_name | avg_salary\nEngineering | 90000.0",
                        "explanation": "Group by department, calculate average salary, order by average descending, take top 1"
                    }
                ],
                "constraints": "Use GROUP BY and aggregate functions. Handle departments with no employees.",
                "difficulty": "Medium",
                "topics": ["GROUP BY", "AVG", "JOIN", "ORDER BY", "LIMIT"],
                "language": "sql"
            }
        ]
        
        # ✅ FIX: Select a SQL question that hasn't been asked - use normalized comparison
        available = []
        questions_normalized = session_data.get("questions_asked_normalized", set())
        
        for q in fallback_sql_questions:
            q_problem = q.get("problem", "")
            if not q_problem:
                continue
            
            # Normalize for comparison
            q_normalized = " ".join(q_problem.strip().lower().split())
            
            # Check if this question was already asked
            is_duplicate = False
            if questions_normalized and q_normalized in questions_normalized:
                is_duplicate = True
            else:
                # Also check against full list
                for prev_q in previous_questions:
                    if not prev_q:
                        continue
                    prev_q_normalized = " ".join(prev_q.strip().lower().split())
                    if q_normalized == prev_q_normalized:
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                available.append(q)
        
        # If all questions have been asked, cycle through them
        if not available:
            available = fallback_sql_questions
        
        # Select question using round-robin to ensure variety
        question_index = len(previous_questions) % len(available) if available else 0
        return available[question_index] if available else fallback_sql_questions[0]

# Create global instance
coding_interview_engine = CodingInterviewEngine()

