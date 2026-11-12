<script setup>

import {useUserStore} from "@/stores/user.js";
import UserSpaceIndex from "@/components/icons/UserSpaceIndex.vue";
import UserProfileIcon from "@/components/icons/UserProfileIcon.vue";
import UserLogoutIcon from "@/components/icons/UserLogoutIcon.vue";
import {useRouter} from "vue-router";
import {ref} from "vue";
import api from "@/js/http/api.js";


const user =useUserStore()
const router = useRouter()
const errorMessage = ref('')

function closeMenu(){
  const element = document.activeElement
  if(element && element instanceof HTMLElement)element.blur()
}

async function handleLogout(){
  closeMenu()
  errorMessage.value = ''
  try{
    const res = await api.post('/api/user/account/logout/')
    if(res.data.result === 'success'){
      user.logout()
      await router.push({ name: 'homepage-index' })
    }else{
      errorMessage.value = '退出失败，请重试'
    }
  }catch{
    errorMessage.value = '退出请求失败，请稍后重试'
  }
}

</script>

<template>
  <div class="dropdown dropdown-end">
    <div tabindex="0" role="button" class="avatar btn btn-circle w-10 h-10 mr-6 ">
      <div class="w-10 rounded-full">
        <img :src="user.photo" alt="">
      </div>
    </div>
    <ul tabindex="-1" class="dropdown-content menu bg-base-100 rounded-box z-1 w-48 p-2 shadow-lg">
      <li class="min-w-0 w-full">
        <RouterLink @click="closeMenu" :to="{name: 'user-space-index',params:{user_id:user.id}}" class="flex min-w-0 w-full">
          <div class="avatar shrink-0">
            <div class="w-12 rounded-full">
              <img :src="user.photo" alt="">
            </div>
          </div>
          <span class="min-w-0 flex-1 truncate text-base font-bold" :title="user.username">{{user.username}}</span>
        </RouterLink>
      </li>
      <li>
        <RouterLink  @click="closeMenu" :to="{name:'user-space-index',params:{user_id:user.id}}" class="text-sm font-bold py-3">
          <UserSpaceIndex/>
          个人空间
        </RouterLink>
      </li>
      <li>
        <RouterLink  @click="closeMenu" :to="{name:'user-profile-index'}" class="text-sm font-bold py-3">
          <UserProfileIcon/>
          编辑资料
        </RouterLink>
      </li>
      <li></li>
      <li>
        <a  @click="handleLogout" class="text-sm font-bold py-3">
          <UserLogoutIcon />
          退出登录
        </a>
      </li>
    </ul>
    <p v-if="errorMessage" role="alert" class="mt-2 max-w-48 text-sm text-error">{{ errorMessage }}</p>
  </div>
</template>

<style scoped>

</style>