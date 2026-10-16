<script>
export default {
  props: { context: { type: Object, required: true } },
  setup: (props) => props.context,
};
</script>

<template>
  <div
    v-if="toastMessage"
    class="fixed top-4 left-1/2 transform -translate-x-1/2 z-50 bg-slate-900 text-white text-xs px-4 py-2 rounded-lg shadow-xl flex items-center space-x-2 transition-all"
  >
    <svg
      class="w-4 h-4 text-emerald-400 shrink-0"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      stroke-width="2"
    >
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
    <span>{{ toastMessage }}</span>
  </div>
</template>
