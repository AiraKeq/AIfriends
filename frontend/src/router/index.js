import { createRouter, createWebHistory } from 'vue-router'
import HomepageIndex from "@/views/homepage/HomePageIndex.vue"
import FriendIndex from "@/views/friend/FriendIndex.vue"
import CreateIndex from "@/views/create/CreateIndex.vue"
import UpdateCharacter from "@/views/create/character/UpdateCharacter.vue"
import LoginIndex from "@/views/user/account/LoginIndex.vue"
import RegisterIndex from "@/views/user/account/RegisterIndex.vue"
import SpaceIndex from "@/views/user/space/SpaceIndex.vue"
import ProfileIndex from "@/views/user/profile/ProfileIndex.vue"
import NotFoundIndex from "@/views/error/NotFoundIndex.vue"
import {useUserStore} from "@/stores/user.js"

const router = createRouter({

  history: createWebHistory('/'),
  routes: [
    {
      path: '/',
      component: HomepageIndex,
      name: 'homepage-index',
      meta:{
        needLogin : true
      }
    },
    {
      path: '/friend',
      component: FriendIndex,
      name: 'friend-index',
      meta:{
        needLogin : true
      }
    },
    {
      // 创建角色页直接渲染在创作首页（和教程一致）
      path: '/create',
      component: CreateIndex,
      name: 'create-index' ,
      meta:{
        needLogin : true
      }
    },
    {
      path: '/create/character/update/:character_id',
      component: UpdateCharacter,
      name: 'update-character',
      meta:{
        needLogin : true
      }
    },
    {
      path: '/login',
      component: LoginIndex,
      name: 'login-index',
      meta:{
        needLogin : false
      }
    },
    {
      path: '/register',
      component: RegisterIndex,
      name: 'register-index',
      meta:{
        needLogin : false
      }
    },
    {
      path: '/user/space/:user_id',
      component: SpaceIndex,
      name: 'user-space-index',
      meta:{
        needLogin : false
      }
    },
    {
      path: '/profile',
      component: ProfileIndex,
      name: 'user-profile-index',
      meta:{
        needLogin : true
      }
    },
    {
      path: '/404/',
      component: NotFoundIndex,
      name: '404',
      meta:{
        needLogin : false
      }
    },
  ],
})

router.beforeEach((to) => {
    const user = useUserStore()

    // 登录恢复完成后，才判断是否需要跳转到登录页
    if (
        to.meta.needLogin &&
        user.hasPulledUserInfo &&
        !user.isLogin()
    ) {
        return {
            name: 'login-index',
        }
    }

    return true
})

export default router
