from typing import List, Dict, Optional, Any
from app.config.settings import settings
from app.services.resume_parser import resume_parser
from app.services.question_generator import question_generator
from app.services.answer_evaluator import answer_evaluator
from app.utils.openai_factory import get_openai_client, get_api_key_for_type
import json
import os
import logging

# Setup logger
logger = logging.getLogger(__name__)

class TechnicalInterviewEngine:
    """Engine for managing technical interview sessions with voice interaction"""
    
    def __init__(self):
        self.client = get_openai_client("technical")
        self.openai_available = self.client is not None
    
    def start_interview_session(
        self,
        user_id: str,
        resume_skills: Optional[List[str]] = None,
        resume_context: Optional[Dict[str, Any]] = None,
        role: Optional[str] = None,
        experience_level: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Start a new technical interview session enriched with resume-specific details
        """
        technical_skills = resume_skills or []
        resume_projects: List[str] = []
        resume_domains: List[str] = []
        
        if resume_context:
            keywords = resume_context.get("keywords", {}) or {}
            technologies = keywords.get("technologies", [])
            tools = keywords.get("tools", [])
            additional_skills = resume_context.get("skills", []) or []
            
            for skill in technologies + tools + additional_skills:
                if skill and skill not in technical_skills:
                    technical_skills.append(skill)
            
            resume_projects = resume_context.get("projects", []) or keywords.get("projects", []) or []
            resume_domains = resume_context.get("domains", []) or keywords.get("job_titles", []) or []
            experience_level = experience_level or resume_context.get("experience_level")
        
        technical_skills = list(dict.fromkeys(technical_skills))[:20]
        
        conversation_history = [{
            "role": "ai",
            "content": "Welcome to your technical interview! I'll tailor each question to the skills and projects you highlighted in your resume."
        }]
        
        return {
            "session_id": None,  # Will be set by the router
            "technical_skills": technical_skills,
            "conversation_history": conversation_history,
            "current_question_index": 0,
            "questions_asked": [],
            "answers_received": [],
            "resume_projects": resume_projects,
            "resume_domains": resume_domains,
            "role": role or "Technical Interview",
            "experience_level": experience_level
        }
    
    def generate_next_question(
        self,
        session_data: Dict[str, Any],
        conversation_history: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Generate the next technical question based on conversation history and resume skills
        """
        technical_skills = session_data.get("technical_skills", [])
        questions_asked = session_data.get("questions_asked", [])
        answers_received = session_data.get("answers_received", [])
        
        if not self.openai_available or self.client is None:
            # Fallback to predefined questions
            return self._get_fallback_question(session_data, questions_asked)
        
        try:
            # Build context for question generation
            skills_context = ", ".join(technical_skills[:10]) if technical_skills else "general technical skills"
            
            # Build full conversation context for natural flow
            # CRITICAL: Use ALL conversation history to maintain memory across all 15-20 questions
            # For 20 questions with Q&A pairs, that's 40 messages - we'll include all of them
            conversation_context = ""
            if conversation_history:
                # Include ALL conversation history to maintain full memory
                # For very long conversations (>50 messages), use last 50 to avoid token limits
                # But for 15-20 questions (30-40 messages), include everything
                if len(conversation_history) > 50:
                    # Only truncate if conversation is extremely long
                    recent_messages = conversation_history[-50:]
                    conversation_context = "\n".join([
                        f"{msg.get('role', 'unknown').upper()}: {msg.get('content', '')[:300]}"
                        for msg in recent_messages
                    ])
                else:
                    # Include ALL messages for full memory
                    conversation_context = "\n".join([
                        f"{msg.get('role', 'unknown').upper()}: {msg.get('content', '')[:300]}"
                        for msg in conversation_history
                    ])
            
            # Build list of ALL previously asked questions to avoid repeats
            # CRITICAL: Include ALL questions, not just recent ones, to prevent duplicates
            questions_list = ""
            if questions_asked:
                # Include ALL questions asked so far to maintain complete memory
                questions_list = "\n".join([f"{i+1}. {q[:150]}" for i, q in enumerate(questions_asked)])
            
            # Generate question using OpenAI with improved prompts
            system_prompt = """You are an experienced, friendly technical interviewer conducting a natural, conversational voice-based interview.

Your interview style:
- Speak naturally and conversationally, as if talking to a colleague
- Build on previous answers - ask follow-up questions when appropriate
- Show genuine interest in the candidate's responses
- Progress logically: start with fundamentals, then dive deeper
- Reference what the candidate mentioned in previous answers
- Avoid awkward pauses - keep the conversation flowing smoothly
- Never repeat questions that have already been asked

Question guidelines:
- Keep questions concise (1-2 sentences) for voice interaction
- Make questions feel natural and conversational
- Build on previous answers to create a cohesive interview flow
- Test technical knowledge progressively (basic → advanced)
- Reference specific technologies/skills from the resume when relevant"""

            user_prompt = f"""Generate the next technical interview question for a smooth, natural conversation flow.

CANDIDATE'S TECHNICAL SKILLS (from resume):
{skills_context}

CONVERSATION HISTORY (full context):
{conversation_context if conversation_context else "This is the first question. Start with a friendly introduction and a foundational question."}

PREVIOUSLY ASKED QUESTIONS (do NOT repeat these):
{questions_list if questions_list else "None - this is the first question"}

INTERVIEW PROGRESS:
- Questions asked so far: {len(questions_asked)}
- Answers received: {len(answers_received)}

Generate ONE natural, conversational technical question that:
1. Flows naturally from the conversation (builds on previous answers if any)
2. Is relevant to the candidate's skills: {skills_context}
3. Has NOT been asked before (check the list above)
4. Feels like a natural next question in a human interview
5. Is appropriate for voice interaction (concise, clear)
6. Tests technical knowledge at an appropriate level

IMPORTANT:
- If this is early in the interview, start with foundational questions
- If the candidate mentioned something interesting, ask a follow-up
- Make it feel like a real conversation, not a scripted Q&A
- Reference specific technologies from their resume when relevant

Return ONLY the question text, nothing else. Make it sound natural and conversational."""

            # CRITICAL: Build messages with full conversation history for memory
            # Include the full conversation history as context so the AI remembers everything
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # Add conversation history as context messages (if available)
            # This ensures the AI has full memory of the entire interview
            # Limit to last 30 messages to fit within token limits while maintaining good memory
            if conversation_history and len(conversation_history) > 0:
                history_messages = conversation_history[-30:] if len(conversation_history) > 30 else conversation_history
                for msg in history_messages:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    if role == "ai" or role == "assistant":
                        messages.append({"role": "assistant", "content": content[:500]})  # Limit length
                    elif role == "user":
                        messages.append({"role": "user", "content": content[:500]})  # Limit length
            
            # Add the current prompt
            messages.append({"role": "user", "content": user_prompt})

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.8,  # Slightly higher for more natural variation
                max_tokens=200,  # Increased for more natural questions
                timeout=30
            )
            
            question = response.choices[0].message.content.strip()
            
            # Remove quotes if present
            if question.startswith('"') and question.endswith('"'):
                question = question[1:-1]
            
            return {
                "question": question,
                "question_type": "Technical",
                "audio_url": None  # Will be generated by TTS endpoint
            }
            
        except Exception as e:
            return self._get_fallback_question(session_data, questions_asked)
    
    def should_generate_followup(
        self,
        question: str,
        answer: str,
        conversation_history: List[Dict[str, str]],
        questions_asked: List[str]
    ) -> bool:
        """
        Determine if a follow-up question should be generated based on the answer
        """
        if not self.openai_available or self.client is None:
            # Simple heuristic: follow-up if answer is short or mentions interesting points
            answer_length = len(answer.strip())
            if answer_length < 50:  # Very short answer might need clarification
                return True
            if answer_length > 200 and any(keyword in answer.lower() for keyword in ["because", "when", "example", "project", "experience"]):
                # Long answer with details might warrant deeper dive
                return True
            return False
        
        try:
            system_prompt = """You are a technical interviewer analyzing whether a follow-up question is needed.
A follow-up question should be asked when:
1. The answer is vague or incomplete and needs clarification
2. The answer mentions something interesting that deserves deeper exploration
3. The answer shows expertise that can be tested further
4. The answer raises new questions or topics worth exploring

Do NOT ask follow-up if:
- The answer is complete and satisfactory
- We've already asked too many follow-ups on this topic
- The answer is clearly wrong and we should move on

Return ONLY "YES" or "NO", nothing else."""
            
            # Count how many follow-ups we've asked recently (last 3 questions)
            recent_questions = questions_asked[-3:] if len(questions_asked) >= 3 else questions_asked
            followup_count = sum(1 for q in recent_questions if "follow-up" in q.lower() or "based on" in q.lower() or "you mentioned" in q.lower())
            
            user_prompt = f"""Question: {question}

Answer: {answer}

Recent follow-ups asked: {followup_count}

Should we ask a follow-up question? Consider:
- Is the answer complete and clear?
- Does it mention something worth exploring deeper?
- Have we already asked too many follow-ups recently?

Return ONLY "YES" or "NO"."""
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,  # Lower temperature for more consistent decisions
                max_tokens=10,
                timeout=30
            )
            
            decision = response.choices[0].message.content.strip().upper()
            return "YES" in decision
            
        except Exception as e:
            # Fallback to simple heuristic
            answer_length = len(answer.strip())
            return answer_length < 100 or (answer_length > 150 and len(answer.split()) > 20)
    
    def generate_followup_question(
        self,
        question: str,
        answer: str,
        conversation_history: List[Dict[str, str]],
        session_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a nested follow-up question based on the user's answer
        Uses memory of previous answers to create contextual follow-ups
        """
        if not self.openai_available or self.client is None:
            # Fallback: simple follow-up based on answer content
            answer_lower = answer.lower()
            if "python" in answer_lower:
                return {
                    "question": "Can you give me a specific example of how you used Python in that project?",
                    "question_type": "Technical",
                    "is_followup": True,
                    "audio_url": None
                }
            elif "django" in answer_lower:
                return {
                    "question": "What challenges did you face when working with Django?",
                    "question_type": "Technical",
                    "is_followup": True,
                    "audio_url": None
                }
            return None
        
        try:
            # Build context from conversation history
            context_summary = ""
            if conversation_history:
                # Get last 6 messages for context
                recent_context = conversation_history[-6:]
                context_summary = "\n".join([
                    f"{msg.get('role', 'user').upper()}: {msg.get('content', '')[:200]}"
                    for msg in recent_context
                ])
            
            technical_skills = session_data.get("technical_skills", [])
            skills_context = ", ".join(technical_skills[:10]) if technical_skills else "general technical skills"
            
            system_prompt = """You are a technical interviewer generating a nested follow-up question.
Your goal is to dive deeper into what the candidate just said.

Follow-up questions should:
1. Be directly related to what the candidate mentioned in their answer
2. Reference specific details from their answer
3. Probe deeper into their experience or knowledge
4. Feel natural and conversational (not scripted)
5. Build on the conversation naturally

Keep questions:
- Concise (1-2 sentences) for voice interaction
- Contextual (reference what they said)
- Relevant to their technical background
- Progressive (go deeper, not sideways)

Return ONLY the follow-up question text, nothing else."""
            
            user_prompt = f"""Original Question: {question}

Candidate's Answer: {answer}

Candidate's Technical Skills: {skills_context}

Recent Conversation Context:
{context_summary if context_summary else "This is early in the interview."}

Generate ONE nested follow-up question that:
- MUST directly reference specific details from their answer above
- Uses their exact words, technologies, or concepts when possible
- Dives deeper into a technical aspect they mentioned
- Feels like a natural next question in a real interview
- References what they just said (e.g., "You mentioned X, can you tell me more about Y?")

CRITICAL: The follow-up MUST explicitly reference something from their answer.
Examples:
- If they said "Django REST API", ask: "You mentioned building a Django REST API. Can you explain how you handled authentication in that API?"
- If they said "I optimized performance", ask: "You mentioned optimizing performance. What specific techniques did you use?"
- If they said "PostgreSQL and Redis", ask: "You mentioned using PostgreSQL and Redis. How did you decide when to use each?"

IMPORTANT: Start with "You mentioned..." or "You said..." or reference their specific words to make it clear you're following up on their answer.

Return ONLY the question text, nothing else."""
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.8,
                max_tokens=150,
                timeout=30
            )
            
            followup_question = response.choices[0].message.content.strip()
            
            # Remove quotes if present
            if followup_question.startswith('"') and followup_question.endswith('"'):
                followup_question = followup_question[1:-1]
            
            if not followup_question:
                return None
            
            return {
                "question": followup_question,
                "question_type": "Technical",
                "is_followup": True,
                "audio_url": None  # Will be generated by TTS endpoint
            }
            
        except Exception as e:
            return None
    
    def evaluate_answer(
        self,
        question: str,
        answer: str,
        session_data: Dict[str, Any],
        conversation_history: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Evaluate the candidate's answer and generate AI response
        """
        # Use existing answer evaluator
        scores = answer_evaluator.evaluate_answer(
            question=question,
            question_type="Technical",
            answer=answer,
            experience_level="Intermediate",  # Default, can be improved
            response_time=None,
            interview_type="technical"  # Use technical API key
        )
        
        # Generate AI response using OpenAI if available
        ai_response = None
        if self.openai_available and self.client is not None:
            try:
                system_prompt = """You are a technical interviewer providing feedback during a voice interview.
After the candidate answers, provide:
1. Brief acknowledgment (1 sentence)
2. Follow-up question or move to next topic (1 sentence)

Keep responses natural and conversational for voice interaction.
Be encouraging but professional."""

                user_prompt = f"""Candidate's Answer: {answer}

Question: {question}

Evaluation Scores:
- Relevance: {scores.relevance}/100
- Technical Accuracy: {scores.technical_accuracy}/100
- Communication: {scores.communication}/100

Provide a brief, natural response (2-3 sentences max) that:
1. Acknowledges their answer
2. Provides brief feedback if needed
3. Either asks a follow-up or indicates moving to the next question

Keep it conversational and suitable for voice interaction."""

                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=100,
                    timeout=30
                )
                
                ai_response = response.choices[0].message.content.strip()
                
            except Exception as e:
                ai_response = "Thank you for your answer. Let's move to the next question."
        
        if not ai_response:
            ai_response = "Thank you for your answer. Let's move to the next question."
        
        return {
            "scores": {
                "relevance": scores.relevance,
                "technical_accuracy": scores.technical_accuracy,
                "communication": scores.communication,
                "overall": scores.overall
            },
            "ai_response": ai_response,
            "audio_url": None  # Will be generated by TTS endpoint
        }
    
    def generate_final_feedback(
        self,
        session_data: Dict[str, Any],
        conversation_history: List[Dict[str, str]],
        all_scores: List[Dict[str, int]]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive, personalized interview feedback based on actual answers
        Analyzes conversation history to provide specific, actionable feedback
        """
        if not all_scores:
            return {
                "overall_score": 0,
                "feedback_summary": "No answers provided.",
                "strengths": [],
                "areas_for_improvement": [],
                "recommendations": []
            }
        
        # ✅ FIX: Calculate overall score based on three key dimensions (out of 100)
        # Knowledge (Technical Accuracy) - 40% weight
        # Depth of Understanding (Relevance) - 35% weight  
        # Communication of Technical Concepts - 25% weight
        
        # Analyze by category
        relevance_scores = [s.get("relevance", 0) for s in all_scores]
        technical_scores = [s.get("technical_accuracy", 0) for s in all_scores]
        communication_scores = [s.get("communication", 0) for s in all_scores]
        
        avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0
        avg_technical = sum(technical_scores) / len(technical_scores) if technical_scores else 0
        avg_communication = sum(communication_scores) / len(communication_scores) if communication_scores else 0
        
        # ✅ FIX: Calculate weighted overall score (out of 100)
        # Weighted average: Knowledge (40%) + Depth (35%) + Communication (25%)
        avg_score = (avg_technical * 0.40) + (avg_relevance * 0.35) + (avg_communication * 0.25)
        
        # Ensure score is between 0 and 100
        avg_score = max(0, min(100, round(avg_score, 2)))
        
        logger.info(f"[FEEDBACK] Score calculation - Technical: {avg_technical:.1f}, Relevance: {avg_relevance:.1f}, Communication: {avg_communication:.1f}, Overall: {avg_score:.1f}/100")
        
        # Build conversation context for AI analysis
        # Extract Q&A pairs with scores for detailed analysis
        qa_pairs = []
        for i, score_data in enumerate(all_scores):
            # Find corresponding question and answer from conversation history
            # Questions are at even indices (0, 2, 4...), answers at odd (1, 3, 5...)
            q_idx = i * 2
            a_idx = i * 2 + 1
            if q_idx < len(conversation_history) and a_idx < len(conversation_history):
                question = conversation_history[q_idx].get("content", "")
                answer = conversation_history[a_idx].get("content", "")
                qa_pairs.append({
                    "question": question[:300],  # Limit length
                    "answer": answer[:500],  # Limit length
                    "relevance": score_data.get("relevance", 0),
                    "technical_accuracy": score_data.get("technical_accuracy", 0),
                    "communication": score_data.get("communication", 0),
                    "overall": score_data.get("overall", 0)
                })
        
        # Build full conversation context (last 20 messages for analysis)
        conversation_context = ""
        if conversation_history:
            recent_history = conversation_history[-20:] if len(conversation_history) > 20 else conversation_history
            conversation_context = "\n".join([
                f"{msg.get('role', 'unknown').upper()}: {msg.get('content', '')[:400]}"
                for msg in recent_history
            ])
        
        # Get technical skills from session data
        technical_skills = session_data.get("technical_skills", [])
        skills_context = ", ".join(technical_skills[:15]) if technical_skills else "general technical skills"
        experience_level = session_data.get("experience_level", "Intermediate")
        
        # Generate personalized feedback using AI if available
        if self.openai_available and self.client is not None:
            try:
                system_prompt = """You are an experienced technical interviewer providing comprehensive, personalized feedback after a technical interview.

Your task is to analyze the candidate's actual answers and provide:
1. SPECIFIC strengths based on what they actually said (not generic)
2. SPECIFIC areas for improvement based on their actual weaknesses
3. PERSONALIZED recommendations tailored to their performance
4. A human-like summary that reflects their actual interview performance

CRITICAL REQUIREMENTS:
- Base ALL feedback on the actual conversation history - reference specific answers
- Strengths must mention what they did well (e.g., "You demonstrated strong understanding of Django when you explained...")
- Weaknesses must reference what they struggled with (e.g., "Your explanation of database indexing could be clearer...")
- Recommendations must be actionable and specific to their gaps
- Summary must feel like a real human interviewer wrote it
- Be encouraging and constructive, never harsh or demotivating
- Focus on growth and learning opportunities

Format your response as JSON with these exact keys:
{
  "strengths": ["strength1", "strength2", "strength3"],
  "areas_for_improvement": ["area1", "area2", "area3"],
  "recommendations": ["recommendation1", "recommendation2", "recommendation3"],
  "summary": "2-3 paragraph human-like summary"
}

Each strength/weakness/recommendation should be 1-2 sentences and reference specific content from their answers."""

                # Build detailed Q&A analysis for the prompt
                qa_analysis = ""
                for idx, qa in enumerate(qa_pairs[:10], 1):  # Analyze up to 10 Q&A pairs
                    qa_analysis += f"""
Question {idx}: {qa['question']}
Answer: {qa['answer']}
Scores - Relevance: {qa['relevance']}/100, Technical: {qa['technical_accuracy']}/100, Communication: {qa['communication']}/100, Overall: {qa['overall']}/100
"""

                user_prompt = f"""Analyze this technical interview and provide personalized feedback.

CANDIDATE'S BACKGROUND:
- Technical Skills: {skills_context}
- Experience Level: {experience_level}

INTERVIEW PERFORMANCE METRICS:
- Overall Average Score: {avg_score:.1f}/100
- Technical Accuracy Average: {avg_technical:.1f}/100
- Communication Average: {avg_communication:.1f}/100
- Relevance Average: {avg_relevance:.1f}/100
- Total Questions Answered: {len(all_scores)}

QUESTION & ANSWER ANALYSIS (with scores):
{qa_analysis if qa_analysis else "No detailed Q&A pairs available."}

FULL CONVERSATION CONTEXT:
{conversation_context if conversation_context else "Limited conversation history available."}

Generate personalized feedback that:
1. References specific answers and examples from the conversation
2. Identifies real strengths (what they did well, specific skills demonstrated)
3. Points out specific weaknesses (what they struggled with, where they were unclear)
4. Provides actionable recommendations (what to learn, practice, or improve)
5. Writes a human-like summary that feels like a real interviewer's evaluation

Be specific, constructive, and encouraging. Reference actual content from their answers."""

                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1000,  # Increased for detailed feedback
                    response_format={"type": "json_object"},  # Force JSON response
                    timeout=30
                )
                
                # Extract and parse JSON response
                content = response.choices[0].message.content.strip()
                
                # Handle cases where JSON might be wrapped in markdown code blocks
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                feedback_json = json.loads(content)
                
                strengths = feedback_json.get("strengths", [])
                areas_for_improvement = feedback_json.get("areas_for_improvement", [])
                recommendations = feedback_json.get("recommendations", [])
                feedback_summary = feedback_json.get("summary", "")
                
                # Validate and ensure we have feedback
                if not strengths or len(strengths) == 0:
                    # Fallback: generate from scores
                    if avg_technical >= 75:
                        strengths.append("Strong technical knowledge demonstrated throughout the interview")
                    if avg_communication >= 75:
                        strengths.append("Clear and effective communication of technical concepts")
                    if avg_relevance >= 75:
                        strengths.append("Answers were relevant and directly addressed the questions")
                    if not strengths:
                        strengths.append("Good effort and engagement throughout the interview")
                
                if not areas_for_improvement or len(areas_for_improvement) == 0:
                    # Fallback: generate from scores
                    if avg_technical < 70:
                        areas_for_improvement.append("Technical accuracy and depth of knowledge need improvement")
                    if avg_communication < 70:
                        areas_for_improvement.append("Communication clarity and structure could be enhanced")
                    if avg_relevance < 70:
                        areas_for_improvement.append("Focus on providing more direct and relevant answers")
                    if not areas_for_improvement:
                        areas_for_improvement.append("Continue building on your technical foundation")
                
                if not recommendations or len(recommendations) == 0:
                    # Fallback: generate from scores
                    if avg_technical < 70:
                        recommendations.append("Review core technical concepts and practice explaining them clearly")
                    if avg_communication < 70:
                        recommendations.append("Practice structuring technical explanations with clear examples")
                    if not recommendations:
                        recommendations.append("Continue practicing technical interviews and reviewing key concepts")
                
                if not feedback_summary or len(feedback_summary.strip()) < 50:
                    # Fallback summary
                    feedback_summary = f"Overall performance score: {avg_score:.1f}/100. "
                    if strengths:
                        feedback_summary += f"Your strengths include {strengths[0].lower()}. "
                    if areas_for_improvement:
                        feedback_summary += f"Focus on improving {areas_for_improvement[0].lower()}. "
                    feedback_summary += "Keep practicing and building your technical skills."
                
                logger.info(f"[FEEDBACK] ✅ Generated personalized feedback with {len(strengths)} strengths, {len(areas_for_improvement)} improvements, {len(recommendations)} recommendations")
                
            except json.JSONDecodeError as json_error:
                logger.error(f"[FEEDBACK] ❌ Failed to parse JSON feedback: {str(json_error)}")
                # Fall through to fallback logic
                strengths = []
                areas_for_improvement = []
                recommendations = []
                feedback_summary = ""
            except Exception as e:
                logger.error(f"[FEEDBACK] ❌ Error generating AI feedback: {str(e)}")
                # Fall through to fallback logic
                strengths = []
                areas_for_improvement = []
                recommendations = []
                feedback_summary = ""
        else:
            # No AI available - use score-based fallback
            strengths = []
            areas_for_improvement = []
            recommendations = []
            feedback_summary = ""
        
        # Fallback: Generate feedback from scores if AI failed or not available
        if not strengths or not areas_for_improvement or not recommendations or not feedback_summary:
            # Analyze by category with more detail
            strengths = []
            areas_for_improvement = []
            recommendations = []
            
            # Technical accuracy analysis
            if avg_technical >= 80:
                strengths.append("Excellent technical knowledge and accuracy in your answers")
            elif avg_technical >= 70:
                strengths.append("Good technical understanding demonstrated in most answers")
            elif avg_technical >= 60:
                areas_for_improvement.append("Technical accuracy needs improvement - review core concepts")
                recommendations.append("Focus on strengthening your foundational technical knowledge through practice and study")
            else:
                areas_for_improvement.append("Significant gaps in technical accuracy - prioritize core concept review")
                recommendations.append("Consider taking structured courses or tutorials on fundamental technical concepts")
            
            # Communication analysis
            if avg_communication >= 80:
                strengths.append("Outstanding communication skills - clear and well-structured explanations")
            elif avg_communication >= 70:
                strengths.append("Good communication - your explanations were generally clear")
            elif avg_communication >= 60:
                areas_for_improvement.append("Communication clarity can be improved - practice structuring your answers")
                recommendations.append("Practice explaining technical concepts step-by-step with concrete examples")
            else:
                areas_for_improvement.append("Communication needs significant improvement - focus on clarity and structure")
                recommendations.append("Practice organizing your thoughts before speaking - use frameworks like 'situation, approach, result'")
            
            # Relevance analysis
            if avg_relevance >= 80:
                strengths.append("Answers were highly relevant and directly addressed the questions")
            elif avg_relevance >= 70:
                strengths.append("Good relevance - most answers stayed on topic")
            elif avg_relevance >= 60:
                areas_for_improvement.append("Work on staying more focused and directly addressing questions")
                recommendations.append("Practice listening carefully to questions and structuring answers to directly answer what was asked")
            else:
                areas_for_improvement.append("Answers often went off-topic - focus on relevance")
                recommendations.append("Practice pausing to understand the question fully before answering")
            
            # Generate summary
            if not feedback_summary:
                feedback_summary = f"Overall performance score: {avg_score:.1f}/100. "
                if avg_score >= 75:
                    feedback_summary += "You demonstrated strong technical knowledge and communication skills throughout the interview. "
                elif avg_score >= 60:
                    feedback_summary += "You showed good understanding in several areas, with room for improvement in others. "
                else:
                    feedback_summary += "This interview highlighted areas where you can focus your learning and practice. "
                
                if strengths:
                    feedback_summary += f"Your strengths include {', '.join([s.lower() for s in strengths[:2]])}. "
                if areas_for_improvement:
                    feedback_summary += f"Focus on improving {', '.join([a.lower() for a in areas_for_improvement[:2]])}. "
                feedback_summary += "Continue practicing and building your technical interview skills."
        
        # Ensure we have at least some feedback (final safety net)
        if not strengths:
            strengths.append("Good effort and engagement throughout the interview")
        if not areas_for_improvement:
            areas_for_improvement.append("Continue building on your technical foundation")
        if not recommendations:
            recommendations.append("Keep practicing technical interviews and reviewing key concepts")
        if not feedback_summary or len(feedback_summary.strip()) < 30:
            feedback_summary = f"Overall performance score: {avg_score:.1f}/100. Review your answers and continue practicing to improve."
        
        return {
            "overall_score": round(avg_score, 2),
            "feedback_summary": feedback_summary,
            "strengths": strengths[:5],  # Limit to top 5
            "areas_for_improvement": areas_for_improvement[:5],  # Limit to top 5
            "recommendations": recommendations[:5]  # Limit to top 5
        }
    
    def _get_fallback_question(
        self,
        session_data: Dict[str, Any],
        questions_asked: List[str]
    ) -> Dict[str, Any]:
        """Fallback questions that still leverage resume-driven context"""
        technical_skills = session_data.get("technical_skills", []) or []
        resume_projects = session_data.get("resume_projects", []) or []
        resume_domains = session_data.get("resume_domains", []) or []
        experience_level = session_data.get("experience_level")

        skill = technical_skills[len(questions_asked) % len(technical_skills)] if technical_skills else "your core stack"
        project = resume_projects[len(questions_asked) % len(resume_projects)] if resume_projects else ""
        domain_label = resume_domains[0] if resume_domains else session_data.get("role") or "your recent role"

        project_reference = project or f"your recent {domain_label} project"

        templates = [
            f"In '{project_reference}', how did you architect critical components using {skill}? Walk me through the design decisions.",
            f"What trade-offs did you evaluate when scaling the {skill}-heavy modules in {project_reference}?",
            f"Describe how you would refactor a legacy feature from {project_reference} using {skill} to improve reliability.",
            f"Based on your experience with {skill}, how do you ensure observability and troubleshooting are baked into your solutions?",
            f"How would you mentor a junior engineer to ramp up on {skill} while contributing to {project_reference}?"
        ]

        if experience_level:
            templates.append(
                f"With {experience_level} under your belt, how do you decide when to introduce advanced {skill} patterns versus keeping implementations simple?"
            )

        question = templates[len(questions_asked) % len(templates)]

        return {
            "question": question,
            "question_type": "Technical",
            "audio_url": None
        }

# Create global instance
technical_interview_engine = TechnicalInterviewEngine()

