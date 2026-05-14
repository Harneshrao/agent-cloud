from __future__ import annotations

from typing import Any, Dict, List

from agentcloud_sdk.agent import AgentBase, AgentContext


class CompetitorIntelligenceAgent(AgentBase):
    name = "Competitor Intelligence Agent"
    description = "Monitors competitor websites for content and pricing changes."
    version = "1.0.0"
    inputs = {"urls": list}
    tags = ["monitoring", "competitive-intel", "web"]

    async def run(self, inputs: Dict[str, Any], ctx: AgentContext) -> Dict[str, Any]:
        urls: List[str] = list(inputs.get("urls") or [])
        ctx.logger.info("competitor_scan_started", urls=urls)

        changes: List[Dict[str, Any]] = []

        # NOTE: This is a placeholder implementation. It demonstrates how an
        # agent would use logging and memory, without doing real HTTP fetching.
        for url in urls:
            # Retrieve last snapshot from long-term memory (if any)
            history = ctx.memory.query_long(namespace=url, limit=1)
            last = history[-1] if history else None

            # Fake "current" snapshot; in a real implementation this would be
            # derived from an HTTP fetch + parsing.
            current_snapshot = {
                "url": url,
                "price": None,
                "content_hash": "placeholder",
            }

            price_changed = False
            old_price = last.get("price") if last else None
            new_price = current_snapshot["price"]

            if last is None or old_price != new_price:
                price_changed = True

            change = {
                "url": url,
                "price_changed": price_changed,
                "old_price": old_price,
                "new_price": new_price,
                "content_diff": None,
            }
            changes.append(change)

            # Append snapshot to long-term memory for future comparisons.
            ctx.memory.append_long(namespace=url, data=current_snapshot)

        summary = f"Scanned {len(urls)} competitor site(s)."
        ctx.memory.append_long(namespace="summary", data={"summary": summary, "urls": urls})
        ctx.logger.info("competitor_scan_completed", summary=summary, changes=len(changes))

        return {"summary": summary, "changes": changes}

