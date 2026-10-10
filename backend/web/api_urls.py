"""URL 路由。

    /api/auth/login/     登录
    /api/auth/refresh/   无感刷新(客户端每 30 分钟自动调一次)
    /api/auth/logout/    登出(拉黑 refresh)
    /api/auth/me/        当前用户
    /api/conversations/  会话 CRUD(DefaultRouter 生成)
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ChatViewSet, LoginView, LogoutView, MeView, RefreshView

router = DefaultRouter()
router.register('conversations', ChatViewSet, basename='conversation')

urlpatterns = [
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/refresh/', RefreshView.as_view(), name='auth-refresh'),
    path('auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('auth/me/', MeView.as_view(), name='auth-me'),
    path('', include(router.urls)),
]
