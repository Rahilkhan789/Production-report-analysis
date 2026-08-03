"""
MCP server entrypoint for the Production Report application.

Exposes the existing Excel -> MongoDB -> Email -> Manifest pipeline
(production_analysis_mongodb.py, send_report_from_mongodb.py) as MCP tools,
so an AI assistant can drive the workflow by calling the existing code
instead of duplicating any business logic. This file only registers tools;
no report-processing logic lives here.
"""

import logging
import os

from fastmcp import FastMCP

from tools import excel_tools, report_tools, mongo_tools, email_tools

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

mcp = FastMCP("production-report-server")

excel_tools.register(mcp)
report_tools.register(mcp)
mongo_tools.register(mcp)
email_tools.register(mcp)


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))