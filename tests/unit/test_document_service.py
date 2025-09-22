"""Tests for the DocumentParsingService class."""

import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock

from src.services.document_service import DocumentParsingService
from src.exceptions import ValidationError


class TestDocumentParsingService:
    """Test cases for DocumentParsingService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.document_service = DocumentParsingService()
    
    def test_service_initialization(self):
        """Test document service initializes with supported formats."""
        formats = self.document_service.get_supported_formats()
        assert 'text/plain' in formats
        
        # Check that at least text parsing is available
        assert formats['text/plain']['extension'] == '.txt'
        assert 'Plain text' in formats['text/plain']['description']
    
    def test_detect_file_type_by_content(self):
        """Test file type detection based on content."""
        # Test plain text
        text_data = b"This is a plain text file"
        detected_type = self.document_service.detect_file_type(text_data, "test.txt")
        assert detected_type == 'text/plain'
        
        # Test PDF signature
        pdf_data = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog"
        detected_type = self.document_service.detect_file_type(pdf_data, "test.pdf")
        assert detected_type == 'application/pdf'
    
    def test_detect_file_type_by_extension(self):
        """Test file type detection based on filename extension."""
        text_data = b"Some content"
        
        # Test different extensions
        assert self.document_service.detect_file_type(text_data, "file.txt") == 'text/plain'
        assert self.document_service.detect_file_type(text_data, "file.pdf") == 'application/pdf'
        assert self.document_service.detect_file_type(text_data, "file.docx") == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    
    def test_validate_file_success(self):
        """Test successful file validation."""
        file_data = b"This is a valid text file content"
        filename = "test.txt"
        
        validation_result = self.document_service.validate_file(file_data, filename)
        
        assert validation_result['is_valid'] is True
        assert len(validation_result['errors']) == 0
        assert validation_result['file_info']['detected_type'] == 'text/plain'
        assert validation_result['file_info']['size_bytes'] == len(file_data)
        assert validation_result['file_info']['filename'] == filename
    
    def test_validate_file_too_large(self):
        """Test file validation failure for oversized files."""
        # Create file data larger than max size
        large_data = b"x" * (self.document_service.max_file_size + 1)
        
        validation_result = self.document_service.validate_file(large_data, "large.txt")
        
        assert validation_result['is_valid'] is False
        assert any("exceeds maximum allowed size" in error for error in validation_result['errors'])
    
    def test_validate_file_empty(self):
        """Test file validation failure for empty files."""
        empty_data = b""
        
        validation_result = self.document_service.validate_file(empty_data, "empty.txt")
        
        assert validation_result['is_valid'] is False
        assert "File is empty" in validation_result['errors']
    
    def test_validate_file_unsupported_format(self):
        """Test file validation failure for unsupported formats."""
        # Binary data that doesn't match any supported format
        binary_data = b"\x89PNG\r\n\x1a\n"  # PNG header
        
        validation_result = self.document_service.validate_file(binary_data, "image.png")
        
        assert validation_result['is_valid'] is False
        assert "Unsupported file format" in validation_result['errors']
    
    def test_parse_text_document(self):
        """Test parsing plain text documents."""
        text_content = "This is a test meeting transcript.\nJohn: Can you finish the task?\nSarah: Yes, I'll do it."
        file_data = text_content.encode('utf-8')
        
        result = self.document_service.parse_document(file_data, "transcript.txt")
        
        assert result['success'] is True
        assert result['text'] == text_content
        assert result['metadata']['filename'] == "transcript.txt"
        assert result['metadata']['mime_type'] == 'text/plain'
        assert result['metadata']['text_length'] == len(text_content)
    
    def test_parse_text_document_with_encoding(self):
        """Test parsing text documents with different encodings."""
        text_content = "Café meeting with résumé review"
        
        # Test UTF-8
        file_data = text_content.encode('utf-8')
        result = self.document_service.parse_document(file_data, "test.txt")
        assert result['text'] == text_content
        
        # Test latin-1 (should work as fallback)
        try:
            file_data = text_content.encode('latin-1')
            result = self.document_service.parse_document(file_data, "test.txt")
            assert result['success'] is True
        except UnicodeEncodeError:
            # Skip this test if the text can't be encoded in latin-1
            pass
    
    def test_parse_document_validation_failure(self):
        """Test document parsing with invalid files."""
        empty_data = b""
        
        with pytest.raises(ValidationError, match="File validation failed"):
            self.document_service.parse_document(empty_data, "empty.txt")
    
    def test_parse_document_no_content(self):
        """Test document parsing with no extractable content."""
        # File with only whitespace
        whitespace_data = b"   \n\t\r\n   "
        
        with pytest.raises(ValidationError, match="No text content found"):
            self.document_service.parse_document(whitespace_data, "whitespace.txt")
    
    def test_parse_document_text_truncation(self):
        """Test document parsing with very long text gets truncated."""
        # Create text longer than max length
        long_text = "A" * (self.document_service.max_text_length + 1000)
        file_data = long_text.encode('utf-8')
        
        result = self.document_service.parse_document(file_data, "long.txt")
        
        assert result['success'] is True
        assert len(result['text']) <= self.document_service.max_text_length + 100  # Allow for truncation message
        assert "[Content truncated due to length...]" in result['text']
    
    @patch('src.services.document_service.PDF_AVAILABLE', True)
    def test_parse_pdf_document_success(self):
        """Test successful PDF parsing."""
        # Mock PyPDF2 functionality
        with patch('src.services.document_service.PyPDF2') as mock_pypdf2:
            mock_reader = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "This is PDF content"
            mock_reader.pages = [mock_page]
            mock_pypdf2.PdfReader.return_value = mock_reader
            
            # PDF file signature
            pdf_data = b"%PDF-1.4\nsome pdf content"
            
            result = self.document_service.parse_document(pdf_data, "test.pdf")
            
            assert result['success'] is True
            assert "This is PDF content" in result['text']
            assert result['metadata']['mime_type'] == 'application/pdf'
    
    @patch('src.services.document_service.PDF_AVAILABLE', False)
    def test_parse_pdf_not_available(self):
        """Test PDF parsing when PyPDF2 not available."""
        pdf_data = b"%PDF-1.4\nsome pdf content"
        
        with pytest.raises(ValidationError, match="PDF parsing not available"):
            self.document_service._parse_pdf(pdf_data)
    
    @patch('src.services.document_service.DOCX_AVAILABLE', True)
    def test_parse_docx_document_success(self):
        """Test successful DOCX parsing."""
        # Mock python-docx functionality
        with patch('src.services.document_service.Document') as mock_document:
            mock_doc = MagicMock()
            mock_paragraph = MagicMock()
            mock_paragraph.text = "This is DOCX content"
            mock_doc.paragraphs = [mock_paragraph]
            mock_doc.tables = []  # No tables
            mock_document.return_value = mock_doc
            
            # Mock tempfile creation
            with patch('tempfile.NamedTemporaryFile') as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = "/tmp/test.docx"
                
                # Mock os.unlink to avoid file not found errors
                with patch('os.unlink'):
                    docx_data = b"PK\x03\x04docx content"
                    
                    result = self.document_service.parse_document(docx_data, "test.docx")
                    
                    assert result['success'] is True
                    assert "This is DOCX content" in result['text']
                    assert result['metadata']['mime_type'] == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    
    @patch('src.services.document_service.DOCX_AVAILABLE', False)
    def test_parse_docx_not_available(self):
        """Test DOCX parsing when python-docx not available."""
        docx_data = b"PK\x03\x04docx content"
        
        with pytest.raises(ValidationError, match="DOCX parsing not available"):
            self.document_service._parse_docx(docx_data)
    
    def test_get_parsing_stats(self):
        """Test getting parsing statistics and capabilities."""
        stats = self.document_service.get_parsing_stats()
        
        assert 'supported_formats' in stats
        assert 'limits' in stats
        assert 'available_parsers' in stats
        
        # Check limits
        assert stats['limits']['max_file_size_bytes'] == self.document_service.max_file_size
        assert stats['limits']['max_text_length'] == self.document_service.max_text_length
        
        # Check parsers availability
        assert 'pdf' in stats['available_parsers']
        assert 'docx' in stats['available_parsers']
        assert 'magic_detection' in stats['available_parsers']
    
    def test_format_descriptions(self):
        """Test format descriptions are human-readable."""
        formats = self.document_service.get_supported_formats()
        
        for mime_type, info in formats.items():
            assert 'extension' in info
            assert 'description' in info
            assert info['extension'].startswith('.')
            assert len(info['description']) > 0
    
    def test_edge_cases(self):
        """Test edge cases and error handling."""
        # Test with None filename
        text_data = b"Test content"
        validation_result = self.document_service.validate_file(text_data, None)
        assert validation_result['file_info']['filename'] is None
        
        # Test with empty filename
        validation_result = self.document_service.validate_file(text_data, "")
        assert validation_result['file_info']['filename'] == ""
        
        # Test detection with no filename and ambiguous content
        # Note: The service may still detect some binary data as text due to fallback logic
        binary_data = b"\x00\x01\x02\x03"
        detected_type = self.document_service.detect_file_type(binary_data, None)
        # Either None or text/plain (fallback) are acceptable for ambiguous binary data
        assert detected_type in [None, 'text/plain']
