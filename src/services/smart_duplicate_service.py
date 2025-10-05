"""Smart duplicate detection service with MCP-enhanced intelligence."""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from fuzzywuzzy import fuzz
import re

from .mcp_jira_service import MCPJiraService, ProjectContext, TaskSimilarity
from ..config import AppConfig
from ..exceptions import DuplicateDetectionError
from ..utils import LoggerMixin
from .cache_service import CacheService


@dataclass
class DuplicateCandidate:
    """A potential duplicate task candidate."""

    issue_key: str
    summary: str
    description: str
    status: str
    assignee: str
    created_date: str
    similarity_score: float
    similarity_factors: List[str]
    recommendation: str  # 'skip', 'merge', 'link', 'create_anyway'
    confidence: float
    project_context: Dict[str, Any]


@dataclass
class ConflictResolution:
    """Resolution for a duplicate conflict."""

    original_task_id: str
    resolution_type: str  # 'skip', 'merge', 'link', 'create_anyway'
    target_issue_key: str
    user_notes: str
    resolved_at: str
    auto_resolved: bool


@dataclass
class SimilarityAnalysis:
    """Comprehensive similarity analysis result."""

    text_similarity: float
    semantic_similarity: float
    context_similarity: float
    temporal_similarity: float
    assignee_similarity: float
    overall_score: float
    factors: List[str]


