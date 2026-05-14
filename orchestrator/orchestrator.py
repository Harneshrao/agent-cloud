import shutil
import copy
import uuid

from agents.loader import load_agents
from orchestrator.router import route_task, build_dag
from orchestrator.capability_index import build_index
from orchestrator.task_manager import collect_subtasks_from_output, enqueue_subtasks
from orchestrator.workflow_controller import check_task_completion
from memory.memory_engine import store_memory, search_memory
from engine.parallel_executor import run_parallel_agents
from engine.execution_tracker import start_agent, finish_agent, fail_agent
from engine.tool_executor import run_agent_tools
from engine.stream_store import append_event
from tools.loader import load_tools
from database.db import db
from database.agent_messages import get_pending_for_instance, mark_delivered
from registry.agent_registry import agent_registry


def _consume_agent_stream(gen, task_id):
    """Consume a generator from agent.run(), append each event to stream_store, return final value."""
    final = None
    try:
        while True:
            event = next(gen)
            if task_id is not None and isinstance(event, dict):
                append_event(task_id, event)
    except StopIteration as e:
        final = e.value
    return final


def run_single_agent_node(
    task_id: uuid.UUID,
    task: str,
    agent_name: str,
    agent_instance_id: str | None = None,
    instance_state: dict | None = None,
):
    """
    Run a single DAG node (one agent). Used for distributed workflow execution.
    When agent_instance_id is set, memory is scoped to that instance and instance_state is merged into state.
    Returns the agent result. Does not store_result or check_task_completion; caller (worker) handles that.
    """
    load_agents()
    load_tools()
    project_id = db.get_task_project_id(task_id) if task_id else None
    state = {
        "task_id": task_id,
        "task": task,
        "project_id": project_id,
        "agent_outputs": {},
        "memory": [],
        "logs": [],
        "metadata": {},
    }
    if instance_state:
        state["agent_instance_state"] = instance_state
        state.update(instance_state)
    start_agent(agent_name, task_id)
    agent_instance = agent_registry.get_agent(agent_name)
    if agent_instance is None:
        # Try deployed (marketplace) agent: load package, run in runtime
        try:
            from database.developer_economy import get_published_agent_by_name, get_latest_version
            from agent_runtime.package_loader import load_agent_package
            from agent_runtime.executor import run_deployed_agent
            from agent_runtime.docker_executor import run_agent_in_container, use_docker_runtime
            pub = get_published_agent_by_name(agent_name)
            if pub:
                ver = get_latest_version(pub["agent_id"])
                if ver and (ver.get("code_location") or "").strip():
                    package_root, extract_root = load_agent_package(pub["agent_id"], task_id=task_id)
                    try:
                        if use_docker_runtime():
                            result = run_agent_in_container(
                                package_root,
                                state,
                                timeout_seconds=60,
                            )
                        else:
                            result = run_deployed_agent(
                                package_root,
                                state,
                                task_id=task_id,
                                agent_name=agent_name,
                            )
                        if hasattr(result, "__next__") and hasattr(result, "__iter__"):
                            result = _consume_agent_stream(result, task_id)
                        if result is None:
                            result = {}
                        finish_agent(agent_name, task_id)
                        if agent_instance_id:
                            return (result, state.get("agent_instance_state", state))
                        return result
                    finally:
                        shutil.rmtree(extract_root, ignore_errors=True)
        except Exception as exc:
            fail_agent(agent_name, task_id, exc)
            return {agent_name: f"Agent failed: {exc}"}
        fail_agent(agent_name, task_id, f"Agent '{agent_name}' not registered")
        return {agent_name: f"Agent '{agent_name}' not registered"}
    agent_instance._memory_project_id = project_id
    if agent_instance_id:
        agent_instance._memory_agent_instance_id = agent_instance_id
        state["pending_messages"] = get_pending_for_instance(agent_instance_id)
        for msg in state["pending_messages"]:
            mark_delivered(msg["id"])
        try:
            agent_instance.coordinate()
        except Exception:
            pass
    try:
        run_agent_tools(agent_instance, state)
        result = agent_instance.run(state)
        if hasattr(result, "__next__") and hasattr(result, "__iter__"):
            result = _consume_agent_stream(result, task_id)
        if result is None:
            result = {}
        finish_agent(agent_name, task_id)
        if agent_instance_id:
            return (result, state.get("agent_instance_state", state))
        return result
    except Exception as exc:
        fail_agent(agent_name, task_id, exc)
        return {agent_name: f"Agent failed: {exc}"}


