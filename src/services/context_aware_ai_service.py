"""Context-aware AI service for enhanced task extraction."""

import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .ai_service import OllamaService
from .mcp_jira_service import MCPJiraService, ProjectContext
from ..config import AppConfig
from ..exceptions import AIServiceError
from ..utils import LoggerMixin


@dataclass
class EnhancedTask:
    """Enhanced task with context-aware metadata."""

    summary: str
    description: str
    issue_type: str
    suggested_epic: Optional[str] = None
    confidence_score: float = 0.0
    context_factors: List[str] = None
    validation_status: str = "pending"  # pending, valid, invalid
    auto_suggestions: Dict[str, Any] = None


class ContextAwareAIService(LoggerMixin):
    """AI service enhanced with project context intelligence."""

    def __init__(self, config: AppConfig, mcp_service: MCPJiraService):
        """
        Initialize context-aware AI service.

        Args:
            config: Application configuration
            mcp_service: MCP JIRA service for context data
        """
        self.config = config
        self.mcp_service = mcp_service
        self.base_ai_service = OllamaService(config)

    async def extract_with_project_context(self, transcript: str, project_key: str,
                                         additional_context: str = "") -> List[EnhancedTask]:
        """
        Extract tasks with project context enhancement.

        Args:
            transcript: Meeting transcript or document text
            project_key: JIRA project key for context
            additional_context: Additional user-provided context

        Returns:
            List of enhanced tasks with project intelligence
        """
        try:
            self.logger.info(f"Starting context-aware extraction for project {project_key}")

            # Get project context
            project_context = await self.mcp_service.get_project_context(project_key)

            # Create enhanced prompt with project context
            enhanced_context = self._create_project_aware_context(
                project_context, additional_context
            )

            # Extract base tasks using enhanced context
            base_tasks = self.base_ai_service.parse_transcript(transcript, enhanced_context)

            # Enhance each task with project intelligence
            enhanced_tasks = []
            for task in base_tasks:
                enhanced_task = await self._enhance_task_with_context(task, project_context)
                enhanced_tasks.append(enhanced_task)

            self.logger.info(f"Enhanced {len(enhanced_tasks)} tasks with project context")
            return enhanced_tasks

        except Exception as e:
            self.logger.error(f"Context-aware extraction failed: {e}")
            # Fallback to basic extraction
            base_tasks = self.base_ai_service.parse_transcript(transcript, additional_context)
            return [self._convert_to_enhanced_task(task) for task in base_tasks]

    async def suggest_issue_types(self, task_content: str, project_context: ProjectContext) -> List[Dict[str, Any]]:
        """
        Suggest appropriate issue types using project patterns.

        Args:
            task_content: Task summary and description
            project_context: Project context for analysis

        Returns:
            List of suggested issue types with confidence scores
        """
        try:
            self.logger.info("Generating issue type suggestions")

            # Analyze recent issues for patterns
            issue_type_patterns = self._analyze_issue_type_patterns(project_context)

            # Create AI prompt for issue type classification
            classification_prompt = self._create_issue_type_prompt(
                task_content, project_context, issue_type_patterns
            )

            # Get AI classification
            classification_response = self.base_ai_service._call_ollama(
                classification_prompt, use_json_format=True
            )

            classification_data = self.base_ai_service._parse_single_task(classification_response)

            if classification_data:
                suggestions = classification_data.get('suggestions', [])

                # Validate against available issue types
                valid_suggestions = []
                available_types = {it['name']: it for it in project_context.issue_types}

                for suggestion in suggestions:
                    if suggestion.get('type') in available_types:
                        valid_suggestions.append({
                            'type': suggestion['type'],
                            'confidence': suggestion.get('confidence', 0.5),
                            'reasoning': suggestion.get('reasoning', ''),
                            'type_id': available_types[suggestion['type']]['id']
                        })

                return valid_suggestions

            return self._get_default_issue_type_suggestions(project_context)

        except Exception as e:
            self.logger.error(f"Issue type suggestion failed: {e}")
            return self._get_default_issue_type_suggestions(project_context)

    async def validate_task_against_schema(self, task: Dict[str, Any],
                                         project_context: ProjectContext) -> Dict[str, Any]:
        """
        Validate task against project schema and workflows.

        Args:
            task: Task data to validate
            project_context: Project context with schema information

        Returns:
            Validation result with suggestions
        """
        try:
            self.logger.info("Validating task against project schema")

            validation_result = {
                'is_valid': True,
                'warnings': [],
                'errors': [],
                'suggestions': []
            }

            # Validate issue type
            issue_type = task.get('issue_type', 'Task')
            available_types = [it['name'] for it in project_context.issue_types]

            if issue_type not in available_types:
                validation_result['warnings'].append(
                    f"Issue type '{issue_type}' not available in project. Available: {', '.join(available_types)}"
                )
                validation_result['suggestions'].append({
                    'field': 'issue_type',
                    'suggested_value': available_types[0] if available_types else 'Task',
                    'reason': 'Default to first available issue type'
                })

            # Validate summary length
            summary = task.get('summary', '')
            if len(summary) > 255:
                validation_result['errors'].append("Summary exceeds maximum length of 255 characters")
                validation_result['is_valid'] = False

            if len(summary) < 5:
                validation_result['warnings'].append("Summary is very short, consider adding more detail")

            # Validate description
            description = task.get('description', '')
            if len(description) > 32767:
                validation_result['errors'].append("Description exceeds maximum length")
                validation_result['is_valid'] = False

            # Check for required custom fields
            for custom_field in project_context.custom_fields:
                if custom_field.get('required', False):
                    field_name = custom_field.get('name', '')
                    if field_name not in task:
                        validation_result['warnings'].append(
                            f"Required field '{field_name}' is missing"
                        )

            return validation_result

        except Exception as e:
            self.logger.error(f"Task validation failed: {e}")
            return {
                'is_valid': True,
                'warnings': [f"Validation check failed: {str(e)}"],
                'errors': [],
                'suggestions': []
            }

    async def auto_categorize_by_epics(self, tasks: List[EnhancedTask],
                                     project_context: ProjectContext) -> List[EnhancedTask]:
        """
        Automatically categorize tasks by linking to appropriate epics.

        Args:
            tasks: List of enhanced tasks
            project_context: Project context with epic information

        Returns:
            Tasks with suggested epic links
        """
        try:
            self.logger.info(f"Auto-categorizing {len(tasks)} tasks by epics")

            if not project_context.epics:
                self.logger.info("No epics available for categorization")
                return tasks

            categorized_tasks = []
            for task in tasks:
                categorized_task = await self._suggest_epic_for_task(task, project_context)
                categorized_tasks.append(categorized_task)

            return categorized_tasks

        except Exception as e:
            self.logger.error(f"Epic categorization failed: {e}")
            return tasks

    def _create_project_aware_context(self, project_context: ProjectContext,
                                    additional_context: str) -> str:
        """Create enhanced context string with project information."""
        context_parts = []

        # Add project information
        context_parts.append(f"Project: {project_context.name} ({project_context.key})")
        context_parts.append(f"Project Type: {project_context.project_type}")

        if project_context.description:
            context_parts.append(f"Project Description: {project_context.description}")

        # Add active sprint information
        if project_context.active_sprint:
            sprint = project_context.active_sprint
            context_parts.append(f"Active Sprint: {sprint.get('name', 'Current Sprint')}")

        # Add available issue types
        if project_context.issue_types:
            issue_types = [it['name'] for it in project_context.issue_types]
            context_parts.append(f"Available Issue Types: {', '.join(issue_types)}")

        # Add epic information
        if project_context.epics:
            epic_summaries = [f"{epic['key']}: {epic['summary']}" for epic in project_context.epics[:5]]
            context_parts.append(f"Current Epics: {'; '.join(epic_summaries)}")

        # Add recent issue patterns
        if project_context.recent_issues:
            recent_count = len(project_context.recent_issues)
            context_parts.append(f"Recent Activity: {recent_count} issues in this project")

        # Add user-provided context
        if additional_context.strip():
            context_parts.append(f"Additional Context: {additional_context}")

        return "\n".join(context_parts)

    async def _enhance_task_with_context(self, task: Dict[str, Any],
                                       project_context: ProjectContext) -> EnhancedTask:
        """Enhance a single task with project context."""
        try:
            # Get issue type suggestions
            task_content = f"{task.get('summary', '')} {task.get('description', '')}"
            issue_type_suggestions = await self.suggest_issue_types(task_content, project_context)

            # Suggest best issue type
            suggested_issue_type = task.get('issue_type', 'Task')
            confidence_score = 0.5

            if issue_type_suggestions:
                best_suggestion = max(issue_type_suggestions, key=lambda x: x['confidence'])
                suggested_issue_type = best_suggestion['type']
                confidence_score = best_suggestion['confidence']

            # Suggest epic link
            suggested_epic = await self._find_best_epic_match(task, project_context)

            # Validate against schema
            validation_result = await self.validate_task_against_schema(task, project_context)

            # Create enhanced task
            enhanced_task = EnhancedTask(
                summary=task.get('summary', ''),
                description=task.get('description', ''),
                issue_type=suggested_issue_type,
                suggested_epic=suggested_epic,
                confidence_score=confidence_score,
                context_factors=['project_patterns', 'epic_matching', 'schema_validation'],
                validation_status='valid' if validation_result['is_valid'] else 'invalid',
                auto_suggestions={
                    'issue_type_suggestions': issue_type_suggestions,
                    'validation': validation_result
                }
            )

            return enhanced_task

        except Exception as e:
            self.logger.error(f"Task enhancement failed: {e}")
            return self._convert_to_enhanced_task(task)

    def _convert_to_enhanced_task(self, task: Dict[str, Any]) -> EnhancedTask:
        """Convert basic task to enhanced task structure."""
        return EnhancedTask(
            summary=task.get('summary', ''),
            description=task.get('description', ''),
            issue_type=task.get('issue_type', 'Task'),
            confidence_score=0.3,  # Low confidence for non-enhanced tasks
            context_factors=['basic_extraction'],
            validation_status='pending'
        )

    def _analyze_issue_type_patterns(self, project_context: ProjectContext) -> Dict[str, Any]:
        """Analyze patterns in recent issues for better issue type suggestions."""
        patterns = {
            'story_keywords': ['user', 'story', 'feature', 'requirement', 'functionality'],
            'task_keywords': ['implement', 'create', 'update', 'configure', 'setup', 'add'],
            'bug_keywords': ['fix', 'bug', 'error', 'issue', 'problem', 'broken'],
            'epic_keywords': ['epic', 'initiative', 'theme', 'major', 'large']
        }

        # Analyze recent issues for project-specific patterns
        if project_context.recent_issues:
            # In a real implementation, this would analyze the recent issues
            # to identify project-specific keywords and patterns
            pass

        return patterns

    def _create_issue_type_prompt(self, task_content: str, project_context: ProjectContext,
                                issue_type_patterns: Dict[str, Any]) -> str:
        """Create AI prompt for issue type classification."""
        available_types = [it['name'] for it in project_context.issue_types]

        prompt = f"""Analyze this task content and suggest the most appropriate issue type:

TASK CONTENT:
{task_content}

AVAILABLE ISSUE TYPES:
{', '.join(available_types)}

CLASSIFICATION PATTERNS:
- Story: User-facing features, requirements, functionality
- Task: Implementation work, technical tasks, configuration
- Bug: Fixes, errors, problems
- Epic: Large initiatives, themes, major features

Return ONLY a JSON object in this format:
{{
    "suggestions": [
        {{
            "type": "suggested_type_name",
            "confidence": 0.8,
            "reasoning": "why this type is suggested"
        }}
    ]
}}

Consider the task content and suggest the most appropriate type from the available options."""

        return prompt

    def _get_default_issue_type_suggestions(self, project_context: ProjectContext) -> List[Dict[str, Any]]:
        """Get default issue type suggestions when AI analysis fails."""
        suggestions = []

        for issue_type in project_context.issue_types:
            confidence = 0.3  # Default low confidence
            if issue_type['name'] == 'Task':
                confidence = 0.6  # Prefer Task as default

            suggestions.append({
                'type': issue_type['name'],
                'confidence': confidence,
                'reasoning': 'Default suggestion',
                'type_id': issue_type['id']
            })

        return sorted(suggestions, key=lambda x: x['confidence'], reverse=True)

    async def _suggest_epic_for_task(self, task: EnhancedTask,
                                   project_context: ProjectContext) -> EnhancedTask:
        """Suggest the best epic for a task."""
        suggested_epic = await self._find_best_epic_match(
            {'summary': task.summary, 'description': task.description},
            project_context
        )

        task.suggested_epic = suggested_epic
        if suggested_epic:
            task.context_factors.append('epic_suggested')

        return task

    async def _find_best_epic_match(self, task: Dict[str, Any],
                                  project_context: ProjectContext) -> Optional[str]:
        """Find the best epic match for a task."""
        if not project_context.epics:
            return None

        task_text = f"{task.get('summary', '')} {task.get('description', '')}".lower()
        best_match = None
        best_score = 0.0

        for epic in project_context.epics:
            epic_text = f"{epic['summary']}".lower()

            # Simple keyword overlap scoring
            task_words = set(task_text.split())
            epic_words = set(epic_text.split())

            # Filter out common words
            significant_words = {word for word in task_words.union(epic_words)
                               if len(word) > 3 and word not in ['with', 'from', 'that', 'this']}

            if significant_words:
                overlap = task_words.intersection(epic_words).intersection(significant_words)
                score = len(overlap) / len(significant_words) if significant_words else 0

                if score > best_score and score > 0.2:  # Minimum threshold
                    best_score = score
                    best_match = epic['key']

        return best_match