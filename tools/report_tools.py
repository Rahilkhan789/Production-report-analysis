"""
MCP tools for querying the currently loaded report (from shared state).

Depends on process_excel() having been called first (see excel_tools.py).
No business logic is duplicated from ExcelProcessor here - these are thin
read/filter operations over the ProductionRecord list it already produced.
"""

import logging
from typing import Dict, List, Optional

from production_analysis_mongodb import Priority
from services.report_state import state_manager

logger = logging.getLogger(__name__)


def _require_data() -> Optional[Dict]:
    """Returns an error dict if no report has been processed yet, else None."""
    if not state_manager.get_report().is_loaded():
        return {"error": "No report loaded. Call process_excel() first."}
    return None


def register(mcp):

    @mcp.tool()
    def get_summary() -> Dict:
        """
        Return aggregate statistics for the currently loaded report:
        total_records, total_quantity, total_clients, and a count of
        records per priority level.
        """
        err = _require_data()
        if err:
            return err

        records = state_manager.get_report().records

        priority_counts = {p.value: 0 for p in Priority}
        for r in records:
            priority_counts[r.priority] = priority_counts.get(r.priority, 0) + 1

        return {
            "total_records": len(records),
            "total_quantity": sum(r.quantity for r in records),
            "total_clients": len({r.client_name for r in records}),
            "highest_priority_count": priority_counts.get(Priority.HIGHEST.value, 0),
            "high_priority_count": priority_counts.get(Priority.HIGH.value, 0),
            "normal_priority_count": priority_counts.get(Priority.NORMAL.value, 0),
        }

    @mcp.tool()
    def list_clients() -> List[str]:
        """Return a sorted list of unique client names in the currently loaded report."""
        err = _require_data()
        if err:
            return [err["error"]]

        records = state_manager.get_report().records
        return sorted({r.client_name for r in records})

    @mcp.tool()
    def get_client_report(client_name: str) -> Dict:
        """
        Return every item, quantity, and priority for a given client, plus totals.

        Args:
            client_name: Exact client name as it appears in list_clients().
        """
        err = _require_data()
        if err:
            return err

        records = state_manager.get_report().records
        matches = [r for r in records if r.client_name == client_name]

        if not matches:
            return {"error": f"No records found for client '{client_name}'. Use list_clients() to see valid names."}

        return {
            "client_name": client_name,
            "items": [
                {
                    "item_description": r.item_description,
                    "quantity": r.quantity,
                    "priority": r.priority,
                }
                for r in matches
            ],
            "total_items": len(matches),
            "total_quantity": sum(r.quantity for r in matches),
        }

    @mcp.tool()
    def get_highest_priority_jobs() -> List[Dict]:
        """Return all records in the currently loaded report flagged as Highest Priority."""
        err = _require_data()
        if err:
            return [err]

        records = state_manager.get_report().records
        return [r.to_dict() for r in records if r.priority == Priority.HIGHEST.value]

    @mcp.tool()
    def get_high_priority_jobs() -> List[Dict]:
        """Return all records in the currently loaded report flagged as High Priority."""
        err = _require_data()
        if err:
            return [err]

        records = state_manager.get_report().records
        return [r.to_dict() for r in records if r.priority == Priority.HIGH.value]

    @mcp.tool()
    def search_item(item_description: str) -> List[Dict]:
        """
        Case-insensitive substring search over item descriptions in the
        currently loaded report.

        Args:
            item_description: Text to search for within item descriptions.
        """
        err = _require_data()
        if err:
            return [err]

        query = item_description.lower().strip()
        records = state_manager.get_report().records

        return [r.to_dict() for r in records if query in r.item_description.lower()]
