const { createApp, ref, reactive, computed, onMounted, watch } = Vue;

createApp({
  setup() {
    const page = ({ '/records': 'records', '/checklists': 'checklists', '/draft': 'draft', '/drafts': 'drafts' })[location.pathname] || 'start';
    const navigation = [
      { key: 'start', name: '开始', href: '/', icon: '⌂' }, { key: 'records', name: '审查记录', href: '/records', icon: '▤' },
      { key: 'checklists', name: '审查清单', href: '/checklists', icon: '☑' }, { key: 'draft', name: '合同起草', href: '/draft', icon: '✎' },
      { key: 'drafts', name: '起草记录', href: '/drafts', icon: '▧' }
    ];
    const modes = [{ id: 'quick', name: '快速审查', description: '基础规则与关键风险' },
    { id: 'deep', name: '深度审查', description: '背景、尺度与参考资料' },
    { id: 'checklist', name: '清单审查', description: '按企业要求逐项核验' },
    { id: 'compare', name: '对比审查', description: '对照参考合同定位变更' }];
    const sources = [{ id: 'file', name: '📤 上传合同' }, { id: 'paste', name: '✍️ 粘贴正文' }, { id: 'sample', name: '📑 示例合同' }];
    const roles = [{ value: '乙方(卖方/开发方/服务方)', label: '乙方 · 供应商/服务方' },
    { value: '甲方(买方/采购方/委托方)', label: '甲方 · 买方/采购方' }, { value: '中立审慎', label: '中立审慎' }];
    const taskStatuses = { draft: '待审查', running: '审查中', pending_review: '待复核', completed: '已完成', failed: '失败', interrupted: '已中断' };
    const statusName = status => ({ ...taskStatuses, background: '确认背景', outline: '确认大纲', text: '正文草稿' })[status] || status;
    const statusColor = status => status === 'completed' ? 'green' : ['failed', 'interrupted', 'pending_review'].includes(status) ? 'amber' : status === 'running' ? 'blue' : '';
    const modeName = id => modes.find(mode => mode.id === id)?.name || id;
    const dateTime = stamp => stamp ? new Date(stamp).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false }) : '—';
    const tasks = ref([]), lists = ref([]), drafts = ref([]), samples = ref({});
    const loading = ref(true), busy = ref(false), importing = ref(false), error = ref(''), toast = ref('');
    const search = ref(''), modeFilter = ref('all'), statusFilter = ref('all'), showArchived = ref(false), fromDate = ref(''), toDate = ref('');
    const inputMethod = ref('file'), sampleKey = ref(''), dragging = ref(false), sourceDrafts = {};
    const form = reactive({ title: '', type: '商务合作协议', text: '', role: roles[0].value, mode: 'deep', scale: '中立', background: '', focus: '', references: [], reference_text: '', checklist_id: '', source_id: null });
    const checklistEditor = ref(null), modalError = ref(''), showModel = ref(false), showHelp = ref(false), modelTest = ref(null);
    const model = reactive({ model_name: localStorage.getItem('LEXIS_MODEL_NAME') || 'deepseek-chat', base_url: localStorage.getItem('LEXIS_BASE_URL') || 'https://api.deepseek.com/v1', api_key: localStorage.getItem('LEXIS_API_KEY') || '' });
    const draftSteps = ['起草要求', '确认交易信息', '确认条款大纲', '编辑合同正文'];
    const draftStep = ref(0), draftVersions = ref([]), previewDraftVersion = ref(null);
    const rewriteSelection = reactive({ original: '', instruction: '', proposal: '' });
    const draft = reactive({ id: null, title: '', background: '', details: { 甲方: '', 乙方: '', 标的: '', 金额: '', 交付: '', 付款: '', 期限: '', 其他要求: '' }, outline: '', text: '', template_text: '', references: [], revision: null });
    const notify = message => { toast.value = message; setTimeout(() => { if (toast.value === message) toast.value = ''; }, 2500); };
    const api = async (path, method = 'GET', body) => {
      const response = await fetch(path, { method, headers: body ? { 'Content-Type': 'application/json' } : {}, body: body ? JSON.stringify(body) : undefined });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : data.detail?.map(item => item.msg).join('；') || '请求失败，请重试');
      return data;
    };
    const recentTasks = computed(() => tasks.value.filter(task => !task.archived));
    const publishedLists = computed(() => lists.value.filter(list => list.published && !list.archived));
    const matches = (row) => !!row.archived === showArchived.value && row.title?.toLowerCase().includes(search.value.trim().toLowerCase());
    const filteredTasks = computed(() => tasks.value.filter(task => matches(task) &&
      (modeFilter.value === 'all' || task.mode === modeFilter.value) && (statusFilter.value === 'all' || task.status === statusFilter.value) &&
      (!fromDate.value || new Date(task.updated_at).getTime() >= new Date(fromDate.value + 'T00:00:00+08:00').getTime()) &&
      (!toDate.value || new Date(task.updated_at).getTime() < new Date(toDate.value + 'T00:00:00+08:00').getTime() + 86400000)));
    const filteredLists = computed(() => lists.value.filter(list => !!list.archived === showArchived.value && list.name.toLowerCase().includes(search.value.trim().toLowerCase())));
    const filteredDrafts = computed(() => drafts.value.filter(matches));
    const loadRecords = async () => {
      const results = await Promise.allSettled([api('/api/tasks'), api('/api/checklists'), api('/api/drafts'), api('/api/samples')]);
      if (results[0].status === 'fulfilled') tasks.value = results[0].value.items;
      if (results[1].status === 'fulfilled') lists.value = results[1].value.items;
      if (results[2].status === 'fulfilled') drafts.value = results[2].value.items;
      if (results[3].status === 'fulfilled') samples.value = results[3].value.samples;
      const failure = results.slice(0, 3).find(result => result.status === 'rejected');
      if (failure) error.value = failure.reason.message;
    };
    const switchSource = next => {
      if (next === inputMethod.value || importing.value) return;
      sourceDrafts[inputMethod.value] = { text: form.text, title: form.title, sampleKey: sampleKey.value, source_id: form.source_id };
      const saved = sourceDrafts[next] || { text: '', title: '', sampleKey: '', source_id: null };
      form.text = saved.text; form.title = saved.title; form.source_id = saved.source_id; sampleKey.value = saved.sampleKey; inputMethod.value = next;
    };
    const selectSample = key => {
      const sample = samples.value[key]; if (!sample) return;
      form.title = sample.title; form.type = sample.type; form.text = sample.text; form.source_id = null; form.role = sample.recommended_role || roles[0].value; sampleKey.value = key;
    };
    const importDocument = async (event, target, dropped = false) => {
      const file = (dropped ? event.dataTransfer.files : event.target.files)?.[0];
      if (!file || importing.value) return;
      importing.value = true; error.value = ''; modalError.value = '';
      try {
        if (!/\.(txt|docx|pdf)$/i.test(file.name)) throw new Error('支持 DOCX、文字型 PDF 和 TXT；DOC 请先另存为 DOCX');
        if (file.size > 10 * 1024 * 1024) throw new Error('文件超过 10 MB，请拆分后上传');
        const body = new FormData(); body.append('file', file);
        const response = await fetch('/api/contracts/import', { method: 'POST', body }); const data = await response.json();
        if (!response.ok) throw new Error(data.detail || '文件提取失败');
        if (target === 'contract') { form.text = data.text; form.title = data.title; form.source_id = data.source_id; sampleKey.value = ''; }
        else if (target === 'reference') form.reference_text = data.text;
        else if (target === 'material') {
          if (form.references.length >= 5 || form.references.reduce((sum, item) => sum + item.text.length, 0) + data.text.length > 50000) throw new Error('参考资料最多 5 份，合计不能超过 5 万字');
          form.references.push({ name: file.name, text: data.text });
        } else if (target === 'draft_material') {
          if (draft.references.length >= 5 || draft.references.reduce((sum, item) => sum + item.text.length, 0) + data.text.length > 50000) throw new Error('参考资料最多 5 份，合计不能超过 5 万字');
          draft.references.push({ name: file.name, text: data.text });
        } else if (target === 'template') {
          if (data.text.length > 50000) throw new Error('模板超过 5 万字，请精简后导入');
          draft.template_text = data.text;
        } else if (target === 'checklist') {
          const lines = data.text.split('\n').map(line => line.trim()).filter(Boolean);
          if (lines.length > 100) throw new Error('提取超过 100 行，请精简清单后导入');
          checklistEditor.value.items = lines.map((line, index) => ({ id: crypto.randomUUID(), title: line.slice(0, 80), requirement: line, operator: 'semantic', keywords: [], keywordText: '', severity: 'warning', suggestion: '' }));
          if (!checklistEditor.value.name) checklistEditor.value.name = data.title;
          notify('已按行提取清单草稿，请合并标题、核对要求后发布'); return;
        }
        notify('已提取正文，请核对内容');
      } catch (err) { if (target === 'checklist') modalError.value = err.message; else error.value = err.message; }
      finally { importing.value = false; if (!dropped) event.target.value = ''; }
    };
    const createTask = async () => {
      busy.value = true; error.value = '';
      try {
        const body = { ...form, references: form.mode === 'deep' ? form.references : [] };
        const task = await api('/api/tasks', 'POST', body);
        sessionStorage.removeItem('LEXIS_HOME_DRAFT');
        location.href = '/workbench?task=' + task.id;
      } catch (err) { error.value = err.message; } finally { busy.value = false; }
    };
    const archive = async (kind, row) => {
      busy.value = true; error.value = '';
      try { await api('/api/' + kind + '/' + row.id + '/archive', 'POST', { archived: !row.archived, revision: row.revision }); await loadRecords(); notify(row.archived ? '已恢复记录' : '已归档，可在已归档列表恢复'); }
      catch (err) { error.value = err.message; } finally { busy.value = false; }
    };
    const addChecklistItem = () => checklistEditor.value.items.push({ id: crypto.randomUUID(), title: '', requirement: '', operator: 'semantic', keywords: [], keywordText: '', severity: 'warning', suggestion: '' });
    const editChecklist = (list) => {
      modalError.value = '';
      checklistEditor.value = list ? JSON.parse(JSON.stringify(list)) : { name: '', contract_type: '通用合同', description: '', items: [], published: false };
      checklistEditor.value.items.forEach(item => item.keywordText = (item.keywords || []).join(','));
      if (!list) addChecklistItem();
    };
    const saveChecklist = async (published) => {
      busy.value = true; modalError.value = '';
      try {
        const editor = checklistEditor.value;
        if (!editor.name.trim() || !editor.items.length || editor.items.some(item => !item.title.trim() || !item.requirement.trim())) throw new Error('请填写清单名称，并为每个检查项填写标题和具体要求');
        const body = { ...editor, published, items: editor.items.map(item => ({ ...item, keywords: item.operator === 'semantic' ? [] : item.keywordText.split(/[,，\n]/).map(word => word.trim()).filter(Boolean) })) };
        await api('/api/checklists' + (editor.id ? '/' + editor.id : ''), editor.id ? 'PUT' : 'POST', body);
        checklistEditor.value = null; await loadRecords(); notify(published ? '清单已发布，历史任务仍使用原版本' : '清单草稿已保存');
      } catch (err) { modalError.value = err.message; } finally { busy.value = false; }
    };
    const saveModel = () => {
      try { localStorage.setItem('LEXIS_API_KEY', model.api_key); localStorage.setItem('LEXIS_BASE_URL', model.base_url); localStorage.setItem('LEXIS_MODEL_NAME', model.model_name); showModel.value = false; notify('模型配置已保存'); }
      catch { modelTest.value = { success: false, message: '当前浏览器无法保存配置' }; }
    };
    const testModel = async () => { busy.value = true; try { modelTest.value = await api('/api/model/check', 'POST', model); } catch (err) { modelTest.value = { success: false, message: err.message }; } finally { busy.value = false; } };
    const persistDraft = async () => {
      const saved = await api('/api/drafts' + (draft.id ? '/' + draft.id : ''), draft.id ? 'PUT' : 'POST', draft);
      Object.assign(draft, saved);
      history.replaceState(null, '', '/draft?id=' + draft.id);
      draftVersions.value = (await api('/api/drafts/' + draft.id + '/versions')).items;
      return saved;
    };
    const saveDraft = async () => { busy.value = true; error.value = ''; try { await persistDraft(); notify('草稿已保存'); } catch (err) { error.value = err.message; } finally { busy.value = false; } };
    const generateDraft = async (stage) => {
      busy.value = true; error.value = '';
      try {
        await persistDraft();
        const generated = await api('/api/drafts/' + draft.id + '/generate', 'POST', { stage, model_config_data: model });
        Object.assign(draft, generated); draftStep.value = ({ details: 1, outline: 2, text: 3 })[stage];
        draftVersions.value = (await api('/api/drafts/' + draft.id + '/versions')).items; notify('已生成，请核对内容');
      } catch (err) {
        error.value = err.message;
        if (draft.id) try { const fresh = await api('/api/drafts/' + draft.id); draft.revision = fresh.revision; draft.status = fresh.status; } catch { }
      } finally { busy.value = false; }
    };
    const sendDraftToReview = async () => {
      busy.value = true; error.value = '';
      try { await persistDraft(); const task = await api('/api/tasks', 'POST', { title: draft.title, type: '起草合同', text: draft.text, role: roles[0].value, mode: 'deep', scale: '中立', background: draft.background, focus: '', references: draft.references }); location.href = '/workbench?task=' + task.id; }
      catch (err) { error.value = err.message; } finally { busy.value = false; }
    };
    const captureSelection = event => {
      const start = event.target.selectionStart, end = event.target.selectionEnd;
      if (end > start) { rewriteSelection.original = draft.text.slice(start, end); rewriteSelection.proposal = ''; }
    };
    const requestRewrite = async () => {
      busy.value = true; error.value = '';
      try {
        await persistDraft();
        const response = await api('/api/drafts/' + draft.id + '/rewrite', 'POST', { original_text: rewriteSelection.original, instruction: rewriteSelection.instruction, revision: draft.revision, model_config_data: model });
        draft.revision = response.revision; rewriteSelection.proposal = response.suggested_text;
      } catch (err) { error.value = err.message; if (draft.id) try { draft.revision = (await api('/api/drafts/' + draft.id)).revision; } catch { } }
      finally { busy.value = false; }
    };
    const applyRewrite = async () => {
      if (!rewriteSelection.original || draft.text.split(rewriteSelection.original).length !== 2) { error.value = '原文已变更或存在多处匹配，请重新选取'; return; }
      draft.text = draft.text.replace(rewriteSelection.original, rewriteSelection.proposal);
      rewriteSelection.proposal = ''; rewriteSelection.original = ''; await saveDraft();
    };
    watch(form, () => { if (page === 'start') try { sessionStorage.setItem('LEXIS_HOME_DRAFT', JSON.stringify({ ...form, inputMethod: inputMethod.value })); } catch { } }, { deep: true });
    onMounted(async () => {
      try {
        if (page === 'start') {
          const saved = JSON.parse(sessionStorage.getItem('LEXIS_HOME_DRAFT') || 'null');
          if (saved) { const { inputMethod: source, ...values } = saved; Object.assign(form, values); inputMethod.value = source || 'paste'; }
        }
        await loadRecords();
        const query = new URLSearchParams(location.search);
        if (query.has('checklist')) { form.mode = 'checklist'; form.checklist_id = query.get('checklist'); }
        if (page === 'draft' && query.has('id')) {
          const saved = await api('/api/drafts/' + query.get('id')); Object.assign(draft, saved);
          draftStep.value = saved.text ? 3 : saved.outline ? 2 : 0;
          draftVersions.value = (await api('/api/drafts/' + draft.id + '/versions')).items;
        }
      } catch (err) { error.value = err.message; } finally { loading.value = false; }
    });
    return {
      page, navigation, modes, sources, roles, taskStatuses, statusName, statusColor, modeName, dateTime,
      tasks, lists, drafts, samples, loading, busy, importing, error, toast, search, modeFilter, statusFilter, showArchived, fromDate, toDate,
      inputMethod, sampleKey, dragging, form, checklistEditor, modalError, showModel, showHelp, modelTest, model,
      draftSteps, draftStep, draftVersions, previewDraftVersion, draft, rewriteSelection, captureSelection, requestRewrite, applyRewrite, recentTasks, publishedLists, filteredTasks, filteredLists, filteredDrafts,
      switchSource, selectSample, importDocument, createTask, archive, addChecklistItem, editChecklist, saveChecklist,
      saveModel, testModel, saveDraft, generateDraft, sendDraftToReview
    };
  }
}).mount('#app');
