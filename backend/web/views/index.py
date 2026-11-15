from pathlib import Path

from django.conf import settings
from django.http import HttpResponse


def index(request):
    # 使用 Vite 生成的入口，避免重新构建后模板仍引用旧的资源文件名。
    built = Path(settings.BASE_DIR) / 'static' / 'frontend' / 'index.html'
    if not built.is_file():
        return HttpResponse(
            'Frontend not built yet -- run "npm run build" in the frontend directory.',
            status=503,
            content_type='text/plain; charset=utf-8',
        )
    return HttpResponse(built.read_text(encoding='utf-8'))