def run_single_agent_node_simulation(
    simulation_id: int,
    sim_task_id: int,
    task: str,
    agent_name: str,
    project_id: uuid.UUID,
    agent_instance_id: str | None = None,
):
    """
    Run a single agent for a simulation task using cloned state only.
    Reads instance state from simulation_agent_instances; memory/KG writes go to simulation clone.
    Updates tasks_completed/tasks_failed and persists instance state back to simulation.
    Does not touch production tasks, memory, or knowledge graph.
    """
    load_agents()
    load_tools()
    from database.simulation import (
        get_instance_simulation,
        update_instance_state_simulation,
        complete_simulation_task,
    )
    instance_state = {}
    if agent_instance_id:
        inst = get_instance_simulation(simulation_id, agent_instance_id)
        if inst and inst.get("state"):
            instance_state = inst["state"]
    state = {
        "task_id": None,
        "task": task,
        "project_id": project_id,
        "agent_outputs": {},
        "memory": [],
        "logs": [],
        "metadata": {},
        "pending_messages": [],
    }
    if instance_state:
        state["agent_instance_state"] = instance_state
        state.update(instance_state)
    agent_instance = agent_registry.get_agent(agent_name)
    if agent_instance is None:
        complete_simulation_task(simulation_id, sim_task_id, success=False)
        return {agent_name: "Agent not registered"}
    agent_instance._memory_project_id = project_id
    agent_instance._memory_simulation_id = simulation_id
    agent_instance._memory_agent_instance_id = agent_instance_id
    try:
        run_agent_tools(agent_instance, state)
        result = agent_instance.run(state)
        if hasattr(result, "__next__") and hasattr(result, "__iter__"):
            result = _consume_agent_stream(result, None)
        if result is None:
            result = {}
        if agent_instance_id:
            update_instance_state_simulation(
                simulation_id,
                agent_instance_id,
                state.get("agent_instance_state", state),
            )
        complete_simulation_task(simulation_id, sim_task_id, success=True)
        return result
    except Exception as exc:
        complete_simulation_task(simulation_id, sim_task_id, success=False)
        return {agent_name: f"Agent failed: {exc}"}


