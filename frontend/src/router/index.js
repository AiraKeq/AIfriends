import { createRouter, createWebHistory } from 'vue-router'
import HomepageIndex from "@/views/homepage/HomePageIndex.vue"
import FriendIndex from "@/views/friend/FriendIndex.vue"
import CreateIndex from "@/views/create/CreateIndex.vue"
import LoginIndex from "@/views/user/account/LoginIndex.vue"
import RegisterIndex from "@/views/user/account/RegisterIndex.vue"
import SpaceIndex from "@/views/user/space/SpaceIndex.vue"
import ProfileIndex from "@/views/profile/ProfileIndex.vue"
import NotFoundIndex from "@/views/error/NotFoundIndex.vue"
import {useUserStore} from "@/stores/user.js"

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
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
      path: '/create',
      component: CreateIndex,
      name: 'create-index' ,
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
  if(to.meta.needLogin && user.setHasPulledUserInfo && !user.isLogin()) {
    return{
      name :  'login-index'
    }
  }
  return true
})

export default router
