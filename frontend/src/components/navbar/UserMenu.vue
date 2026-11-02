<script setup>

import {useUserStore} from "@/stores/user.js";
import UserSpaceIndex from "@/components/icons/UserSpaceIndex.vue";
import ProfileIndex from "@/views/profile/ProfileIndex.vue";
import UserProfileIcon from "@/components/icons/UserProfileIcon.vue";
import UserLogoutIcon from "@/components/icons/UserLogoutIcon.vue";


const user =useUserStore()

function closeMenu(){
  const element = document.activeElement
  if(element && element instanceof HTMLElement)element.blur()
}
</script>

<template>
  <div class="dropdown dropdown-end">
    <div tabindex="0" role="button" class="avatar btn btn-circle w-10 h-10 mr-6 ">
      <div class="w-10 rounded-full">
        <img :src="user.photo" alt="">
      </div>
    </div>
    <ul tabindex="-1" class="dropdown-content menu bg-base-100 rounded-box z-1 w-52 p-2 shadow-lg">
      <li>
        <RouterLink @click="closeMenu" :to="{name: 'user-space-index',params:{user_id:user.id}}">
          <div class="avatar">
            <div class="w-12 rounded-full">
              <img :src="user.photo" alt="">
            </div>
          </div>
          <span class="text-base font-bold line-clamp-1">{{user.username}}</span>
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
        <a  @click="closeMenu" class="text-sm font-bold py-3">
          <UserLogoutIcon />
          退出登录
        </a>
      </li>
    </ul>
  </div>
</template>

<style scoped>

</style>