"""Performance-focused code review agent"""

from app.agents.base import BaseAgent
from app.models.review import FindingCategory
from typing import List


class PerformanceAgent(BaseAgent):
    """Agent focused on performance issues"""
    
    def __init__(self):
        super().__init__("PerformanceAgent")
    
    def get_system_prompt(self) -> str:
        return """You are a performance optimization expert reviewing code for efficiency issues.
Your role is to identify:
- Inefficient algorithms (e.g., O(n²) when O(n) is possible)
- N+1 query problems in database operations
- Unnecessary loops or iterations
- Memory leaks or excessive memory usage
- Blocking operations that should be async
- Redundant computations
- Inefficient data structures
- Missing caching opportunities
- Large file operations without streaming

Focus on issues that have measurable performance impact."""
    
    def get_focus_areas(self) -> List[str]:
        return [
            "Algorithm efficiency",
            "Database query optimization",
            "Memory usage",
            "Async/await patterns",
            "Caching opportunities",
            "Data structure selection",
        ]
    
    def _get_category(self):
        return FindingCategory.PERFORMANCE

