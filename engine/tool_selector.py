from __future__ import annotations

from typing import List

from registry.tool_registry import tool_registry


def select_tools(task_description: str) -> List[str]:
    """
    Very simple rule-based tool selection.

    Returns a list of tool names based on keywords in the task description.
    """
    description_lc = (task_description or "").lower()

    selected: List[str] = []

    # Rule 1: research/market/startup/trend/analysis -> web_search, analysis_tool
    if any(
        word in description_lc
        for word in ("research", "market", "startup", "trend", "analysis")
    ):
        selected.append("web_search")
        selected.append("analysis_tool")

    # Rule 2: website/url/scrape -> web_scraper
    if any(word in description_lc for word in ("website", "url", "scrape")):
        selected.append("web_scraper")

    # Rule 3: file/document -> file_reader
    if any(word in description_lc for word in ("file", "document")):
        selected.append("file_reader")

    # Ensure uniqueness and preserve order
    seen = set()
    unique_selected: List[str] = []
    for name in selected:
        if name not in seen:
            seen.add(name)
            unique_selected.append(name)

    # Rule 4: default to web_search if nothing matched
    if not unique_selected:
        return ["web_search"]

    return unique_selected


if __name__ == "__main__":
    tools = select_tools("research AI startup market")
    print("Selected tools:", tools)

