import os
from typing import TypedDict, Annotated, Sequence

from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from langgraph.constants import START, END
from langgraph.graph import add_messages, StateGraph


def _env(*names, default=''):
    for name in names:
        value = (os.getenv(name) or '').strip()
        if value:
            return value
    return default


class MemoryGraph:
    """单节点的图：把「旧记忆 + 最近对话」丢给模型，让它总结出一段新记忆。"""

    @staticmethod
    def create_app():
        llm = ChatOpenAI(
            model=_env('CHAT_MODEL', 'DEEPSEEK_MODEL', default='deepseek-chat'),
            openai_api_key=_env('API_KEY', 'DEEPSEEK_API_KEY'),
            openai_api_base=_env('API_BASE', 'DEEPSEEK_BASE_URL',
                                 default='https://api.deepseek.com/v1'),
        )

        class AgentState(TypedDict):
            messages: Annotated[Sequence[BaseMessage], add_messages]

        def model_call(state: AgentState) -> AgentState:
            res = llm.invoke(state['messages'])
            return {'messages': [res]}

        graph = StateGraph(AgentState)
        graph.add_node('agent', model_call)

        graph.add_edge(START, 'agent')
        graph.add_edge('agent', END)

        return graph.compile()
