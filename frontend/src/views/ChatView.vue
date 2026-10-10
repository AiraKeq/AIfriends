<script setup>
import { computed, onMounted, ref, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import http from '@/api/http'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const conversations = ref([])
const current = ref(null)        // 当前会话详情（含 messages）
const draft = ref('')
const sending = ref(false)
const listEl = ref(null)

const currentId = computed(() => (route.params.id ? Number(route.params.id) : null))

async function loadList() {
  const { data } = await http.get('/conversations/')
  // 后端没开分页，直接是数组；开了分页则是 {results: [...]}
  conversations.value = Array.isArray(data) ? data : (data.results ?? [])
}

async function loadDetail(id) {
  if (!id) { current.value = null; return }
  const { data } = await http.get(`/conversations/${id}/`)
  current.value = data
  scrollToBottom()
}

async function newConversation() {
  const { data } = await http.post('/conversations/', { title: '新对话' })
  await loadList()
  router.push(`/chat/${data.id}`)
}

async function send() {
  const text = draft.value.trim()
  if (!text || sending.value) return

  let id = currentId.value
  if (!id) {
    // 还没有会话：先建一个再发
    const { data } = await http.post('/conversations/', { title: '新对话' })
    id = data.id
    await loadList()
    await router.push(`/chat/${id}`)
  }

  sending.value = true
  draft.value = ''

  // 先把用户消息画上去（乐观更新），不然要等一个来回才看到自己说的话
  if (!current.value) current.value = { id, title: '', messages: [] }
  current.value.messages.push({ id: -1, role: 'user', content: text, created_at: new Date().toISOString() })
  scrollToBottom()

  try {
    const { data } = await http.post(`/conversations/${id}/messages/`, { content: text })
    // 用服务端返回的真实记录替换掉刚才那条临时的
    current.value.messages.splice(-1, 1, data.user_message)
    current.value.messages.push(data.assistant_message)
    await loadList()
  } catch (e) {
    // 失败就把那句话还回输入框，别让用户白打
    draft.value = text
    current.value.messages.pop()
    alert('发送失败：' + (e.response?.data?.detail || e.message))
  } finally {
    sending.value = false
    scrollToBottom()
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (listEl.value) listEl.value.scrollTop = listEl.value.scrollHeight
  })
}

async function removeConversation(id) {
  if (!confirm('删除这个对话？')) return
  await http.delete(`/conversations/${id}/`)
  await loadList()
  if (id === currentId.value) router.push('/chat')
}

onMounted(async () => {
  await loadList()
  await loadDetail(currentId.value)
})

// 切换会话（点侧边栏、或地址栏变了）
watch(currentId, (id) => loadDetail(id))
</script>

<template>
  <div class="layout">
    <aside class="sidebar">
      <button class="new" @click="newConversation">+ 新对话</button>

      <ul class="list">
        <li
          v-for="c in conversations"
          :key="c.id"
          :class="{ active: c.id === currentId }"
        >
          <router-link :to="`/chat/${c.id}`" class="item">
            <span class="title">{{ c.title }}</span>
            <span class="meta">{{ c.message_count }} 条</span>
          </router-link>
          <button class="del" title="删除" @click.stop="removeConversation(c.id)">×</button>
        </li>
      </ul>

      <div class="me">
        <span>{{ auth.user?.username || '…' }}</span>
        <button @click="auth.logout().then(() => router.push('/login'))">退出</button>
      </div>
    </aside>

    <main class="main">
      <div ref="listEl" class="messages">
        <p v-if="!current?.messages?.length" class="empty">
          说点什么吧 —— 现在还是占位回复，模型接上之前只负责把链路跑通。
        </p>

        <div
          v-for="m in current?.messages || []"
          :key="m.id"
          class="msg"
          :class="m.role"
        >
          <div class="bubble">{{ m.content }}</div>
        </div>
      </div>

      <form class="composer" @submit.prevent="send">
        <textarea
          v-model="draft"
          rows="1"
          placeholder="输消息，Enter 发送，Shift+Enter 换行"
          @keydown.enter.exact.prevent="send"
        ></textarea>
        <button type="submit" :disabled="sending || !draft.trim()">
          {{ sending ? '…' : '发送' }}
        </button>
      </form>
    </main>
  </div>
</template>

<style scoped>
.layout { display: flex; height: 100vh; background: #f5f6f8; }

.sidebar {
  width: 240px;
  flex: none;
  background: #fff;
  border-right: 1px solid #eee;
  display: flex;
  flex-direction: column;
  padding: 12px;
  gap: 10px;
}
.new {
  height: 36px;
  border: 1px solid #4f9dd9;
  background: #fff;
  color: #4f9dd9;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
}
.list { list-style: none; margin: 0; padding: 0; flex: 1; overflow-y: auto; }
.list li { display: flex; align-items: center; border-radius: 8px; }
.list li:hover { background: #f2f5f8; }
.list li.active { background: #e8f2fb; }
.item {
  flex: 1;
  min-width: 0;
  padding: 8px 10px;
  text-decoration: none;
  color: #333;
  display: flex;
  justify-content: space-between;
  gap: 6px;
  font-size: 14px;
}
.title { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.meta { color: #aaa; font-size: 12px; flex: none; }
.del { border: none; background: none; color: #bbb; cursor: pointer; font-size: 16px; padding: 0 6px; }
.del:hover { color: #d9534f; }
.me {
  border-top: 1px solid #eee;
  padding-top: 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: #666;
}
.me button {
  border: none; background: none; color: #4f9dd9; cursor: pointer; font-size: 13px;
}

.main { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.messages { flex: 1; overflow-y: auto; padding: 24px; display: flex; flex-direction: column; gap: 12px; }
.empty { color: #aaa; font-size: 14px; text-align: center; margin-top: 40px; }
.msg { display: flex; }
.msg.user { justify-content: flex-end; }
.bubble {
  max-width: 70%;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}
.msg.user .bubble { background: #4f9dd9; color: #fff; border-bottom-right-radius: 4px; }
.msg.assistant .bubble { background: #fff; color: #333; border-bottom-left-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,.06); }

.composer {
  flex: none;
  display: flex;
  gap: 10px;
  padding: 14px 24px 20px;
  border-top: 1px solid #eee;
  background: #fff;
}
.composer textarea {
  flex: 1;
  resize: none;
  max-height: 140px;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 10px;
  font-size: 14px;
  font-family: inherit;
}
.composer textarea:focus { outline: none; border-color: #4f9dd9; }
.composer button {
  flex: none;
  width: 72px;
  border: none;
  border-radius: 10px;
  background: #4f9dd9;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
}
.composer button:disabled { opacity: .5; cursor: default; }
</style>