class SmartDuplicateService(LoggerMixin):
    """Advanced duplicate detection with MCP-enhanced intelligence."""

    def __init__(self, config: AppConfig, mcp_service: MCPJiraService):
        """
        Initialize smart duplicate detection service.

        Args:
            config: Application configuration
            mcp_service: MCP JIRA service for live data access
        """
        self.config = config
        self.mcp_service = mcp_service
        self._cache_service = CacheService()

    async def find_duplicates_via_mcp(self, task: Dict[str, Any], project_key: str,
                                    include_resolved: bool = False) -> List[DuplicateCandidate]:
        """
        Find duplicate candidates using MCP-powered JIRA search.

        Args:
            task: Task data to check for duplicates
            project_key: JIRA project key
            include_resolved: Whether to include resolved issues

        Returns:
            List of duplicate candidates with analysis
        """
        try:
            self.logger.info(f"Starting smart duplicate detection for project {project_key}")

            # Get project context for enhanced matching
            project_context = await self.mcp_service.get_project_context(project_key)

            # Search for similar tasks using multiple strategies
            candidates = await self._search_similar_tasks_multi_strategy(
                task, project_key, project_context, include_resolved
            )

            # Analyze each candidate for similarity
            analyzed_candidates = []
            for candidate in candidates:
                analysis = await self._analyze_comprehensive_similarity(
                    task, candidate, project_context
                )

                if analysis.overall_score >= self.config.jira.similarity_threshold:
                    duplicate_candidate = DuplicateCandidate(
                        issue_key=candidate.get('key', ''),
                        summary=candidate.get('fields', {}).get('summary', ''),
                        description=candidate.get('fields', {}).get('description', '') or '',
                        status=candidate.get('fields', {}).get('status', {}).get('name', ''),
                        assignee=self._get_assignee_name(candidate),
                        created_date=candidate.get('fields', {}).get('created', ''),
                        similarity_score=analysis.overall_score,
                        similarity_factors=analysis.factors,
                        recommendation=self._get_recommendation(analysis),
                        confidence=self._calculate_confidence(analysis),
                        project_context=self._extract_issue_context(candidate, project_context)
                    )
                    analyzed_candidates.append(duplicate_candidate)

            # Sort by similarity score
            analyzed_candidates.sort(key=lambda x: x.similarity_score, reverse=True)

            self.logger.info(f"Found {len(analyzed_candidates)} potential duplicates")
            return analyzed_candidates[:self.config.jira.max_search_results]

        except Exception as e:
            self.logger.error(f"Duplicate detection failed: {e}")
            raise DuplicateDetectionError(f"Failed to find duplicates: {str(e)}")

    async def analyze_bulk_duplicates(self, tasks: List[Dict[str, Any]], project_key: str) -> Dict[str, Any]:
        """
        Analyze multiple tasks for duplicates and cross-references.

        Args:
            tasks: List of tasks to analyze
            project_key: JIRA project key

        Returns:
            Comprehensive duplicate analysis report
        """
        try:
            self.logger.info(f"Starting bulk duplicate analysis for {len(tasks)} tasks")

            project_context = await self.mcp_service.get_project_context(project_key)

            # Analyze each task for duplicates
            all_duplicates = {}
            cross_references = []

            for i, task in enumerate(tasks):
                task_id = f"task_{i}"

                # Find duplicates in JIRA
                duplicates = await self.find_duplicates_via_mcp(task, project_key)
                all_duplicates[task_id] = duplicates

                # Check for cross-references with other tasks in the batch
                for j, other_task in enumerate(tasks[i+1:], i+1):
                    similarity = await self._analyze_task_to_task_similarity(task, other_task)
                    if similarity.overall_score >= self.config.jira.similarity_threshold:
                        cross_references.append({
                            'task_1_id': task_id,
                            'task_2_id': f"task_{j}",
                            'similarity_score': similarity.overall_score,
                            'recommendation': self._get_recommendation(similarity),
                            'factors': similarity.factors
                        })

            # Generate summary statistics
            summary = self._generate_duplicate_summary(all_duplicates, cross_references)

            return {
                'project_key': project_key,
                'total_tasks_analyzed': len(tasks),
                'duplicates_found': all_duplicates,
                'cross_references': cross_references,
                'summary': summary,
                'analysis_timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Bulk duplicate analysis failed: {e}")
            raise DuplicateDetectionError(f"Bulk analysis failed: {str(e)}")

    async def resolve_duplicate_conflicts(self, conflicts: List[Dict[str, Any]],
                                        user_resolutions: List[Dict[str, Any]]) -> List[ConflictResolution]:
        """
        Resolve duplicate conflicts based on user decisions.

        Args:
            conflicts: List of detected conflicts
            user_resolutions: User decisions for each conflict

        Returns:
            List of applied resolutions
        """
        try:
            self.logger.info(f"Resolving {len(conflicts)} duplicate conflicts")

            resolutions = []
            for i, (conflict, resolution) in enumerate(zip(conflicts, user_resolutions)):
                conflict_resolution = ConflictResolution(
                    original_task_id=conflict.get('task_id', f'task_{i}'),
                    resolution_type=resolution.get('action', 'create_anyway'),
                    target_issue_key=resolution.get('target_issue_key', ''),
                    user_notes=resolution.get('notes', ''),
                    resolved_at=datetime.now().isoformat(),
                    auto_resolved=resolution.get('auto_resolved', False)
                )

                # Apply the resolution
                await self._apply_resolution(conflict, resolution)
                resolutions.append(conflict_resolution)

            self.logger.info(f"Successfully resolved {len(resolutions)} conflicts")
            return resolutions

        except Exception as e:
            self.logger.error(f"Conflict resolution failed: {e}")
            raise DuplicateDetectionError(f"Resolution failed: {str(e)}")

    async def suggest_task_relationships(self, tasks: List[Dict[str, Any]],
                                       project_context: ProjectContext) -> List[Dict[str, Any]]:
        """
        Suggest relationships between tasks and existing issues.

        Args:
            tasks: List of tasks to analyze
            project_context: Project context for relationship analysis

        Returns:
            List of suggested relationships
        """
        try:
            self.logger.info("Analyzing task relationships")

            relationships = []

            for i, task in enumerate(tasks):
                task_id = f"task_{i}"

                # Find potential parent epics
                epic_suggestions = await self._suggest_epic_relationships(task, project_context)

                # Find blocking/blocked relationships
                blocking_suggestions = await self._suggest_blocking_relationships(task, project_context)

                # Find related stories
                related_suggestions = await self._suggest_related_stories(task, project_context)

                if epic_suggestions or blocking_suggestions or related_suggestions:
                    relationships.append({
                        'task_id': task_id,
                        'task_summary': task.get('summary', ''),
                        'epic_suggestions': epic_suggestions,
                        'blocking_suggestions': blocking_suggestions,
                        'related_suggestions': related_suggestions
                    })

            return relationships

        except Exception as e:
            self.logger.error(f"Relationship suggestion failed: {e}")
            return []

    async def _search_similar_tasks_multi_strategy(self, task: Dict[str, Any], project_key: str,
                                                 project_context: ProjectContext,
                                                 include_resolved: bool) -> List[Dict[str, Any]]:
        """Search for similar tasks using multiple strategies."""
        all_candidates = []

        # Strategy 1: Exact text matching
        text_candidates = await self._search_by_text_similarity(
            task, project_key, include_resolved
        )
        all_candidates.extend(text_candidates)

        # Strategy 2: Keyword-based search
        keyword_candidates = await self._search_by_keywords(
            task, project_key, project_context, include_resolved
        )
        all_candidates.extend(keyword_candidates)

        # Strategy 3: Semantic search using AI
        semantic_candidates = await self._search_by_semantic_similarity(
            task, project_key, project_context, include_resolved
        )
        all_candidates.extend(semantic_candidates)

        # Remove duplicates based on issue key
        seen_keys = set()
        unique_candidates = []
        for candidate in all_candidates:
            key = candidate.get('key', '')
            if key and key not in seen_keys:
                seen_keys.add(key)
                unique_candidates.append(candidate)

        return unique_candidates

    async def _search_by_text_similarity(self, task: Dict[str, Any], project_key: str,
                                       include_resolved: bool) -> List[Dict[str, Any]]:
        """Search using direct text similarity."""
        summary = task.get('summary', '')
        description = task.get('description', '')

        # Create search query based on key terms
        search_terms = self._extract_search_terms(summary + ' ' + description)

        # Mock search results (in real implementation, use MCP)
        mock_results = [
            {
                'key': 'DEMO-123',
                'fields': {
                    'summary': 'Implement user authentication system',
                    'description': 'Create login and registration functionality',
                    'status': {'name': 'In Progress'},
                    'assignee': {'displayName': 'John Doe'},
                    'created': '2025-09-01T10:00:00.000Z'
                }
            }
        ]

        return mock_results if 'auth' in summary.lower() else []

    async def _search_by_keywords(self, task: Dict[str, Any], project_key: str,
                                project_context: ProjectContext, include_resolved: bool) -> List[Dict[str, Any]]:
        """Search using keyword extraction and matching."""
        keywords = self._extract_keywords(task, project_context)

        # Mock keyword-based search
        return []

    async def _search_by_semantic_similarity(self, task: Dict[str, Any], project_key: str,
                                           project_context: ProjectContext,
                                           include_resolved: bool) -> List[Dict[str, Any]]:
        """Search using AI-powered semantic similarity."""
        # This would use the AI service to find semantically similar tasks
        return []

    async def _analyze_comprehensive_similarity(self, task: Dict[str, Any],
                                              candidate: Dict[str, Any],
                                              project_context: ProjectContext) -> SimilarityAnalysis:
        """Perform comprehensive similarity analysis."""
        task_summary = task.get('summary', '')
        task_description = task.get('description', '')
        task_text = f"{task_summary} {task_description}"

        candidate_summary = candidate.get('fields', {}).get('summary', '')
        candidate_description = candidate.get('fields', {}).get('description', '') or ''
        candidate_text = f"{candidate_summary} {candidate_description}"

        # Text similarity using fuzzywuzzy
        text_sim = fuzz.token_sort_ratio(task_text.lower(), candidate_text.lower()) / 100.0

        # Semantic similarity (mock for now)
        semantic_sim = self._calculate_semantic_similarity(task_text, candidate_text)

        # Context similarity
        context_sim = self._calculate_context_similarity(task, candidate, project_context)

        # Temporal similarity
        temporal_sim = self._calculate_temporal_similarity(task, candidate)

        # Assignee similarity
        assignee_sim = self._calculate_assignee_similarity(task, candidate)

        # Calculate weighted overall score
        weights = {
            'text': 0.4,
            'semantic': 0.3,
            'context': 0.15,
            'temporal': 0.1,
            'assignee': 0.05
        }

        overall_score = (
            text_sim * weights['text'] +
            semantic_sim * weights['semantic'] +
            context_sim * weights['context'] +
            temporal_sim * weights['temporal'] +
            assignee_sim * weights['assignee']
        )

        # Determine contributing factors
        factors = []
        if text_sim > 0.8:
            factors.append('high_text_similarity')
        if semantic_sim > 0.7:
            factors.append('semantic_match')
        if context_sim > 0.6:
            factors.append('similar_context')
        if temporal_sim > 0.8:
            factors.append('recent_timing')
        if assignee_sim > 0.9:
            factors.append('same_assignee')

        return SimilarityAnalysis(
            text_similarity=text_sim,
            semantic_similarity=semantic_sim,
            context_similarity=context_sim,
            temporal_similarity=temporal_sim,
            assignee_similarity=assignee_sim,
            overall_score=overall_score,
            factors=factors
        )

    async def _analyze_task_to_task_similarity(self, task1: Dict[str, Any],
                                             task2: Dict[str, Any]) -> SimilarityAnalysis:
        """Analyze similarity between two new tasks."""
        task1_text = f"{task1.get('summary', '')} {task1.get('description', '')}"
        task2_text = f"{task2.get('summary', '')} {task2.get('description', '')}"

        text_sim = fuzz.token_sort_ratio(task1_text.lower(), task2_text.lower()) / 100.0
        semantic_sim = self._calculate_semantic_similarity(task1_text, task2_text)

        overall_score = (text_sim * 0.6 + semantic_sim * 0.4)

        factors = []
        if text_sim > 0.8:
            factors.append('high_text_similarity')
        if semantic_sim > 0.7:
            factors.append('semantic_match')

        return SimilarityAnalysis(
            text_similarity=text_sim,
            semantic_similarity=semantic_sim,
            context_similarity=0.0,
            temporal_similarity=1.0,  # Same batch, so recent
            assignee_similarity=0.0,
            overall_score=overall_score,
            factors=factors
        )

    def _calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity (simplified implementation)."""
        # Simplified semantic similarity based on common meaningful words
        words1 = set(word.lower() for word in text1.split() if len(word) > 3)
        words2 = set(word.lower() for word in text2.split() if len(word) > 3)

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0

    def _calculate_context_similarity(self, task: Dict[str, Any], candidate: Dict[str, Any],
                                    project_context: ProjectContext) -> float:
        """Calculate context-based similarity."""
        # Compare issue types
        task_type = task.get('issue_type', 'Task')
        candidate_type = candidate.get('fields', {}).get('issuetype', {}).get('name', '')

        type_match = 1.0 if task_type == candidate_type else 0.0

        # Compare components/categories (mock for now)
        return type_match * 0.8

    def _calculate_temporal_similarity(self, task: Dict[str, Any], candidate: Dict[str, Any]) -> float:
        """Calculate temporal similarity based on creation dates."""
        try:
            created_str = candidate.get('fields', {}).get('created', '')
            if not created_str:
                return 0.5

            created_date = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
            now = datetime.now(created_date.tzinfo)
            days_old = (now - created_date).days

            # More recent issues are more likely to be duplicates
            if days_old <= 7:
                return 1.0
            elif days_old <= 30:
                return 0.8
            elif days_old <= 90:
                return 0.6
            else:
                return 0.4

        except Exception:
            return 0.5

    def _calculate_assignee_similarity(self, task: Dict[str, Any], candidate: Dict[str, Any]) -> float:
        """Calculate assignee similarity."""
        task_assignee = task.get('assignee', '')
        candidate_assignee = self._get_assignee_name(candidate)

        if task_assignee and candidate_assignee:
            return 1.0 if task_assignee == candidate_assignee else 0.0

        return 0.5  # Unknown similarity when assignee info is missing

    def _get_assignee_name(self, issue: Dict[str, Any]) -> str:
        """Extract assignee name from issue."""
        assignee = issue.get('fields', {}).get('assignee')
        if assignee:
            return assignee.get('displayName', assignee.get('name', ''))
        return ''

    def _extract_search_terms(self, text: str) -> List[str]:
        """Extract meaningful search terms from text."""
        # Remove common words and extract meaningful terms
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        words = re.findall(r'\b\w{3,}\b', text.lower())
        return [word for word in words if word not in common_words]

    def _extract_keywords(self, task: Dict[str, Any], project_context: ProjectContext) -> List[str]:
        """Extract keywords considering project context."""
        text = f"{task.get('summary', '')} {task.get('description', '')}"
        terms = self._extract_search_terms(text)

        # Add project-specific keywords
        project_keywords = ['authentication', 'login', 'user', 'api', 'form', 'validation']
        return [term for term in terms if term in project_keywords or len(term) > 5]

    def _get_recommendation(self, analysis: SimilarityAnalysis) -> str:
        """Get recommendation based on similarity analysis."""
        if analysis.overall_score >= 0.95:
            return 'skip'  # Very likely duplicate, skip creation
        elif analysis.overall_score >= 0.85:
            return 'merge'  # High similarity, consider merging
        elif analysis.overall_score >= 0.70:
            return 'link'   # Related, create with link
        else:
            return 'create_anyway'  # Different enough to create

    def _calculate_confidence(self, analysis: SimilarityAnalysis) -> float:
        """Calculate confidence in the similarity assessment."""
        factor_weight = len(analysis.factors) * 0.1
        score_weight = analysis.overall_score * 0.8
        return min(1.0, score_weight + factor_weight)

    def _extract_issue_context(self, issue: Dict[str, Any], project_context: ProjectContext) -> Dict[str, Any]:
        """Extract relevant context from an issue."""
        return {
            'project_key': project_context.key,
            'issue_type': issue.get('fields', {}).get('issuetype', {}).get('name', ''),
            'status': issue.get('fields', {}).get('status', {}).get('name', ''),
            'priority': issue.get('fields', {}).get('priority', {}).get('name', ''),
            'components': [c.get('name', '') for c in issue.get('fields', {}).get('components', [])],
            'labels': issue.get('fields', {}).get('labels', [])
        }

    def _generate_duplicate_summary(self, all_duplicates: Dict[str, List],
                                  cross_references: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics for duplicate analysis."""
        total_duplicates = sum(len(dups) for dups in all_duplicates.values())
        tasks_with_duplicates = len([task_id for task_id, dups in all_duplicates.items() if dups])

        recommendations = {}
        for dups in all_duplicates.values():
            for dup in dups:
                rec = dup.recommendation
                recommendations[rec] = recommendations.get(rec, 0) + 1

        return {
            'total_potential_duplicates': total_duplicates,
            'tasks_with_duplicates': tasks_with_duplicates,
            'cross_references_found': len(cross_references),
            'recommendations_breakdown': recommendations,
            'high_confidence_duplicates': sum(1 for dups in all_duplicates.values()
                                            for dup in dups if dup.confidence > 0.8)
        }

    async def _apply_resolution(self, conflict: Dict[str, Any], resolution: Dict[str, Any]):
        """Apply the user's resolution to a conflict."""
        # In a real implementation, this would:
        # - Skip task creation if resolution is 'skip'
        # - Create task with links if resolution is 'link'
        # - Merge task information if resolution is 'merge'
        # - Create task normally if resolution is 'create_anyway'

        self.logger.info(f"Applied resolution: {resolution.get('action')} for conflict")

    async def _suggest_epic_relationships(self, task: Dict[str, Any],
                                        project_context: ProjectContext) -> List[Dict[str, Any]]:
        """Suggest epic relationships for a task."""
        suggestions = []

        if project_context.epics:
            task_text = f"{task.get('summary', '')} {task.get('description', '')}".lower()

            for epic in project_context.epics:
                epic_text = epic.get('summary', '').lower()
                similarity = fuzz.token_sort_ratio(task_text, epic_text) / 100.0

                if similarity > 0.3:  # Lower threshold for epic relationships
                    suggestions.append({
                        'epic_key': epic.get('key', ''),
                        'epic_summary': epic.get('summary', ''),
                        'similarity_score': similarity,
                        'relationship_type': 'parent_epic'
                    })

        return suggestions[:3]  # Return top 3 suggestions

    async def _suggest_blocking_relationships(self, task: Dict[str, Any],
                                            project_context: ProjectContext) -> List[Dict[str, Any]]:
        """Suggest blocking/blocked relationships."""
        # In a real implementation, this would analyze task dependencies
        return []

    async def _suggest_related_stories(self, task: Dict[str, Any],
                                     project_context: ProjectContext) -> List[Dict[str, Any]]:
        """Suggest related story relationships."""
        # In a real implementation, this would find related stories
        return []