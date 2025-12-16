"""
Content personalization service based on user background and preferences.
"""
from openai import OpenAI
from typing import Dict
import os
import logging

logger = logging.getLogger(__name__)


class PersonalizationService:
    """Service for personalizing educational content."""

    def __init__(self):
        """Initialize OpenAI client."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        self.openai_client = OpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"

    async def personalize_content(
        self,
        content: str,
        user_background: Dict,
        level: str
    ) -> str:
        """
        Personalize content based on user background and target level.

        Args:
            content: Original content to personalize
            user_background: Dict with software_background and hardware_background
            level: Target level (simplified, standard, advanced)

        Returns:
            Personalized content
        """
        # Build user background description
        software_bg = user_background.get('software_background', 'beginner')
        hardware_bg = user_background.get('hardware_background', 'none')

        background_desc = f"""User Profile:
- Software Background: {software_bg}
- Hardware Background: {hardware_bg}
- Target Level: {level}"""

        # Determine instruction based on level
        instructions = {
            "simplified": """Simplify this content for absolute beginners:
- Use everyday analogies and examples
- Avoid technical jargon or explain it clearly
- Break down complex concepts into simple steps
- Use conversational, encouraging tone
- Add practical examples from daily life
- Focus on conceptual understanding over technical details""",

            "standard": """Present this content at a standard technical level:
- Suitable for engineering students
- Balance theory with practical applications
- Use appropriate technical terminology
- Include relevant examples and use cases
- Maintain clear, educational tone
- Provide enough depth without overwhelming detail""",

            "advanced": """Expand this content with advanced technical details:
- Include mathematical formulations where relevant
- Add industry best practices and optimization techniques
- Discuss edge cases and limitations
- Reference current research and state-of-the-art approaches
- Use precise technical language
- Assume strong foundational knowledge"""
        }

        instruction = instructions.get(level, instructions["standard"])

        # Additional context based on background
        bg_context = ""
        if software_bg == "beginner":
            bg_context += "\n- The user is new to programming, so explain code examples carefully"
        elif software_bg == "advanced":
            bg_context += "\n- The user has strong programming skills, so you can use advanced patterns"

        if hardware_bg == "none":
            bg_context += "\n- The user has no hardware experience, so explain physical concepts clearly"
        elif hardware_bg in ["intermediate", "advanced"]:
            bg_context += "\n- The user has hardware experience, so you can reference electronics and mechanics"

        try:
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are an expert educational content adapter specializing in Physical AI and Humanoid Robotics.

{background_desc}

{instruction}

{bg_context}

Important:
- Preserve all markdown formatting
- Keep code blocks intact (but may add comments)
- Maintain factual accuracy
- Adjust complexity and depth based on the target level
- Keep the content engaging and educational"""
                    },
                    {
                        "role": "user",
                        "content": content
                    }
                ],
                temperature=0.7,
                max_tokens=4000
            )

            personalized = response.choices[0].message.content
            logger.info(f"Content personalized to level: {level}")
            return personalized

        except Exception as e:
            logger.error(f"Error personalizing content: {str(e)}")
            raise

    async def generate_learning_path(
        self,
        user_background: Dict,
        chapters: list[str]
    ) -> Dict:
        """
        Generate a personalized learning path based on user background.

        Args:
            user_background: User's technical background
            chapters: List of available chapters

        Returns:
            Recommended learning path with difficulty indicators
        """
        software_bg = user_background.get('software_background', 'beginner')
        hardware_bg = user_background.get('hardware_background', 'none')

        try:
            chapters_list = "\n".join([f"- {ch}" for ch in chapters])

            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are an educational advisor for a Physical AI and Humanoid Robotics course.

User Background:
- Software: {software_bg}
- Hardware: {hardware_bg}

Create a personalized learning path that:
1. Starts with fundamentals they might be missing
2. Builds progressively on their existing knowledge
3. Highlights chapters that might be challenging
4. Suggests focus areas based on their background

Return a JSON object with:
{{
  "recommended_order": ["chapter1", "chapter2", ...],
  "difficulty_map": {{"chapter1": "easy", "chapter2": "medium", ...}},
  "focus_areas": ["area1", "area2", ...],
  "prerequisites": {{"chapter_x": ["prereq1", "prereq2"]}}
}}"""
                    },
                    {
                        "role": "user",
                        "content": f"Available chapters:\n{chapters_list}"
                    }
                ],
                temperature=0.5,
                response_format={"type": "json_object"}
            )

            import json
            learning_path = json.loads(response.choices[0].message.content)
            logger.info("Generated personalized learning path")
            return learning_path

        except Exception as e:
            logger.error(f"Error generating learning path: {str(e)}")
            # Return default path on error
            return {
                "recommended_order": chapters,
                "difficulty_map": {ch: "medium" for ch in chapters},
                "focus_areas": ["fundamentals"],
                "prerequisites": {}
            }

    async def suggest_exercises(
        self,
        content: str,
        user_background: Dict,
        num_exercises: int = 3
    ) -> list[Dict]:
        """
        Generate personalized practice exercises based on content.

        Args:
            content: Chapter content
            user_background: User's technical background
            num_exercises: Number of exercises to generate

        Returns:
            List of exercise dictionaries
        """
        software_bg = user_background.get('software_background', 'beginner')

        try:
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"""Create {num_exercises} practice exercises based on the content.

User's software level: {software_bg}

Generate exercises appropriate for their level:
- Beginner: Step-by-step guided exercises
- Intermediate: Problem-solving with hints
- Advanced: Open-ended challenges

Return a JSON array of exercises with:
{{
  "title": "Exercise title",
  "description": "What to do",
  "difficulty": "easy/medium/hard",
  "hints": ["hint1", "hint2"],
  "solution_outline": "Brief outline"
}}"""
                    },
                    {
                        "role": "user",
                        "content": f"Content:\n{content[:2000]}"  # Limit content length
                    }
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )

            import json
            result = json.loads(response.choices[0].message.content)
            exercises = result.get("exercises", [])
            logger.info(f"Generated {len(exercises)} personalized exercises")
            return exercises

        except Exception as e:
            logger.error(f"Error generating exercises: {str(e)}")
            return []
