#!/usr/bin/env python3
"""
Gemini CLI MCP Server for OpenTaxCopilot.

This Model Context Protocol (MCP) server integrates Google's Gemini CLI
for Google product expertise, tax-related research, and technical consultation.

Use this server for:
- All matters related to Google products and frameworks (ADK, Vertex AI, Gemini models)
- Troubleshooting Google product/framework errors
- Tax authority API research and integration guidance
- Security review of Google Cloud configurations

Supports both stdio and HTTP modes for use with Claude Code and other MCP clients.

IMPORTANT: Must run on host system, not in containers (Gemini CLI requires Docker access).

Usage:
    # Stdio mode (for Claude Desktop)
    python server.py --mode stdio

    # HTTP mode (for development/testing)
    python server.py --mode http --port 8006

Configuration:
    Create .env file or set environment variables:
    - GEMINI_ENABLED=true
    - GEMINI_TIMEOUT=300
    - GEMINI_RATE_LIMIT=2
    - GEMINI_DAILY_LIMIT=250 (daily request quota)
"""

import asyncio
import json
import subprocess
import sys
import os
import logging
from datetime import datetime
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("gemini-mcp")

# Configuration
GEMINI_ENABLED = os.environ.get("GEMINI_ENABLED", "true").lower() == "true"
GEMINI_TIMEOUT = int(os.environ.get("GEMINI_TIMEOUT", "300"))
GEMINI_RATE_LIMIT = int(os.environ.get("GEMINI_RATE_LIMIT", "2"))
GEMINI_DAILY_LIMIT = int(os.environ.get("GEMINI_DAILY_LIMIT", "250"))
GEMINI_OUTPUT_FORMAT = "json"

# Import quota manager
from quota_manager import get_quota_manager


@dataclass
class ConsultationResult:
    """Result from a Gemini consultation."""
    consultation_id: str
    query: str
    response: str
    execution_time: float
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    error: Optional[str] = None


