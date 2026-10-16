import { ref, reactive, computed } from "vue";

export function setup(context) {
  const { tasks, matches, modeFilter, statusFilter, fromDate, toDate } =
    context;
  const filteredTasks = computed(() =>
    tasks.value.filter(
      (task) =>
        matches(task) &&
        (modeFilter.value === "all" || task.mode === modeFilter.value) &&
        (statusFilter.value === "all" || task.status === statusFilter.value) &&
        (!fromDate.value ||
          new Date(task.updated_at).getTime() >=
            new Date(fromDate.value + "T00:00:00+08:00").getTime()) &&
        (!toDate.value ||
          new Date(task.updated_at).getTime() <
            new Date(toDate.value + "T00:00:00+08:00").getTime() + 86400000),
    ),
  );

  return { filteredTasks };
}
