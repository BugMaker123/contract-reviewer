<script setup>
import { ref, shallowRef, watch } from "vue";
import { useRoute } from "vue-router";
import WorkbenchSession from "./WorkbenchSession.vue";

const route = useRoute();
const session = shallowRef(null);
const sessionKey = ref(0);
watch(
  () => [route.query.task, route.query.run],
  ([task, run], [_previousTask, previousRun]) => {
    // Assigning the first saved task ID must keep the current editor alive.
    // Opening another task or historical run creates a clean review session.
    if (
      String(task || "") !== String(session.value?.workspace.taskId || "") ||
      String(run || "") !== String(previousRun || "")
    ) {
      sessionKey.value++;
    }
  },
);
</script>
<template>
  <WorkbenchSession :key="sessionKey" @ready="session = $event" />
</template>
