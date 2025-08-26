"""API routes for the JIRA CSV Generator application."""

from flask import Blueprint, request, jsonify, Response
from typing import Dict, Any

from ..config import get_config
from ..services import TranscriptAnalysisService, CSVGenerationService, ContextService
from ..exceptions import TranscriptError, AIServiceError, CSVGenerationError, ValidationError
from ..utils import LoggerMixin


class APIRoutes(LoggerMixin):
    """API routes handler for the JIRA CSV Generator."""
    
    def __init__(self):
        """Initialize API routes."""
        self.config = get_config()
        self.transcript_service = TranscriptAnalysisService(self.config)
        self.csv_service = CSVGenerationService()
        self.context_service = ContextService()
        self.blueprint = self._create_blueprint()
    
    def _create_blueprint(self) -> Blueprint:
        """Create Flask blueprint with all routes."""
        api = Blueprint('api', __name__, url_prefix='/api')
        
        # Health check endpoint
        api.add_url_rule('/health', 'health', self.health_check, methods=['GET'])
        
        # Task extraction endpoints
        api.add_url_rule('/parse-transcript', 'parse_transcript', self.parse_transcript, methods=['POST'])
        api.add_url_rule('/extract-qa', 'extract_qa', self.extract_qa, methods=['POST'])
        api.add_url_rule('/process-enhanced', 'process_enhanced', self.process_enhanced, methods=['POST'])
        
        # CSV generation endpoint
        api.add_url_rule('/generate-csv', 'generate_csv', self.generate_csv, methods=['POST'])
        
        # Service status endpoint
        api.add_url_rule('/status', 'status', self.get_status, methods=['GET'])
        
        # Context management endpoints
        api.add_url_rule('/context/templates', 'get_templates', self.get_context_templates, methods=['GET'])
        api.add_url_rule('/context/template/<template_key>', 'get_template', self.get_context_template, methods=['GET'])
        api.add_url_rule('/context/validate', 'validate_context', self.validate_context, methods=['POST'])
        api.add_url_rule('/context/enhance', 'enhance_context', self.enhance_context, methods=['POST'])
        
        return api
    
    def health_check(self) -> Dict[str, Any]:
        """Health check endpoint."""
        return jsonify({
            'status': 'healthy',
            'service': 'JIRA CSV Generator API',
            'version': '1.0.0'
        })
    
    def parse_transcript(self) -> Dict[str, Any]:
        """Extract tasks from transcript."""
        try:
            data = request.get_json()
            if not data or 'transcript' not in data:
                return jsonify({'error': 'Transcript text is required'}), 400
            
            transcript = data['transcript']
            context = data.get('context', '')  # Optional context parameter
            
            # Validate transcript
            is_valid, error_msg = self.transcript_service.validate_transcript(transcript)
            if not is_valid:
                return jsonify({'error': error_msg}), 400
            
            # Extract tasks with context
            tasks = self.transcript_service.extract_tasks_only(transcript, context)
            
            return jsonify({
                'success': True,
                'tasks': tasks,
                'count': len(tasks)
            })
            
        except TranscriptError as e:
            self.logger.error(f"Transcript error: {e}")
            return jsonify({'error': str(e)}), 400
        except AIServiceError as e:
            self.logger.error(f"AI service error: {e}")
            return jsonify({'error': 'AI service temporarily unavailable'}), 503
        except Exception as e:
            self.logger.error(f"Unexpected error in parse_transcript: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    def extract_qa(self) -> Dict[str, Any]:
        """Extract Q&A from transcript."""
        try:
            data = request.get_json()
            if not data or 'transcript' not in data:
                return jsonify({'error': 'Transcript text is required'}), 400
            
            transcript = data['transcript']
            context = data.get('context', '')  # Optional context parameter
            
            # Validate transcript
            is_valid, error_msg = self.transcript_service.validate_transcript(transcript)
            if not is_valid:
                return jsonify({'error': error_msg}), 400
            
            # Extract Q&A with context
            qa_items = self.transcript_service.extract_qa_only(transcript, context)
            
            return jsonify({
                'success': True,
                'qa_items': qa_items,
                'count': len(qa_items)
            })
            
        except TranscriptError as e:
            self.logger.error(f"Transcript error: {e}")
            return jsonify({'error': str(e)}), 400
        except AIServiceError as e:
            self.logger.error(f"AI service error: {e}")
            return jsonify({'error': 'AI service temporarily unavailable'}), 503
        except Exception as e:
            self.logger.error(f"Unexpected error in extract_qa: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    def process_enhanced(self) -> Dict[str, Any]:
        """Process transcript with both tasks and Q&A extraction."""
        try:
            data = request.get_json()
            if not data or 'transcript' not in data:
                return jsonify({'error': 'Transcript text is required'}), 400
            
            transcript = data['transcript']
            context = data.get('context', '')  # Optional context parameter
            
            # Validate transcript
            is_valid, error_msg = self.transcript_service.validate_transcript(transcript)
            if not is_valid:
                return jsonify({'error': error_msg}), 400
            
            # Analyze transcript with context
            result = self.transcript_service.analyze_transcript(transcript, context)
            
            return jsonify(result)
            
        except TranscriptError as e:
            self.logger.error(f"Transcript error: {e}")
            return jsonify({'error': str(e)}), 400
        except AIServiceError as e:
            self.logger.error(f"AI service error: {e}")
            return jsonify({'error': 'AI service temporarily unavailable'}), 503
        except Exception as e:
            self.logger.error(f"Unexpected error in process_enhanced: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    def generate_csv(self) -> Response:
        """Generate CSV file from tasks."""
        try:
            data = request.get_json()
            if not data or 'tasks' not in data:
                return jsonify({'error': 'Tasks data is required'}), 400
            
            tasks = data['tasks']
            
            # Generate CSV
            csv_content = self.csv_service.generate_csv(tasks)
            filename = self.csv_service.get_csv_filename()
            
            return Response(
                csv_content,
                mimetype='text/csv',
                headers={'Content-Disposition': f'attachment; filename={filename}'}
            )
            
        except ValidationError as e:
            self.logger.error(f"Validation error: {e}")
            return jsonify({'error': str(e)}), 400
        except CSVGenerationError as e:
            self.logger.error(f"CSV generation error: {e}")
            return jsonify({'error': 'Failed to generate CSV file'}), 500
        except Exception as e:
            self.logger.error(f"Unexpected error in generate_csv: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    def get_status(self) -> Dict[str, Any]:
        """Get service status."""
        try:
            status = self.transcript_service.get_service_status()
            return jsonify(status)
            
        except Exception as e:
            self.logger.error(f"Error getting status: {e}")
            return jsonify({'error': 'Failed to get service status'}), 500
    
    def get_context_templates(self) -> Dict[str, Any]:
        """Get list of available context templates."""
        try:
            templates = self.context_service.get_template_list()
            return jsonify({
                'success': True,
                'templates': templates
            })
            
        except Exception as e:
            self.logger.error(f"Error getting templates: {e}")
            return jsonify({'error': 'Failed to get context templates'}), 500
    
    def get_context_template(self, template_key: str) -> Dict[str, Any]:
        """Get specific context template by key."""
        try:
            template_content = self.context_service.get_template(template_key)
            if not template_content:
                return jsonify({'error': 'Template not found'}), 404
            
            return jsonify({
                'success': True,
                'template_key': template_key,
                'content': template_content
            })
            
        except Exception as e:
            self.logger.error(f"Error getting template {template_key}: {e}")
            return jsonify({'error': 'Failed to get template'}), 500
    
    def validate_context(self) -> Dict[str, Any]:
        """Validate context content and provide suggestions."""
        try:
            data = request.get_json()
            if not data or 'context' not in data:
                return jsonify({'error': 'Context text is required'}), 400
            
            context = data['context']
            validation_result = self.context_service.validate_context(context)
            
            return jsonify({
                'success': True,
                'validation': validation_result
            })
            
        except Exception as e:
            self.logger.error(f"Error validating context: {e}")
            return jsonify({'error': 'Failed to validate context'}), 500
    
    def enhance_context(self) -> Dict[str, Any]:
        """Enhance context with suggestions and templates."""
        try:
            data = request.get_json()
            if not data or 'context' not in data:
                return jsonify({'error': 'Context text is required'}), 400
            
            context = data['context']
            template_key = data.get('template_key')
            
            enhanced_context = self.context_service.enhance_context(context, template_key)
            validation_result = self.context_service.validate_context(enhanced_context)
            
            return jsonify({
                'success': True,
                'enhanced_context': enhanced_context,
                'validation': validation_result
            })
            
        except Exception as e:
            self.logger.error(f"Error enhancing context: {e}")
            return jsonify({'error': 'Failed to enhance context'}), 500


def create_api_blueprint() -> Blueprint:
    """Create and return the API blueprint."""
    api_routes = APIRoutes()
    return api_routes.blueprint