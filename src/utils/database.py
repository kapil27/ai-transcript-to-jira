"""Database schema utilities for JIRA integration tables."""

import sqlite3
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager
from dataclasses import asdict

from ..config.settings import get_config

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Database manager for JIRA integration schema."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize database manager with schema support."""
        config = get_config()

        if db_path is None:
            # Use same directory as cache for consistency
            cache_dir = getattr(config, 'cache_directory', './cache')
            Path(cache_dir).mkdir(exist_ok=True)
            db_path = f"{cache_dir}/jira_integration.db"

        self.db_path = db_path
        self.connection_pool_size = 5
        self._initialized = False

        # Initialize schema
        self.init_schema()

    @contextmanager
    def get_connection(self):
        """Get database connection with proper error handling."""
        conn = None
        try:
            conn = sqlite3.connect(
                self.db_path,
                timeout=30.0,
                check_same_thread=False
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def init_schema(self) -> None:
        """Initialize database schema for JIRA integration."""
        if self._initialized:
            return

        with self.get_connection() as conn:
            # Create schema version table first
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    description TEXT
                )
            """)

            # Check current schema version
            current_version = self._get_schema_version(conn)

            # Apply migrations if needed
            if current_version < 1:
                self._apply_migration_v1(conn)
            if current_version < 2:
                self._apply_migration_v2(conn)

            conn.commit()
            self._initialized = True
            logger.info(f"Database schema initialized at version {self._get_schema_version(conn)}")

    def _get_schema_version(self, conn: sqlite3.Connection) -> int:
        """Get current schema version."""
        try:
            cursor = conn.execute("SELECT MAX(version) FROM schema_version")
            result = cursor.fetchone()
            return result[0] if result and result[0] is not None else 0
        except sqlite3.OperationalError:
            return 0

    def _apply_migration_v1(self, conn: sqlite3.Connection) -> None:
        """Apply initial schema migration (v1)."""
        logger.info("Applying database migration v1...")

        # JIRA connections table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jira_connections (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                base_url TEXT NOT NULL,
                encrypted_credentials BLOB NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                last_validated TIMESTAMP,
                validation_status TEXT DEFAULT 'unknown',
                connection_metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Project contexts table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS project_contexts (
                id TEXT PRIMARY KEY,
                connection_id TEXT NOT NULL,
                project_key TEXT NOT NULL,
                project_name TEXT,
                context_data TEXT NOT NULL,
                cached_sprints TEXT,
                cached_epics TEXT,
                cached_components TEXT,
                cached_issue_types TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                cache_expires_at TIMESTAMP,
                FOREIGN KEY (connection_id) REFERENCES jira_connections(id) ON DELETE CASCADE,
                UNIQUE(connection_id, project_key)
            )
        """)

        # Enhanced tasks table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS enhanced_tasks (
                id TEXT PRIMARY KEY,
                original_task_data TEXT NOT NULL,
                project_key TEXT NOT NULL,
                connection_id TEXT,
                suggestions TEXT,
                project_context_score REAL DEFAULT 0.0,
                confidence_score REAL DEFAULT 0.0,
                extracted_from TEXT,
                jira_issue_key TEXT,
                jira_url TEXT,
                creation_status TEXT DEFAULT 'pending',
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                FOREIGN KEY (connection_id) REFERENCES jira_connections(id) ON DELETE SET NULL
            )
        """)

        # Duplicate analysis table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS duplicate_analyses (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                project_key TEXT NOT NULL,
                connection_id TEXT,
                search_query TEXT,
                similar_issues TEXT NOT NULL,
                best_match_data TEXT,
                confidence REAL DEFAULT 0.0,
                recommended_action TEXT,
                reasoning TEXT,
                analysis_time_ms INTEGER DEFAULT 0,
                total_issues_searched INTEGER DEFAULT 0,
                algorithm_version TEXT DEFAULT '1.0.0',
                user_resolution TEXT,
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES enhanced_tasks(id) ON DELETE CASCADE,
                FOREIGN KEY (connection_id) REFERENCES jira_connections(id) ON DELETE SET NULL
            )
        """)

        # Indexes for performance
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jira_connections_active ON jira_connections(is_active)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_project_contexts_connection ON project_contexts(connection_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_project_contexts_key ON project_contexts(project_key)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_enhanced_tasks_project ON enhanced_tasks(project_key)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_enhanced_tasks_status ON enhanced_tasks(creation_status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_duplicate_analyses_task ON duplicate_analyses(task_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_duplicate_analyses_project ON duplicate_analyses(project_key)")

        # Record migration
        conn.execute(
            "INSERT INTO schema_version (version, description) VALUES (1, 'Initial JIRA integration schema')"
        )

    def _apply_migration_v2(self, conn: sqlite3.Connection) -> None:
        """Apply schema migration v2 - Add performance and analytics tables."""
        logger.info("Applying database migration v2...")

        # Performance metrics table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id TEXT PRIMARY KEY,
                operation_type TEXT NOT NULL,
                connection_id TEXT,
                project_key TEXT,
                execution_time_ms INTEGER NOT NULL,
                success BOOLEAN NOT NULL,
                error_type TEXT,
                metadata TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (connection_id) REFERENCES jira_connections(id) ON DELETE SET NULL
            )
        """)

        # User preferences table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id TEXT NOT NULL,
                preference_key TEXT NOT NULL,
                preference_value TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, preference_key)
            )
        """)

        # Processing sessions table for tracking transcript processing workflows
        conn.execute("""
            CREATE TABLE IF NOT EXISTS processing_sessions (
                id TEXT PRIMARY KEY,
                transcript_hash TEXT NOT NULL,
                connection_id TEXT,
                project_key TEXT,
                session_status TEXT DEFAULT 'started',
                tasks_extracted INTEGER DEFAULT 0,
                tasks_created INTEGER DEFAULT 0,
                duplicates_found INTEGER DEFAULT 0,
                session_metadata TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (connection_id) REFERENCES jira_connections(id) ON DELETE SET NULL
            )
        """)

        # Additional indexes for v2 tables
        conn.execute("CREATE INDEX IF NOT EXISTS idx_performance_metrics_operation ON performance_metrics(operation_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_performance_metrics_timestamp ON performance_metrics(timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_processing_sessions_status ON processing_sessions(session_status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_processing_sessions_project ON processing_sessions(project_key)")

        # Add new columns to existing tables for enhanced functionality
        try:
            conn.execute("ALTER TABLE jira_connections ADD COLUMN rate_limit_remaining INTEGER DEFAULT 100")
            conn.execute("ALTER TABLE jira_connections ADD COLUMN rate_limit_reset_at TIMESTAMP")
        except sqlite3.OperationalError:
            # Column already exists
            pass

        # Record migration
        conn.execute(
            "INSERT INTO schema_version (version, description) VALUES (2, 'Performance metrics and user preferences')"
        )

    # CRUD operations for JIRA connections
    def save_jira_connection(self, connection_data: Dict[str, Any]) -> str:
        """Save JIRA connection to database."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO jira_connections
                (id, name, base_url, encrypted_credentials, is_active, connection_metadata, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                connection_data['id'],
                connection_data['name'],
                connection_data['base_url'],
                connection_data['encrypted_credentials'],
                connection_data.get('is_active', True),
                json.dumps(connection_data.get('metadata', {}))
            ))
            conn.commit()
            logger.info(f"Saved JIRA connection: {connection_data['name']}")
            return connection_data['id']

    def get_jira_connection(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get JIRA connection by ID."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM jira_connections WHERE id = ?
            """, (connection_id,))

            row = cursor.fetchone()
            if row:
                return {
                    'id': row['id'],
                    'name': row['name'],
                    'base_url': row['base_url'],
                    'encrypted_credentials': row['encrypted_credentials'],
                    'is_active': bool(row['is_active']),
                    'last_validated': row['last_validated'],
                    'validation_status': row['validation_status'],
                    'metadata': json.loads(row['connection_metadata'] or '{}'),
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                }
            return None

    def list_active_jira_connections(self) -> List[Dict[str, Any]]:
        """List all active JIRA connections."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT id, name, base_url, validation_status, last_validated, created_at
                FROM jira_connections
                WHERE is_active = 1
                ORDER BY name
            """)

            return [dict(row) for row in cursor.fetchall()]

    def update_connection_validation(self, connection_id: str, status: str, last_validated: Optional[datetime] = None) -> None:
        """Update connection validation status."""
        if last_validated is None:
            last_validated = datetime.now(timezone.utc)

        with self.get_connection() as conn:
            conn.execute("""
                UPDATE jira_connections
                SET validation_status = ?, last_validated = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, last_validated.isoformat(), connection_id))
            conn.commit()

    # CRUD operations for project contexts
    def save_project_context(self, context_data: Dict[str, Any]) -> str:
        """Save project context to database."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO project_contexts
                (id, connection_id, project_key, project_name, context_data,
                 cached_sprints, cached_epics, cached_components, cached_issue_types,
                 cache_expires_at, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                context_data['id'],
                context_data['connection_id'],
                context_data['project_key'],
                context_data.get('project_name'),
                json.dumps(context_data['context_data']),
                json.dumps(context_data.get('cached_sprints', [])),
                json.dumps(context_data.get('cached_epics', [])),
                json.dumps(context_data.get('cached_components', [])),
                json.dumps(context_data.get('cached_issue_types', [])),
                context_data.get('cache_expires_at')
            ))
            conn.commit()
            logger.info(f"Saved project context: {context_data['project_key']}")
            return context_data['id']

    def get_project_context(self, connection_id: str, project_key: str) -> Optional[Dict[str, Any]]:
        """Get project context from database."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM project_contexts
                WHERE connection_id = ? AND project_key = ?
            """, (connection_id, project_key))

            row = cursor.fetchone()
            if row:
                return {
                    'id': row['id'],
                    'connection_id': row['connection_id'],
                    'project_key': row['project_key'],
                    'project_name': row['project_name'],
                    'context_data': json.loads(row['context_data']),
                    'cached_sprints': json.loads(row['cached_sprints'] or '[]'),
                    'cached_epics': json.loads(row['cached_epics'] or '[]'),
                    'cached_components': json.loads(row['cached_components'] or '[]'),
                    'cached_issue_types': json.loads(row['cached_issue_types'] or '[]'),
                    'last_updated': row['last_updated'],
                    'cache_expires_at': row['cache_expires_at']
                }
            return None

    # CRUD operations for enhanced tasks
    def save_enhanced_task(self, task_data: Dict[str, Any]) -> str:
        """Save enhanced task to database."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO enhanced_tasks
                (id, original_task_data, project_key, connection_id, suggestions,
                 project_context_score, confidence_score, extracted_from, creation_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task_data['id'],
                json.dumps(task_data['original_task_data']),
                task_data['project_key'],
                task_data.get('connection_id'),
                json.dumps(task_data.get('suggestions', {})),
                task_data.get('project_context_score', 0.0),
                task_data.get('confidence_score', 0.0),
                task_data.get('extracted_from', ''),
                task_data.get('creation_status', 'pending')
            ))
            conn.commit()
            logger.info(f"Saved enhanced task: {task_data['id']}")
            return task_data['id']

    def update_task_jira_info(self, task_id: str, jira_issue_key: str, jira_url: str, status: str = 'created') -> None:
        """Update task with JIRA issue information."""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE enhanced_tasks
                SET jira_issue_key = ?, jira_url = ?, creation_status = ?, processed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (jira_issue_key, jira_url, status, task_id))
            conn.commit()

    # Performance tracking
    def record_performance_metric(self, operation_type: str, execution_time_ms: int,
                                 success: bool, connection_id: Optional[str] = None,
                                 project_key: Optional[str] = None, error_type: Optional[str] = None,
                                 metadata: Optional[Dict[str, Any]] = None) -> None:
        """Record performance metric."""
        metric_id = f"{operation_type}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO performance_metrics
                (id, operation_type, connection_id, project_key, execution_time_ms,
                 success, error_type, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metric_id, operation_type, connection_id, project_key, execution_time_ms,
                success, error_type, json.dumps(metadata or {})
            ))
            conn.commit()

    def get_performance_stats(self, operation_type: Optional[str] = None,
                            hours: int = 24) -> Dict[str, Any]:
        """Get performance statistics."""
        with self.get_connection() as conn:
            where_clause = "WHERE timestamp >= datetime('now', '-{} hours')".format(hours)
            if operation_type:
                where_clause += f" AND operation_type = '{operation_type}'"

            cursor = conn.execute(f"""
                SELECT
                    COUNT(*) as total_operations,
                    AVG(execution_time_ms) as avg_time_ms,
                    MIN(execution_time_ms) as min_time_ms,
                    MAX(execution_time_ms) as max_time_ms,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as error_count
                FROM performance_metrics
                {where_clause}
            """)

            result = cursor.fetchone()
            if result:
                total = result['total_operations']
                return {
                    'total_operations': total,
                    'avg_time_ms': round(result['avg_time_ms'] or 0, 2),
                    'min_time_ms': result['min_time_ms'] or 0,
                    'max_time_ms': result['max_time_ms'] or 0,
                    'success_count': result['success_count'],
                    'error_count': result['error_count'],
                    'success_rate': round((result['success_count'] / total * 100) if total > 0 else 0, 2),
                    'hours_analyzed': hours
                }

            return {
                'total_operations': 0,
                'avg_time_ms': 0,
                'min_time_ms': 0,
                'max_time_ms': 0,
                'success_count': 0,
                'error_count': 0,
                'success_rate': 0,
                'hours_analyzed': hours
            }

    def cleanup_old_data(self, days: int = 30) -> Dict[str, int]:
        """Clean up old data beyond specified days."""
        with self.get_connection() as conn:
            cutoff_date = f"datetime('now', '-{days} days')"

            # Clean performance metrics
            cursor = conn.execute(f"""
                DELETE FROM performance_metrics
                WHERE timestamp < {cutoff_date}
            """)
            performance_deleted = cursor.rowcount

            # Clean completed sessions
            cursor = conn.execute(f"""
                DELETE FROM processing_sessions
                WHERE completed_at IS NOT NULL AND completed_at < {cutoff_date}
            """)
            sessions_deleted = cursor.rowcount

            conn.commit()

            logger.info(f"Cleaned up {performance_deleted} performance metrics and {sessions_deleted} sessions")
            return {
                'performance_metrics_deleted': performance_deleted,
                'sessions_deleted': sessions_deleted
            }

    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self.get_connection() as conn:
            stats = {}

            # Table counts
            tables = ['jira_connections', 'project_contexts', 'enhanced_tasks',
                     'duplicate_analyses', 'performance_metrics', 'processing_sessions']

            for table in tables:
                try:
                    cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                    stats[f"{table}_count"] = cursor.fetchone()[0]
                except sqlite3.OperationalError:
                    stats[f"{table}_count"] = 0

            # Database file size
            stats['db_file_size_bytes'] = Path(self.db_path).stat().st_size if Path(self.db_path).exists() else 0
            stats['db_file_size_mb'] = round(stats['db_file_size_bytes'] / (1024 * 1024), 2)

            # Schema version
            stats['schema_version'] = self._get_schema_version(conn)

            return stats


# Global database manager instance
_db_manager = None

def get_database_manager() -> DatabaseManager:
    """Get global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager