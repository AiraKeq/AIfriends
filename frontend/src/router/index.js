import { createRouter, createWebHistory } from 'vue-router'
import HomepageIndex from "@/views/homepage/HomePageIndex.vue"
import FriendIndex from "@/views/friend/FriendIndex.vue"
import CreateIndex from "@/views/create/CreateIndex.vue"
import LoginIndex from "@/views/user/account/LoginIndex.vue"
import RegisterIndex from "@/views/user/account/RegisterIndex.vue"
import SpaceIndex from "@/views/user/space/SpaceIndex.vue"
import ProfileIndex from "@/views/profile/ProfileIndex.vue"
import NotFoundIndex from "@/views/error/NotFoundIndex.vue"

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', component: HomepageIndex, name: 'homepage-index' },
    { path: '/friend', component: FriendIndex, name: 'friend-index' },
    { path: '/create', component: CreateIndex, name: 'create-index' },
    { path: '/login', component: LoginIndex, name: 'login-index' },
    { path: '/register', component: RegisterIndex, name: 'register-index' },
    { path: '/user/space', component: SpaceIndex, name: 'space-index' },
    { path: '/profile', component: ProfileIndex, name: 'profile-index' },
    { path: '/:pathMatch(.*)*', component: NotFoundIndex, name: 'not-found' },
  ],
})

export default router
