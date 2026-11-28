import asyncio
import base64
import json
import os
import threading
from queue import Queue

import websockets
from django.http import StreamingHttpResponse
from langchain_core.messages import AIMessage, BaseMessageChunk, HumanMessage, SystemMessage
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
    prompt += f'\n【长期记忆】\n{friend.memory or "暂无"}\n'
    prompt += (
        '\n【记忆规则】\n'
        '当工具返回里出现「待确认」时，说明这条信息还没有保存。'
        '你只能问用户愿不愿意让你记住，不能说「已经记住了」。\n'
    )
    return prompt


class MessageChatView(APIView):
    """聊天接口：文字流 + TTS 音频流，都从同一条 SSE 推给前端。

    为什么是「双线程 + 汇合队列」而不是直接 astream：
      LangGraph 的同步 checkpointer（SqliteSaver）不支持 async 方法，
      astream 会直接抛「does not support async methods」。
      而 websockets 只有 async API。
      所以切成两条线程：
        ① 生成线程：app.stream（同步）→ 文字放进 text_q 和 out_q
        ② TTS 线程：asyncio 读 text_q → 送 TTS → 音频放进 out_q
        主线程读 out_q，按到达顺序发 SSE。
    """

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
            'configurable': {'thread_id': f'friend-{friend.id}'},
            'recursion_limit': RECURSION_LIMIT,
            'callbacks': build_langfuse_callbacks(),
        }

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

    # ─────────────────────────────────────────────────────────────────
    # 生成线程：同步跑图，文字同时进 TTS 队列和输出队列
    # ─────────────────────────────────────────────────────────────────

    def generate(self, app, inputs, config, text_q, out_q):
        try:
            for msg, metadata in app.stream(inputs, stream_mode='messages', config=config):
                if isinstance(msg, BaseMessageChunk):
                    if msg.content:
                        text_q.put(msg.content)
                        out_q.put({'content': msg.content})
                    if getattr(msg, 'usage_metadata', None):
                        out_q.put({'usage': msg.usage_metadata})
        except Exception as exc:
            print(f'[chat] 生成异常：{exc}')
            out_q.put({'error': f'模型调用失败：{exc}'})
        finally:
            # 通知 TTS：文字说完了
            text_q.put(None)

    # ─────────────────────────────────────────────────────────────────
    # TTS 线程：async WebSocket，收音频进输出队列
    # ─────────────────────────────────────────────────────────────────

    def tts_worker(self, text_q, out_q):
        try:
            asyncio.run(self.tts_loop(text_q, out_q))
        except Exception as exc:
            print(f'[chat] TTS 线程异常：{exc}')
        finally:
            out_q.put(None)

    async def tts_loop(self, text_q, out_q):
        api_key = os.getenv('API_KEY') or os.getenv('DEEPSEEK_API_KEY')
        tts_url = os.getenv('TTS_URL', 'wss://api.deepseek.com/v1/tools/tts')
        # DeepSeek 只有两个内置音色；角色音色系统还没做，先用默认
        voice = 'stella'
        url = f'{tts_url}?voice_id={voice}&format=pcm'
        headers = {'Authorization': f'Bearer {api_key}'}

        try:
            ws = await websockets.connect(url, additional_headers=headers)
        except Exception as exc:
            print(f'[chat] TTS 连接失败，降级为纯文字：{exc}')
            # ★ 必须等文字排空再退出 ★
            #   提前 return 会让 tts_worker 立刻往 out_q 塞结束哨兵，
            #   主线程就会在文字还没生成完时收尾 —— 回复被截断。
            while True:
                text = await asyncio.to_thread(text_q.get)
                if text is None:
                    break
            return

        async with ws:
            await asyncio.gather(
                self.tts_sender_loop(text_q, ws),
                self.tts_receiver_loop(out_q, ws),
            )

    async def tts_sender_loop(self, text_q, ws):
        while True:
            # Queue.get 是阻塞的，丢进线程池免得堵住事件循环
            text = await asyncio.to_thread(text_q.get)
            if text is None:
                await ws.send(json.dumps({'event': 'finish_text'}))
                break
            await ws.send(json.dumps({'event': 'text', 'text': text}))

    async def tts_receiver_loop(self, out_q, ws):
        async for msg in ws:
            if isinstance(msg, bytes):
                audio = base64.b64encode(msg).decode('utf-8')
                out_q.put({'audio': audio})
            else:
                data = json.loads(msg)
                if data.get('event') == 'finish':
                    if data.get('code') != 'success':
                        print(f'[chat] TTS 结束：{data}')
                    break

    # ─────────────────────────────────────────────────────────────────
    # SSE 主循环
    # ─────────────────────────────────────────────────────────────────

    def event_stream(self, app, inputs, config, friend, message):
        text_q = Queue()
        out_q = Queue()

        gen_thread = threading.Thread(
            target=self.generate,
            args=(app, inputs, config, text_q, out_q),
        )
        tts_thread = threading.Thread(
            target=self.tts_worker,
            args=(text_q, out_q),
        )
        gen_thread.start()
        tts_thread.start()

        full_output = ''
        full_usage = {}

        while True:
            item = out_q.get()
            if item is None:
                break
            if item.get('content'):
                full_output += item['content']
                yield f'data: {json.dumps({"content": item["content"]}, ensure_ascii=False)}\n\n'
            if item.get('audio'):
                yield f'data: {json.dumps({"audio": item["audio"]}, ensure_ascii=False)}\n\n'
            if item.get('usage'):
                full_usage = item['usage']
            if item.get('error'):
                yield f'data: {json.dumps({"error": item["error"]}, ensure_ascii=False)}\n\n'

        gen_thread.join(timeout=5)
        tts_thread.join(timeout=5)

        # ★ 检查确认门（必须在 [DONE] 之前）★
        try:
            snapshot = app.get_state(config)
            pending = []
            for task in getattr(snapshot, 'tasks', ()) or ():
                for interrupt_item in getattr(task, 'interrupts', ()) or ():
                    pending.append(interrupt_item.value)
            if pending:
                yield f'data: {json.dumps({"event": "interrupt", "payload": pending[0]}, ensure_ascii=False)}\n\n'
        except Exception as exc:
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
      Command(resume=...) 只传决定；带 steps 会把确认前的步数清掉。
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        friend_id = request.data.get('friend_id')
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
        # 取最后一条有正文的 AIMessage：resume 之后状态末尾可能是 ToolMessage
        ai_messages = [
            m for m in messages
            if isinstance(m, AIMessage) and (m.content or '').strip()
        ]
        content = ai_messages[-1].content if ai_messages else ''
        return Response({'result': 'success', 'content': content})
