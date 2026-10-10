/**
 * 认证状态。用 Pinia，因为「当前用户」和「是否登录」要跨多个组件共享。
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import http, { tokenStore } from '@/api/http'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const loading = ref(false)

  /** 是否已登录：有 access 就先当登录态，真实有效性由后端 401 判定。 */
  const isAuthenticated = () => Boolean(tokenStore.getAccess())

  async function login(username, password) {
    loading.value = true
    try {
      const { data } = await http.post('/auth/login/', { username, password })
      tokenStore.set(data)
      user.value = data.user
      return data
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    try {
      const refresh = tokenStore.getRefresh()
      await http.post('/auth/logout/', refresh ? { refresh } : {})
    } catch {
      // 后端失败（比如 refresh 已过期）也要把本地清干净，否则用户卡在「假登录」状态
    } finally {
      tokenStore.clear()
      user.value = null
    }
  }

  /** 刷新页面后把用户信息取回来（token 在 localStorage 里还在）。 */
  async function fetchMe() {
    if (!isAuthenticated()) return null
    try {
      const { data } = await http.get('/auth/me/')
      user.value = data
      return data
    } catch {
      // 拦截器已经处理过刷新；到这里说明真的失效了
      user.value = null
      return null
    }
  }

  function clear() {
    tokenStore.clear()
    user.value = null
  }

  return { user, loading, isAuthenticated, login, logout, fetchMe, clear }
})
