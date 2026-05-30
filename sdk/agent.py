from __future__ import annotations

from typing import Any

"""
Base Agent class for the developer SDK.
"""

from tools.tool_executor import execute_tool


class Agent:
    """
    Base Agent that developers can subclass to implement custom behavior.

    Optional class attributes for monetization:
      price_per_run: float — charge per execution (e.g. 0.01); stored in agent_pricing when registered.
      currency: str — currency code (default "USD").

    Optional for edge execution:
      edge_compatible: bool — if True, this agent can run on edge workers (low-latency).

    Persistent memory (per agent, per project):
      Use self.memory_store(key, value) and self.memory_get(key) inside run(state).
      Memory persists across tasks and workflows; project_id comes from execution context.

    Organization knowledge graph (shared across agents):
      Use self.get_entity(entity_id) and self.find_related_entities(entity_id, ...) to query
      shared knowledge (company data, market insights, customer information).

    Autonomous workforce (agent-initiated workflows):
      Use self.emit_event(event_type, payload) to trigger event-driven workflows.
      Use self.enqueue_task(task, agent?) to enqueue a task directly.
      Override run_autonomous_cycle() to return task(s) to enqueue when run as an instance.
      All are subject to policy (which agents may launch, max frequency, limits).

    Multi-agent coordination (messages and delegation):
      Use self.send_message(target_agent_instance_id, message_type, payload) to send a message.
      Use self.get_pending_messages() to read messages for this instance.
      Use self.delegate_task(agent_name, task) to assign work to an instance of that agent.
      Override coordinate() to check messages, delegate tasks, and update shared knowledge.
    """

    name: str = ""
    tools: list = []
    price_per_run: float | None = None  # optional; when set, agent charges per execution
    edge_compatible: bool = False  # if True, scheduler prefers edge workers for this agent
    # Optional input_schema for user configuration: { "param": { "type": "string", "default": "...", "required": True } }
    input_schema: dict | None = None
    # Optional example_output for marketplace display (e.g. {"report": "..."})
    example_output: dict | None = None

    def __init__(self) -> None:
        # No required constructor parameters; subclasses can extend as needed.
        # Set by orchestrator before run() for memory context:
        self._memory_project_id: int | None = None
        # When running as a persistent agent instance, set for instance-scoped memory:
        self._memory_agent_instance_id: str | None = None

    def run(self, state):
        """
        Execute the agent given a state dictionary.
        Subclasses must override this method.
        """
        raise NotImplementedError("Agent.run must be implemented by subclasses.")

    def memory_store(self, key: str, value: str | dict | list) -> None:
        """
        Store a value in this agent's persistent memory for the current project.
        When running as an agent instance, memory is scoped to that instance (key prefix).
        Call from inside run(state). Value can be str, dict, or list (dict/list are JSON-serialized).
        """
        from database.agent_memory import store_memory
        store_memory(
            agent_name=self.name,
            project_id=getattr(self, "_memory_project_id", None),
            key=key,
            value=value,
            agent_instance_id=getattr(self, "_memory_agent_instance_id", None),
            simulation_id=getattr(self, "_memory_simulation_id", None),
        )

    def memory_get(self, key: str) -> str | None:
        """
        Retrieve a value from this agent's persistent memory for the current project.
        When running as an agent instance, uses instance-scoped memory.
        Call from inside run(state). Returns None if not found.
        """
        from database.agent_memory import retrieve_memory
        return retrieve_memory(
            agent_name=self.name,
            project_id=getattr(self, "_memory_project_id", None),
            key=key,
            agent_instance_id=getattr(self, "_memory_agent_instance_id", None),
            simulation_id=getattr(self, "_memory_simulation_id", None),
        )

    def memory_search(self) -> list[dict]:
        """
        Return all stored memory entries for this agent and current project (and instance if set).
        Each entry has keys: key, value, created_at. Call from inside run(state).
        """
        from database.agent_memory import search_memory
        return search_memory(
            agent_name=self.name,
            project_id=getattr(self, "_memory_project_id", None),
            agent_instance_id=getattr(self, "_memory_agent_instance_id", None),
            simulation_id=getattr(self, "_memory_simulation_id", None),
        )

    def get_entity(self, entity_id: str) -> dict | None:
        """
        Get an entity from the organization knowledge graph for the current project.
        Call from inside run(state). Returns dict with entity_id, entity_type, data, project_id, created_at,
        or None if not found.
        """
        from database.knowledge_graph import get_entity as kg_get_entity
        project_id = getattr(self, "_memory_project_id", None)
        if project_id is None:
            return None
        return kg_get_entity(entity_id, project_id, simulation_id=getattr(self, "_memory_simulation_id", None))

    def find_related_entities(
        self,
        entity_id: str,
        relationship: str | None = None,
        direction: str = "outgoing",
    ) -> list[dict]:
        """
        Find entities related to entity_id in the organization knowledge graph.
        direction: "outgoing" (this entity is source), "incoming" (this entity is target), or "both".
        Returns list of { related_entity_id, relationship, direction, entity? }.
        Call from inside run(state).
        """
        from database.knowledge_graph import find_related_entities as kg_find_related
        project_id = getattr(self, "_memory_project_id", None)
        if project_id is None:
            return []
        return kg_find_related(entity_id, project_id, relationship=relationship, direction=direction)

    def kg_upsert_entity(self, entity_id: str, entity_type: str, data: dict | str) -> None:
        """Upsert an entity into the organization knowledge graph for the current project. Call from run(state)."""
        from database.knowledge_graph import upsert_entity
        project_id = getattr(self, "_memory_project_id", None)
        if project_id is None:
            return
        upsert_entity(entity_id, entity_type, data, project_id, simulation_id=getattr(self, "_memory_simulation_id", None))

    def kg_add_edge(self, source_entity: str, target_entity: str, relationship: str) -> None:
        """Add a directed edge between two entities in the knowledge graph. Call from run(state)."""
        from database.knowledge_graph import add_edge
        project_id = getattr(self, "_memory_project_id", None)
        if project_id is None:
            return
        add_edge(source_entity, target_entity, relationship, project_id, simulation_id=getattr(self, "_memory_simulation_id", None))

    def emit_event(self, event_type: str, payload: dict) -> list[int]:
        """
        Emit an event that may trigger workflows (via event triggers). Subject to policy.
        Call from inside run(state). Returns list of enqueued task IDs, or [] if not allowed.
        """
        from database.autonomous_policies import record_launch_and_check, LAUNCH_SOURCE_AGENT
        from engine.event_engine import process_event
        project_id = getattr(self, "_memory_project_id", None)
        if project_id is None:
            return []
        if not record_launch_and_check(self.name, project_id, LAUNCH_SOURCE_AGENT):
            return []
        return process_event(event_type, payload or {}, project_id=project_id, source="agent")

    def enqueue_task(self, task: str | dict, agent: str | None = None) -> int | None:
        """
        Enqueue a task directly (agent-initiated). In simulation, enqueues to simulation_tasks.
        Call from inside run(state). Returns task_id or None if not allowed.
        """
        sim_id = getattr(self, "_memory_simulation_id", None)
        project_id = getattr(self, "_memory_project_id", None)
        if project_id is None:
            return None
        if sim_id is not None:
            from database.simulation import enqueue_simulation_task, update_simulation_metrics
            import json
            payload = {"task": task} if isinstance(task, str) else dict(task)
            if agent is not None:
                payload["agent"] = agent
            tid = enqueue_simulation_task(sim_id, json.dumps(payload))
            update_simulation_metrics(sim_id, workflows_executed=1)
            return tid
        from database.autonomous_policies import record_launch_and_check, LAUNCH_SOURCE_AGENT
        from services.task_service import enqueue_task as queue_enqueue
        if not record_launch_and_check(self.name, project_id, LAUNCH_SOURCE_AGENT):
            return None
        payload = {"task": task} if isinstance(task, str) else task
        if agent is not None:
            payload["agent"] = agent
        return queue_enqueue(payload, project_id=project_id)

    def run_autonomous_cycle(self) -> dict | list[dict] | None:
        """
        Override in subclasses to return task(s) to enqueue when run as an autonomous cycle.
        Called by the platform (e.g. POST /agent-instances/{id}/autonomous-cycle).
        Return None, a single task dict (e.g. {"task": "...", "agent": "..."}), or a list of task dicts.
        """
        return None

    def send_message(self, target_agent_instance: str, message_type: str, payload: Any = None) -> int | None:
        """
        Send a message to another agent instance. In simulation, only increments messages_sent.
        Call from inside run(state). Returns message id or None if sender is not an instance.
        """
        sim_id = getattr(self, "_memory_simulation_id", None)
        if sim_id is not None:
            from database.simulation import update_simulation_metrics
            update_simulation_metrics(sim_id, messages_sent=1)
            return 0
        from database.agent_messages import create_message
        from_inst = getattr(self, "_memory_agent_instance_id", None)
        if not from_inst:
            return None
        return create_message(
            from_agent_instance=from_inst,
            to_agent_instance=target_agent_instance.strip(),
            message_type=message_type.strip(),
            payload=payload,
        )

    def get_pending_messages(self) -> list[dict]:
        """
        Return pending messages for this agent instance. In simulation, returns [] (no production messages).
        """
        if getattr(self, "_memory_simulation_id", None) is not None:
            return []
        from database.agent_messages import get_pending_for_instance
        to_inst = getattr(self, "_memory_agent_instance_id", None)
        if not to_inst:
            return []
        return get_pending_for_instance(to_inst)

    def mark_message_processed(self, message_id: int) -> bool:
        """Mark a message as processed. Returns True if updated."""
        from database.agent_messages import mark_processed
        return mark_processed(message_id)

    def mark_message_delivered(self, message_id: int) -> bool:
        """Mark a message as delivered. Returns True if updated."""
        from database.agent_messages import mark_delivered
        return mark_delivered(message_id)

    def delegate_task(self, agent_name: str, task: str) -> int | None:
        """
        Delegate a task to an agent instance of the given type (e.g. data_agent).
        In simulation, enqueues to simulation_tasks and increments workflows_executed.
        """
        sim_id = getattr(self, "_memory_simulation_id", None)
        project_id = getattr(self, "_memory_project_id", None)
        if project_id is None:
            return None
        if sim_id is not None:
            from database.simulation import (
                list_instances_for_project_simulation,
                enqueue_simulation_task,
                update_simulation_metrics,
            )
            instances = list_instances_for_project_simulation(sim_id, project_id, agent_name=agent_name, limit=1)
            payload: dict = {"task": task, "agent": agent_name}
            if instances:
                payload["agent_instance_id"] = instances[0]["id"]
            import json
            task_id = enqueue_simulation_task(sim_id, json.dumps(payload))
            update_simulation_metrics(sim_id, workflows_executed=1)
            return task_id
        from database.autonomous_policies import record_launch_and_check, LAUNCH_SOURCE_AGENT
        from database.agent_instances import list_instances_for_project
        from services.task_service import enqueue_task as queue_enqueue
        if not record_launch_and_check(self.name, project_id, LAUNCH_SOURCE_AGENT):
            return None
        instances = list_instances_for_project(project_id, agent_name=agent_name, limit=1)
        payload = {"task": task, "agent": agent_name}
        if instances:
            payload["agent_instance_id"] = instances[0]["id"]
        return queue_enqueue(payload, project_id=project_id)

    def coordinate(self) -> None:
        """
        Override in subclasses to implement coordination: check messages, delegate tasks, update knowledge.
        Default: no-op. Called by the platform before run() when running as an instance (optional).
        Subclasses can call self.get_pending_messages(), process them, and self.delegate_task() or
        self.kg_upsert_entity() to collaborate with other agents.
        """
        pass

    def use_tool(self, tool_name, input_data):
        """
        Helper to execute a registered tool and return its result.
        """
        print(f"[Agent:{self.name}] Using tool: {tool_name}")
        return execute_tool(tool_name, input_data)


class ExampleAgent(Agent):

    name = "example_agent"
    tools = ["web_search"]

    def run(self, state):
        """
        Simple example agent that demonstrates how to call a tool
        from within an Agent subclass.
        """
        task = state.get("task")
        result = self.use_tool("web_search", task)
        return {"example_result": result}


