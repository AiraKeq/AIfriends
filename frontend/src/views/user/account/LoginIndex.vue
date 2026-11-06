<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user.js'
import api from "@/js/http/api.js";

const user = useUserStore()


const router = useRouter()
const username = ref('')
const password = ref('')
const errorMessage = ref('')

async function handleLogin(){
  errorMessage.value = ''
  if (!username.value.trim()) {
    errorMessage.value = '用户名不能为空'
  }else if (!password.value.trim()) {
    errorMessage.value = '密码不能为空'
  }else{
    try{
      const res =await api.post('/api/user/account/login/', {
        username: username.value,
        password: password.value,
      })
      const data = res.data
      if(data.result === 'success'){
        user.setAccessToken(data.access)
        user.setUserInfo(data)
        router.push({
          name: 'homepage-index'
        })
      }else{
        errorMessage.value = data.result
      }
    }catch(err){
      console.log(err)
    }
  }
}
</script>

<template>
  <div class="login-index">
    <!-- 把 mt-[100px] 换成 pt-[100px] -->
    <div class="flex justify-center pt-[100px]">
        <form @submit.prevent="handleLogin">
          <fieldset class="fieldset bg-base-200 border-base-300 rounded-box w-xs border p-4 ">
            <legend class="fieldset-legend text-xl font-semibold">登录</legend>

            <label class="label">用户名</label>
            <input v-model="username" type="text" class="input" placeholder="用户名" autocomplete="username" required />

            <label class="label">密码</label>
            <input v-model="password" type="password" class="input" placeholder="密码" autocomplete="current-password" required />

            <p v-if="errorMessage" class="text-sm text-red-500 mt-1">{{ errorMessage }}</p>
            <button @class="handleLogin" class="btn btn-neutral mt-4">登录</button>
            <div class="flex justify-end">
              <RouterLink :to="{name:'register-index'}" class="btn btn-sm btn-ghost text-gray-500">
                注册
              </RouterLink>
            </div>
          </fieldset>
        </form>
    </div>
  </div>
</template>

<style scoped>
</style>
