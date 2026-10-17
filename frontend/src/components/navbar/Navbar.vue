<script setup>
/**
 * 顶部导航 + 左侧抽屉。
 *
 * 结构上相对课上那版只动了一处，但这一处是「看着不对」的根源：
 *
 *   课上版把 <nav> 放进了 .drawer-content 里面 —— 于是顶栏只从侧边栏右边开始，
 *   logo、搜索框、注册登录全被挤进右侧那一格，左边永远缺一块。
 *   现在把 <nav> 提到 .drawer 外面、作为它的兄弟节点：顶栏贯穿整宽，
 *   抽屉只占下面剩下的高度，侧边栏自然就从顶栏下方开始。
 *
 * 顺带修的三个小毛病：
 *   - 搜索框原来套了两层 80% 宽度再包 join，实际渲染出来比中间那格还宽，
 *     和右侧「注册/登录」挤在一起；改成 flex-1 + max-w-2xl 自己撑开。
 *   - 侧栏折叠时（只留图标）才该有 tooltip，原来展开时也挂着，鼠标一停就冒字；
 *     现在用 lg:is-drawer-close:tooltip 把桌面端展开态的提示关掉。
 *
 * ⚠️ 踩过的坑（别改回去）：daisyUI 的 .navbar-start / .navbar-end 自带
 *   `width: 50%`，而 .navbar-center 是 `flex-shrink: 0`。三个加起来必然超宽，
 *   被压扁的只有中间那块 —— 搜索框实测被挤成 0 宽。所以左右两边要 w-auto!，
 *   让它们只占内容宽度，把剩下的空间留给中间的 flex-1，搜索框才有地方长。
 */
import MenuIcon from "@/components/navbar/icons/MenuIcon.vue";
import HomepageIcon from "@/components/navbar/icons/HomepageIcon.vue";
import FriendIcon from "@/components/navbar/icons/FriendIcon.vue";
import CreateIcon from "@/components/navbar/icons/CreateIcon.vue";
import SearchIcon from "@/components/navbar/icons/SearchIcon.vue";

// 侧栏三个入口：路径、图标、文案、折叠时的提示语
const DRAWER_ITEMS = [
  { name: "homepage-index", label: "首页", icon: HomepageIcon },
  { name: "friend-index", label: "好友", icon: FriendIcon },
  { name: "create-index", label: "创作", icon: CreateIcon },
];
</script>

<template>
  <div>
    <div class="flex h-dvh flex-col overflow-hidden bg-base-100">
      <!-- 顶栏：贯穿全宽，不属于抽屉 -->
      <nav class="navbar relative z-20 w-full shrink-0 gap-2 bg-base-100 shadow-sm">
        <div class="navbar-start w-auto!">
          <label for="my-drawer-4" aria-label="展开或收起侧边栏" class="btn btn-square btn-ghost btn-sm">
            <MenuIcon />
          </label>
          <RouterLink :to="{ name: 'homepage-index' }" class="px-3 text-xl font-bold whitespace-nowrap">
            <!-- 小屏把品牌字收起来：420px 宽时它和搜索框会互相挤，搜索框只剩 84px -->
            <span class="hidden sm:inline">AIFriends</span>
          </RouterLink>
        </div>
        <!-- 中间这块用 flex-1 吃掉左右剩下的空间，再让里面的搜索框居中。
             居中必须用 justify-center，别改用子元素的 mx-auto —— 实测在 .drawer
             这个 grid 容器里，grid 的 justify-items:start 会把这一格钉在左边，
             auto 外边距拿不到剩余空间，搜索框会停在最左（量到 x=160，应该是 389）。 -->
        <div class="navbar-center min-w-0 flex-1 justify-center  px-2 sm:px-6">
          <div class="join w-full max-w-2xl">
            <input type="search" class="input join-item w-full" placeholder="搜索你感兴趣的内容">
            <!-- overflow-visible 不能删：<button> 自己也算 overflow:hidden 的一份子，
                 图标只要贴到边，缩放/取整时就会缺一块。图标组件里也放开了 svg 的。
                 图标与文字的间距写死成 gap-1.5（6px），别再让 btn 的默认 gap 参与。 -->
            <button type="button" class="btn join-item gap-1.5 overflow-visible">
              <SearchIcon />
              搜索
            </button>
          </div>
        </div>
        <div class="navbar-end w-auto!">
          <RouterLink :to="{ name: 'register-index' }" class="btn btn-ghost btn-sm text-base">注册</RouterLink>
          <RouterLink :to="{ name: 'login-index' }" class="btn btn-ghost btn-sm text-base">登录</RouterLink>
        </div>
      </nav>

      <!-- 抽屉：只占顶栏下面剩下的高度 -->
      <div class="drawer min-h-0 flex-1 lg:drawer-open">
        <input id="my-drawer-4" type="checkbox" class="drawer-toggle">
        <div class="drawer-content flex min-h-0 flex-col">
          <main class="min-h-0 flex-1 overflow-y-auto">
            <slot></slot>
          </main>
        </div>
        <div class="drawer-side z-30 max-lg:top-16 max-lg:h-[calc(100dvh-4rem)] lg:h-full is-drawer-close:overflow-visible">
          <label for="my-drawer-4" aria-label="收起侧边栏" class="drawer-overlay"></label>
          <div class="flex min-h-full flex-col bg-base-200 is-drawer-close:w-18 is-drawer-open:w-54">
            <ul class="menu w-full grow">
              <li v-for="item in DRAWER_ITEMS" :key="item.name">
                <RouterLink
                  :to="{ name: item.name }"
                  class="is-drawer-close:tooltip is-drawer-close:tooltip-right lg:is-drawer-close:tooltip lg:is-drawer-close:tooltip-open lg:is-drawer-close:tooltip-right min-h-12"
                  :data-tip="item.label"
                >
                  <component :is="item.icon" />
                  <span class="is-drawer-close:hidden ml-1 whitespace-nowrap">{{ item.label }}</span>
                </RouterLink>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
