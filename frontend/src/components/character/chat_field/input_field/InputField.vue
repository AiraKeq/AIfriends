<script setup>
import SendIcon from "@/components/character/icons/SendIcon.vue";
import {ref, useTemplateRef} from "vue";
import streamApi from "@/js/http/streamApi.js";

const props = defineProps(['friendId'])
const emit = defineEmits(['pushBackMessage', 'addToLastMessage'])
const inputRef = useTemplateRef('input-ref')
const message = ref('')
let processId = 0

function focus() {
  inputRef.value.focus()
}

async function handleSend() {
  const content = message.value.trim()
  if (!content) return

  const curId = ++processId
  message.value = ''

  // 先把自己这句话和一条空的 AI 消息画上去，流式片段再往空的里追加
  emit('pushBackMessage', {role: 'user', content: content, id: crypto.randomUUID()})
  emit('pushBackMessage', {role: 'ai', content: '', id: crypto.randomUUID()})

  try {
    await streamApi('/api/friend/message/chat/', {
      body: {
        friend_id: props.friendId,
        message: content,
      },
      onmessage(data, isDone) {
        if (curId !== processId) return

        if (data.content) {
          emit('addToLastMessage', data.content)
        }
        if (data.error) {
          emit('addToLastMessage', `（${data.error}）`)
        }
      },
      onerror(err) {
        console.error(err)
      },
    })
  } catch (err) {
    console.error(err)
  }
}

function close() {
  ++processId
}

defineExpose({
  focus,
  close,
})
</script>

<template>
  <form @submit.prevent="handleSend" class="absolute bottom-4 left-2 h-12 w-86 flex items-center">
    <input
        ref="input-ref"
        v-model="message"
        class="input bg-black/30 backdrop-blur-sm text-white text-base w-full h-full rounded-2xl pr-20"
        type="text"
        placeholder="文本输入..."
    >
    <div @click="handleSend" class="absolute right-2 w-8 h-8 flex justify-center items-center cursor-pointer">
      <SendIcon />
    </div>
  </form>
</template>

<style scoped>

</style>
