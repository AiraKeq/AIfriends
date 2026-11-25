from django.utils.timezone import now
from langchain_core.messages import HumanMessage, SystemMessage

from web.models.friend import FriendMessage
from web.models.prompt import SystemPrompt
from web.views.friend.message.memory.graph import MemoryGraph


def create_system_message():
    system_prompts = SystemPrompt.objects.filter(title='记忆').order_by('order_number')
    prompt = ''.join(sp.prompt for sp in system_prompts)
    return SystemMessage(prompt)


def create_human_message(friend):
    prompt = f'【原始记忆】\n{friend.memory or "暂无"}\n'
    prompt += '【最近对话】\n'
    messages = list(
        FriendMessage.objects.filter(friend=friend).order_by('-id')[:10]
    )
    messages.reverse()
    for m in messages:
        prompt += f'user: {m.user_message}\n'
        prompt += f'ai: {m.output}\n'
    return HumanMessage(prompt)


def update_memory(friend):
    """调用记忆图，把「旧记忆 + 最近对话」压成一段新记忆写回 Friend.memory。"""
    app = MemoryGraph.create_app()

    inputs = {
        'messages': [
            create_system_message(),
            create_human_message(friend),
        ]
    }

    res = app.invoke(inputs)
    friend.memory = res['messages'][-1].content
    friend.update_time = now()
    friend.save()
