"""Enhanced logging configuration and utilities for JIRA integration."""

import json
import logging
import sys
import time
import uuid
from contextlib import contextmanager
from typing import Optional, Dict, Any, Union
from datetime import datetime, timezone
from pathlib import Path

from ..config.settings import get_config


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        # Create base log data
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        # Add correlation ID if present
        if hasattr(record, 'correlation_id'):
            log_data['correlation_id'] = record.correlation_id

        # Add JIRA-specific fields if present
        jira_fields = ['connection_id', 'project_key', 'task_id', 'operation',
                      'execution_time_ms', 'jira_issue_key', 'similarity_score']

        for field in jira_fields:
            if hasattr(record, field):
                log_data[field] = getattr(record, field)

        # Add exception information
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': self.formatException(record.exc_info)
            }

        # Add extra fields from LoggerAdapter or manual addition
        if hasattr(record, '_extra_fields'):
            log_data.update(record._extra_fields)

        return json.dumps(log_data)


class JiraLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter for JIRA operations with context tracking."""

    def __init__(self, logger: logging.Logger, extra: Dict[str, Any] = None):
        """Initialize with optional extra context."""
        super().__init__(logger, extra or {})
        self.correlation_id = str(uuid.uuid4())
        self.operation_start_time = None

    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """Process log message and add context."""
        # Add correlation ID to all log messages
        if 'extra' not in kwargs:
            kwargs['extra'] = {}

        kwargs['extra']['correlation_id'] = self.correlation_id

        # Add any stored extra context
        if self.extra:
            kwargs['extra'].update(self.extra)

        # Store extra fields for structured formatter - skip this for now to avoid errors
        # This would be used for more advanced structured logging
        pass

        return msg, kwargs

    def start_operation(self, operation: str, **context) -> None:
        """Start timing an operation."""
        self.operation_start_time = time.time()
        self.info(f"Starting {operation}", extra={'operation': operation, **context})

    def end_operation(self, operation: str, success: bool = True, **context) -> float:
        """End timing an operation and log results."""
        execution_time_ms = 0
        if self.operation_start_time:
            execution_time_ms = int((time.time() - self.operation_start_time) * 1000)

        log_level = self.info if success else self.error
        status = "completed" if success else "failed"

        log_level(
            f"{operation} {status} in {execution_time_ms}ms",
            extra={
                'operation': operation,
                'execution_time_ms': execution_time_ms,
                'success': success,
                **context
            }
        )

        self.operation_start_time = None
        return execution_time_ms

    def log_jira_request(self, method: str, endpoint: str, status_code: int,
                        response_time_ms: int, **context) -> None:
        """Log JIRA API request details."""
        success = 200 <= status_code < 300
        log_level = self.info if success else self.warning if status_code < 500 else self.error

        log_level(
            f"JIRA API {method} {endpoint} -> {status_code} ({response_time_ms}ms)",
            extra={
                'operation': 'jira_api_request',
                'http_method': method,
                'endpoint': endpoint,
                'status_code': status_code,
                'execution_time_ms': response_time_ms,
                'success': success,
                **context
            }
        )

    def log_duplicate_analysis(self, task_id: str, similar_issues_count: int,
                             best_match_score: float, analysis_time_ms: int, **context) -> None:
        """Log duplicate analysis results."""
        self.info(
            f"Duplicate analysis for {task_id}: {similar_issues_count} similar issues, "
            f"best match {best_match_score:.2%} ({analysis_time_ms}ms)",
            extra={
                'operation': 'duplicate_analysis',
                'task_id': task_id,
                'similar_issues_count': similar_issues_count,
                'similarity_score': best_match_score,
                'execution_time_ms': analysis_time_ms,
                **context
            }
        )

    def log_task_creation(self, task_id: str, jira_issue_key: str,
                         processing_time_ms: int, **context) -> None:
        """Log task creation success."""
        self.info(
            f"Created JIRA issue {jira_issue_key} for task {task_id} ({processing_time_ms}ms)",
            extra={
                'operation': 'task_creation',
                'task_id': task_id,
                'jira_issue_key': jira_issue_key,
                'execution_time_ms': processing_time_ms,
                'success': True,
                **context
            }
        )

    def log_workflow_progress(self, stage: str, tasks_processed: int,
                            total_tasks: int, **context) -> None:
        """Log workflow progress."""
        progress_pct = (tasks_processed / total_tasks * 100) if total_tasks > 0 else 0

        self.info(
            f"Workflow {stage}: {tasks_processed}/{total_tasks} tasks ({progress_pct:.1f}%)",
            extra={
                'operation': 'workflow_progress',
                'workflow_stage': stage,
                'tasks_processed': tasks_processed,
                'total_tasks': total_tasks,
                'progress_percentage': round(progress_pct, 1),
                **context
            }
        )


def setup_logger(
    name: str,
    level: str = "INFO",
    format_string: Optional[str] = None,
    structured: bool = False,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Set up a logger with enhanced formatting for JIRA operations.

    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Custom format string (optional)
        structured: Use structured JSON logging
        log_file: Optional log file path

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Choose formatter
    if structured:
        formatter = StructuredFormatter()
    else:
        if format_string is None:
            format_string = (
                "%(asctime)s - %(name)s - %(levelname)s - "
                "[%(correlation_id)s] %(message)s"
            )
        formatter = logging.Formatter(format_string)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def setup_jira_logging(config=None) -> Dict[str, logging.Logger]:
    """Set up specialized loggers for JIRA integration components."""
    if config is None:
        config = get_config()

    log_level = "DEBUG" if config.debug else "INFO"
    use_structured = getattr(config, 'structured_logging', False)
    log_dir = getattr(config, 'log_directory', './logs')

    loggers = {}

    # Core JIRA integration logger
    loggers['jira'] = setup_logger(
        'jira_integration',
        level=log_level,
        structured=use_structured,
        log_file=f"{log_dir}/jira_integration.log" if log_dir else None
    )

    # MCP operations logger
    loggers['mcp'] = setup_logger(
        'mcp_operations',
        level=log_level,
        structured=use_structured,
        log_file=f"{log_dir}/mcp_operations.log" if log_dir else None
    )

    # Duplicate detection logger
    loggers['duplicates'] = setup_logger(
        'duplicate_detection',
        level=log_level,
        structured=use_structured,
        log_file=f"{log_dir}/duplicate_detection.log" if log_dir else None
    )

    # Performance logger
    loggers['performance'] = setup_logger(
        'performance',
        level=log_level,
        structured=use_structured,
        log_file=f"{log_dir}/performance.log" if log_dir else None
    )

    # Workflow logger
    loggers['workflow'] = setup_logger(
        'workflow',
        level=log_level,
        structured=use_structured,
        log_file=f"{log_dir}/workflow.log" if log_dir else None
    )

    return loggers


class LoggerMixin:
    """Enhanced mixin class with JIRA-specific logging capabilities."""

    @property
    def logger(self) -> JiraLoggerAdapter:
        """Get a JIRA logger adapter for this class."""
        if not hasattr(self, '_logger'):
            base_logger = setup_logger(self.__class__.__name__)
            self._logger = JiraLoggerAdapter(base_logger, {
                'component': self.__class__.__name__
            })
        return self._logger

    @contextmanager
    def log_operation(self, operation: str, **context):
        """Context manager for logging operations with timing."""
        self.logger.start_operation(operation, **context)
        start_time = time.time()
        success = False

        try:
            yield self.logger
            success = True
        except Exception as e:
            self.logger.error(f"{operation} failed: {str(e)}", extra={
                'operation': operation,
                'error_type': type(e).__name__,
                **context
            })
            raise
        finally:
            execution_time = self.logger.end_operation(operation, success, **context)

            # Record performance metric if database manager is available
            try:
                from .database import get_database_manager
                db_manager = get_database_manager()
                db_manager.record_performance_metric(
                    operation_type=operation,
                    execution_time_ms=int(execution_time),
                    success=success,
                    connection_id=context.get('connection_id'),
                    project_key=context.get('project_key'),
                    metadata=context
                )
            except Exception:
                # Don't fail the operation if performance recording fails
                pass


class PerformanceLogger:
    """Specialized logger for performance tracking."""

    def __init__(self):
        self.logger = setup_logger('performance', structured=True)
        self._operation_stack = []

    @contextmanager
    def track_operation(self, operation: str, **context):
        """Track operation performance with nested operation support."""
        operation_id = str(uuid.uuid4())
        start_time = time.time()

        operation_data = {
            'operation_id': operation_id,
            'operation': operation,
            'start_time': start_time,
            'context': context
        }

        self._operation_stack.append(operation_data)

        try:
            yield operation_id
            success = True
        except Exception as e:
            success = False
            operation_data['error'] = str(e)
            operation_data['error_type'] = type(e).__name__
            raise
        finally:
            end_time = time.time()
            execution_time_ms = int((end_time - start_time) * 1000)

            self._operation_stack.pop()

            # Log performance data
            self.logger.info(
                f"Operation {operation} {'completed' if success else 'failed'} in {execution_time_ms}ms",
                extra={
                    'operation_id': operation_id,
                    'operation': operation,
                    'execution_time_ms': execution_time_ms,
                    'success': success,
                    'parent_operation': self._operation_stack[-1]['operation'] if self._operation_stack else None,
                    **context,
                    **(operation_data.get('error_context', {}))
                }
            )