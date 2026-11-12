from web.views.user.account.get_user_info import GetUserInfoView
from web.views.user.account.refresh_token import RefreshTokenViews
from web.views.user.account.logout import LogoutView
from web.views.user.account.login import LoginViews
from django.urls import path, re_path
from web.views.index import index
from web.views.user.account.register import RegisterView
from web.views.user.profile.update import UpdateProfileView

urlpatterns = [
    path('api/user/account/login/',LoginViews.as_view()),
    path('api/user/account/logout/',LogoutView.as_view()),
    path('api/user/account/register/', RegisterView.as_view()),
    path('api/user/account/refresh_token/', RefreshTokenViews.as_view()),
    path('api/user/account/get_user_info/',GetUserInfoView.as_view()),
    path('api/user/profile/update/',UpdateProfileView.as_view()),

    path('',index),

    # 管理后台交给 Django，前端兜底不要接住 /admin。
    re_path(r'^(?!admin(?:/|$)|media/|static/|assets/).*$', index),
]
