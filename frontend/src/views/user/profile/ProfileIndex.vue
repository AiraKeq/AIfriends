<script setup>

import Username from "@/views/user/profile/components/Username.vue";
import Photo from "@/views/user/profile/components/Photo.vue";
import {useUserStore} from "@/stores/user.js";
import Profile from "@/views/user/profile/components/Profile.vue";

const user = useUserStore()
</script>

<template>
  <div class="flex justify-center">
    <div class="card w-120 bg-base-200 shadow-sm mt-16">
      <div class="card-body w-120">
        <h3 class="text-lg font-bold my-4">编辑资料</h3>
        <Photo :photo="user.photo"/>
        <Username :username="user.username"/>
        <profile :profile="user.profile"/>
        <div class="flex justify-center">
          <button class="btn btn-neutral w-60 mt-2">更新</button>
        </div>
      </div>

    </div>
  </div>
</template>

<style scoped>

</style>
