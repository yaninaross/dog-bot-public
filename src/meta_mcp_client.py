import os
import requests
import json

class MetaSocialMCPClient:
    """
    Client for Meta Social Technologies MCP (Model Context Protocol) Server
    Endpoint: https://mcp.facebook.com/devtools
    """
    def __init__(self, endpoint_url: str = "https://mcp.facebook.com/devtools", access_token: str = None):
        self.endpoint_url = endpoint_url
        self.access_token = access_token or os.environ.get("META_ACCESS_TOKEN")

    def call_mcp_tool(self, tool_name: str, arguments: dict = None) -> dict:
        headers = {
            "Content-Type": "application/json"
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments or {}
            }
        }

        try:
            res = requests.post(self.endpoint_url, json=payload, headers=headers, timeout=8)
            print(f" [Meta MCP] Executed tool '{tool_name}' -> Status {res.status_code}")
            if res.status_code == 200:
                return res.json()
            else:
                return {"status": res.status_code, "raw_response": res.text}
        except Exception as e:
            return {"error": str(e)}

    def list_apps(self) -> dict:
        """
        Executes devtools_app_list via Meta Social Technologies MCP.
        """
        return self.call_mcp_tool("devtools_app_list")

    def search_docs(self, query: str) -> dict:
        """
        Executes devtools_discovery (Search Meta Developer Documentation) via Meta MCP.
        """
        return self.call_mcp_tool("devtools_discovery", {"query": query})