def run_pipeline(
    task,
    task_id: int | None = None,
    agent: str | None = None,
    agent_instance_id: str | None = None,
    instance_state: dict | None = None,
):
    """
    Run the agent pipeline for the given task. Uses a centralized execution
    state passed to workers, orchestrator, agents, and tools.
    If agent is provided (e.g. from marketplace), run that agent only; otherwise use the router.
    When agent_instance_id is set, memory is scoped to that instance and instance_state is merged into state.
    """
    print("\n==============================")
    print("Starting Agent Pipeline")
    print("Task:", task)
    print("==============================\n")

    # Ensure agents and tools are loaded and capability index is built before routing.
    load_agents()
    load_tools()
    build_index()

    previous_memory = search_memory(task)

    print("Previous knowledge:")
    print(previous_memory)
    print("\n")

    # Use selected agent from queue if provided; otherwise try planner, then fallback to router.
    if agent is not None:
        selected_agents = [agent]
        print("Selected agents (from task):", selected_agents)
    else:
        workflow = None
        planner = agent_registry.get_agent("planner_agent")
        if planner is not None:
            try:
                planner_state = {"task": task}
                result = planner.run(planner_state)
                if isinstance(result, dict) and result.get("workflow"):
                    w = result["workflow"]
                    if isinstance(w, list) and len(w) > 0:
                        workflow = w
            except Exception:
                pass
        if workflow is not None:
            selected_agents = workflow
            print("Selected agents (from planner):", selected_agents)
        else:
            selected_agents = route_task(task)
            print("Selected agents:", selected_agents)

    # Build DAG
    AGENT_GRAPH = build_dag(selected_agents)

    print("Agent DAG:", AGENT_GRAPH)
    print("\n")

    # Create database record for ad-hoc runs when no task_id is provided.
    if task_id is None:
        task_id = db.create_task(task)

    project_id = db.get_task_project_id(task_id) if task_id else None

    # Centralized execution state for composition, tracing, streaming, billing, logs.
    memory_list = (
        list(previous_memory)
        if isinstance(previous_memory, (list, tuple))
        else [previous_memory]
        if previous_memory is not None
        else []
    )
    state = {
        "task_id": task_id,
        "task": task,
        "project_id": project_id,
        "agent_outputs": {},
        "tools": [],
        "memory": memory_list,
        "logs": [],
        "metadata": {},
    }
    if instance_state:
        state["agent_instance_state"] = instance_state
        state.update(instance_state)
    if agent_instance_id:
        state["pending_messages"] = get_pending_for_instance(agent_instance_id)
        for msg in state["pending_messages"]:
            mark_delivered(msg["id"])

    def safe_state_clone(s):
        # Prevent shared mutable state races between parallel agent threads.
        return copy.deepcopy(s)

    completed = set()

    while len(completed) < len(AGENT_GRAPH):

        runnable = []

        for agent, deps in AGENT_GRAPH.items():

            if agent not in completed and all(d in completed for d in deps):
                runnable.append(agent)

        if not runnable:
            break

        agent_functions = []

        for agent in runnable:

            def make_agent_fn(name):

                def _fn(_shared_state):
                    local_state = safe_state_clone(state)

                    print(f"Running {name} agent...")
                    local_state["logs"].append({"event": "agent_start", "agent": name})
                    start_agent(name, task_id)

                    # Look up the agent instance from the registry or deployed (marketplace) package
                    agent_instance = agent_registry.get_agent(name)
                    if agent_instance is None:
                        try:
                            from database.developer_economy import get_published_agent_by_name, get_latest_version
                            from agent_runtime.package_loader import load_agent_package
                            from agent_runtime.executor import run_deployed_agent
                            from agent_runtime.docker_executor import run_agent_in_container, use_docker_runtime
                            pub = get_published_agent_by_name(name)
                            if pub:
                                ver = get_latest_version(pub["agent_id"])
                                if ver and (ver.get("code_location") or "").strip():
                                    package_root, extract_root = load_agent_package(pub["agent_id"], task_id=task_id)
                                    try:
                                        if use_docker_runtime():
                                            result = run_agent_in_container(
                                                package_root,
                                                local_state,
                                                timeout_seconds=60,
                                            )
                                        else:
                                            result = run_deployed_agent(
                                                package_root,
                                                local_state,
                                                task_id=task_id,
                                                agent_name=name,
                                            )
                                        if hasattr(result, "__next__") and hasattr(result, "__iter__"):
                                            result = _consume_agent_stream(result, task_id)
                                        if result is None:
                                            result = {}
                                        local_state["logs"].append({"event": "agent_complete", "agent": name})
                                        finish_agent(name, task_id)
                                        return result
                                    finally:
                                        shutil.rmtree(extract_root, ignore_errors=True)
                        except Exception as exc:
                            local_state["logs"].append({"event": "agent_fail", "agent": name, "error": str(exc)})
                            fail_agent(name, task_id, exc)
                            return {name: f"Agent failed: {exc}"}
                        error_message = (
                            f"Agent '{name}' is not registered and could not be executed."
                        )
                        local_state["logs"].append(
                            {"event": "agent_fail", "agent": name, "error": error_message}
                        )
                        fail_agent(name, task_id, error_message)
                        return {name: error_message}

                    agent_instance._memory_project_id = local_state.get("project_id")
                    if agent_instance_id:
                        agent_instance._memory_agent_instance_id = agent_instance_id
                        try:
                            agent_instance.coordinate()
                        except Exception:
                            pass
                    try:
                        # Run any tools declared on the agent before executing it.
                        run_agent_tools(agent_instance, local_state)

                        result = agent_instance.run(local_state)
                        # Support streaming: if agent returns a generator, consume events and use return value.
                        if hasattr(result, "__next__") and hasattr(result, "__iter__"):
                            result = _consume_agent_stream(result, task_id)
                        if result is None:
                            result = {}
                        local_state["logs"].append(
                            {"event": "agent_complete", "agent": name}
                        )
                        finish_agent(name, task_id)
                        return result
                    except Exception as exc:
                        local_state["logs"].append(
                            {
                                "event": "agent_fail",
                                "agent": name,
                                "error": str(exc),
                            }
                        )
                        fail_agent(name, task_id, exc)
                        return {
                            name: f"Agent '{name}' failed with error: {exc}"
                        }

                _fn.__name__ = name
                return _fn

            agent_functions.append(make_agent_fn(agent))

        # Run runnable agents in parallel
        parallel_results = run_parallel_agents(agent_functions, state)

        for agent in runnable:

            output = parallel_results.get(agent)

            # Normalize all outputs to dictionaries so state is always updated consistently.
            if isinstance(output, dict):
                normalized_output = output
            else:
                normalized_output = {agent: output}

            # Centralized agent output for composition, tracing, marketplace logs.
            state["agent_outputs"][agent] = output
            # Keep backward compatibility for agents that read state by agent key.
            state.update(normalized_output)

            # Recursive subtasks: if agent returned subtasks, enqueue them and record in task graph.
            subtasks = collect_subtasks_from_output(output)
            if subtasks:
                enqueue_subtasks(
                    parent_task=task,
                    subtasks=subtasks,
                    agent=agent,
                    parent_task_id=task_id,
                )

            print(f"{agent} agent completed")

            completed.add(agent)

            # Store agent run in database
            db.store_agent_run(task_id, agent, str(output))

    # Determine the final pipeline result.
    final_result = None

    if isinstance(state.get("result"), str):
        final_result = state.get("result")
    elif state.get("execution") is not None:
        final_result = state.get("execution")

    if final_result is not None:
        store_memory(str(final_result))
        db.store_result(task_id, str(final_result))

    # Workflow controller: update task graph and parent status when all children complete.
    check_task_completion(task_id)

    print("\nPipeline completed\n")

    if agent_instance_id:
        return (final_result, state.get("agent_instance_state", state))
    return final_result
