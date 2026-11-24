<script setup>
import Navbar from '@/components/navbar/Navbar.vue'
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user.js'
import api from '@/js/http/api.js'

const route = useRoute()
const router = useRouter()
const user = useUserStore()

onMounted(async () => {
    try {
        // 没有 access token 时，现有响应拦截器会尝试通过 Cookie 刷新
        const res = await api.get('/api/user/account/get_user_info/')
        const data = res.data

        if (data.result === 'success') {
            user.setUserInfo(data)
        }
    } catch {
        user.logout()
    } finally {
        user.setHasPulledUserInfo(true)

        // 登录恢复结束后，再决定是否跳转
        if (route.meta.needLogin && !user.isLogin()) {
            await router.replace({
                name: 'user-account-login-index',
            })
        }
    }
})
</script>

<template>
    <Navbar>
        <RouterView
            v-if="
                user.hasPulledUserInfo &&
                (!route.meta.needLogin || user.isLogin())
            "
        />
    </Navbar>
</template>