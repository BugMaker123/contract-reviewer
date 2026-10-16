<script>
export default {
  props: { context: { type: Object, required: true } },
  setup: (props) => props.context,
};
</script>

<template>
  <div v-if="isReviewing" class="review-overlay">
    <section
      class="review-dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="review-dialog-title"
    >
      <header class="review-dialog-header">
        <div>
          <div class="review-dialog-eyebrow">
            合同审查 · {{ reviewProgress }}%
          </div>
          <h3 id="review-dialog-title">正在分析合同</h3>
        </div>
        <button @click="cancelReview" class="review-cancel">取消审查</button>
      </header>
      <div class="review-dialog-progress">
        <i :style="{ width: reviewProgress + '%' }"></i>
      </div>
      <div class="review-dialog-status">
        <i></i><span>{{ latestLogMessage || "正在连接模型服务…" }}</span>
      </div>
      <div class="review-dialog-body">
        <div class="review-analysis-heading">
          <h4>分析摘要</h4>
          <span>初步发现，待校验</span>
        </div>
        <div v-if="!publicAnalysis.length" class="review-waiting">
          <div class="review-waiting-line"></div>
          <h4>正在核对合同条款</h4>
          <p>收到模型的完整意见后，会逐条展示依据和修改方向。</p>
          <p class="review-waiting-note">
            等待期间可随时取消，已保存的文档不会被覆盖。
          </p>
        </div>
        <div
          v-else
          data-public-analysis
          class="review-analysis-list"
          aria-live="polite"
        >
          <article
            v-for="(item, index) in publicAnalysis"
            :key="index"
            class="review-analysis-item"
          >
            <div class="review-analysis-index">{{ index + 1 }}</div>
            <div class="review-analysis-copy">
              <p class="review-analysis-clause">{{ item.clause }}</p>
              <h5>{{ item.title }}</h5>
              <p>{{ item.analysis }}</p>
              <div v-if="item.proposal" class="review-proposal">
                <strong>修改方向</strong>
                <p>{{ item.proposal }}</p>
              </div>
              <details v-if="item.evidence">
                <summary>原文依据</summary>
                <blockquote>{{ item.evidence }}</blockquote>
              </details>
            </div>
          </article>
        </div>
        <details class="review-execution">
          <summary>
            执行记录 <span>{{ reviewTrace.length }} 条</span>
          </summary>
          <ol data-review-trace>
            <li v-for="(item, index) in reviewTrace" :key="index">
              <time>{{
                new Date(item.time).toLocaleTimeString("zh-CN", {
                  hour12: false,
                })
              }}</time
              ><span>{{ item.detail }}</span>
            </li>
          </ol>
        </details>
      </div>
      <footer class="review-dialog-footer">
        <span>完整校验后生成修订文档</span
        ><span>{{ publicAnalysis.length }} 条初步意见</span>
      </footer>
    </section>
  </div>
</template>
