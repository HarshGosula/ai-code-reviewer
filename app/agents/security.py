"""Security-focused code review agent"""

from app.agents.base import BaseAgent
from app.models.review import FindingCategory
from typing import List


class SecurityAgent(BaseAgent):
    """Agent focused on security vulnerabilities"""
    
    def __init__(self):
        super().__init__("SecurityAgent")
    
    def get_system_prompt(self) -> str:
        return """You are a security expert reviewing code for vulnerabilities and security issues.
Your role is to identify:
- SQL injection vulnerabilities
- Cross-site scripting (XSS) vulnerabilities
- Authentication and authorization issues
- Insecure data handling
- Hardcoded secrets or credentials
- Insecure dependencies
- Cryptographic weaknesses
- Input validation issues
- Path traversal vulnerabilities
- Command injection risks

Be thorough but avoid false positives. Only report genuine security concerns."""
    
    def get_focus_areas(self) -> List[str]:
        return [
            "SQL injection",
            "XSS vulnerabilities",
            "Authentication/Authorization",
            "Secrets management",
            "Input validation",
            "Cryptography",
            "Dependency security",
        ]
    
    def _get_category(self):
        return FindingCategory.SECURITY

