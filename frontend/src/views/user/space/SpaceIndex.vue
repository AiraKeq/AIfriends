<script setup>
import {useRoute} from "vue-router";

const route = useRoute()
</script>

<template>
  <div class="space-index">
    个人空间:{{route.params.user_id}}
  </div>
</template>

<style scoped>
</style>
