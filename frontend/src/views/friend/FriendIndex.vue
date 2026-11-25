<script setup>
import {nextTick, onBeforeUnmount, onMounted, ref, useTemplateRef} from "vue";
import Character from "@/components/character/Character.vue";
import api from "@/js/http/api.js";

const friends = ref([])
const isLoading = ref(false)
const hasFriends = ref(true)
const sentinelRef = useTemplateRef('sentinel-ref')

function checkSentinelVisible() {
  if (!sentinelRef.value) return false
  const rect = sentinelRef.value.getBoundingClientRect()
  return rect.top < window.innerHeight && rect.bottom > 0
}

async function loadMore() {
  if (isLoading.value || !hasFriends.value) return
  isLoading.value = true

  let newFriends = []
  try {
    const res = await api.get('/api/friend/get_list/', {
      params: {
        items_count: friends.value.length,
      }
    })
    const data = res.data
    if (data.result === 'success') {
      newFriends = data.friends
    }
  } catch (err) {
    console.log(err)
  } finally {
    isLoading.value = false
    if (newFriends.length === 0) {
      hasFriends.value = false
    } else {
      friends.value.push(...newFriends)
      await nextTick()

      if (checkSentinelVisible()) {
        await loadMore()
      }
    }
  }
}

let observer = null
onMounted(async () => {
  await loadMore()

  observer = new IntersectionObserver(
    entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          loadMore()
        }
      })
    },
    {root: null, rootMargin: '2px', threshold: 0}
  )

  observer.observe(sentinelRef.value)
})

function removeFriend(friendId) {
  friends.value = friends.value.filter(f => f.id !== friendId)
}

onBeforeUnmount(() => {
  observer?.disconnect()
})
</script>

<template>
  <div class="flex flex-col items-center mb-12">
    <div class="grid grid-cols-[repeat(auto-fill,minmax(240px,1fr))] gap-9 mt-12 justify-items-center w-full px-9">
      <Character
        v-for="friend in friends"
        :key="friend.id"
        :character="friend.character"
        :can-remove-friend="true"
        :friend-id="friend.id"
        @remove="removeFriend"
      />
    </div>

    <div ref="sentinel-ref" class="h-2 mt-8"></div>
    <div v-if="isLoading" class="text-gray-500 mt-4">加载中...</div>
    <div v-else-if="!hasFriends" class="text-gray-500 mt-4">没有更多聊天了</div>
  </div>
</template>