class GeminiMCPServer:
    """
    MCP Server wrapping Gemini CLI for OpenTaxCopilot.

    Provides tools for:
    - Google ADK and Gemini model consultation
    - Tax authority research and grounding
    - Google Cloud configuration review
    - Security review for Google integrations
    - General Gemini consultation
    """

    def __init__(self):
        self.consultation_history: List[ConsultationResult] = []
        self.auto_consult = os.environ.get("GEMINI_AUTO_CONSULT", "false").lower() == "true"
        self.quota_manager = get_quota_manager(
            location_id="claude",
            daily_limit=GEMINI_DAILY_LIMIT
        )
        self.tools = {
            "consult_gemini": {
                "description": "Get AI assistance from Gemini for Google products, frameworks, ADK, Vertex AI, Gemini models, or tax-related technical queries",
                "parameters": {
                    "query": {"type": "string", "description": "The question or task for Gemini"},
                    "context": {"type": "string", "description": "Additional context (optional)"},
                    "all_files": {"type": "boolean", "description": "Analyze entire codebase (default: false)"}
                }
            },
            "analyze_google_integration": {
                "description": "Analyze codebase for Google ADK, Gemini API, or Vertex AI integration issues",
                "parameters": {
                    "focus": {"type": "string", "description": "Focus area: adk, vertex_ai, gemini_models, search_grounding, all"}
                }
            },
            "research_tax_authority_api": {
                "description": "Research tax authority APIs and official portals for a specific jurisdiction",
                "parameters": {
                    "jurisdiction": {"type": "string", "description": "Country or region code (e.g., US, GB, CA, AU)"},
                    "topic": {"type": "string", "description": "Specific topic (e.g., filing API, tax rates, deadlines)"}
                }
            },
            "troubleshoot_google_error": {
                "description": "Troubleshoot errors related to Google products/frameworks (ADK, Vertex AI, Gemini, Cloud)",
                "parameters": {
                    "error_message": {"type": "string", "description": "The error message or stack trace"},
                    "context": {"type": "string", "description": "What you were trying to do when the error occurred"}
                }
            },
            "security_review": {
                "description": "Run security review on Google Cloud configurations and API key usage",
                "parameters": {
                    "target": {"type": "string", "description": "File or directory to review"},
                    "focus": {"type": "string", "description": "Security focus: api_keys, iam, credentials, all"}
                }
            },
            "gemini_status": {
                "description": "Get Gemini CLI integration status and statistics",
                "parameters": {}
            },
            "gemini_quota_status": {
                "description": "Get daily quota status (requests made, remaining, limit)",
                "parameters": {}
            },
            "clear_gemini_history": {
                "description": "Clear consultation history for fresh start",
                "parameters": {}
            },
            "toggle_gemini_auto_consult": {
                "description": "Enable/disable automatic consultation on uncertainty detection",
                "parameters": {
                    "enabled": {"type": "boolean", "description": "Enable auto-consultation"}
                }
            }
        }

    async def consult_gemini(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get AI assistance from Gemini."""
        query = params.get("query", "")
        context = params.get("context", "")
        all_files = params.get("all_files", False)

        if not GEMINI_ENABLED:
            return {"error": "Gemini integration is disabled"}

        full_prompt = f"{context}\n\n{query}" if context else query

        escaped_prompt = full_prompt.replace("'", "'\"'\"'")
        flags = "--all-files" if all_files else ""
        result = await self._run_gemini(f"{flags} '{escaped_prompt}'", query=query)

        consultation = ConsultationResult(
            consultation_id=f"consult_{len(self.consultation_history) + 1}",
            query=query,
            response=result,
            execution_time=0.0
        )
        self.consultation_history.append(consultation)

        return {
            "consultation_id": consultation.consultation_id,
            "response": result,
            "timestamp": consultation.timestamp
        }

    async def analyze_google_integration(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze codebase for Google integration issues."""
        focus = params.get("focus", "all")

        focus_prompts = {
            "adk": "Analyze this OpenTaxCopilot codebase for Google ADK (Agent Development Kit) integration patterns, compatibility issues, and best practices",
            "vertex_ai": "Analyze this codebase for Vertex AI integration, focusing on model deployment, authentication, and API usage patterns",
            "gemini_models": "Analyze this codebase for Gemini model usage (gemini-3.1-pro, gemini-2.5-flash-lite, gemini-2.5-flash-live, computer-use-preview), checking configuration and API call patterns",
            "search_grounding": "Analyze this codebase for Google Search Grounding integration for real-time tax code retrieval from official government portals",
            "all": """Analyze this OpenTaxCopilot codebase for Google product integration. Identify:
1. Google ADK compatibility and agent orchestration patterns
2. Gemini model configuration (3.1 Pro, 2.5 Flash-Lite, 2.5 Flash Live, Computer Use)
3. Vertex AI vs AI Studio authentication setup
4. Google Search Grounding for tax authority queries
5. Google Drive API integration for document management
6. Google Calendar API integration"""
        }

        prompt = focus_prompts.get(focus, focus_prompts["all"])
        escaped_prompt = prompt.replace("'", "'\"'\"'")
        result = await self._run_gemini(f"--all-files '{escaped_prompt}'")

        return {
            "focus": focus,
            "analysis": result
        }

    async def research_tax_authority_api(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Research tax authority APIs for a jurisdiction."""
        jurisdiction = params.get("jurisdiction", "US")
        topic = params.get("topic", "general")

        prompt = f"""Research the official tax authority APIs and digital services for {jurisdiction}.
Focus on: {topic}

Include:
- Official API endpoints (if they exist)
- Authentication methods
- Data formats accepted
- Rate limits and quotas
- Developer documentation links
- Any open-source client libraries
- Filing deadlines for the current tax year"""

        escaped_prompt = prompt.replace("'", "'\"'\"'")
        result = await self._run_gemini(f"'{escaped_prompt}'")

        return {
            "jurisdiction": jurisdiction,
            "topic": topic,
            "research": result
        }

    async def troubleshoot_google_error(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Troubleshoot Google product/framework errors."""
        error_message = params.get("error_message", "")
        context = params.get("context", "")

        prompt = f"""Troubleshoot this Google product/framework error in the context of OpenTaxCopilot (a Python FastAPI application using Google ADK and Gemini models):

Error: {error_message}

Context: {context}

Provide:
1. Root cause analysis
2. Step-by-step fix
3. Prevention measures
4. Related documentation links"""

        escaped_prompt = prompt.replace("'", "'\"'\"'")
        result = await self._run_gemini(f"'{escaped_prompt}'", query=f"troubleshoot: {error_message[:50]}")

        return {
            "error": error_message,
            "context": context,
            "troubleshooting": result
        }

    async def security_review(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run security review on Google Cloud configurations."""
        target = params.get("target", ".")
        focus = params.get("focus", "all")

        focus_prompts = {
            "api_keys": "exposed API keys, Gemini/Google Cloud credentials, service account keys",
            "iam": "IAM roles, permissions, service accounts for Vertex AI and Google Cloud",
            "credentials": "credential storage patterns, .env file security, GOOGLE_APPLICATION_CREDENTIALS handling",
            "all": "API keys, IAM permissions, credential storage, network security, and input validation for Google Cloud integrations"
        }

        focus_str = focus_prompts.get(focus, focus_prompts["all"])

        security_prompt = f"Review {target} for security issues focusing on: {focus_str}"
        escaped_security_prompt = security_prompt.replace("'", "'\"'\"'")
        result = await self._run_gemini(f"'{escaped_security_prompt}'")

        return {
            "target": target,
            "focus": focus,
            "security_findings": result
        }

    async def gemini_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Returns Gemini integration status."""
        quota_status = self.quota_manager.get_status()
        return {
            "enabled": GEMINI_ENABLED,
            "model": "CLI default (auto-select)",
            "output_format": GEMINI_OUTPUT_FORMAT,
            "timeout": GEMINI_TIMEOUT,
            "auto_consult": self.auto_consult,
            "consultations_count": len(self.consultation_history),
            "last_consultation": self.consultation_history[-1].timestamp if self.consultation_history else None,
            "quota": quota_status
        }

    async def gemini_quota_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Returns daily quota status."""
        return self.quota_manager.get_status()

    async def clear_gemini_history(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Clears consultation history."""
        count = len(self.consultation_history)
        self.consultation_history = []
        return {
            "cleared": True,
            "consultations_cleared": count
        }

    async def toggle_gemini_auto_consult(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Toggles auto-consultation."""
        enabled = params.get("enabled", not self.auto_consult)
        self.auto_consult = enabled
        return {
            "auto_consult": self.auto_consult
        }

    async def _run_gemini(self, args: str, query: str = None) -> str:
        """Execute Gemini CLI command with quota enforcement."""
        if not self.quota_manager.can_make_request():
            fallback = self.quota_manager.get_fallback_response(query or args)
            logger.warning(f"Quota exceeded: {fallback['quota_status']}")
            return json.dumps(fallback, indent=2)

        try:
            full_args = f"--output-format {GEMINI_OUTPUT_FORMAT} {args}"
            logger.info(f"Executing: gemini {full_args}")
            logger.info(f"Quota status: {self.quota_manager.get_remaining()} requests remaining")

            process = await asyncio.create_subprocess_shell(
                f"gemini {full_args}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=GEMINI_TIMEOUT
            )

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(f"Gemini CLI error: {error_msg}")
                self.quota_manager.record_request(query=query, success=False)
                return f"Error: {error_msg}"

            result = stdout.decode()
            logger.info(f"Gemini response: {len(result)} characters")
            self.quota_manager.record_request(query=query, success=True)
            return result

        except asyncio.TimeoutError:
            logger.error(f"Gemini CLI timed out after {GEMINI_TIMEOUT}s")
            self.quota_manager.record_request(query=query, success=False)
            return f"Error: Gemini CLI timed out after {GEMINI_TIMEOUT} seconds"

        except FileNotFoundError:
            logger.error("Gemini CLI not found")
            return "Error: Gemini CLI not found. Install with: npm install -g @google/gemini-cli"

        except Exception as e:
            logger.error(f"Gemini CLI exception: {e}")
            self.quota_manager.record_request(query=query, success=False)
            return f"Error: {str(e)}"

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handles incoming MCP requests."""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        logger.info(f"Handling request: {method}")

        if method == "tools/list":
            return {
                "id": request_id,
                "result": {
                    "tools": [
                        {
                            "name": name,
                            "description": tool["description"],
                            "inputSchema": {
                                "type": "object",
                                "properties": tool["parameters"]
                            }
                        }
                        for name, tool in self.tools.items()
                    ]
                }
            }

        if method == "tools/call":
            tool_name = params.get("name")
            tool_params = params.get("arguments", {})

            tool_methods = {
                "consult_gemini": self.consult_gemini,
                "analyze_google_integration": self.analyze_google_integration,
                "research_tax_authority_api": self.research_tax_authority_api,
                "troubleshoot_google_error": self.troubleshoot_google_error,
                "security_review": self.security_review,
                "gemini_status": self.gemini_status,
                "gemini_quota_status": self.gemini_quota_status,
                "clear_gemini_history": self.clear_gemini_history,
                "toggle_gemini_auto_consult": self.toggle_gemini_auto_consult
            }

            if tool_name in tool_methods:
                result = await tool_methods[tool_name](tool_params)
                return {
                    "id": request_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": json.dumps(result, indent=2)}
                        ]
                    }
                }

            return {
                "id": request_id,
                "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}
            }

        if method == "initialize":
            return {
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "gemini-mcp",
                        "version": "1.0.0"
                    }
                }
            }

        return {
            "id": request_id,
            "error": {"code": -32601, "message": f"Unknown method: {method}"}
        }


