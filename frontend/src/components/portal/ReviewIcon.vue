<script setup>
defineProps({name:String});
const paths={
 home:'m3 10 9-7 9 7M5 9v11h5v-6h4v6h5V9',
 records:'M7 3h10l3 3v15H4V3h3m1 5h8m-8 5h8m-8 4h5',
 categories:'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z',
 checklists:'m5 6 2 2 3-4m3 2h7M5 13l2 2 3-4m3 2h7M5 20l2 2 3-4m3 2h7',
 templates:'M8 3h8l4 4v14H4V3h4m7 0v5h5M8 12h8m-8 4h5',
 document:'M7 3h9l4 4v14H4V3h3m8 0v5h5M8 12h8m-8 4h5',
 sparkles:'m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3ZM20 2v4m-2-2h4',
 arrow:'M5 12h14m-6-6 6 6-6 6',
 save:'M5 3h13l3 3v15H3V3h2m2 0v6h10V3M7 21v-8h10v8',
 plus:'M12 5v14M5 12h14',
 search:'M20 20l-5-5m2-5a7 7 0 1 1-14 0 7 7 0 0 1 14 0',
 settings:'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8m0-5v2m0 14v2M3 12h2m14 0h2M5.6 5.6 7 7m10 10 1.4 1.4M5.6 18.4 7 17M17 7l1.4-1.4',
 shield:'m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6l8-3m-4 9 3 3 5-6',
 info:'M12 11v6m0-10v.1M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0',
 check:'m5 12 4 4L19 6',
 drafting:'M17 3a2.85 2.85 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z',
 validations:'M9 11l3 3L22 4M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11',
 scale:'M3 7h18M12 3v18M7 7l-4 8h8L7 7zm10 0l-4 8h8l-4-8z',
};
</script>
<template><svg class="review-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path :d="paths[name]||paths.document"/></svg></template>
<style scoped>.review-icon{display:inline-block;flex-shrink:0;vertical-align:middle}</style>
