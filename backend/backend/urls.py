from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('web.api_urls')),      # 认证 + 聊天 API
    path('', include('web.urls')),              # 前端页面（最后，别抢前面的）
]

# Development only. In production nginx serves these.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
