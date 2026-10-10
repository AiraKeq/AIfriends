<script setup>
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

// 刷新页面后：token 还在 localStorage，但 user 是空的。
// 这里把它取回来，页面顶部的用户名才不会一闪就没。
onMounted(() => {
  if (auth.isAuthenticated() && !auth.user) {
    auth.fetchMe()
  }
})
</script>

<template>
  <router-view />
</template>
