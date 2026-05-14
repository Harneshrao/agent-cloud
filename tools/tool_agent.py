from tools.tool_executor import execute_tool


def run(state):

    print("🔧 Tool Agent selecting tools")

    task = state["task"]

    search_result = execute_tool("web_search", task)
    analysis_result = execute_tool("analysis_tool", task)

    return f"""
Tools Selected for: {task}

Web Search Output:
{search_result}

Analysis Output:
{analysis_result}
"""