<script setup>
import Navbar from "@/components/navbar/Navbar.vue";
import {onMounted} from "vue";
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user.js'
import api from '@/js/http/api.js'

const route = useRoute()

const user = useUserStore()
const router = useRouter()

onMounted(async() => {
  try{
    const res = await api.get('/api/user/account/get_user_info/')
    const data = res.data
    if(data.result === 'success'){
      user.setUserInfo(data)
    }
  }catch(err){
    console.log(err)
  }finally{
    user.setHasPulledUserInfo(true)

    if (route.meta.needLogin && !user.isLogin()){
      await router.replace({
        name:'user-account-login-index'
      })
    }
  }
})
</script>

<template>
  <Navbar>
    <RouterView />
  </Navbar>
</template>
