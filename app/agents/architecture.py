"""Architecture and design review agent"""

from app.agents.base import BaseAgent
from app.models.review import FindingCategory
from typing import List


class ArchitectureAgent(BaseAgent):
    """Agent focused on architecture and design patterns"""
    
    def __init__(self):
        super().__init__("ArchitectureAgent")
    
    def get_system_prompt(self) -> str:
        return """You are a software architecture expert reviewing code for design quality.
Your role is to identify:
- Violation of SOLID principles
- Tight coupling between components
- Missing abstraction layers
- Inappropriate use of design patterns
- Circular dependencies
- God objects or classes with too many responsibilities
- Inconsistent layering (e.g., business logic in controllers)
- Missing interfaces or contracts
- Poor separation of concerns
- Scalability concerns

Focus on architectural issues that affect long-term maintainability and extensibility."""
    
    def get_focus_areas(self) -> List[str]:
        return [
            "SOLID principles",
            "Coupling and cohesion",
            "Design patterns",
            "Separation of concerns",
            "Scalability",
            "Modularity",
        ]
    
    def _get_category(self):
        return FindingCategory.ARCHITECTURE

