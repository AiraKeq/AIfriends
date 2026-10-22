<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const username = ref('')
const password = ref('')
const error = ref('')

async function submit() {
  if (auth.loading) return
  error.value = ''
  try {
    await auth.login(username.value, password.value)
    await router.replace({ name: 'homepage-index' })
  } catch (e) {
    const data = e.response?.data
    if (data?.detail) {
      error.value = data.detail
    } else if (data && typeof data === 'object') {
      error.value = Object.values(data).flat().join(' ')
    } else {
      error.value = '登录失败，请检查网络连接后重试'
    }
  }
}
</script>

<template>
  <div class="login-index">
    <!-- 把 mt-[100px] 换成 pt-[100px] -->
    <div class="flex justify-center pt-[100px]">
      <form @submit.prevent="submit">
        <fieldset class="fieldset bg-base-200 border-base-300 rounded-box w-xs border p-4">
          <legend class="fieldset-legend text-xl font-semibold">注册</legend>

          <label class="label">用户名</label>
          <input v-model="username" type="text" class="input" placeholder="用户名" autocomplete="username" required />

          <label class="label">密码</label>
          <input v-model="password" type="password" class="input" placeholder="密码" autocomplete="current-password" required />

          <label class="label">确认密码</label>
          <input v-model="password" type="password" class="input" placeholder="确认密码" autocomplete="current-password" required />


          <p v-if="error" role="alert" class="text-error">{{ error }}</p>
          <button type="submit" class="btn btn-neutral mt-4" :disabled="auth.loading">
            {{ auth.loading ? '注册中…' : '注册' }}
          </button>
          <div class="flex justify-end">
            <RouterLink :to="{name:'login-index'}" class="btn btn-sm btn-ghost text-gray-500">
              登录
            </RouterLink>
          </div>
        </fieldset>
      </form>
    </div>
  </div>
</template>

<style scoped>
</style>
