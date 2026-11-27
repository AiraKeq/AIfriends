"""聊天 Agent 图。

和教程版的区别（也是这一轮改造的重点）：

1. 工具由模型选，不是代码里写死「先检索再回答」
2. 步数有上限，超了走 fallback 收尾，不许再调工具
3. 工具调用记进 state，供后续可观测与评测使用
4. save_memory 只登记、不写库 —— 写库放在第三批的确认门之后

关于 steps：
    它只统计「本轮」的工具轮数。checkpointer 会把整段状态按 conversation_id
    存下来，如果不按轮清零，用户第二句话进来时 steps 还是满的，直接掉进 fallback。
    清零的责任在调用方（chat.py 构造 inputs 时写 steps: 0）；
    Command(resume=...) 恢复时不要重置，否则确认门之后步数被清掉。
"""
import os
from pathlib import Path
from typing import Annotated, Sequence, TypedDict

import lancedb
from django.conf import settings
from django.utils.timezone import localtime, now
from langchain_community.vectorstores import LanceDB
from langchain_core.messages import BaseMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.constants import START, END
from langgraph.graph import add_messages, StateGraph
from langgraph.types import interrupt

from web.documents.utils.custom_embeddings import CustomEmbeddings
from web.models.friend import Friend

# 知识库落在 backend/web/documents/ 下，用绝对路径免得 cwd 一变就找不到
DOCS_DIR = Path(settings.BASE_DIR) / 'web' / 'documents'

# 一轮对话里最多允许几轮工具调用。
# 做成环境变量是为了能验证 fallback：把它设成 1，问一个必须查两次才能答的问题。
MAX_TOOL_ROUNDS = int(os.getenv('MAX_TOOL_ROUNDS', '6'))

# 兜底用的 recursion_limit：比 MAX_TOOL_ROUNDS 大一些就够。
# 它是「图自身别跑飞」的保险丝，不能拿来代替 fallback ——
# 撞上 recursion_limit 是抛异常，撞上 fallback 是正常收尾。
RECURSION_LIMIT = MAX_TOOL_ROUNDS * 2 + 4


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


def build_langfuse_callbacks():
    """有 key 就挂 Langfuse，没 key 或装不上就返回空列表。

    ★ 绝不能因为观测把对话搞挂 ★
      没装包、key 失效、网络抖动，都只该让「看不到 trace」，
      而不是让用户发不出消息。

    ★ 注意措辞 ★
      没配 key 时这里什么都不发，所以简历上只能写「没 key 不发送」，
      不能写「轨迹已接入」——还没有一条真实 trace。
    """
    if not (_env('LANGFUSE_SECRET_KEY') and _env('LANGFUSE_PUBLIC_KEY')):
        return []
    try:
        from langfuse.callback import CallbackHandler

        return [CallbackHandler(
            public_key=_env('LANGFUSE_PUBLIC_KEY'),
            secret_key=_env('LANGFUSE_SECRET_KEY'),
            host=_env('LANGFUSE_HOST', default='https://cloud.langfuse.com'),
        )]
    except Exception:
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Checkpointer：让「同一条对话断了能续」
# ─────────────────────────────────────────────────────────────────────────────

CHECKPOINT_DB = Path(settings.BASE_DIR) / 'checkpoints.sqlite3'
_CHECKPOINTER = None


def get_checkpointer():
    """单独一个 SQLite 文件，不和 Django 的 db.sqlite3 共用。

    共用一个文件有两个问题：
      1. Django 的迁移表和 checkpointer 的建表混在一起，备份和清理都麻烦；
      2. Django 的连接是长生命周期的，checkpointer 的写入容易撞锁。
    check_same_thread=False 是因为落库发生在不同的调用栈上。
    """
    global _CHECKPOINTER
    if _CHECKPOINTER is None:
        import sqlite3

        from langgraph.checkpoint.sqlite import SqliteSaver

        conn = sqlite3.connect(str(CHECKPOINT_DB), check_same_thread=False)
        _CHECKPOINTER = SqliteSaver(conn)
        _CHECKPOINTER.setup()   # 建表；重复调用是幂等的
    return _CHECKPOINTER


