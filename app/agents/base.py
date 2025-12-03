"""Base agent class for code review"""

import google.generativeai as genai
from typing import List, Dict, Any
from abc import ABC, abstractmethod
from app.config import get_settings
from app.models.review import AgentFinding
import logging

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all review agents"""
    
    def __init__(self, name: str):
        self.name = name
        self.settings = get_settings()
        genai.configure(api_key=self.settings.gemini_api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent"""
        pass
    
    @abstractmethod
    def get_focus_areas(self) -> List[str]:
        """Get the focus areas for this agent"""
        pass
    
    async def analyze(
        self,
        code: str,
        context: str = "",
        file_path: str = "",
    ) -> List[AgentFinding]:
        """
        Analyze code and return findings.
        
        Args:
            code: Code to analyze
            context: Additional context from RAG
            file_path: Path to the file being analyzed
            
        Returns:
            List of findings
        """
        prompt = self._build_prompt(code, context, file_path)
        
        try:
            response = self.model.generate_content(prompt)
            findings = self._parse_response(response.text, file_path)
            return findings
        except Exception as e:
            logger.error(f"Error in {self.name} analysis: {e}")
            return []
    
    def _build_prompt(self, code: str, context: str, file_path: str) -> str:
        """Build the analysis prompt"""
        prompt = f"{self.get_system_prompt()}\n\n"
        
        if context:
            prompt += f"## Repository Context\n{context}\n\n"
        
        prompt += f"## Code to Review\n"
        if file_path:
            prompt += f"File: {file_path}\n\n"
        
        prompt += f"```\n{code}\n```\n\n"
        
        prompt += """
Please analyze the code and provide findings in the following JSON format:
[
  {
    "title": "Brief title of the issue",
    "description": "Detailed description",
    "severity": "critical|high|medium|low|info",
    "line_number": <line number if applicable>,
    "code_snippet": "relevant code snippet",
    "suggestion": "how to fix it"
  }
]

Focus on: """ + ", ".join(self.get_focus_areas())
        
        return prompt
    
    def _parse_response(self, response_text: str, file_path: str) -> List[AgentFinding]:
        """Parse LLM response into AgentFinding objects"""
        import json
        import re
        
        findings = []
        
        # Try to extract JSON from response
        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if not json_match:
            logger.warning(f"{self.name}: No JSON found in response")
            return findings
        
        try:
            findings_data = json.loads(json_match.group())
            
            for item in findings_data:
                # Map severity string to enum
                from app.models.review import FindingSeverity, FindingCategory
                
                severity_map = {
                    "critical": FindingSeverity.CRITICAL,
                    "high": FindingSeverity.HIGH,
                    "medium": FindingSeverity.MEDIUM,
                    "low": FindingSeverity.LOW,
                    "info": FindingSeverity.INFO,
                }
                
                finding = AgentFinding(
                    agent_name=self.name,
                    category=self._get_category(),
                    severity=severity_map.get(item.get("severity", "info"), FindingSeverity.INFO),
                    title=item.get("title", "Issue found"),
                    description=item.get("description", ""),
                    file_path=file_path,
                    line_number=item.get("line_number"),
                    code_snippet=item.get("code_snippet"),
                    suggestion=item.get("suggestion"),
                )
                findings.append(finding)
        
        except json.JSONDecodeError as e:
            logger.error(f"{self.name}: Failed to parse JSON: {e}")
        
        return findings
    
    @abstractmethod
    def _get_category(self):
        """Get the category for findings from this agent"""
        pass

