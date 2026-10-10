<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const username = ref('')
const password = ref('')
const error = ref('')

async function submit() {
  error.value = ''
  try {
    await auth.login(username.value, password.value)
    router.replace(route.query.redirect || '/chat')
  } catch (e) {
    // 后端的错误形状：字段错误 {} 或 {'detail': '...'}
    const data = e.response?.data
    if (data?.detail) {
      error.value = data.detail
    } else if (data && typeof data === 'object') {
      error.value = Object.values(data).flat().join(' ')
    } else {
      error.value = '登录失败，请检查用户名和密码'
    }
  }
}
</script>

<template>
  <div class="login-wrap">
    <form class="login-card" @submit.prevent="submit">
      <h1>AI Friends</h1>
      <p class="sub">登录后开始对话</p>

      <label>
        <span>用户名</span>
        <input v-model="username" autocomplete="username" required />
      </label>

      <label>
        <span>密码</span>
        <input v-model="password" type="password" autocomplete="current-password" required />
      </label>

      <p v-if="error" class="error">{{ error }}</p>

      <button type="submit" :disabled="auth.loading">
        {{ auth.loading ? '登录中…' : '登录' }}
      </button>
    </form>
  </div>
</template>

<style scoped>
.login-wrap {
  min-height: 100vh;
  display: grid;
  place-items: center;
  background: #f5f6f8;
}
.login-card {
  width: 320px;
  padding: 28px 26px;
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
  gap: 14px;
}
h1 { margin: 0; font-size: 22px; }
.sub { margin: 0 0 6px; color: #888; font-size: 13px; }
label { display: flex; flex-direction: column; gap: 6px; font-size: 13px; color: #555; }
input {
  height: 38px;
  padding: 0 10px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 14px;
}
input:focus { outline: none; border-color: #4f9dd9; }
button {
  height: 40px;
  border: none;
  border-radius: 8px;
  background: #4f9dd9;
  color: #fff;
  font-size: 15px;
  cursor: pointer;
}
button:disabled { opacity: 0.6; cursor: default; }
.error { margin: 0; color: #d9534f; font-size: 13px; }
</style>
