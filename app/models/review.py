"""Code review and analysis models"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class FindingSeverity(str, Enum):
    """Severity levels for findings"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingCategory(str, Enum):
    """Categories of findings"""
    SECURITY = "security"
    PERFORMANCE = "performance"
    STYLE = "style"
    ARCHITECTURE = "architecture"
    BUG = "bug"
    BEST_PRACTICE = "best_practice"


class AgentFinding(BaseModel):
    """A single finding from an agent"""
    agent_name: str
    category: FindingCategory
    severity: FindingSeverity
    title: str
    description: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    code_snippet: Optional[str] = None
    suggestion: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    
    def to_markdown(self) -> str:
        """Convert finding to markdown format"""
        severity_emoji = {
            FindingSeverity.CRITICAL: "🔴",
            FindingSeverity.HIGH: "🟠",
            FindingSeverity.MEDIUM: "🟡",
            FindingSeverity.LOW: "🔵",
            FindingSeverity.INFO: "ℹ️",
        }
        
        md = f"{severity_emoji[self.severity]} **{self.title}** ({self.severity.value})\n\n"
        md += f"**Category:** {self.category.value}\n\n"
        md += f"{self.description}\n\n"
        
        if self.file_path:
            location = f"`{self.file_path}`"
            if self.line_number:
                location += f" (line {self.line_number})"
            md += f"**Location:** {location}\n\n"
        
        if self.code_snippet:
            md += f"**Code:**\n```\n{self.code_snippet}\n```\n\n"
        
        if self.suggestion:
            md += f"**Suggestion:** {self.suggestion}\n\n"
        
        return md


class ReviewComment(BaseModel):
    """A review comment to post on GitHub"""
    path: str
    line: int
    body: str
    side: str = "RIGHT"  # RIGHT for new code, LEFT for old code


class ReviewResult(BaseModel):
    """Complete review result from all agents"""
    repository: str
    pr_number: Optional[int] = None
    findings: List[AgentFinding] = Field(default_factory=list)
    summary: str = ""
    total_files_analyzed: int = 0
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == FindingSeverity.CRITICAL)
    
    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == FindingSeverity.HIGH)
    
    @property
    def medium_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == FindingSeverity.MEDIUM)
    
    def to_markdown_summary(self) -> str:
        """Generate markdown summary of review"""
        md = "# 🤖 AI Code Review Summary\n\n"
        md += f"**Repository:** {self.repository}\n"
        if self.pr_number:
            md += f"**PR:** #{self.pr_number}\n"
        md += f"**Files Analyzed:** {self.total_files_analyzed}\n"
        md += f"**Timestamp:** {self.analysis_timestamp.isoformat()}\n\n"
        
        md += "## 📊 Findings Overview\n\n"
        md += f"- 🔴 Critical: {self.critical_count}\n"
        md += f"- 🟠 High: {self.high_count}\n"
        md += f"- 🟡 Medium: {self.medium_count}\n"
        md += f"- Total Issues: {len(self.findings)}\n\n"
        
        if self.summary:
            md += f"## 📝 Summary\n\n{self.summary}\n\n"
        
        if self.findings:
            md += "## 🔍 Detailed Findings\n\n"
            
            # Group by category
            by_category: Dict[FindingCategory, List[AgentFinding]] = {}
            for finding in self.findings:
                if finding.category not in by_category:
                    by_category[finding.category] = []
                by_category[finding.category].append(finding)
            
            for category, findings in by_category.items():
                md += f"### {category.value.replace('_', ' ').title()}\n\n"
                for finding in sorted(findings, key=lambda x: x.severity.value):
                    md += finding.to_markdown()
                    md += "---\n\n"
        else:
            md += "✅ No issues found! Great work!\n\n"
        
        md += "*Powered by AI Code Review Bot*\n"
        return md

