import os
from pathlib import Path
from typing import TypedDict, Annotated, Sequence

import lancedb
from django.conf import settings
from django.utils.timezone import localtime, now
from langchain_community.vectorstores import LanceDB
from langchain_core.messages import BaseMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.constants import START, END
from langgraph.graph import add_messages, StateGraph
from langgraph.prebuilt import ToolNode

from web.documents.utils.custom_embeddings import CustomEmbeddings

# 知识库落在 backend/web/documents/ 下，用绝对路径免得 cwd 一变就找不到
DOCS_DIR = Path(settings.BASE_DIR) / 'web' / 'documents'


def _env(*names, default=''):
    """按顺序找环境变量，找到第一个非空的就用。

    教程里写的是 API_KEY / API_BASE / CHAT_MODEL，
    而项目 .env 里同时留了 DEEPSEEK_* 一套，这里两套都认。
    """
    for name in names:
        value = (os.getenv(name) or '').strip()
        if value:
            return value
    return default


class ChatGraph:
    @staticmethod
    def create_app():
        @tool
        def get_time() -> str:
            """当需要查询精确时间时，调用此函数。返回格式为：[年-月-日 时:分:秒]"""
            return localtime(now()).strftime('%Y-%m-%d %H:%M:%S')

        @tool
        def search_knowledge_base(query: str) -> str:
            """当用户查询阿里云百炼平台的相关信息时，调用此函数。输入为要查询的问题，输出为查询结果。"""
            db = lancedb.connect(str(DOCS_DIR / 'lancedb_storage'))
            embeddings = CustomEmbeddings()
            vector_db = LanceDB(
                connection=db,
                embedding=embeddings,
                table_name='my_knowledge_base',
            )
            docs = vector_db.similarity_search(query, k=3)
            context = '\n\n'.join(
                f'内容片段：{i + 1}\n{doc.page_content}' for i, doc in enumerate(docs)
            )
            return f'从知识库中找到以下相关信息：\n\n{context}\n'

        tools = [get_time, search_knowledge_base]

        llm = ChatOpenAI(
            model=_env('CHAT_MODEL', 'DEEPSEEK_MODEL', default='deepseek-chat'),
            openai_api_key=_env('API_KEY', 'DEEPSEEK_API_KEY'),
            openai_api_base=_env('API_BASE', 'DEEPSEEK_BASE_URL',
                                 default='https://api.deepseek.com/v1'),
            streaming=True,
            model_kwargs={
                'stream_options': {
                    'include_usage': True,   # 输出 token 消耗数量
                },
            },
        ).bind_tools(tools)

        class AgentState(TypedDict):
            messages: Annotated[Sequence[BaseMessage], add_messages]

        def model_call(state: AgentState) -> AgentState:
            res = llm.invoke(state['messages'])
            return {'messages': [res]}

        def should_continue(state: AgentState) -> str:
            last_message = state['messages'][-1]
            if getattr(last_message, 'tool_calls', None):
                return 'tools'
            return 'end'

        graph = StateGraph(AgentState)
        graph.add_node('agent', model_call)
        graph.add_node('tools', ToolNode(tools))

        graph.add_edge(START, 'agent')
        graph.add_conditional_edges(
            'agent',
            should_continue,
            {
                'tools': 'tools',
                'end': END,
            }
        )
        graph.add_edge('tools', 'agent')

        return graph.compile()
