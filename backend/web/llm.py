"""DeepSeek 模型接入。

单独放一个文件的原因:这是整个后端唯一「会花你的钱、会超时、会失败」的地方。
把它和视图分开,视图只负责存取数据库、调用这里、回包;
失败怎么处理、prompt 怎么组装,都集中在这一个文件里,别处不用关心。

为什么用 openai 这个 SDK 去调 DeepSeek:
DeepSeek 的接口是 OpenAI 兼容的 —— 同一个 SDK,只换 base_url 和 key。
不用另学一套 API,官方文档也是这么建议的。
"""

import os
import sys

from openai import APIError, APITimeoutError, OpenAI, RateLimitError

# 可覆盖,方便换 deepseek-reasoner 之类
DEFAULT_MODEL = os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat')
BASE_URL = os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
TIMEOUT_S = float(os.environ.get('DEEPSEEK_TIMEOUT', '60'))

# 只保留最近这么多条历史。deepseek-chat 的上下文有 64K,
# 但每轮都全量发过去既慢又贵;30 条约等于 15 轮问答,够用了。
HISTORY_LIMIT = 30

SYSTEM_PROMPT = (
    '你是「AI Friends」里的伙伴,说话自然、亲切、简洁。'
    '回答用中文,除非用户用别的语言。'
    '不要自称「作为一个AI」。'
)


class LLMUnavailable(Exception):
    """模型侧不可用 —— 缺 key、超时、限流、接口报错,都归这里。

    视图捕获它,把话转成人能看懂的一句,而不是把堆栈丢给用户。
    """


def _read_windows_user_env(name):
    """从 Windows 注册表读「用户环境变量」。

    为什么需要这个兜底(2026-10-09 实际踩到):
      环境变量是「进程启动那一刻的快照」。
      用户后来在 系统设置 里加了 DEEPSEEK_API_KEY,注册表里有了,
      但**已经开着的终端、以及从它启动的一切进程都看不到它** ——
      必须重开终端才会带上。

      症状很有欺骗性:同一个 key,在刚开的 PowerShell 里能读到,
      在你现在这个终端里读不到。加了这个兜底之后,不用重开任何东西。

    @returns 变量值;读不到(非 Windows / 没有该变量)时返回 ''
    """
    if sys.platform != 'win32':
        return ''
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as k:
            return str(winreg.QueryValueEx(k, name)[0])
    except Exception:
        return ''


def read_api_key():
    """按优先级找 key:先环境变量,再注册表。"""
    key = (os.environ.get('DEEPSEEK_API_KEY') or '').strip()
    if key:
        return key
    return _read_windows_user_env('DEEPSEEK_API_KEY').strip()


_client = None
_client_key = None


def get_client():
    """惰性建客户端。

    不放在模块顶层:那样 import 这个模块时就会读 key,
    缺 key 会直接让 Django 起不来。惰性化之后,没配 key 也能正常启动,
    只是发消息时才告诉你「还没配 key」。
    """
    global _client, _client_key

    api_key = read_api_key()
    if not api_key:
        raise LLMUnavailable(
            '还没配置 DEEPSEEK_API_KEY。'
            '在系统环境变量里加一个(或在 F:\\AIFriends\\.env 里写),然后重启服务。'
        )

    # key 变了就重建客户端 —— 否则改了 .env 不重启不生效
    if _client is None or _client_key != api_key:
        _client = OpenAI(api_key=api_key, base_url=BASE_URL, timeout=TIMEOUT_S)
        _client_key = api_key
    return _client


def build_messages(conversation):
    """把数据库里的消息转成大模型要的格式。

    顺序天然是对的:Message.Meta.ordering = ['created_at'],
    而大模型要求的正是「按时间正序」。

    两个容易忽略的点:
      1. 只取最后 HISTORY_LIMIT 条 —— 不加这个,聊久了每轮请求体越来越大。
      2. 角色名必须是 user / assistant —— 数据库里存的正好就是这两个值。
    """
    history = list(conversation.messages.all())[-HISTORY_LIMIT:]
    return [{'role': 'system', 'content': SYSTEM_PROMPT}] + [
        {'role': m.role, 'content': m.content} for m in history
    ]


def chat(conversation):
    """拿整段对话历史问模型,返回回复文本。

    @param conversation - 已经存好当前用户消息的 Conversation 实例
    @returns 模型的回复文本
    @raises LLMUnavailable - 任何模型侧的问题
    """
    client = get_client()
    messages = build_messages(conversation)

    try:
        resp = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=messages,
            stream=False,
        )
    except APITimeoutError as exc:
        raise LLMUnavailable(f'模型响应超时（{TIMEOUT_S:.0f} 秒），稍后再试') from exc
    except RateLimitError as exc:
        raise LLMUnavailable('触发限流或余额不足，稍后再试') from exc
    except APIError as exc:
        # 401(错误key) / 402(欠费) / 400(参数) 都会落到这里
        raise LLMUnavailable(f'模型接口报错：{exc}') from exc
    except Exception as exc:
        # 网络不通等 —— 不吞掉,转成同一类异常,视图那边统一处理
        raise LLMUnavailable(f'调用模型失败：{exc}') from exc

    if not resp.choices:
        raise LLMUnavailable('模型没有返回任何内容')

    text = (resp.choices[0].message.content or '').strip()
    return text or '（模型返回了空内容）'
