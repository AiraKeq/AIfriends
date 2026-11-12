<script setup>
import {ref,watch} from "vue";

const props = defineProps(["profile"])


const myProfile = ref(props.profile)

watch(()=>props.profile,newVal=>{
  myProfile.value = newVal
})
</script>

<template>

</template>

<style scoped>

</style>