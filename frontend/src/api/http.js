/**
 * axios 实例 —— 「无感刷新」的客户端那一半就在这里。
 *
 * 双 Token 的分工：
 *   access   活 30 分钟，每次请求带在 Authorization 头里
 *   refresh  活 7 天，只用来换新的 access（后端还把它塞进了 httpOnly cookie）
 *
 * 「无感」的意思是：用户在页面上正常操作，access 悄悄过期了，
 * 前端自己拿 refresh 换一对新的、把原请求重发一遍，用户完全不知道。
 */
import axios from 'axios'

const ACCESS_KEY = 'aifriends.access'
const REFRESH_KEY = 'aifriends.refresh'

export const tokenStore = {
  getAccess: () => localStorage.getItem(ACCESS_KEY),
  getRefresh: () => localStorage.getItem(REFRESH_KEY),
  set({ access, refresh }) {
    if (access) localStorage.setItem(ACCESS_KEY, access)
    // ★ 后端开了 ROTATE_REFRESH_TOKENS：每次刷新都会发一个新的 refresh，
    //   必须覆盖旧的，否则下一次刷新会用已被拉黑的那个，直接失败。
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
  },
}

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api',
  timeout: 15000,
  // 让浏览器带上 refresh 的 httpOnly cookie
  withCredentials: true,
})

// ── 请求拦截器：每个请求自动带上 access ──────────────────────────────
http.interceptors.request.use((config) => {
  const access = tokenStore.getAccess()
  if (access) config.headers.Authorization = `Bearer ${access}`
  return config
})

// ── 响应拦截器：撞到 401 就刷新，然后重发 ────────────────────────────
//
// 两个必须做对的地方：
//
//  1. 并发去重。页面同时发 3 个请求、access 恰好都过期 —— 三个都会拿到 401。
//     如果各自去刷新，就会发出 3 次 refresh：第一次成功并把旧 refresh 拉黑，
//     后两次拿已拉黑的 token 去换，全部失败，用户被莫名踢下线。
//     所以用一个共享 promise，让它们等同一个刷新结果。
//
//  2. 防死循环。刷新接口自己失败时不能再走刷新逻辑，否则无限递归。
let refreshing = null

http.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { response, config } = error
    const status = response?.status

    const isRefreshCall = (config?.url || '').includes('/auth/refresh/')
    if (status !== 401 || config?._retry || isRefreshCall) {
      return Promise.reject(error)
    }

    config._retry = true      // 这个请求最多重发一次

    try {
      if (!refreshing) {
        refreshing = http
          // 不传 refresh：让它走 httpOnly cookie。若没 cookie，退回 localStorage。
          .post('/auth/refresh/', tokenStore.getRefresh() ? { refresh: tokenStore.getRefresh() } : {})
          .then((res) => {
            tokenStore.set(res.data)
            return res.data
          })
          .finally(() => {
            // 无论成败都要清掉，否则后续 401 会一直等这个已经结束的 promise
            refreshing = null
          })
      }

      const data = await refreshing
      config.headers.Authorization = `Bearer ${data.access}`
      return http(config)          // 用新 access 重发原请求
    } catch (refreshError) {
      // refresh 也过期/被拉黑了 —— 真的该重新登录
      tokenStore.clear()
      if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
        window.location.replace('/login')
      }
      return Promise.reject(refreshError)
    }
  },
)

export default http
