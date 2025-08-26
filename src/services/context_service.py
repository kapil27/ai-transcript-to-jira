"""Context management service for project-specific settings and templates."""

from typing import Dict, List, Any
from ..utils import LoggerMixin


class ContextService(LoggerMixin):
    """Service for managing project context templates and validation."""
    
    def __init__(self):
        """Initialize context service with predefined templates."""
        self.templates = self._get_predefined_templates()
    
    def _get_predefined_templates(self) -> Dict[str, Dict[str, str]]:
        """Get predefined context templates for common project types."""
        return {
            "web_application": {
                "name": "Web Application",
                "description": "Full-stack web application development",
                "template": """Project Type: Web Application
Tech Stack: [React/Vue/Angular] + [Node.js/Python/Java] + [PostgreSQL/MongoDB]
Team Roles:
• Frontend Developer: UI/UX implementation
• Backend Developer: API and database
• DevOps Engineer: Deployment and infrastructure
• QA Engineer: Testing and quality assurance

Current Sprint Focus: [Authentication/Dashboard/Payment/etc.]
Architecture: [Microservices/Monolith]
Testing Strategy: [Unit tests with Jest/Pytest, E2E with Cypress/Selenium]
Deployment: [Docker/Kubernetes/Cloud platform]

Acceptance Criteria:
• All features must have unit tests (80%+ coverage)
• API endpoints must follow REST standards
• UI must be responsive and accessible
• Security: Authentication and authorization required"""
            },
            
            "mobile_app": {
                "name": "Mobile Application", 
                "description": "Mobile app development (iOS/Android)",
                "template": """Project Type: Mobile Application
Platform: [iOS/Android/Cross-platform]
Tech Stack: [React Native/Flutter/Swift/Kotlin]
Team Roles:
• Mobile Developer: App development
• Backend Developer: API services
• UI/UX Designer: User interface design
• QA Engineer: Device testing

Current Sprint Focus: [User onboarding/Core features/Integration]
Architecture: [Native/Hybrid/PWA]
Testing Strategy: [Unit tests, Device testing, App store guidelines]
Backend: [REST API/GraphQL/Firebase]

Acceptance Criteria:
• App must work on target OS versions
• Performance: Loading time < 3 seconds
• UI follows platform design guidelines
• Offline functionality where applicable"""
            },
            
            "api_service": {
                "name": "API/Microservice",
                "description": "Backend API or microservice development", 
                "template": """Project Type: API/Microservice
Tech Stack: [Node.js/Python/Java/Go] + [Express/FastAPI/Spring Boot]
Database: [PostgreSQL/MongoDB/Redis]
Team Roles:
• Backend Developer: API implementation
• DevOps Engineer: Infrastructure and deployment
• Database Admin: Schema and optimization
• QA Engineer: API testing

Current Sprint Focus: [Authentication/Data processing/Integration]
Architecture: [REST API/GraphQL/gRPC]
Testing Strategy: [Unit tests, Integration tests, Load testing]
Documentation: [OpenAPI/Swagger]

Acceptance Criteria:
• API must follow OpenAPI specification
• Response time: < 200ms for 95% of requests
• Error handling with proper HTTP status codes
• Comprehensive logging and monitoring
• Security: Rate limiting and authentication"""
            },
            
            "data_analytics": {
                "name": "Data Analytics/ML",
                "description": "Data science and machine learning projects",
                "template": """Project Type: Data Analytics/Machine Learning
Tech Stack: [Python/R] + [Pandas/NumPy/Scikit-learn/TensorFlow]
Data Sources: [APIs/Databases/Files/Streaming]
Team Roles:
• Data Scientist: Model development and analysis
• Data Engineer: Data pipeline and infrastructure
• ML Engineer: Model deployment and monitoring
• Business Analyst: Requirements and validation

Current Sprint Focus: [Data collection/Model training/Deployment]
Architecture: [Batch processing/Real-time/MLOps pipeline]
Tools: [Jupyter/MLflow/Airflow/Docker]
Testing Strategy: [Data validation, Model testing, A/B testing]

Acceptance Criteria:
• Data quality: 95%+ accuracy and completeness
• Model performance: Meet baseline metrics
• Reproducible experiments and versioning
• Monitoring and alerting for data drift
• Documentation of methodology and findings"""
            },
            
            "e_commerce": {
                "name": "E-commerce Platform",
                "description": "Online shopping and e-commerce systems",
                "template": """Project Type: E-commerce Platform
Tech Stack: [Frontend] + [Backend] + [Payment Gateway] + [Database]
Team Roles:
• Frontend Developer: Shopping interface
• Backend Developer: Order processing and inventory
• Payment Integration Specialist: Payment systems
• Security Engineer: PCI compliance and security

Current Sprint Focus: [Product catalog/Shopping cart/Checkout/Orders]
Features: [User accounts/Product search/Payment/Shipping/Returns]
Testing Strategy: [Payment testing, Security testing, Performance testing]
Compliance: [PCI DSS/GDPR/Accessibility]

Acceptance Criteria:
• Payment processing: 99.9% uptime
• Security: PCI DSS compliance
• Performance: Page load < 2 seconds
• Mobile-responsive design
• Inventory sync and order tracking"""
            },
            
            "enterprise_software": {
                "name": "Enterprise Software",
                "description": "Large-scale enterprise applications",
                "template": """Project Type: Enterprise Software
Tech Stack: [Java/.NET/Python] + [Spring/ASP.NET/Django] + [Enterprise DB]
Team Roles:
• Senior Developer: Architecture and complex features
• Junior Developer: Implementation and testing
• Business Analyst: Requirements gathering
• System Administrator: Infrastructure and deployment

Current Sprint Focus: [Core modules/Integration/Reporting]
Architecture: [Multi-tier/SOA/Microservices]
Integration: [ERP/CRM/Legacy systems]
Testing Strategy: [Unit/Integration/System/UAT]

Acceptance Criteria:
• Scalability: Handle enterprise user load
• Security: Enterprise-grade authentication/authorization
• Integration: Seamless with existing systems
• Documentation: Technical and user documentation
• Compliance: Industry standards and regulations"""
            }
        }
    
    def get_template_list(self) -> List[Dict[str, str]]:
        """Get list of available templates with metadata."""
        return [
            {
                "key": key,
                "name": template["name"],
                "description": template["description"]
            }
            for key, template in self.templates.items()
        ]
    
    def get_template(self, template_key: str) -> str:
        """Get template content by key."""
        if template_key in self.templates:
            return self.templates[template_key]["template"]
        return ""
    
    def validate_context(self, context: str) -> Dict[str, Any]:
        """Validate and analyze context content."""
        if not context.strip():
            return {
                "is_valid": True,
                "suggestions": [],
                "missing_elements": [],
                "quality_score": 0,
                "word_count": 0,
                "found_elements": []
            }
        
        context_lower = context.lower()
        suggestions = []
        missing_elements = []
        quality_score = 0
        
        # Check for essential elements
        essential_elements = {
            "tech_stack": ["tech stack", "technology", "framework", "language"],
            "team_info": ["team", "developer", "engineer", "role"],
            "project_type": ["project", "application", "system", "platform"],
            "testing": ["test", "testing", "qa", "quality"],
        }
        
        found_elements = []
        for element, keywords in essential_elements.items():
            if any(keyword in context_lower for keyword in keywords):
                found_elements.append(element)
                quality_score += 25
        
        # Generate suggestions based on missing elements
        if "tech_stack" not in found_elements:
            missing_elements.append("tech_stack")
            suggestions.append("Consider adding tech stack information (frameworks, languages, databases)")
        
        if "team_info" not in found_elements:
            missing_elements.append("team_info")
            suggestions.append("Add team member roles and expertise areas")
        
        if "testing" not in found_elements:
            missing_elements.append("testing")
            suggestions.append("Include testing requirements and acceptance criteria")
        
        # Length-based quality adjustment
        word_count = len(context.split())
        if word_count < 20:
            suggestions.append("Consider providing more detailed context (aim for 50+ words)")
            quality_score = max(0, quality_score - 20)
        elif word_count > 200:
            suggestions.append("Context is very detailed - consider organizing with bullet points")
            quality_score = min(100, quality_score + 10)
        
        return {
            "is_valid": True,
            "suggestions": suggestions,
            "missing_elements": missing_elements,
            "quality_score": min(100, quality_score),
            "word_count": word_count,
            "found_elements": found_elements
        }
    
    def enhance_context(self, context: str, template_key: str = None) -> str:
        """Enhance existing context with template elements."""
        if not context.strip():
            return self.get_template(template_key) if template_key else ""
        
        validation = self.validate_context(context)
        
        if validation["quality_score"] >= 80:
            return context.strip()  # Already high quality - return stripped version
        
        # Add suggestions as comments
        enhanced = context + "\n\n"
        if validation["suggestions"]:
            enhanced += "# AI Suggestions for Context Enhancement:\n"
            for suggestion in validation["suggestions"]:
                enhanced += f"# • {suggestion}\n"
        
        return enhanced.strip()