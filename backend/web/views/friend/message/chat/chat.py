import json

from django.http import StreamingHttpResponse
from langchain_core.messages import AIMessage, BaseMessageChunk, HumanMessage, SystemMessage
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BaseRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from web.models.friend import Friend, FriendMessage
from web.models.prompt import SystemPrompt
from web.views.friend.message.chat.graph import ChatGraph
from web.views.friend.message.memory.update import update_memory


class SSERenderer(BaseRenderer):
    """让 DRF 别去序列化流：SSE 帧在生成器里已经拼好了，原样返回即可。"""

    media_type = 'text/event-stream'
    format = 'txt'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


def add_system_prompt(state, friend):
    """拼系统提示词：数据库里的『回复』提示词 + 角色性格 + 长期记忆。"""
    msgs = state['messages']
    system_prompts = SystemPrompt.objects.filter(title='回复').order_by('order_number')
    prompt = ''.join(sp.prompt for sp in system_prompts)
    prompt += f'\n【角色性格】\n{friend.character.profile}\n'
    prompt += f'【长期记忆】\n{friend.memory or "暂无"}\n'
    return {'messages': [SystemMessage(prompt)] + msgs}


def add_recent_messages(state, friend):
    """把最近 10 轮对话插到系统词和当前消息之间。"""
    msgs = state['messages']
    message_raw = list(
        FriendMessage.objects.filter(friend=friend).order_by('-id')[:10]
    )
    message_raw.reverse()
    history = []
    for m in message_raw:
        history.append(HumanMessage(m.user_message))
        history.append(AIMessage(m.output))
    # msgs[:1] 是系统提示词，msgs[-1:] 是用户刚发的这句
    return {'messages': msgs[:1] + history + msgs[-1:]}


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
        inputs = {'messages': [HumanMessage(message)]}
        inputs = add_system_prompt(inputs, friend)
        inputs = add_recent_messages(inputs, friend)

        response = StreamingHttpResponse(
            self.event_stream(app, inputs, friend, message),
            content_type='text/event-stream',
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response

    def event_stream(self, app, inputs, friend, message):
        full_output = ''
        full_usage = {}

        try:
            for msg, metadata in app.stream(inputs, stream_mode='messages'):
                if isinstance(msg, BaseMessageChunk):
                    if msg.content:
                        full_output += msg.content
                        yield f'data: {json.dumps({"content": msg.content}, ensure_ascii=False)}\n\n'
                    if getattr(msg, 'usage_metadata', None):
                        full_usage = msg.usage_metadata
        except Exception as exc:
            # 模型侧出错时，把话说人话推给前端，而不是让流干巴巴断掉
            yield f'data: {json.dumps({"error": f"模型调用失败：{exc}"}, ensure_ascii=False)}\n\n'

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
