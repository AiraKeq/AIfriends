"""前端页面路由。

Django 在这里只做一件事：把「不是 API、不是 admin、不是静态文件」的路径
统统交还给前端，让 Vue Router 自己去解析。

为什么必须有一条 catch-all（前端路由回退）：
  Vue Router 用的是 history 模式，地址是 /login、/chat/1 这种，不带 #。
  用户在 /login 按 F5，浏览器就去问 Django 要 /login ——
  如果 Django 没有这条路由，直接 404，页面白屏。
  （2026-10-09 实测：/login、/chat、/chat/1 全部 404，就是缺这一条。）
"""

from pathlib import Path

from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound
from django.urls import path

from .views import index


def spa_fallback(request, path=''):
    """把未知路径还给前端，但放行真正的静态资源。

    两条判断都不是可有可无的：
      - 带后缀的（.js/.css/vite.svg...）就是资源请求。抓不到就该 404，
        回退成 HTML 会让浏览器拿一页 HTML 当 JS 去解析，报一堆莫名其妙的
        语法错误，比 404 难查得多。
      - 静态目录下的同理，交给 staticfiles 处理，别在这里拦。

    注意这个视图挂在最末尾：Django 按顺序匹配，/api/ 和 /admin/ 在前面
    已经被各自的 include 接走了，所以不会走到这里。
    """
    if Path(path).suffix:
        return HttpResponseNotFound()
    if path.startswith('static/'):
        return HttpResponseNotFound()

    built = Path(settings.BASE_DIR) / 'static' / 'frontend' / 'index.html'
    if not built.exists():
        return HttpResponse(
            'Frontend not built yet -- run "npm run build" in F:\\AIFriends\\frontend.',
            status=503,
        )
    return HttpResponse(built.read_text(encoding='utf-8'))


urlpatterns = [
    path('', index, name='index'),
    path('<path:path>', spa_fallback, name='spa-fallback'),
]