class ChatGraph:
    @staticmethod
    def create_app():
        @tool
        def get_time() -> str:
            """当用户问「现在几点」「今天几号」这类时间问题时调用。

            其他问题不要调用 —— 它只返回一个时间字符串，对闲聊没有帮助。
            """
            return localtime(now()).strftime('%Y-%m-%d %H:%M:%S')

        @tool
        def search_knowledge_base(query: str) -> str:
            """当用户问到角色设定之外的资料性问题时调用，比如这个项目的技术细节、
            某个文档里写过的东西。输入是检索问题，输出是知识库里的相关片段。

            闲聊、寒暄、角色扮演对话不要调用。
            """
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

        @tool
        def save_memory(fact: str) -> str:
            """当用户透露了值得长期记住的个人信息时调用：名字/称呼、喜好、重要经历、
            你们的约定。

            不要用于：
              - 寒暄和临时话题
              - 已经记过的内容（重复记只会让记忆变脏）
              - 你自己的推测（用户没明说的不要记）

            fact 必须是一句完整的第三者陈述，例如「用户叫罗瑞，喜欢崩坏3」。
            """
            # 第一批只做登记，不写库 —— 真正的写入在第三批的确认节点里。
            # ★ 返回里必须说「尚未保存」★
            #   否则模型会顺着「已登记」说「我记住了」，而实际上一个字都没落库。
            return (
                f'【待确认】{fact}\n'
                '（这条信息还没有保存。请先问用户愿不愿意让你记住；'
                '用户同意之后才算记住，现在不要说“已经记住了”。）'
            )

        tools = [get_time, search_knowledge_base, save_memory]
        tool_map = {t.name: t for t in tools}

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
        )
        llm_with_tools = llm.bind_tools(tools)

        class AgentState(TypedDict):
            messages: Annotated[Sequence[BaseMessage], add_messages]
            # ★ 覆盖语义（没有 reducer），不是 operator.add ★
            #   新用户消息：输入里带 steps: 0
            #   Command(resume=...)：不要带这个键，否则确认前的步数会被清掉
            steps: int
            pending_fact: str | None   # save_memory 待确认的事实
            friend_id: int | None      # 写记忆时要知道写谁
            memory_decision: bool | None  # 确认门恢复后的决定

        def model_call(state: AgentState) -> dict:
            res = llm_with_tools.invoke(state['messages'])
            return {'messages': [res]}

        def run_tools(state: AgentState) -> dict:
            """自己跑工具，不用 ToolNode。

            原因：save_memory 要把 fact 放进 state（pending_fact），
            ToolNode 不方便做这种「工具顺带更新状态」的事。
            自定义节点还能顺便把 steps 加一。
            """
            last_message = state['messages'][-1]
            tool_messages = []
            pending_fact = None

            for call in getattr(last_message, 'tool_calls', None) or []:
                name = call.get('name')
                args = call.get('args') or {}
                tool = tool_map.get(name)

                if tool is None:
                    content = f'未知工具：{name}'
                else:
                    content = tool.invoke(args)

                if name == 'save_memory':
                    pending_fact = (args.get('fact') or '').strip() or None

                tool_messages.append(
                    ToolMessage(content=str(content), tool_call_id=call['id'])
                )

            update = {
                'messages': tool_messages,
                'steps': state.get('steps', 0) + 1,
            }
            if pending_fact:
                update['pending_fact'] = pending_fact
            return update

        def next_after_tools(state: AgentState) -> str:
            """工具跑完后：有待确认的记忆就进确认门，否则回 agent。"""
            return 'confirm' if state.get('pending_fact') else 'agent'

        def confirm(state: AgentState) -> dict:
            """确认门：暂停整张图，把「要不要记住」交给用户决定。

            ★ pause 点放在节点里，不放在工具里 ★
              工具是「提议」，确认是「审批」。两件事分开，
              用户拒绝之后模型才知道「被拒了」，而不是顺着工具返回假装记下了。
            """
            fact = state.get('pending_fact')
            if not fact:
                return {}
            decision = interrupt({'type': 'memory_confirm', 'fact': fact})
            return {'memory_decision': bool(decision)}

        def route_after_confirm(state: AgentState) -> str:
            return 'write_memory' if state.get('memory_decision') else 'reject'

        def write_memory(state: AgentState) -> dict:
            """用户同意后才落库 —— 全项目唯一一处真正写 Friend.memory 的地方。"""
            fact = state.get('pending_fact') or ''
            friend_id = state.get('friend_id')
            written = False

            if fact and friend_id:
                try:
                    friend = Friend.objects.get(pk=friend_id)
                    old = (friend.memory or '').strip()
                    friend.memory = f'{old}\n{fact}'.strip() if old else fact
                    friend.save(update_fields=['memory'])
                    written = True
                except Friend.DoesNotExist:
                    pass

            note = (
                f'用户同意了。这条已经写入长期记忆：{fact}。'
                '不要再调用 save_memory，直接给用户一句自然的确认。'
                if written
                else '写入失败，请如实告诉用户这次没记住。'
            )
            return {
                'messages': [SystemMessage(content=note)],
                'pending_fact': None,
                'memory_decision': None,
            }

        def reject(state: AgentState) -> dict:
            """用户拒绝：不写库，但要明确告诉模型「被拒了」，别再说已经记住。

            ★ 措辞要写成「不同意」，不能写成「没有同意」★
              「没有同意」会被模型读成「还没问过」，于是它又问一遍。
            """
            return {
                'messages': [SystemMessage(content=(
                    '用户已经明确不同意记住这条信息。'
                    '不要再重复询问，也不要声称已经记住，直接按用户的意愿继续对话。'
                ))],
                'pending_fact': None,
                'memory_decision': None,
            }

        def should_continue(state: AgentState) -> str:
            last_message = state['messages'][-1]
            has_tools = bool(getattr(last_message, 'tool_calls', None))
            steps = state.get('steps', 0)
            if not has_tools:
                print(f'[agent] 路由 -> end（无工具请求，steps={steps}）')
                return 'end'
            if steps >= MAX_TOOL_ROUNDS:
                print(f'[agent] 路由 -> fallback（steps={steps} >= 上限 {MAX_TOOL_ROUNDS}）')
                return 'fallback'
            print(f'[agent] 路由 -> tools（steps={steps} < 上限 {MAX_TOOL_ROUNDS}）')
            return 'tools'

        def fallback(state: AgentState) -> dict:
            """步数用尽时的收尾。

            ★ 只许用已有信息回答，不许再调工具 ★
              所以这里用的是没有 bind_tools 的 llm；
              给模型的那句提示也明确说了「不要再请求工具」。

            ★ 必须给未执行的 tool_calls 补上 ToolMessage ★
              走到这里时，最后一条 AIMessage 是带着 tool_calls 的，
              但工具还没跑。OpenAI 兼容接口要求每个 tool_call 都有响应，
              不补就会 400：
                "An assistant message with 'tool_calls' must be followed by
                 tool messages responding to each 'tool_call_id'"
            """
            messages = list(state['messages'])
            last = messages[-1]
            patch_messages = []

            for call in getattr(last, 'tool_calls', None) or []:
                patch_messages.append(
                    ToolMessage(
                        content='（本轮未执行：工具调用次数已用完）',
                        tool_call_id=call['id'],
                    )
                )

            note = SystemMessage(content=(
                f'本轮的工具调用次数已经用完（上限 {MAX_TOOL_ROUNDS} 次）。'
                '请只根据前面已经拿到的信息回答用户，不要再请求任何工具。'
                '如果信息不足，就直说你知道什么、还缺什么。'
            ))
            print(f'[agent] 步数超限，进入 fallback（steps={state.get("steps")}，补 {len(patch_messages)} 条工具响应）')
            res = llm.invoke([*messages, *patch_messages, note])
            # 补的 ToolMessage 要写回 state，否则这段历史下一轮还会 400
            return {'messages': [*patch_messages, res]}

        graph = StateGraph(AgentState)
        graph.add_node('agent', model_call)
        graph.add_node('tools', run_tools)
        graph.add_node('fallback', fallback)
        graph.add_node('confirm', confirm)
        graph.add_node('write_memory', write_memory)
        graph.add_node('reject', reject)

        graph.add_edge(START, 'agent')
        graph.add_conditional_edges(
            'agent',
            should_continue,
            {
                'tools': 'tools',
                'fallback': 'fallback',
                'end': END,
            }
        )
        # 工具之后先看有没有待确认的记忆
        graph.add_conditional_edges(
            'tools',
            next_after_tools,
            {'confirm': 'confirm', 'agent': 'agent'},
        )
        # 确认门：同意才写库，拒绝就回模型
        graph.add_conditional_edges(
            'confirm',
            route_after_confirm,
            {'write_memory': 'write_memory', 'reject': 'reject'},
        )
        graph.add_edge('write_memory', 'agent')
        graph.add_edge('reject', 'agent')
        graph.add_edge('fallback', END)

        # checkpointer 一挂上，同一 thread_id 的整段状态就能续上
        return graph.compile(checkpointer=get_checkpointer())
