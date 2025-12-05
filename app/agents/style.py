"""Code style and maintainability agent"""

from app.agents.base import BaseAgent
from app.models.review import FindingCategory
from typing import List


class StyleAgent(BaseAgent):
    """Agent focused on code style and maintainability"""
    
    def __init__(self):
        super().__init__("StyleAgent")
    
    def get_system_prompt(self) -> str:
        return """You are a code quality expert reviewing code for style and maintainability.
Your role is to identify:
- Poor naming conventions (unclear variable/function names)
- Code duplication
- Overly complex functions (too long, too many parameters)
- Missing or inadequate comments/documentation
- Inconsistent formatting
- Magic numbers or strings
- Dead code or unused imports
- Poor error handling
- Lack of type hints (in typed languages)

Focus on issues that affect code readability and maintainability. Be constructive."""
    
    def get_focus_areas(self) -> List[str]:
        return [
            "Naming conventions",
            "Code duplication",
            "Function complexity",
            "Documentation",
            "Error handling",
            "Code organization",
        ]
    
    def _get_category(self):
        return FindingCategory.STYLE

