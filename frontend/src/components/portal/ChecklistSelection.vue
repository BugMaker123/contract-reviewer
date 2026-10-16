<script>
export default {
  props: { context: { type: Object, required: true } },
  setup: (props) => props.context,
};
</script>

<template>
  <div
    v-if="form.mode === 'checklist' && selectedList"
    class="checklist-selection"
  >
    <div class="selection-heading">
      <strong>专项清单审查要点</strong
      ><span class="pill blue"
        >已勾选
        {{
          form.checklist_item_ids?.length ?? selectedList.items.length
        }}
        项</span
      ><button
        class="text-xs text-blue-600"
        @click="
          form.checklist_item_ids =
            (form.checklist_item_ids?.length ?? selectedList.items.length) ===
            selectedList.items.length
              ? []
              : selectedList.items.map((item) => item.id)
        "
      >
        {{
          (form.checklist_item_ids?.length ?? selectedList.items.length) ===
          selectedList.items.length
            ? "取消全选"
            : "全选"
        }}
      </button>
    </div>
    <div class="checklist-options">
      <label
        v-for="item in selectedList.items"
        :key="item.id"
        class="checklist-option"
        :class="{
          selected:
            form.checklist_item_ids === null ||
            form.checklist_item_ids.includes(item.id),
        }"
        ><input
          type="checkbox"
          :checked="
            form.checklist_item_ids === null ||
            form.checklist_item_ids.includes(item.id)
          "
          @change="
            form.checklist_item_ids = $event.target.checked
              ? [
                  ...(form.checklist_item_ids ??
                    selectedList.items.map((i) => i.id)),
                  item.id,
                ]
              : (
                  form.checklist_item_ids ?? selectedList.items.map((i) => i.id)
                ).filter((id) => id !== item.id)
          "
        />
        <div>
          <div class="selection-heading">
            <strong>{{ item.title }}</strong
            ><span
              class="pill"
              :class="
                item.severity === 'critical'
                  ? 'red'
                  : item.severity === 'warning'
                    ? 'amber'
                    : 'blue'
              "
              >{{
                { critical: "高风险", warning: "中风险", info: "低风险" }[
                  item.severity
                ]
              }}</span
            >
          </div>
          <p>{{ item.requirement }}</p>
          <p v-if="item.suggestion">处理建议：{{ item.suggestion }}</p>
        </div></label
      >
    </div>
  </div>
</template>
