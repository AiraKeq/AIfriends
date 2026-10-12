<template>
  <!-- viewBox 别随手改小 —— 这里踩过两次：
       圆心 (26,26) r=14 → 外沿 12；斜线画到 (50,50)，stroke 6 的圆头再外扩 3 → 顶点 53。
       图形的真实占位是 12~53。所以取景框要在四边各留出余量：
         "9 9 46 46" → 图形落 3~44/46 的位置，上下左右各留 3 个单位，
         换成屏幕上大约是 1 个物理像素的余量。
       教训：只要取景框和图形齐平，「贴边」的那一侧在缩放/取整时就会缺一块；
       留 1px 余量才稳。stroke-width 从 5 提到 6 是为了抵消取景框放大后的视觉变细
       （5/40 = 0.125，6/46 ≈ 0.130，看着一样粗）。 -->
  <svg viewBox="9 9 46 46" role="img" aria-label="放大镜" stroke="currentColor" class="size-5 overflow-visible align-middle">
    <g stroke="currentColor" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" fill="none">
      <circle cx="26" cy="26" r="14"/>
      <path d="M37.5 37.5L50 50"/>
    </g>
  </svg>
</template>

<script setup>
/**
 * 搜索图标。
 *
 * 来源：AcWing《Svg Icons合集》里的「5. Search Icon」（作者 yxc）
 *       https://www.acwing.com/blog/content/83396/
 * 相对原文改了：class（size-6 → size-5）、去掉 xmlns 与 width/height、
 * 补 stroke="currentColor"，以及 viewBox —— 原文画布 64×64 而图形只占一小块，
 * 缩到 20px 时笔画细得发虚；但收得太紧（试过 "14 14 36 36"、"12.5 12.5 40 40"）
 * 会让贴边的那一侧缺一块，最后定成 "9 9 46 46"：图形四周各留约 1 物理像素余量，
 * stroke-width 相应给到 6 保持粗细观感。
 * 原文注释一并保留。
 */
</script>
