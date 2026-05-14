from agents.research_agent import ResearchAgent
from agents.strategy_agent import StrategyAgent
from agents.content_agent import ContentAgent
from agents.tool_agent import ToolAgent
from agents.execution_agent import ExecutionAgent


AGENTS = {
    "research": ResearchAgent().run,
    "strategy": StrategyAgent().run,
    "content": ContentAgent().run,
    "tool": ToolAgent().run,
    "execution": ExecutionAgent().run
}