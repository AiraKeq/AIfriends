import json

from django.http import StreamingHttpResponse
from langchain_core.messages import BaseMessageChunk, HumanMessage, SystemMessage
from langgraph.types import Command
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BaseRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from web.models.friend import Friend, FriendMessage
from web.models.prompt import SystemPrompt
from web.views.friend.message.chat.graph import (
    RECURSION_LIMIT,
    ChatGraph,
    build_langfuse_callbacks,
)
from web.views.friend.message.memory.update import update_memory


class SSERenderer(BaseRenderer):
    """让 DRF 别去序列化流：SSE 帧在生成器里已经拼好了，原样返回即可。"""

    media_type = 'text/event-stream'
    format = 'txt'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


def build_system_prompt(friend):
    """拼系统提示词：数据库里的『回复』提示词 + 角色性格 + 长期记忆 + 记忆规则。"""
    system_prompts = SystemPrompt.objects.filter(title='回复').order_by('order_number')
    prompt = ''.join(sp.prompt for sp in system_prompts)
    prompt += f'\n【角色性格】\n{friend.character.profile}\n'
    prompt += f'【长期记忆】\n{friend.memory or "暂无"}\n'
    # ★ 确认门还没做，工具只是「登记」★
    #   不加这条，模型会顺着 save_memory 的返回说「我记住了」，
    #   而实际上一个字都没落库 —— 用户被误导，面试也会被问穿。
    prompt += (
        '\n【记忆规则】\n'
        '当工具返回里出现「待确认」时，说明这条信息还没有保存。'
        '你只能问用户愿不愿意让你记住，不能说「已经记住了」。\n'
    )
    return prompt


class MessageChatView(APIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [SSERenderer]

    def post(self, request):
        friend_id = request.data.get('friend_id')
        message = (request.data.get('message') or '').strip()
        if not message:
            return Response({'result': '消息不能为空'})

        friends = Friend.objects.filter(pk=friend_id, me__user=request.user)
        if not friends.exists():
            return Response({'result': '好友不存在'})
        friend = friends.first()

        app = ChatGraph.create_app()
        config = {
            # ★ thread_id = 这条好友关系 ★
            #   checkpointer 按它存整段状态，断线重连能接着跑
            'configurable': {'thread_id': f'friend-{friend.id}'},
            # 保险丝：比 MAX_TOOL_ROUNDS 大一些。撞上它是异常，不是正常收尾
            'recursion_limit': RECURSION_LIMIT,
            # 没配 Langfuse key 时是空列表，对话不受影响
            'callbacks': build_langfuse_callbacks(),
        }

        # ★ 有历史就不再塞 ★
        #   checkpointer 已经存了完整对话；再塞一遍会重复，
        #   而且「我刚才问了什么」这类问题会因为上下文重复而答歪。
        #   system prompt 只在第一次对话时写入，之后跟着状态走。
        graph_state = app.get_state(config)
        has_history = bool(graph_state.values.get('messages'))
        if has_history:
            inputs = {'messages': [HumanMessage(message)], 'steps': 0, 'friend_id': friend.id}
        else:
            inputs = {
                'messages': [
                    SystemMessage(build_system_prompt(friend)),
                    HumanMessage(message),
                ],
                'steps': 0,
                'friend_id': friend.id,
            }

        response = StreamingHttpResponse(
            self.event_stream(app, inputs, config, friend, message),
            content_type='text/event-stream',
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response

    def event_stream(self, app, inputs, config, friend, message):
        full_output = ''
        full_usage = {}

        try:
            for msg, metadata in app.stream(inputs, stream_mode='messages', config=config):
                if isinstance(msg, BaseMessageChunk):
                    if msg.content:
                        full_output += msg.content
                        yield f'data: {json.dumps({"content": msg.content}, ensure_ascii=False)}\n\n'
                    if getattr(msg, 'usage_metadata', None):
                        full_usage = msg.usage_metadata
        except Exception as exc:
            # 模型侧出错时，把话说人话推给前端，而不是让流干巴巴断掉
            yield f'data: {json.dumps({"error": f"模型调用失败：{exc}"}, ensure_ascii=False)}\n\n'

        # ★ 检查确认门（必须在 [DONE] 之前）★
        #   interrupt 之后 stream 会自然结束，这里从快照里把待确认的事捞出来，
        #   推一条独立事件给前端。前端据此弹「要不要记住」。
        #   顺序反了的话，前端一收到 [DONE] 就把这条流当作结束，确认框永远不会弹。
        try:
            snapshot = app.get_state(config)
            pending = []
            for task in getattr(snapshot, 'tasks', ()) or ():
                for interrupt_item in getattr(task, 'interrupts', ()) or ():
                    pending.append(interrupt_item.value)
            if pending:
                yield f'data: {json.dumps({"event": "interrupt", "payload": pending[0]}, ensure_ascii=False)}\n\n'
        except Exception as exc:
            # 查中断失败不该让整个回复失败
            print(f'[chat] 检查中断失败：{exc}')

        yield 'data: [DONE]\n\n'

        if full_output:
            FriendMessage.objects.create(
                friend=friend,
                user_message=message[:500],
                input=json.dumps(
                    [m.model_dump() for m in inputs['messages']],
                    ensure_ascii=False,
                )[:10000],
                output=full_output[:500],
                input_token=full_usage.get('input_tokens', 0),
                output_token=full_usage.get('output_tokens', 0),
                total_tokens=full_usage.get('total_tokens', 0),
            )

            # 每 10 轮整理一次长期记忆；记忆更新失败不能影响这次对话
            if FriendMessage.objects.filter(friend=friend).count() % 10 == 0:
                try:
                    update_memory(friend)
                except Exception as exc:
                    print(f'[memory] 更新失败：{exc}')


class MessageResumeView(APIView):
    """POST /api/friend/message/chat/resume/  {friend_id, approve}

    确认门的另一半：用户点了「要记住 / 不用」之后，带着决定恢复图。

    ★ 恢复时不要带 steps ★
      Command(resume=...) 只传决定；带 steps 会把确认前的步数清掉，
      于是恢复后模型又能调一轮工具，步数上限就形同虚设。
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        friend_id = request.data.get('friend_id')
        # 前端传布尔或字符串都认
        approve = request.data.get('approve')
        approve = approve if isinstance(approve, bool) else str(approve).lower() in ('1', 'true', 'yes')

        friends = Friend.objects.filter(pk=friend_id, me__user=request.user)
        if not friends.exists():
            return Response({'result': '好友不存在'})
        friend = friends.first()

        app = ChatGraph.create_app()
        config = {
            'configurable': {'thread_id': f'friend-{friend.id}'},
            'recursion_limit': RECURSION_LIMIT,
            'callbacks': build_langfuse_callbacks(),
        }

        try:
            result = app.invoke(Command(resume=approve), config=config)
        except Exception as exc:
            return Response({'result': f'恢复失败：{exc}'})

        messages = result.get('messages') or []
        # ★ 取最后一条有正文的 AIMessage ★
        #   resume 之后状态末尾可能是 ToolMessage（"待确认"那段），
        #   直接拿 messages[-1] 会把工具输出当成模型回复返回给前端。
        from langchain_core.messages import AIMessage

        ai_messages = [
            m for m in messages
            if isinstance(m, AIMessage) and (m.content or '').strip()
        ]
        content = ai_messages[-1].content if ai_messages else ''
        return Response({'result': 'success', 'content': content})
