from .api_views import RefreshView, LogoutView
from web.views.user.account.login import LoginViews
from django.urls import path
from web.views.index import index
from web.views.user.account.register import RegisterView

urlpatterns = [
    path('api/user/account/login/',LoginViews.as_view()),
    path('api/user/account/logout/',LogoutView.as_view()),
    path('api/user/account/register/', RegisterView.as_view()),
    path('api/user/account/refresh_token/',RefreshView.as_view()),

    path('',index)
]
