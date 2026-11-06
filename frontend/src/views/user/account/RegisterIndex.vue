<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {useUserStore} from "@/stores/user.js";
import api from "@/js/http/api.js";

const auth = useAuthStore()
const router = useRouter()
const username = ref('')
const password = ref('')
const passwordConfirm = ref('')
const errorMessage = ref('')

const user = useUserStore()

async function handleRegister() {
  errorMessage.value = ''
  if (!username.value.trim()){
    errorMessage.value = '用户名不能为空'
  }else if(!password.value.trim()){
    errorMessage.value = '密码不能为空'
  }else if(password.value.trim() !==passwordConfirm.value.trim()){
    errorMessage.value = '两次输入的密码不一样'
  }else{
    try {
      const res = await api.post('/api/user/account/register/',{
        username: username.value,
        password: password.value,
      })
      const data = res.data
      if(data.result==='success'){
        user.setAccessToken(data.access)
        user.setUserInfo(data)
        await router.push({
          name: 'homepage-index'
        })
      }else{
        errorMessage.value = data.result
      }
    }catch(err){
      console.log(err)
      errorMessage.value = '注册请求失败，请稍后重试'
    }
  }
}
</script>

<template>
  <div class="login-index">
    <!-- 把 mt-[100px] 换成 pt-[100px] -->
    <div class="flex justify-center pt-[100px]">
      <form @submit.prevent="handleRegister" novalidate>
        <fieldset class="fieldset bg-base-200 border-base-300 rounded-box w-xs border p-4">
          <legend class="fieldset-legend text-xl font-semibold">注册</legend>

          <label class="label">用户名</label>
          <input v-model="username" type="text" class="input" placeholder="用户名" autocomplete="username" required />

          <label class="label">密码</label>
          <input v-model="password" type="password" class="input" placeholder="密码" autocomplete="current-password" required />

          <label class="label">确认密码</label>
          <input v-model="passwordConfirm
 " type="password" class="input" placeholder="确认密码" autocomplete="current-password" required />


          <p v-if="errorMessage" role="alert" class="text-sm text-red-500 mt-1">{{ errorMessage }}</p>
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
