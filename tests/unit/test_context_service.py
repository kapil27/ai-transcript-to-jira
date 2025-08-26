"""Unit tests for context management service."""

import pytest
from src.services.context_service import ContextService


class TestContextService:
    """Test cases for ContextService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.context_service = ContextService()
    
    def test_get_template_list(self):
        """Test getting list of available templates."""
        templates = self.context_service.get_template_list()
        
        assert isinstance(templates, list)
        assert len(templates) > 0
        
        # Check template structure
        for template in templates:
            assert 'key' in template
            assert 'name' in template
            assert 'description' in template
            assert isinstance(template['key'], str)
            assert isinstance(template['name'], str)
            assert isinstance(template['description'], str)
    
    def test_get_template_content(self):
        """Test getting specific template content."""
        # Test valid template
        template_content = self.context_service.get_template('web_application')
        assert isinstance(template_content, str)
        assert len(template_content) > 0
        assert 'Web Application' in template_content
        
        # Test invalid template
        invalid_content = self.context_service.get_template('nonexistent')
        assert invalid_content == ""
    
    def test_validate_empty_context(self):
        """Test validation of empty context."""
        result = self.context_service.validate_context("")
        
        assert result['is_valid'] is True
        assert result['quality_score'] == 0
        assert result['word_count'] == 0
        assert isinstance(result['suggestions'], list)
        assert isinstance(result['missing_elements'], list)
    
    def test_validate_basic_context(self):
        """Test validation of basic context."""
        context = "Project: Web App\nTech Stack: React + Node.js\nTeam: 3 developers"
        result = self.context_service.validate_context(context)
        
        assert result['is_valid'] is True
        assert result['quality_score'] > 0
        assert result['word_count'] > 0
        assert 'tech_stack' in result['found_elements']
        assert 'team_info' in result['found_elements']
        assert 'project_type' in result['found_elements']
    
    def test_validate_comprehensive_context(self):
        """Test validation of comprehensive context."""
        context = """
        Project Type: E-commerce Platform
        Tech Stack: React + Node.js + PostgreSQL
        Team: Sarah (Frontend), Mike (Backend), Lisa (Designer)
        Testing: Unit tests with Jest, E2E with Cypress
        Current Sprint: User Authentication & Payment Integration
        Architecture: Microservices
        Deployment: Docker + AWS
        
        Acceptance Criteria:
        • All features must have unit tests (80%+ coverage)
        • API endpoints must follow REST standards
        • UI must be responsive and accessible
        """
        result = self.context_service.validate_context(context)
        
        assert result['is_valid'] is True
        assert result['quality_score'] >= 80  # Should be high quality
        assert len(result['found_elements']) >= 3
        assert 'tech_stack' in result['found_elements']
        assert 'team_info' in result['found_elements']
        assert 'testing' in result['found_elements']
    
    def test_validate_context_with_suggestions(self):
        """Test validation provides helpful suggestions."""
        context = "Simple project"  # Very basic context
        result = self.context_service.validate_context(context)
        
        assert result['is_valid'] is True
        assert result['quality_score'] < 50  # Should be low quality
        assert len(result['suggestions']) > 0
        assert any('tech stack' in suggestion.lower() for suggestion in result['suggestions'])
    
    def test_enhance_empty_context_with_template(self):
        """Test enhancing empty context with template."""
        enhanced = self.context_service.enhance_context("", "web_application")
        
        assert isinstance(enhanced, str)
        assert len(enhanced) > 0
        assert "Web Application" in enhanced
    
    def test_enhance_existing_context(self):
        """Test enhancing existing context."""
        original_context = "Project: Simple web app"
        enhanced = self.context_service.enhance_context(original_context)
        
        assert isinstance(enhanced, str)
        assert original_context in enhanced
        # Should contain suggestions if quality is low
        if "# AI Suggestions" in enhanced:
            assert "# •" in enhanced  # Should have bullet points for suggestions
    
    def test_enhance_high_quality_context(self):
        """Test that high-quality context is not over-enhanced."""
        high_quality_context = """
        Project Type: E-commerce Platform
        Tech Stack: React + Node.js + PostgreSQL + Redis
        Team: Sarah (Frontend Expert), Mike (Backend Lead), Lisa (UI/UX Designer), Tom (DevOps)
        Testing: Jest for unit tests, Cypress for E2E, Selenium for cross-browser
        Current Sprint: User Authentication & Payment Integration with Stripe
        Architecture: Microservices with Docker containers
        Database: PostgreSQL with Redis for caching
        
        Acceptance Criteria:
        • All features must have unit tests (85%+ coverage)
        • API endpoints must follow REST standards
        • UI must be responsive and accessible (WCAG 2.1)
        • Security: Authentication with JWT, authorization with RBAC
        • Performance: Page load time < 2 seconds
        """
        
        enhanced = self.context_service.enhance_context(high_quality_context)
        
        # High quality context should not be significantly changed
        assert enhanced == high_quality_context.strip()
    
    def test_template_keys_exist(self):
        """Test that all expected template keys exist."""
        expected_templates = [
            'web_application',
            'mobile_app', 
            'api_service',
            'data_analytics',
            'e_commerce',
            'enterprise_software'
        ]
        
        templates = self.context_service.get_template_list()
        template_keys = [t['key'] for t in templates]
        
        for expected_key in expected_templates:
            assert expected_key in template_keys
    
    def test_template_content_structure(self):
        """Test that template content has expected structure."""
        template_content = self.context_service.get_template('web_application')
        
        # Should contain key elements
        assert 'Tech Stack:' in template_content
        assert 'Team' in template_content
        assert 'Testing' in template_content
        assert 'Acceptance Criteria:' in template_content
        
        # Should be substantial content
        assert len(template_content.split('\n')) > 5
        assert len(template_content) > 200