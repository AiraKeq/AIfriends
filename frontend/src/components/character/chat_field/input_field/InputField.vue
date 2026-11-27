<script setup>
import SendIcon from "@/components/character/icons/SendIcon.vue";
import MicIcon from "@/components/character/icons/MicIcon.vue";
import {onUnmounted, ref, useTemplateRef} from "vue";
import streamApi from "@/js/http/streamApi.js";
import api from "@/js/http/api.js";
import Microphone from "@/components/character/chat_field/input_field/Microphone.vue";

const props = defineProps(['friendId'])
const emit = defineEmits(['pushBackMessage', 'addToLastMessage'])
const inputRef = useTemplateRef('input-ref')
const confirmRef = useTemplateRef('confirm-ref')
const message = ref('')
const pendingFact = ref('')
const deciding = ref(false)
const showMic = ref(false)
let processId = 0

// ───────────────────────────────────────────────────────────────────
// TTS 音频播放：后端流回来的是 base64 的 PCM 片段，要排队播放，
// 不能每片新建一个 AudioContext（会有缝隙和延迟）。
// ───────────────────────────────────────────────────────────────────
let audioCtx = null
let nextPlayTime = 0
let activeSources = []
const SAMPLE_RATE = 24000  // DeepSeek TTS 输出：24kHz、16 位、单声道 PCM

const initAudioStream = () => {
  stopAudio()
  audioCtx = new (window.AudioContext || window.webkitAudioContext)()
  nextPlayTime = 0
  activeSources = []
  audioCtx.resume().catch(() => {})
}

const stopAudio = () => {
  activeSources.forEach(src => {
    try {
      src.stop()
    } catch (e) {
      // 已经停过的 source 再 stop 会抛，忽略
    }
  })
  activeSources = []
  nextPlayTime = 0

  if (audioCtx) {
    audioCtx.close().catch(() => {})
    audioCtx = null
  }
}

const handleAudioChunk = (base64Data) => {  // base64 的 PCM 片段 → 排队播放
  if (!audioCtx) return
  try {
    const binary = atob(base64Data)
    const bytes = new Uint8Array(binary.length)
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i)
    }
    const sampleCount = Math.floor(bytes.length / 2)
    if (sampleCount === 0) return

    const buffer = audioCtx.createBuffer(1, sampleCount, SAMPLE_RATE)
    const channel = buffer.getChannelData(0)
    const view = new DataView(bytes.buffer)
    for (let i = 0; i < sampleCount; i++) {
      channel[i] = view.getInt16(i * 2, true) / 32768
    }

    const source = audioCtx.createBufferSource()
    source.buffer = buffer
    source.connect(audioCtx.destination)
    const startAt = Math.max(audioCtx.currentTime, nextPlayTime)
    source.start(startAt)
    nextPlayTime = startAt + buffer.duration

    activeSources.push(source)
    source.onended = () => {
      activeSources = activeSources.filter(s => s !== source)
    }
  } catch (e) {
    console.error("Audio Decode Error:", e)
  }
}

onUnmounted(() => {
  stopAudio()
})

// ───────────────────────────────────────────────────────────────────
// 确认门
// ───────────────────────────────────────────────────────────────────
function openConfirm(payload) {
  const fact = payload?.fact || ''
  if (!fact) return
  pendingFact.value = fact
  confirmRef.value.showModal()
}

async function handleDecision(approve) {
  if (deciding.value) return
  deciding.value = true
  confirmRef.value.close()

  try {
    const res = await api.post('/api/friend/message/chat/resume/', {
      friend_id: props.friendId,
      approve,
    })
    if (res.data.result === 'success' && res.data.content) {
      emit('addToLastMessage', res.data.content)
    }
  } catch (err) {
    console.error(err)
    emit('addToLastMessage', '（确认失败，请稍后重试）')
  } finally {
    deciding.value = false
    pendingFact.value = ''
  }
}

// ───────────────────────────────────────────────────────────────────
// 发消息（文字 / 语音共用）
// ───────────────────────────────────────────────────────────────────
function focus() {
  inputRef.value.focus()
}

async function handleSend(event, audio_msg) {
  let content
  if (audio_msg) {
    content = audio_msg.trim()
  } else {
    content = message.value.trim()
  }
  if (!content) return

  initAudioStream()

  // ★ 打断旧回复 ★
  //   每次发消息都 ++processId，旧的那条流在 onmessage 里发现 curId 对不上就丢弃，
  //   它迟到的文字和音频都不会再画到界面上。
  const curId = ++processId
  message.value = ''

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

        // ★ 确认门事件：不是正文，不能追加到消息里 ★
        if (data && data.event === 'interrupt') {
          openConfirm(data.payload)
          return
        }

        if (data && data.content) {
          emit('addToLastMessage', data.content)
        }
        if (data && data.audio) {
          handleAudioChunk(data.audio)
        }
        if (data && data.error) {
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
  showMic.value = false
  stopAudio()
}

// 用户开口说话时打断播放；也是「停止接收/播放」的统一入口
function handleStop() {
  ++processId
  stopAudio()
}

defineExpose({
  focus,
  close,
})
</script>

<template>
  <form v-if="!showMic" @submit.prevent="handleSend" class="absolute bottom-4 left-2 h-12 w-86 flex items-center">
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
    <div @click="showMic = true" class="absolute right-10 w-8 h-8 flex justify-center items-center cursor-pointer">
      <MicIcon />
    </div>
  </form>

  <Microphone
      v-else
      @close="showMic = false"
      @send="handleSend"
      @stop="handleStop"
  />

  <!-- 确认门：模型提议记住某件事，等用户点头 -->
  <dialog ref="confirm-ref" class="modal">
    <div class="modal-box">
      <h3 class="text-lg font-bold">要记住这件事吗？</h3>
      <p class="py-4 text-sm break-all">{{ pendingFact }}</p>
      <p class="text-xs opacity-60">
        同意之后才会写进长期记忆；拒绝的话这次就不存。
      </p>
      <div class="modal-action">
        <button class="btn btn-sm" :disabled="deciding" @click="handleDecision(false)">不用</button>
        <button class="btn btn-sm btn-neutral" :disabled="deciding" @click="handleDecision(true)">记住</button>
      </div>
    </div>
  </dialog>
</template>

<style scoped>

</style>
