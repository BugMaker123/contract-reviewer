<template>
  <RouterView v-slot="{ Component, route }">
    <KeepAlive include="PortalLayout"
      ><component
        :is="Component"
        :key="route.path.startsWith('/workbench') ? 'workbench' : 'portal'"
    /></KeepAlive>
  </RouterView>
</template>