async def run_stdio():
    """Run server in stdio mode for Claude Desktop integration."""
    server = GeminiMCPServer()
    logger.info("Starting Gemini MCP Server in stdio mode")

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                logger.info("EOF received, shutting down")
                break

            request = json.loads(line.strip())
            response = await server.handle_request(request)
            print(json.dumps(response), flush=True)

        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON: {e}")
            continue

        except Exception as e:
            logger.error(f"Error handling request: {e}")
            error_response = {
                "error": {"code": -32603, "message": str(e)}
            }
            print(json.dumps(error_response), flush=True)


async def run_http(port: int = 8006):
    """Run server in HTTP mode for development/testing."""
    try:
        from fastapi import FastAPI, Request
        import uvicorn
    except ImportError:
        logger.error("FastAPI/uvicorn not installed. Run: pip install fastapi uvicorn")
        return

    app = FastAPI(title="Gemini MCP Server - OpenTaxCopilot")
    server = GeminiMCPServer()

    @app.post("/")
    async def handle_mcp(request: Request):
        body = await request.json()
        return await server.handle_request(body)

    @app.get("/health")
    async def health():
        return {"status": "healthy", "gemini_enabled": GEMINI_ENABLED}

    logger.info(f"Starting Gemini MCP Server in HTTP mode on port {port}")
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server_instance = uvicorn.Server(config)
    await server_instance.serve()


def main():
    parser = argparse.ArgumentParser(description="Gemini CLI MCP Server - OpenTaxCopilot")
    parser.add_argument("--mode", choices=["stdio", "http"], default="stdio",
                        help="Server mode (stdio for Claude Desktop, http for testing)")
    parser.add_argument("--port", type=int, default=8006,
                        help="HTTP port (only for http mode)")

    args = parser.parse_args()

    if args.mode == "stdio":
        asyncio.run(run_stdio())
    else:
        asyncio.run(run_http(args.port))


if __name__ == "__main__":
    main()
