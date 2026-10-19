<template>
  <svg class="ui-chevron" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path :d="direction === 'up' ? 'm5 12 5-5 5 5' : direction === 'right' ? 'm8 5 5 5-5 5' : 'm5 8 5 5 5-5'" /></svg>
</template>
<script>
export default { props: { direction: {type:String,default:'down'} } };
</script>
<style>
.ui-chevron { display:inline-block; width:14px; height:14px; flex-shrink:0; vertical-align:middle; transition:transform .15s; }
.wb-menu[open] > summary .ui-chevron { transform:rotate(180deg); }
</style>
