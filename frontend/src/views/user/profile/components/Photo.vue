<script setup>
import {ref,watch} from "vue";

const props = defineProps(["photo"])


const myPhoto = ref(props.photo)

watch(()=>props.photo,newVal=>{
  myPhoto.value = newVal
})
</script>

<template>

</template>

<style scoped>

</style>