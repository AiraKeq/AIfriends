import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/chat' },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true },          // 不需要登录
    },
    {
      path: '/chat',
      name: 'chat',
      component: () => import('@/views/ChatView.vue'),
    },
    {
      path: '/chat/:id',
      name: 'chat-detail',
      component: () => import('@/views/ChatView.vue'),
    },
    { path: '/:pathMatch(.*)*', redirect: '/chat' },
  ],
})

// 路由守卫：没登录就往 /login 赶
router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.isAuthenticated()) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  // 已登录还去登录页，直接送回聊天
  if (to.meta.public && auth.isAuthenticated() && to.name === 'login') {
    return { name: 'chat' }
  }
  return true
})

export default router
