"""
kc_mcp_modbus — MCP Server Entry Point
MCP Server 進入點，啟動 FastMCP HTTP server。
"""

import os
import logging

from dotenv import load_dotenv

from src.tools import init_tools

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("mcp-server")

PROFILE_PATH = os.getenv("MODBUS_PROFILE", "devices.yaml")
MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.getenv("MCP_PORT", "8765"))


def main():
    mcp = init_tools(PROFILE_PATH)
    log.info(f"Loaded profile: {PROFILE_PATH}")
    log.info(f"Starting MCP Server on {MCP_HOST}:{MCP_PORT}")
    mcp.run(transport="streamable-http", host=MCP_HOST, port=MCP_PORT)


if __name__ == "__main__":
    main()
