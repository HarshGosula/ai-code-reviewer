"""Orchestrator for multi-agent code review using LangGraph"""

import asyncio
from typing import List, Dict, Any, TypedDict, Annotated
from langgraph.graph import StateGraph, END
import logging
import operator

from app.agents.security import SecurityAgent
from app.agents.performance import PerformanceAgent
from app.agents.style import StyleAgent
from app.agents.architecture import ArchitectureAgent
from app.models.review import ReviewResult, AgentFinding
from app.rag.vector_store import get_vector_store

logger = logging.getLogger(__name__)


class ReviewState(TypedDict):
    """State for the review workflow"""
    code: str
    file_path: str
    repo_namespace: str
    context: str
    # Use Annotated with operator.add to allow concurrent updates
    findings: Annotated[List[AgentFinding], operator.add]
    agents_completed: Annotated[List[str], operator.add]


class ReviewOrchestrator:
    """Orchestrates multi-agent code review using LangGraph"""
    
    def __init__(self):
        self.security_agent = SecurityAgent()
        self.performance_agent = PerformanceAgent()
        self.style_agent = StyleAgent()
        self.architecture_agent = ArchitectureAgent()
        self.vector_store = get_vector_store()
        
        # Build the workflow graph
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(ReviewState)
        
        # Add nodes for each agent
        workflow.add_node("retrieve_context", self._retrieve_context)
        workflow.add_node("security_review", self._security_review)
        workflow.add_node("performance_review", self._performance_review)
        workflow.add_node("style_review", self._style_review)
        workflow.add_node("architecture_review", self._architecture_review)
        workflow.add_node("aggregate_results", self._aggregate_results)
        
        # Define the flow
        workflow.set_entry_point("retrieve_context")
        
        # After context retrieval, run all agents in parallel
        workflow.add_edge("retrieve_context", "security_review")
        workflow.add_edge("retrieve_context", "performance_review")
        workflow.add_edge("retrieve_context", "style_review")
        workflow.add_edge("retrieve_context", "architecture_review")
        
        # All agents flow to aggregation
        workflow.add_edge("security_review", "aggregate_results")
        workflow.add_edge("performance_review", "aggregate_results")
        workflow.add_edge("style_review", "aggregate_results")
        workflow.add_edge("architecture_review", "aggregate_results")
        
        # End after aggregation
        workflow.add_edge("aggregate_results", END)
        
        return workflow.compile()
    
    async def _retrieve_context(self, state: ReviewState) -> ReviewState:
        """Retrieve relevant context from RAG"""
        logger.info(f"Retrieving context for {state['file_path']}")
        
        # Search for similar code in the repository
        query = f"Code from {state['file_path']}: {state['code'][:500]}"
        
        try:
            matches = self.vector_store.search(
                query=query,
                repo_namespace=state["repo_namespace"],
                top_k=5,
            )
            
            # Build context from matches
            context_parts = []
            for match in matches:
                metadata = match.get("metadata", {})
                text = metadata.get("text", "")
                file_path = metadata.get("file_path", "")
                context_parts.append(f"From {file_path}:\n{text}")
            
            state["context"] = "\n\n".join(context_parts)
        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
            state["context"] = ""
        
        return state
    
    async def _security_review(self, state: ReviewState) -> Dict[str, Any]:
        """Run security agent"""
        logger.info("Running security review")
        findings = await self.security_agent.analyze(
            code=state["code"],
            context=state["context"],
            file_path=state["file_path"],
        )
        # Return only the new values to be added
        return {
            "findings": findings,
            "agents_completed": ["security"]
        }

    async def _performance_review(self, state: ReviewState) -> Dict[str, Any]:
        """Run performance agent"""
        logger.info("Running performance review")
        findings = await self.performance_agent.analyze(
            code=state["code"],
            context=state["context"],
            file_path=state["file_path"],
        )
        # Return only the new values to be added
        return {
            "findings": findings,
            "agents_completed": ["performance"]
        }

    async def _style_review(self, state: ReviewState) -> Dict[str, Any]:
        """Run style agent"""
        logger.info("Running style review")
        findings = await self.style_agent.analyze(
            code=state["code"],
            context=state["context"],
            file_path=state["file_path"],
        )
        # Return only the new values to be added
        return {
            "findings": findings,
            "agents_completed": ["style"]
        }

    async def _architecture_review(self, state: ReviewState) -> Dict[str, Any]:
        """Run architecture agent"""
        logger.info("Running architecture review")
        findings = await self.architecture_agent.analyze(
            code=state["code"],
            context=state["context"],
            file_path=state["file_path"],
        )
        # Return only the new values to be added
        return {
            "findings": findings,
            "agents_completed": ["architecture"]
        }
    
    async def _aggregate_results(self, state: ReviewState) -> ReviewState:
        """Aggregate results from all agents"""
        logger.info(f"Aggregating results: {len(state['findings'])} findings from {len(state['agents_completed'])} agents")
        return state
    
    async def review_code(
        self,
        code: str,
        file_path: str,
        repo_namespace: str,
    ) -> List[AgentFinding]:
        """
        Review code using all agents.
        
        Args:
            code: Code to review
            file_path: Path to the file
            repo_namespace: Repository namespace for RAG context
            
        Returns:
            List of findings from all agents
        """
        initial_state: ReviewState = {
            "code": code,
            "file_path": file_path,
            "repo_namespace": repo_namespace,
            "context": "",
            "findings": [],
            "agents_completed": [],
        }
        
        # Run the workflow
        final_state = await self.workflow.ainvoke(initial_state)
        
        return final_state["findings"]
    
    async def review_multiple_files(
        self,
        files: List[Dict[str, str]],
        repo_namespace: str,
    ) -> ReviewResult:
        """
        Review multiple files.
        
        Args:
            files: List of dicts with 'path' and 'content' keys
            repo_namespace: Repository namespace
            
        Returns:
            Complete review result
        """
        all_findings = []
        
        # Review files concurrently (with some limit to avoid overwhelming the API)
        semaphore = asyncio.Semaphore(3)  # Max 3 concurrent reviews
        
        async def review_with_semaphore(file_data):
            async with semaphore:
                return await self.review_code(
                    code=file_data["content"],
                    file_path=file_data["path"],
                    repo_namespace=repo_namespace,
                )
        
        tasks = [review_with_semaphore(file_data) for file_data in files]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error in file review: {result}")
            else:
                all_findings.extend(result)
        
        # Create review result
        review_result = ReviewResult(
            repository=repo_namespace.replace("_", "/"),
            findings=all_findings,
            total_files_analyzed=len(files),
        )
        
        return review_result


# Singleton instance
_orchestrator = None


def get_orchestrator() -> ReviewOrchestrator:
    """Get the review orchestrator singleton"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ReviewOrchestrator()
    return _orchestrator

