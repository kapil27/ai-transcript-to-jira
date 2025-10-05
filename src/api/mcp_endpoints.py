"""API endpoints for MCP-enhanced JIRA integration."""

import asyncio
from flask import Blueprint, request, jsonify, current_app
from typing import Dict, Any, List

from ..services.mcp_jira_service import MCPJiraService
from ..services.context_aware_ai_service import ContextAwareAIService
from ..services.smart_duplicate_service import SmartDuplicateService
from ..config import get_config
from ..exceptions import JiraIntegrationError, AIServiceError, DuplicateDetectionError
from ..utils import LoggerMixin


class MCPEndpoints(LoggerMixin):
    """MCP-enhanced API endpoints."""

    def __init__(self):
        """Initialize MCP endpoints."""
        self.config = get_config()
        self.mcp_service = MCPJiraService(self.config)
        self.context_ai_service = ContextAwareAIService(self.config, self.mcp_service)
        self.duplicate_service = SmartDuplicateService(self.config, self.mcp_service)

    def create_blueprint(self) -> Blueprint:
        """Create Flask blueprint with MCP endpoints."""
        bp = Blueprint('mcp_api', __name__, url_prefix='/api/mcp')

        # JIRA Integration endpoints
        bp.add_url_rule('/jira/connect', 'test_connection',
                       self.test_jira_connection, methods=['POST'])
        bp.add_url_rule('/jira/projects/enriched', 'get_enriched_projects',
                       self.get_enriched_projects, methods=['GET'])
        bp.add_url_rule('/jira/projects/<project_key>/context', 'get_project_context',
                       self.get_project_context, methods=['GET'])
        bp.add_url_rule('/jira/create-smart-tasks', 'create_smart_tasks',
                       self.create_smart_tasks, methods=['POST'])
        bp.add_url_rule('/jira/search/similar', 'search_similar_tasks',
                       self.search_similar_tasks, methods=['POST'])

        # Context-aware AI processing endpoints
        bp.add_url_rule('/ai/extract-with-context', 'extract_with_context',
                       self.extract_with_context, methods=['POST'])
        bp.add_url_rule('/ai/suggest-issue-types', 'suggest_issue_types',
                       self.suggest_issue_types, methods=['POST'])
        bp.add_url_rule('/ai/validate-tasks', 'validate_tasks',
                       self.validate_tasks, methods=['POST'])
        bp.add_url_rule('/ai/auto-link-epics', 'auto_link_epics',
                       self.auto_link_epics, methods=['POST'])

        return bp

    async def test_jira_connection(self):
        """Test MCP-enhanced JIRA connection."""
        try:
            data = request.get_json()
            jira_url = data.get('jira_url')
            username = data.get('username')
            api_token = data.get('api_token')

            if not all([jira_url, username, api_token]):
                return jsonify({
                    'success': False,
                    'error': 'Missing required connection parameters'
                }), 400

            self.logger.info(f"Testing MCP JIRA connection to {jira_url}")

            # Test connection via MCP
            connection_result = await self.mcp_service.authenticate_via_mcp(
                jira_url, username, api_token
            )

            if connection_result:
                return jsonify({
                    'success': True,
                    'message': 'MCP JIRA connection successful',
                    'capabilities': ['projects', 'issues', 'search', 'create']
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Connection test failed'
                }), 401

        except JiraIntegrationError as e:
            self.logger.error(f"JIRA connection test failed: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
        except Exception as e:
            self.logger.error(f"Unexpected error in connection test: {e}")
            return jsonify({
                'success': False,
                'error': 'Internal server error'
            }), 500

    async def get_enriched_projects(self):
        """Get enriched project list with context data."""
        try:
            self.logger.info("Fetching enriched projects via MCP")

            projects = await self.mcp_service.get_enriched_projects()

            return jsonify({
                'success': True,
                'projects': projects,
                'count': len(projects)
            })

        except Exception as e:
            self.logger.error(f"Failed to get enriched projects: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    async def get_project_context(self, project_key: str):
        """Get comprehensive project context."""
        try:
            self.logger.info(f"Fetching context for project {project_key}")

            context = await self.mcp_service.get_project_context(project_key)

            return jsonify({
                'success': True,
                'project_context': {
                    'key': context.key,
                    'name': context.name,
                    'description': context.description,
                    'project_type': context.project_type,
                    'lead': context.lead,
                    'active_sprint': context.active_sprint,
                    'epics_count': len(context.epics) if context.epics else 0,
                    'epics': context.epics[:10],  # Return first 10 epics
                    'issue_types': context.issue_types,
                    'recent_issues_count': len(context.recent_issues) if context.recent_issues else 0
                }
            })

        except Exception as e:
            self.logger.error(f"Failed to get project context: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    async def extract_with_context(self):
        """Extract tasks with project context enhancement."""
        try:
            data = request.get_json()
            transcript = data.get('transcript', '')
            project_key = data.get('project_key', '')
            additional_context = data.get('additional_context', '')

            if not transcript.strip():
                return jsonify({
                    'success': False,
                    'error': 'Transcript text is required'
                }), 400

            if not project_key:
                return jsonify({
                    'success': False,
                    'error': 'Project key is required for context-aware extraction'
                }), 400

            self.logger.info(f"Context-aware extraction for project {project_key}")

            # Extract tasks with project context
            enhanced_tasks = await self.context_ai_service.extract_with_project_context(
                transcript, project_key, additional_context
            )

            # Convert enhanced tasks to JSON-serializable format
            tasks_data = []
            for task in enhanced_tasks:
                task_data = {
                    'summary': task.summary,
                    'description': task.description,
                    'issue_type': task.issue_type,
                    'suggested_epic': task.suggested_epic,
                    'confidence_score': task.confidence_score,
                    'context_factors': task.context_factors,
                    'validation_status': task.validation_status,
                    'auto_suggestions': task.auto_suggestions
                }
                tasks_data.append(task_data)

            return jsonify({
                'success': True,
                'tasks': tasks_data,
                'count': len(tasks_data),
                'project_key': project_key,
                'extraction_type': 'context_aware'
            })

        except AIServiceError as e:
            self.logger.error(f"AI extraction failed: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
        except Exception as e:
            self.logger.error(f"Context extraction failed: {e}")
            return jsonify({
                'success': False,
                'error': 'Extraction failed'
            }), 500

    async def suggest_issue_types(self):
        """Get AI-powered issue type suggestions."""
        try:
            data = request.get_json()
            task_content = data.get('task_content', '')
            project_key = data.get('project_key', '')

            if not task_content.strip():
                return jsonify({
                    'success': False,
                    'error': 'Task content is required'
                }), 400

            if not project_key:
                return jsonify({
                    'success': False,
                    'error': 'Project key is required'
                }), 400

            # Get project context
            project_context = await self.mcp_service.get_project_context(project_key)

            # Get issue type suggestions
            suggestions = await self.context_ai_service.suggest_issue_types(
                task_content, project_context
            )

            return jsonify({
                'success': True,
                'suggestions': suggestions,
                'project_key': project_key
            })

        except Exception as e:
            self.logger.error(f"Issue type suggestion failed: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    async def validate_tasks(self):
        """Validate tasks against project schema."""
        try:
            data = request.get_json()
            tasks = data.get('tasks', [])
            project_key = data.get('project_key', '')

            if not tasks:
                return jsonify({
                    'success': False,
                    'error': 'Tasks list is required'
                }), 400

            if not project_key:
                return jsonify({
                    'success': False,
                    'error': 'Project key is required'
                }), 400

            # Get project context
            project_context = await self.mcp_service.get_project_context(project_key)

            # Validate each task
            validation_results = []
            for i, task in enumerate(tasks):
                result = await self.context_ai_service.validate_task_against_schema(
                    task, project_context
                )
                result['task_index'] = i
                validation_results.append(result)

            # Calculate overall validation status
            all_valid = all(result['is_valid'] for result in validation_results)
            has_warnings = any(result['warnings'] for result in validation_results)

            return jsonify({
                'success': True,
                'validation_results': validation_results,
                'overall_status': 'valid' if all_valid else 'has_errors',
                'has_warnings': has_warnings,
                'project_key': project_key
            })

        except Exception as e:
            self.logger.error(f"Task validation failed: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    async def auto_link_epics(self):
        """Auto-link tasks to appropriate epics."""
        try:
            data = request.get_json()
            tasks = data.get('tasks', [])
            project_key = data.get('project_key', '')

            if not tasks:
                return jsonify({
                    'success': False,
                    'error': 'Tasks list is required'
                }), 400

            if not project_key:
                return jsonify({
                    'success': False,
                    'error': 'Project key is required'
                }), 400

            # Get project context
            project_context = await self.mcp_service.get_project_context(project_key)

            # Convert tasks to enhanced task format
            enhanced_tasks = []
            for task in tasks:
                enhanced_task = self.context_ai_service._convert_to_enhanced_task(task)
                enhanced_tasks.append(enhanced_task)

            # Auto-categorize by epics
            categorized_tasks = await self.context_ai_service.auto_categorize_by_epics(
                enhanced_tasks, project_context
            )

            # Convert back to JSON format
            results = []
            for task in categorized_tasks:
                results.append({
                    'summary': task.summary,
                    'description': task.description,
                    'issue_type': task.issue_type,
                    'suggested_epic': task.suggested_epic,
                    'confidence_score': task.confidence_score
                })

            return jsonify({
                'success': True,
                'tasks_with_epic_suggestions': results,
                'project_key': project_key,
                'available_epics': project_context.epics[:10]  # Return first 10 epics
            })

        except Exception as e:
            self.logger.error(f"Epic auto-linking failed: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    async def search_similar_tasks(self):
        """Search for similar tasks using MCP intelligence."""
        try:
            data = request.get_json()
            project_key = data.get('project_key', '')
            task_summary = data.get('task_summary', '')
            task_description = data.get('task_description', '')

            if not project_key:
                return jsonify({
                    'success': False,
                    'error': 'Project key is required'
                }), 400

            if not task_summary.strip():
                return jsonify({
                    'success': False,
                    'error': 'Task summary is required'
                }), 400

            self.logger.info(f"Searching for similar tasks in {project_key}")

            # Search for similar tasks
            similar_tasks = await self.mcp_service.search_similar_tasks(
                project_key, task_summary, task_description
            )

            # Convert to JSON format
            similarities = []
            for similarity in similar_tasks:
                similarities.append({
                    'existing_issue_key': similarity.existing_issue_key,
                    'existing_summary': similarity.existing_summary,
                    'similarity_score': similarity.similarity_score,
                    'recommendation': similarity.recommendation,
                    'suggested_action': similarity.suggested_action,
                    'context_factors': similarity.context_factors
                })

            return jsonify({
                'success': True,
                'similar_tasks': similarities,
                'count': len(similarities),
                'project_key': project_key,
                'search_summary': task_summary[:100] + '...' if len(task_summary) > 100 else task_summary
            })

        except Exception as e:
            self.logger.error(f"Similar task search failed: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    async def create_smart_tasks(self):
        """Create tasks with MCP intelligence and context awareness."""
        try:
            data = request.get_json()
            project_key = data.get('project_key', '')
            tasks = data.get('tasks', [])

            if not project_key:
                return jsonify({
                    'success': False,
                    'error': 'Project key is required'
                }), 400

            if not tasks:
                return jsonify({
                    'success': False,
                    'error': 'Tasks list is required'
                }), 400

            self.logger.info(f"Creating {len(tasks)} smart tasks in project {project_key}")

            # Get project context
            project_context = await self.mcp_service.get_project_context(project_key)

            created_tasks = []
            failed_tasks = []

            for i, task_data in enumerate(tasks):
                try:
                    # Create context-aware task
                    created_task = await self.mcp_service.create_context_aware_task(
                        project_key, task_data, project_context
                    )

                    created_tasks.append({
                        'index': i,
                        'original_summary': task_data.get('summary', ''),
                        'created_key': created_task.get('key', ''),
                        'status': 'created'
                    })

                except Exception as e:
                    self.logger.error(f"Failed to create task {i}: {e}")
                    failed_tasks.append({
                        'index': i,
                        'original_summary': task_data.get('summary', ''),
                        'error': str(e),
                        'status': 'failed'
                    })

            return jsonify({
                'success': True,
                'created_tasks': created_tasks,
                'failed_tasks': failed_tasks,
                'success_count': len(created_tasks),
                'failure_count': len(failed_tasks),
                'project_key': project_key
            })

        except Exception as e:
            self.logger.error(f"Smart task creation failed: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    async def check_duplicates_mcp(self):
        """Check for duplicates using MCP-powered intelligence."""
        try:
            data = request.get_json()
            task = data.get('task', {})
            project_key = data.get('project_key', '')
            include_resolved = data.get('include_resolved', False)

            if not task:
                return jsonify({
                    'success': False,
                    'error': 'Task data is required'
                }), 400

            if not project_key:
                return jsonify({
                    'success': False,
                    'error': 'Project key is required'
                }), 400

            self.logger.info(f"Checking duplicates for task in project {project_key}")

            # Find duplicate candidates
            duplicates = await self.duplicate_service.find_duplicates_via_mcp(
                task, project_key, include_resolved
            )

            # Convert to JSON-serializable format
            duplicates_data = []
            for dup in duplicates:
                duplicates_data.append({
                    'issue_key': dup.issue_key,
                    'summary': dup.summary,
                    'description': dup.description,
                    'status': dup.status,
                    'assignee': dup.assignee,
                    'created_date': dup.created_date,
                    'similarity_score': dup.similarity_score,
                    'similarity_factors': dup.similarity_factors,
                    'recommendation': dup.recommendation,
                    'confidence': dup.confidence,
                    'project_context': dup.project_context
                })

            return jsonify({
                'success': True,
                'project_key': project_key,
                'task_summary': task.get('summary', ''),
                'duplicates_found': len(duplicates_data),
                'duplicates': duplicates_data,
                'include_resolved': include_resolved
            })

        except DuplicateDetectionError as e:
            self.logger.error(f"Duplicate detection failed: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
        except Exception as e:
            self.logger.error(f"Unexpected error in duplicate check: {e}")
            return jsonify({
                'success': False,
                'error': 'Internal server error'
            }), 500

    async def analyze_bulk_duplicates(self):
        """Analyze multiple tasks for duplicates and cross-references."""
        try:
            data = request.get_json()
            tasks = data.get('tasks', [])
            project_key = data.get('project_key', '')

            if not tasks:
                return jsonify({
                    'success': False,
                    'error': 'Tasks list is required'
                }), 400

            if not project_key:
                return jsonify({
                    'success': False,
                    'error': 'Project key is required'
                }), 400

            self.logger.info(f"Analyzing {len(tasks)} tasks for duplicates in project {project_key}")

            # Perform bulk duplicate analysis
            analysis = await self.duplicate_service.analyze_bulk_duplicates(tasks, project_key)

            # Convert duplicate candidates to JSON-serializable format
            serialized_duplicates = {}
            for task_id, duplicates in analysis['duplicates_found'].items():
                serialized_duplicates[task_id] = []
                for dup in duplicates:
                    serialized_duplicates[task_id].append({
                        'issue_key': dup.issue_key,
                        'summary': dup.summary,
                        'similarity_score': dup.similarity_score,
                        'recommendation': dup.recommendation,
                        'confidence': dup.confidence,
                        'similarity_factors': dup.similarity_factors
                    })

            analysis['duplicates_found'] = serialized_duplicates

            return jsonify({
                'success': True,
                'analysis': analysis
            })

        except DuplicateDetectionError as e:
            self.logger.error(f"Bulk duplicate analysis failed: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
        except Exception as e:
            self.logger.error(f"Unexpected error in bulk analysis: {e}")
            return jsonify({
                'success': False,
                'error': 'Internal server error'
            }), 500

    async def resolve_conflicts(self):
        """Resolve duplicate conflicts based on user decisions."""
        try:
            data = request.get_json()
            conflicts = data.get('conflicts', [])
            resolutions = data.get('resolutions', [])

            if not conflicts or not resolutions:
                return jsonify({
                    'success': False,
                    'error': 'Both conflicts and resolutions are required'
                }), 400

            if len(conflicts) != len(resolutions):
                return jsonify({
                    'success': False,
                    'error': 'Number of conflicts and resolutions must match'
                }), 400

            self.logger.info(f"Resolving {len(conflicts)} duplicate conflicts")

            # Resolve conflicts
            resolved = await self.duplicate_service.resolve_duplicate_conflicts(
                conflicts, resolutions
            )

            # Convert to JSON-serializable format
            resolutions_data = []
            for resolution in resolved:
                resolutions_data.append({
                    'original_task_id': resolution.original_task_id,
                    'resolution_type': resolution.resolution_type,
                    'target_issue_key': resolution.target_issue_key,
                    'user_notes': resolution.user_notes,
                    'resolved_at': resolution.resolved_at,
                    'auto_resolved': resolution.auto_resolved
                })

            return jsonify({
                'success': True,
                'resolutions_applied': len(resolutions_data),
                'resolutions': resolutions_data
            })

        except DuplicateDetectionError as e:
            self.logger.error(f"Conflict resolution failed: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
        except Exception as e:
            self.logger.error(f"Unexpected error in conflict resolution: {e}")
            return jsonify({
                'success': False,
                'error': 'Internal server error'
            }), 500

    async def suggest_relationships(self):
        """Suggest relationships between tasks and existing issues."""
        try:
            data = request.get_json()
            tasks = data.get('tasks', [])
            project_key = data.get('project_key', '')

            if not tasks:
                return jsonify({
                    'success': False,
                    'error': 'Tasks list is required'
                }), 400

            if not project_key:
                return jsonify({
                    'success': False,
                    'error': 'Project key is required'
                }), 400

            self.logger.info(f"Suggesting relationships for {len(tasks)} tasks")

            # Get project context
            project_context = await self.mcp_service.get_project_context(project_key)

            # Suggest relationships
            relationships = await self.duplicate_service.suggest_task_relationships(
                tasks, project_context
            )

            return jsonify({
                'success': True,
                'project_key': project_key,
                'tasks_analyzed': len(tasks),
                'relationships_found': len(relationships),
                'relationships': relationships
            })

        except Exception as e:
            self.logger.error(f"Relationship suggestion failed: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500


# Helper function to run async endpoints in Flask
def run_async(coro):
    """Run async coroutine in Flask context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)

# Create the blueprint with corrected endpoint registration
def create_mcp_blueprint() -> Blueprint:
    """Create Flask blueprint with MCP endpoints."""
    bp = Blueprint('mcp_api', __name__, url_prefix='/api/mcp')
    endpoints = MCPEndpoints()

    # JIRA Integration endpoints
    bp.add_url_rule('/jira/connect', 'test_connection',
                   lambda: run_async(endpoints.test_jira_connection()), methods=['POST'])
    bp.add_url_rule('/jira/projects/enriched', 'get_enriched_projects',
                   lambda: run_async(endpoints.get_enriched_projects()), methods=['GET'])
    bp.add_url_rule('/jira/projects/<project_key>/context', 'get_project_context',
                   lambda project_key: run_async(endpoints.get_project_context(project_key)), methods=['GET'])
    bp.add_url_rule('/jira/create-smart-tasks', 'create_smart_tasks',
                   lambda: run_async(endpoints.create_smart_tasks()), methods=['POST'])
    bp.add_url_rule('/jira/search/similar', 'search_similar_tasks',
                   lambda: run_async(endpoints.search_similar_tasks()), methods=['POST'])

    # Context-aware AI processing endpoints
    bp.add_url_rule('/ai/extract-with-context', 'extract_with_context',
                   lambda: run_async(endpoints.extract_with_context()), methods=['POST'])
    bp.add_url_rule('/ai/suggest-issue-types', 'suggest_issue_types',
                   lambda: run_async(endpoints.suggest_issue_types()), methods=['POST'])
    bp.add_url_rule('/ai/validate-tasks', 'validate_tasks',
                   lambda: run_async(endpoints.validate_tasks()), methods=['POST'])
    bp.add_url_rule('/ai/auto-link-epics', 'auto_link_epics',
                   lambda: run_async(endpoints.auto_link_epics()), methods=['POST'])

    # Smart duplicate detection endpoints
    bp.add_url_rule('/smart/check-duplicates', 'check_duplicates_mcp',
                   lambda: run_async(endpoints.check_duplicates_mcp()), methods=['POST'])
    bp.add_url_rule('/smart/analyze-bulk', 'analyze_bulk_duplicates',
                   lambda: run_async(endpoints.analyze_bulk_duplicates()), methods=['POST'])
    bp.add_url_rule('/smart/resolve-conflicts', 'resolve_conflicts',
                   lambda: run_async(endpoints.resolve_conflicts()), methods=['POST'])
    bp.add_url_rule('/smart/suggest-relationships', 'suggest_relationships',
                   lambda: run_async(endpoints.suggest_relationships()), methods=['POST'])

    return bp