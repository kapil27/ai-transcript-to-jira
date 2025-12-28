"""MCP (Model Context Protocol) client utilities for enhanced JIRA integration."""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime, timedelta


logger = logging.getLogger(__name__)


@dataclass
class MCPResponse:
    """Response from MCP server."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    status_code: int = 200
    response_time_ms: int = 0


class MCPClientError(Exception):
    """Custom exception for MCP client errors."""
    pass


class MCPClient:
    """Async client for MCP protocol communication."""

    def __init__(self,
                 server_url: str = "http://localhost:3000/mcp",
                 timeout: int = 30,
                 max_retries: int = 3):
        """Initialize MCP client."""
        self.server_url = server_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _ensure_session(self):
        """Ensure aiohttp session is available."""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(limit=10, ttl_dns_cache=300)
            timeout_config = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout_config,
                headers={'Content-Type': 'application/json'}
            )

    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _make_request(self,
                          method: str,
                          endpoint: str,
                          data: Optional[Dict] = None) -> MCPResponse:
        """Make an HTTP request to MCP server with retries."""
        await self._ensure_session()

        url = f"{self.server_url}/{endpoint.lstrip('/')}"
        start_time = datetime.now()

        for attempt in range(self.max_retries + 1):
            try:
                async with self._session.request(method, url, json=data) as response:
                    response_time = (datetime.now() - start_time).total_seconds() * 1000

                    if response.status == 200:
                        response_data = await response.json()
                        return MCPResponse(
                            success=True,
                            data=response_data,
                            status_code=response.status,
                            response_time_ms=int(response_time)
                        )
                    else:
                        error_text = await response.text()
                        logger.warning(f"MCP request failed with status {response.status}: {error_text}")

                        if attempt < self.max_retries:
                            await asyncio.sleep(2 ** attempt)  # Exponential backoff
                            continue

                        return MCPResponse(
                            success=False,
                            error=f"HTTP {response.status}: {error_text}",
                            status_code=response.status,
                            response_time_ms=int(response_time)
                        )

            except asyncio.TimeoutError:
                logger.warning(f"MCP request timeout on attempt {attempt + 1}")
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return MCPResponse(
                    success=False,
                    error=f"Request timeout after {self.timeout} seconds"
                )

            except Exception as e:
                logger.error(f"MCP request error on attempt {attempt + 1}: {str(e)}")
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return MCPResponse(
                    success=False,
                    error=f"Request failed: {str(e)}"
                )

        return MCPResponse(
            success=False,
            error=f"Max retries ({self.max_retries}) exceeded"
        )

    async def get_tools(self) -> MCPResponse:
        """Get available MCP tools."""
        return await self._make_request("GET", "/tools")

    async def call_tool(self,
                       tool_name: str,
                       arguments: Dict[str, Any]) -> MCPResponse:
        """Call a specific MCP tool with arguments."""
        data = {
            "name": tool_name,
            "arguments": arguments
        }
        return await self._make_request("POST", "/tools/call", data)

    async def health_check(self) -> MCPResponse:
        """Check MCP server health."""
        return await self._make_request("GET", "/health")


class JiraMCPClient(MCPClient):
    """Specialized MCP client for JIRA operations."""

    def __init__(self, *args, **kwargs):
        """Initialize JIRA MCP client."""
        super().__init__(*args, **kwargs)

    async def authenticate_jira(self,
                              base_url: str,
                              username: str,
                              api_token: str) -> MCPResponse:
        """Authenticate with JIRA via MCP."""
        arguments = {
            "base_url": base_url,
            "username": username,
            "api_token": api_token
        }
        return await self.call_tool("jira_authenticate", arguments)

    async def get_projects(self, connection_id: str) -> MCPResponse:
        """Get JIRA projects via MCP."""
        arguments = {"connection_id": connection_id}
        return await self.call_tool("jira_get_projects", arguments)

    async def get_project_context(self,
                                connection_id: str,
                                project_key: str) -> MCPResponse:
        """Get comprehensive project context via MCP."""
        arguments = {
            "connection_id": connection_id,
            "project_key": project_key
        }
        return await self.call_tool("jira_get_project_context", arguments)

    async def search_issues(self,
                          connection_id: str,
                          project_key: str,
                          query: str,
                          max_results: int = 50) -> MCPResponse:
        """Search for issues via MCP."""
        arguments = {
            "connection_id": connection_id,
            "project_key": project_key,
            "query": query,
            "max_results": max_results
        }
        return await self.call_tool("jira_search_issues", arguments)

    async def create_issue(self,
                         connection_id: str,
                         issue_data: Dict[str, Any]) -> MCPResponse:
        """Create JIRA issue via MCP."""
        arguments = {
            "connection_id": connection_id,
            "issue_data": issue_data
        }
        return await self.call_tool("jira_create_issue", arguments)

    async def get_issue_types(self,
                            connection_id: str,
                            project_key: str) -> MCPResponse:
        """Get issue types for project via MCP."""
        arguments = {
            "connection_id": connection_id,
            "project_key": project_key
        }
        return await self.call_tool("jira_get_issue_types", arguments)

    async def get_sprints(self,
                        connection_id: str,
                        board_id: int) -> MCPResponse:
        """Get sprints for board via MCP."""
        arguments = {
            "connection_id": connection_id,
            "board_id": board_id
        }
        return await self.call_tool("jira_get_sprints", arguments)

    async def get_epics(self,
                      connection_id: str,
                      project_key: str) -> MCPResponse:
        """Get epics for project via MCP."""
        arguments = {
            "connection_id": connection_id,
            "project_key": project_key
        }
        return await self.call_tool("jira_get_epics", arguments)


class MCPFallbackClient:
    """Fallback client that mimics MCP interface but uses direct HTTP calls.

    Used when MCP server is not available or for development/testing.
    """

    def __init__(self,
                 jira_base_url: str,
                 username: str,
                 api_token: str,
                 timeout: int = 30):
        """Initialize fallback client with direct JIRA credentials."""
        self.jira_base_url = jira_base_url.rstrip('/')
        self.username = username
        self.api_token = api_token
        self.timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _ensure_session(self):
        """Ensure aiohttp session is available."""
        if self._session is None or self._session.closed:
            auth = aiohttp.BasicAuth(self.username, self.api_token)
            connector = aiohttp.TCPConnector(limit=10)
            timeout_config = aiohttp.ClientTimeout(total=self.timeout)

            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout_config,
                auth=auth,
                headers={'Content-Type': 'application/json'}
            )

    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _jira_request(self,
                          endpoint: str,
                          method: str = "GET",
                          data: Optional[Dict] = None) -> MCPResponse:
        """Make direct JIRA REST API call."""
        await self._ensure_session()

        url = f"{self.jira_base_url}/rest/api/3/{endpoint.lstrip('/')}"
        start_time = datetime.now()

        try:
            async with self._session.request(method, url, json=data) as response:
                response_time = (datetime.now() - start_time).total_seconds() * 1000

                if response.status == 200:
                    response_data = await response.json()
                    return MCPResponse(
                        success=True,
                        data=response_data,
                        status_code=response.status,
                        response_time_ms=int(response_time)
                    )
                else:
                    error_text = await response.text()
                    return MCPResponse(
                        success=False,
                        error=f"JIRA API error {response.status}: {error_text}",
                        status_code=response.status,
                        response_time_ms=int(response_time)
                    )

        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            return MCPResponse(
                success=False,
                error=f"Request failed: {str(e)}",
                response_time_ms=int(response_time)
            )

    async def authenticate_jira(self, base_url: str, username: str, api_token: str) -> MCPResponse:
        """Test JIRA authentication."""
        # Simply test with a basic API call
        return await self._jira_request("myself")

    async def get_projects(self, connection_id: str = None) -> MCPResponse:
        """Get JIRA projects directly."""
        return await self._jira_request("project")

    async def get_project_context(self, connection_id: str, project_key: str) -> MCPResponse:
        """Get project details directly."""
        return await self._jira_request(f"project/{project_key}")

    async def search_issues(self, connection_id: str, project_key: str, query: str, max_results: int = 50) -> MCPResponse:
        """Search issues using JQL."""
        jql = f"project = {project_key} AND text ~ \"{query}\""
        params = {
            "jql": jql,
            "maxResults": max_results,
            "fields": "key,summary,description,status,assignee,issuetype"
        }

        # Convert to query string for GET request
        endpoint = "search"
        return await self._jira_request(endpoint, data=params)

    async def create_issue(self, connection_id: str, issue_data: Dict[str, Any]) -> MCPResponse:
        """Create JIRA issue directly."""
        return await self._jira_request("issue", method="POST", data=issue_data)


# Utility functions for sync/async bridge

def run_mcp_operation(coro):
    """Run MCP operation in sync context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)


async def test_mcp_connection(server_url: str) -> bool:
    """Test if MCP server is available."""
    try:
        async with MCPClient(server_url, timeout=5) as client:
            response = await client.health_check()
            return response.success
    except Exception:
        return False


def get_mcp_client(config) -> Union[JiraMCPClient, MCPFallbackClient]:
    """Factory function to get appropriate MCP client based on availability."""
    # For now, always return fallback client since MCP servers aren't widely available
    # This can be enhanced later to check for actual MCP server availability

    if (hasattr(config, 'jira') and
        config.jira.base_url and
        config.jira.username and
        config.jira.api_token):

        return MCPFallbackClient(
            jira_base_url=config.jira.base_url,
            username=config.jira.username,
            api_token=config.jira.api_token,
            timeout=getattr(config.jira, 'timeout', 30)
        )
    else:
        # Return MCP client for future use
        mcp_url = getattr(config.mcp, 'atlassian_server_url', 'http://localhost:3000/mcp')
        return JiraMCPClient(
            server_url=mcp_url,
            timeout=getattr(config.mcp, 'connection_timeout', 30)
        )