#!/bin/bash
# Setup script for ArchIntel web app workspace
# Run this in the web app project directory

echo "=== Setting up MCP servers for ArchIntel ==="

# Add Supabase MCP
claude mcp add --scope project --transport http supabase "https://mcp.supabase.com/mcp"

# Add Vercel MCP
claude mcp add --transport http vercel https://mcp.vercel.com

echo "=== MCP servers configured ==="
echo "Run 'claude /mcp' to authenticate each server"
echo ""
echo "=== Gemini API Key ==="
echo "The Gemini API key is set in .env.local as GOOGLE_GENERATIVE_AI_API_KEY"
echo "The Vercel AI SDK reads this automatically via @ai-sdk/google"
