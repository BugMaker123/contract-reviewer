/* Detailed prototype views reuse the base demo state and actions. */
state.activeCategory = state.activeCategory || '采购合同';
state.activeRecordTab = state.activeRecordTab || '全部';
state.activeCatalogTab = state.activeCatalogTab || '全部';
state.draftPreviewMode = state.draftPreviewMode || '编辑';

function setDetail(key,value){state[key]=value;render()}
function sectionHead(title,caption=''){return `<div class="form-heading"><b>${title}</b><span>${caption}</span></div>`}
function demoNote(){return `<div class="note-row">这是界面原型。审查、生成、保存及导出展示流程反馈，正式结果以系统实际运行为准。</div>`}
function renderStart(){
 const choosing=state.flow==='choose';
 return `<div class="hero"><div><span class="kicker">合同工作台</span><h1>今天要处理哪份合同？</h1><p>选择一项任务开始，或从最近的记录继续。每一步都会显示当前材料、处理状态和下一步操作。</p></div><div class="mini"><span class="hint">当前工作空间</span><strong>LexisGraph · 本地</strong><span class="hint">模型状态：按当前配置运行</span></div></div>
 <div class="overview"><div class="metric"><div><small>进行中的审查</small><strong>1</strong><span class="hint">继续处理未决建议</span></div><span class="metric-icon">▤</span></div><div class="metric"><div><small>待人工确认</small><strong>2</strong><span class="hint">模板核验与要求覆盖</span></div><span class="metric-icon">◇</span></div><div class="metric"><div><small>最近的合同草稿</small><strong>1</strong><span class="hint">可编辑、导出或送审</span></div><span class="metric-icon">✎</span></div></div>
 <div class="workspace-grid"><section class="card flow-card"><div class="section-title"><div><h2>发起新任务</h2><p class="section-caption">先确定任务类型，再添加合同和审查条件。</p></div>${P(choosing?'选择方式':state.flow==='ai'?'风险审查准备':'模板核验准备')}</div>
 <div class="choice"><button class="${choosing?'active':''}" onclick="set('flow','choose')">1 选择方式</button><button class="${state.flow==='ai'?'active':''}" onclick="set('flow','ai')">2 风险审查</button><button class="${state.flow==='template'?'active':''}" onclick="set('flow','template')">2 模板核验</button></div>
 ${choosing?`<div class="path-list"><button class="path" onclick="set('flow','ai')"><span class="path-icon">✧</span><b>审查合同风险</b><span>上传合同、指定立场与重点，逐条查看意见并处理修订。</span></button><button class="path" onclick="set('flow','template')"><span class="path-icon">☑</span><b>核验标准模板</b><span>以已发布的 DOCX 模板为基准，检查固定文字和填写规则。</span></button></div><div class="section">${demoNote()}</div>`:state.flow==='ai'?detailedAiForm():detailedTemplateForm()}</section>
 <aside><section class="card"><div class="section-title"><h2>最近工作</h2>${B('查看全部',"nav('records')")}</div><div class="timeline"><div><strong>云服务采购协议 ${P('复核中','medium')}</strong>待处理建议 3 项 · 今天 14:28</div><div><strong>技术保密协议 ${P('已完成','good')}</strong>可查看当前稿与意见书 · 10 月 20 日</div><div><strong>办公设备采购合同 ${P('需人工确认','medium')}</strong>模板核验报告 · 10 月 18 日</div></div><div class="section">${B('继续审查云服务采购协议',"nav('workbench')",'primary')}</div></section><section class="card section"><h2>常用入口</h2><div class="quick-link" onclick="nav('drafts')"><span>起草新合同<br><small>描述交易需求，生成可编辑草稿</small></span>↗</div><div class="quick-link" onclick="nav('templates')"><span>维护合同模板<br><small>管理原件、字段规则与版本</small></span>↗</div><div class="quick-link" onclick="nav('checklists')"><span>维护审查清单<br><small>确认制度要求并发布</small></span>↗</div></section></aside></div>`
}
function detailedAiForm(){return `<div class="micro-steps"><span><b>1</b>添加合同</span><em></em><span><b>2</b>设置审查条件</span><em></em><span><b>3</b>进入工作台</span></div>
 <div class="form-section">${sectionHead('合同内容','DOCX / 文字型 PDF / TXT')}<div class="choice" style="margin-bottom:12px"><button class="${!state.source?'active':''}" onclick="set('source','')">上传文件</button><button class="${state.source==='paste'?'active':''}" onclick="set('source','paste')">粘贴正文</button></div>${state.source==='paste'?`<label class="field">合同正文<textarea style="min-height:135px" placeholder="粘贴可复制的合同正文…" oninput="state.contractText=this.value">${esc(state.contractText||'')}</textarea></label>`:`<label class="drop"><input type="file" accept=".docx,.pdf,.txt" onchange="chooseFile(this,'file')"><span style="font-size:24px">⇧</span><b>${esc(state.file||'将文件拖至此处，或点击选择')}</b><span class="hint">不超过 10 MB；扫描版 PDF 请先完成 OCR</span></label>`}</div>
 <div class="form-section">${sectionHead('审查视角','决定建议的判断方向')}<div class="select-chips">${['中立审慎','甲方立场','乙方立场'].map(s=>`<button class="${state.stance===s?'active':''}" onclick="setDetail('stance','${s}')">${s}</button>`).join('')}</div><div class="form-two section"><label class="field">审查尺度<select onchange="state.scale=this.value"><option ${state.scale==='标准'?'selected':''}>标准</option><option ${state.scale==='快速'?'selected':''}>快速</option><option ${state.scale==='深入'?'selected':''}>深入</option></select></label><label class="field">业务分类<select onchange="state.category=this.value"><option>暂不指定</option>${categories.map(c=>`<option ${state.category===c[0]?'selected':''}>${c[0]}</option>`).join('')}</select></label></div><label class="field">企业审查清单 <small>选填</small><select><option>不使用清单</option>${checklists.map(c=>`<option>${c[0]}</option>`).join('')}</select></label></div>
 <div class="form-section">${sectionHead('背景与特别要求','便于结合真实交易解释条款')}<label class="field">交易背景 <small>选填</small><textarea placeholder="例如：我方为采购方，服务涉及客户数据，分阶段验收…" oninput="state.background=this.value">${esc(state.background)}</textarea></label><label class="field">重点关注 <small>选填</small><textarea placeholder="例如：重点检查数据安全、付款节点和责任上限…" oninput="state.focus=this.value">${esc(state.focus)}</textarea></label><div class="row">${B('添加制度资料 / 手工要求',"openModal('policy')")}</div></div>
 <div class="bottom-actions"><small>开始后会在工作台保留本次输入与审查条件。</small>${B('开始审查 →',"startReview()",'primary')}</div>`}
function detailedTemplateForm(){return `<div class="micro-steps"><span><b>1</b>选择已发布模板</span><em></em><span><b>2</b>上传待核验合同</span><em></em><span><b>3</b>查看报告</span></div><div class="form-section">${sectionHead('基准模板','只使用已发布的规则版本')}<label class="field">合同模板<select onchange="state.selectedTemplate=this.value;render()">${templates.filter(x=>x[1]==='DOCX').map(t=>`<option ${state.selectedTemplate===t[0]?'selected':''}>${t[0]}</option>`).join('')}</select></label><div class="preview-box"><h3>${esc(state.selectedTemplate)} ${P('已发布 · v3','good')}</h3><p>核对固定条款、必填字段、金额范围、日期及枚举取值。版本在本次核验中固定。</p></div></div><div class="form-section">${sectionHead('待核验合同','仅 DOCX，最大 10 MB')}<label class="drop"><input type="file" accept=".docx" onchange="chooseFile(this,'validationFile')"><span style="font-size:24px">⇧</span><b>${esc(state.validationFile||'点击选择或拖入 DOCX 合同')}</b><span class="hint">上传后对比模板固定文字与已配置区域</span></label></div><div class="form-section">${demoNote()}<div class="bottom-actions"><small>无法确定的内容会明确列入人工确认。</small>${B('开始核验 →',"validate()",'primary')}</div></div>`}

function renderWorkbench(){let issue=state.issues[state.selectedIssue];let counts={high:state.issues.filter(x=>x.level==='high').length,medium:state.issues.filter(x=>x.level==='medium').length,pending:state.issues.filter(x=>x.status==='待处理').length};return `<div class="work-top"><div class="work-title"><span class="work-icon">▤</span><div><h1>云服务采购协议</h1><p>合同审查工作台 · 标准尺度 · 中立审慎 · 当前处理状态：${state.reviewStatus}</p></div></div><div class="actions">${B('返回审查记录',"nav('records')")}${B('保存进度',"toast('处理进度已保存（原型演示）')")}${B('交付与导出',"openModal('report')")}${B('完成审核',"finishReview()",'primary')}</div></div>
 <div class="work-grid"><section class="work-panel"><div class="panel-head"><h2>问题与任务</h2>${P(counts.pending+' 项待处理','medium')}</div><div class="panel-body"><div class="tiny">按问题定位正文，处理意见后状态会同步更新。</div><div class="issue-counts"><span><b>${counts.high}</b>高风险</span><span><b>${counts.medium}</b>中风险</span><span><b>${counts.pending}</b>待处理</span></div><div class="field">审查项目</div>${state.issues.map((x,n)=>`<div class="work-issue ${n===state.selectedIssue?'selected':''}" tabindex="0" role="button" onclick="focusIssue(${n})" onkeydown="if(event.key==='Enter')focusIssue(${n})"><span class="index">0${n+1} · ${x.clause}</span><h3>${esc(x.title)}</h3><div class="row">${P(x.levelName,x.level)} ${P(x.status,x.status==='已采纳'?'good':'wait')}</div></div>`).join('')}<div class="section">${B('重新审查',"openModal('rerun')")}</div><div class="section notice">高风险建议保持逐条确认；低风险建议可批量采纳。处理结果会反映在当前稿。</div></div></section>
 <section class="work-panel"><div class="panel-head"><div><h2>合同正文</h2><span class="tiny">点击高亮条款，右侧显示证据与建议</span></div><div class="row">${B('编辑',"openModal('edit')")}${B('导出 Word',"downloadText('当前稿')")}</div></div><div class="document-bar"><div class="choice">${[['marked','修订标记'],['current','当前稿'],['original','原始稿'],['compare','双栏对照']].map(([key,label])=>`<button class="${state.mode===key?'active':''}" onclick="setDetail('mode','${key}')">${label}</button>`).join('')}</div><span class="tiny">A4 预览 · 100%</span></div><div class="document-scroll"><div class="paper"><div class="doc-meta"><span>LEXISGRAPH · 合同正文</span><span>第 1 页 / 共 2 页</span></div><h2 class="doc-title">云服务采购协议</h2><p class="doc-paragraph">甲方：星河科技有限公司<br>乙方：远山云计算有限公司</p><p class="doc-paragraph"><b>第一条 服务内容</b><br>乙方向甲方提供云计算资源、系统维护及技术支持。服务内容及交付标准以附件为准。</p><p class="doc-paragraph"><b>第二条 服务期限</b><br>本协议自双方签署之日起生效，服务期限为十二个月。</p>${state.issues.map((x,n)=>`<div class="doc-clause ${n===state.selectedIssue?'selected':''}" onclick="focusIssue(${n})"><b>${x.clause}</b>${P(x.status==='待处理'?x.levelName:x.status,x.status==='已采纳'?'good':x.level)}<br>${esc(state.mode==='original'?x.old:x.status==='已采纳'?x.next:x.old)}${state.mode==='compare'?`<div class="diff-new">建议：${esc(x.next)}</div>`:''}</div>`).join('')}<p class="doc-paragraph"><b>第六条 争议解决</b><br>因本协议产生的争议，双方应先友好协商解决。</p></div></div><div class="document-bar"><span class="tiny">当前稿仅包含已采纳的修改</span><div class="row">${B('导出修订稿',"downloadText('修订稿')")}</div></div></section>
 <section class="work-panel"><div class="side-tab">${[['opinions','审查意见'],['requirements','要求核验'],['activity','处理记录']].map(([key,label])=>`<button class="${state.tab===key?'active':''}" onclick="setDetail('tab','${key}')">${label}</button>`).join('')}</div><div class="panel-body">${state.tab==='opinions'?`<div class="row">${P(issue.levelName,issue.level)} ${P(issue.status,issue.status==='已采纳'?'good':'wait')}</div><h2 class="opinion-title">${esc(issue.title)}</h2><p class="opinion-text">定位：${issue.clause} · 审查建议 0${state.selectedIssue+1} / 0${state.issues.length}</p><div class="form-section">${sectionHead('原文证据')}<div class="evidence">${esc(issue.old)}</div></div><div class="form-section">${sectionHead('建议修订','红色为原文，绿色为建议')}<div class="diff-old">− ${esc(issue.old)}</div><div class="diff-new">＋ ${esc(issue.next)}</div></div><div class="form-section">${sectionHead('判断依据')}<p class="opinion-text">${esc(issue.reason)}</p></div><div class="decision-row">${B('采纳此条修改',"issueAction('已采纳')",'primary')}${B('拒绝',"issueAction('已拒绝')")}${B('调整建议',"openModal('rewrite')")}</div><div class="section">${B('批量采纳非高风险建议',"acceptLowRisk()")}</div>`:state.tab==='requirements'?`<h2>要求覆盖情况</h2><p class="opinion-text">显示每项要求的结论、证据和需要人工判断的原因。</p><div class="status-line"><span>付款与验收挂钩</span>${P('待确认','medium')}</div><div class="status-line"><span>服务中断责任</span>${P('不符合','high')}</div><div class="status-line"><span>商业秘密保护</span>${P('待确认','medium')}</div><div class="section">${B('查看企业审查清单',"nav('checklists')")}</div>`:`<h2>处理记录</h2><div class="timeline">${state.issues.map(x=>`<div><strong>${esc(x.title)}</strong>${x.status} · 本次审查</div>`).join('')}</div><div class="section">${B('下载 JSON 审核记录',"downloadText('审核记录')")}</div>`}<div class="form-section">${sectionHead('交付')}<div class="row">${B('意见书预览',"openModal('report')")}${B('导出意见书',"downloadText('意见书')")}</div></div></div></section></div>`}
function focusIssue(n){state.selectedIssue=n;render();document.querySelector('.doc-clause.selected')?.scrollIntoView({behavior:'smooth',block:'center'})}

function renderDrafts(){return `<div class="hero"><div><span class="kicker">合同起草</span><h1>从交易需求到可审查的合同草稿</h1><p>先写清交易事实，生成后继续编辑、保存、导出，或直接带入风险审查。</p></div><div class="actions">${B('起草记录',"openModal('draftlist')")}${B('新建草稿',"resetDraft()")}</div></div><div class="draft-step"><span><b>① 明确交易需求</b></span><span>② 生成并编辑正文</span><span>③ 导出或送审</span></div><div class="draft-shell"><section class="card"><div class="pad"><div class="section-title"><div><h2>起草需求</h2><p class="section-caption">缺少的关键信息将在草稿中保留待补充位置。</p></div>${P('步骤 1 / 3')}</div>${sectionHead('基本信息')}<div class="form-two"><label class="field">合同类型<select onchange="state.draftType=this.value"><option ${state.draftType==='服务采购合同'?'selected':''}>服务采购合同</option><option>保密协议</option><option>销售合同</option><option>技术服务合同</option></select></label><label class="field">我方立场<select onchange="state.draftPerspective=this.value"><option ${state.draftPerspective==='中立审慎'?'selected':''}>中立审慎</option><option>甲方立场</option><option>乙方立场</option></select></label></div><div class="form-two"><label class="field">甲方名称<input value="${esc(state.draftPartyA)}" oninput="state.draftPartyA=this.value"></label><label class="field">乙方名称<input value="${esc(state.draftPartyB)}" oninput="state.draftPartyB=this.value"></label></div><div class="form-section">${sectionHead('交易事实与起草要求','建议写明标的、金额、期限、交付')}<label class="field">交易背景<textarea style="min-height:125px" placeholder="例如：采购一年期云服务，按季度验收付款…" oninput="state.draftReq=this.value">${esc(state.draftReq)}</textarea></label><div class="field">常用要求</div><div class="select-chips">${['付款安排','交付与验收','数据安全','违约责任','争议解决'].map(t=>`<button onclick="addReq('${t}')">＋ ${t}</button>`).join('')}</div></div><div class="form-section">${demoNote()}<div class="bottom-actions"><small>调整需求后重新生成会保留当前草稿。</small><div class="actions">${B('填入示例',"state.draftReq='提供云服务资源与技术支持，服务期限十二个月，按验收节点分期付款。';render()")}${B('生成草稿',"generateDraft()",'primary')}</div></div></div></div></section><section class="card"><div class="pad"><div class="section-title"><div><h2>合同正文</h2><p class="section-caption">在纸张视图中编辑，完成后保存或导出。</p></div>${P(state.draftSaved?'已保存':'有未保存修改',state.draftSaved?'good':'medium')}</div><label class="field">草稿标题<input value="${esc(state.draftTitle)}" oninput="state.draftTitle=this.value;state.draftSaved=false"></label><div class="choice"><button class="${state.draftPreviewMode==='编辑'?'active':''}" onclick="setDetail('draftPreviewMode','编辑')">编辑</button><button class="${state.draftPreviewMode==='预览'?'active':''}" onclick="setDetail('draftPreviewMode','预览')">预览</button></div></div><div class="draft-preview"><div class="draft-paper">${state.draftPreviewMode==='编辑'?`<textarea class="doc-edit" placeholder="生成后可在此编辑合同正文…" oninput="state.draftText=this.value;state.draftSaved=false">${esc(state.draftText)}</textarea>`:state.draftText?`<div style="white-space:pre-wrap;line-height:1.85">${esc(state.draftText)}</div>`:'<div class="empty">生成后在这里预览合同正文</div>'}</div></div><div class="pad"><div class="bottom-actions"><small>${state.draftText.length} 字 · 导出或送审前请核对正文</small><div class="actions">${B('保存草稿',"saveDraft()")}${B('导出 Word',"downloadText('合同草稿')")}${B('进入审查 →',"draftReview()",'primary')}</div></div></div></section></div>`}

function detailedCatalog(kind,rows,filterKey,columns,modalType,desc){let selected=rows.filter(r=>r.join(' ').includes(state[filterKey]));let helpers=kind==='合同模板'?[['原件管理','DOCX、文字型 PDF 和 TXT 可存档；DOCX 可配置字段规则。'],['规则发布','确认字段区域和校验条件后发布版本，核验使用固定版本。'],['模板核验','上传实际合同，对比固定条款和字段约束。']]:kind==='审查清单'?[['要求来源','支持文件提取草稿，也可逐条手工添加。'],['确认与发布','硬性要求与优先偏好分开，发布后版本固定。'],['用于审查','审查结果逐项展示通过、不通过、待确认或不适用。']]:[['分类关联','一个分类下可关联多份清单。'],['名称与编码','分类名称和编码需保持唯一。'],['删除条件','移除或迁移关联清单后可删除分类。']];return `<div class="catalog-hero"><div><span class="kicker">标准与资料</span><h1>${kind}</h1><p>${desc}</p></div><div class="actions">${kind==='合同模板'?B('模板分组',"openModal('groups')")+B('配置规则',"openModal('rules')"):''}${B('新建'+kind,`openModal('${modalType}')`,'primary')}</div></div><div class="catalog-detail"><section class="card"><div class="tool-row"><div class="row"><input class="search" data-filter="${filterKey}" placeholder="搜索名称、状态或分类" value="${esc(state[filterKey])}" oninput="updateFilter(this,'${filterKey}')">${B('清空',`state.${filterKey}='';render()`)}</div>${P('共 '+selected.length+' 项')}</div><div class="table-wrap"><table class="table"><thead><tr>${columns.map(c=>`<th>${c}</th>`).join('')}<th>操作</th></tr></thead><tbody>${selected.map(r=>`<tr>${r.map((v,i)=>`<td>${i===2&&v.includes('已发布')?P(v,'good'):esc(v)}</td>`).join('')}<td>${B('详情',`openModal('${modalType}detail')`)}${B('编辑',`openModal('${modalType}')`)}</td></tr>`).join('')}</tbody></table>${selected.length?'':'<div class="empty">没有匹配项目。清空搜索后重试。</div>'}</div></section><aside class="card"><h2>操作指引</h2>${helpers.map(([title,text])=>`<div class="helper-card"><b>${title}</b><p>${text}</p></div>`).join('')}${kind==='合同模板'?B('发起模板核验',"state.flow='template';nav('start')"):kind==='审查清单'?B('查看业务分类',"nav('categories')"):B('查看审查清单',"nav('checklists')")}</aside></div>`}
function renderTemplates(){return detailedCatalog('合同模板',templates,'templateFilter',['模板名称','格式','规则状态','分组'],'template','维护原件、分组和可发布的 DOCX 模板规则。')}
function renderChecklists(){return detailedCatalog('审查清单',checklists,'checkFilter',['清单名称','业务分类','状态'],'checklist','将企业制度整理为可核验的逐项审查要求。')}
function renderCategories(){return detailedCatalog('业务分类',categories,'categoryFilter',['分类名称','编码','关联清单'],'category','用稳定的业务分类组织模板与审查清单。')}

function renderRecords(){let rows=records.filter(r=>(state.activeRecordTab==='全部'||r[2]===state.activeRecordTab)&&r.join(' ').includes(state.recordFilter));return `<div class="catalog-hero"><div><span class="kicker">工作记录</span><h1>审查记录</h1><p>继续未完成的复核、查看交付版本，或导出审查记录。</p></div>${B('发起新审查',"state.flow='ai';nav('start')",'primary')}</div><div class="overview"><div class="metric"><div><small>全部任务</small><strong>3</strong><span class="hint">包含历史审查与模板核验</span></div><span class="metric-icon">▤</span></div><div class="metric"><div><small>复核中</small><strong>1</strong><span class="hint">可继续处理意见</span></div><span class="metric-icon">✎</span></div><div class="metric"><div><small>已完成</small><strong>1</strong><span class="hint">可导出交付文件</span></div><span class="metric-icon">✓</span></div></div><section class="card"><div class="tool-row"><div class="row"><input class="search" data-filter="recordFilter" placeholder="搜索合同名称、类型或状态" value="${esc(state.recordFilter)}" oninput="updateFilter(this,'recordFilter')">${B('清空',"state.recordFilter='';render()")}</div>${B('导出 CSV',"downloadText('审查记录')")}</div><div class="tabs">${['全部','复核中','已完成','需人工确认'].map(t=>`<button class="${state.activeRecordTab===t?'active':''}" onclick="setDetail('activeRecordTab','${t}')">${t}</button>`).join('')}</div><div class="table-wrap"><table class="table"><thead><tr><th>合同 / 任务</th><th>类型</th><th>处理状态</th><th>更新日期</th><th>下一步</th></tr></thead><tbody>${rows.map(r=>`<tr><td><b>${r[0]}</b><br><span class="tiny">${r[1]==='风险审查'?'合同风险及条款建议':'标准模板字段与固定内容'}</span></td><td>${r[1]}</td><td>${P(r[2],r[2]==='已完成'?'good':'medium')}</td><td>${r[3]}</td><td>${B(r[1]==='模板核验'?'查看报告':r[2]==='已完成'?'查看结果':'继续复核',r[1]==='模板核验'?"nav('validations')":"nav('workbench')")}${B('导出',"downloadText('报告')")}</td></tr>`).join('')}</tbody></table>${rows.length?'':'<div class="empty">没有匹配记录。调整关键词或状态筛选。</div>'}</div></section>`}
function renderValidations(){return `<div class="catalog-hero"><div><span class="kicker">工作记录</span><h1>模板核验记录</h1><p>逐项查看固定条款与字段规则的结论；无法确定的内容保留人工确认。</p></div>${B('新建模板核验',"state.flow='template';nav('start')",'primary')}</div><div class="catalog-detail"><section class="card"><div class="section-title"><h2>最近的核验</h2>${P('1 份报告')}</div><div class="table-wrap"><table class="table"><thead><tr><th>核验文件</th><th>基准模板</th><th>结论</th><th>日期</th><th>操作</th></tr></thead><tbody><tr><td><b>${esc(state.validationResult?state.validationFile:'办公设备采购合同.docx')}</b><br><span class="tiny">DOCX · 规则版本固定</span></td><td>${esc(state.selectedTemplate)}</td><td>${P('需人工确认','medium')}</td><td>2026-10-22</td><td>${B('查看报告',"openModal('validation')")}</td></tr></tbody></table></div></section><aside class="card"><h2>结果说明</h2><div class="helper-card"><b>符合规则</b><p>已检查的固定内容和字段满足当前模板规则。</p></div><div class="helper-card"><b>需修改</b><p>发现明确的固定内容差异或字段约束不符。</p></div><div class="helper-card"><b>需人工确认</b><p>解析或规则覆盖不足，不能自动判断。</p></div></aside></div>`}

const baseOpenModal=openModal;
openModal=function(type){if(!['validation','rules','report'].includes(type)){baseOpenModal(type);return}let title='',body='';if(type==='validation'){title='合同模板核验报告';body=`<div class="report-grid"><div><strong>3</strong><small>已检查项目</small></div><div><strong>1</strong><small>待人工确认</small></div><div><strong>0</strong><small>明确不符合</small></div></div><div class="form-section">${sectionHead('字段与固定内容')}<div class="rule-card"><b>甲方名称 ${P('符合规则','good')}</b><small>必填字段，已提取有效文本</small></div><div class="rule-card"><b>合同金额 ${P('需人工确认','medium')}</b><small>文件中的金额表达无法可靠映射至整数范围规则</small></div><div class="rule-card"><b>固定条款 ${P('符合规则','good')}</b><small>未发现可确认的固定文字改动</small></div></div><p class="notice">本报告是原型示例，不能作为自动免审结论。</p>`}else if(type==='rules'){title='模板规则配置 · 云服务采购标准模板';body=`<div class="micro-steps"><span><b>1</b>定位字段</span><em></em><span><b>2</b>设置规则</span><em></em><span><b>3</b>试算与发布</span></div><div class="form-two"><div><div class="rule-card"><b>甲方名称 ${P('已确认','good')}</b><small>第 1 页 · 第 2 段 · 必填</small></div><div class="rule-card"><b>合同金额 ${P('待确认','medium')}</b><small>第 1 页 · 第 8 段 · 整数范围</small></div><div class="rule-card"><b>签署日期 ${P('已确认','good')}</b><small>第 2 页 · 日期格式</small></div></div><div><label class="field">字段名称<input value="合同金额"></label><label class="field">规则类型<select><option>整数范围</option><option>必填</option><option>长度</option><option>日期</option><option>枚举</option></select></label><div class="form-two"><label class="field">最小值<input value="1000"></label><label class="field">最大值<input value="500000"></label></div></div></div><div class="notice">发布后形成不可变版本。试算实际 DOCX 后，再确认字段区域与无法判断的内容。</div>`}else{title='审查交付与意见书';body=`<div class="report-grid"><div><strong>${state.issues.length}</strong><small>建议事项</small></div><div><strong>${state.issues.filter(x=>x.status==='待处理').length}</strong><small>待处理</small></div><div><strong>${state.issues.filter(x=>x.status==='已采纳').length}</strong><small>已采纳</small></div></div><div class="form-section">${sectionHead('交付内容')}<div class="rule-card"><b>当前稿</b><small>包含已采纳修改的可编辑正文</small></div><div class="rule-card"><b>修订稿</b><small>保留原文与修改痕迹</small></div><div class="rule-card"><b>审查意见书</b><small>背景、证据、判断、要求核验与处理状态</small></div></div>`}document.getElementById('modal-body').innerHTML=`<div class="section-title"><h2>${title}</h2><button class="btn" onclick="closeModal()">关闭</button></div>${body}<div class="section row" style="justify-content:flex-end">${B('返回',"closeModal()")}${B(type==='report'?'导出示例':'完成',type==='report'?"closeModal();downloadText('意见书')":"closeModal()",'primary')}</div>`;document.getElementById('modal').classList.remove('hide')}

document.addEventListener('dragover',event=>{const drop=event.target.closest?.('.drop');if(drop){event.preventDefault();drop.classList.add('drag')}});
document.addEventListener('dragleave',event=>{event.target.closest?.('.drop')?.classList.remove('drag')});
document.addEventListener('drop',event=>{const drop=event.target.closest?.('.drop');if(!drop)return;event.preventDefault();drop.classList.remove('drag');const file=event.dataTransfer?.files?.[0];if(!file)return;if(file.size>10*1024*1024){toast('文件超过 10 MB，请重新选择');return}const key=state.flow==='template'?'validationFile':'file';if(key==='validationFile'&&!file.name.toLowerCase().endsWith('.docx')){toast('模板核验仅支持 DOCX');return}state[key]=file.name;render();toast('已选择 '+file.name)});
function renderWorkbench(){
 const issue=state.issues[state.selectedIssue];
 const pending=state.issues.filter(x=>x.status==='待处理').length;
 const accepted=state.issues.filter(x=>x.status==='已采纳').length;
 const rejected=state.issues.filter(x=>x.status==='已拒绝').length;
 const high=state.issues.filter(x=>x.level==='high').length;
 return `<div class="work-top"><div class="work-title"><span class="work-icon">▤</span><div><h1>云服务采购协议</h1><p>合同审查工作台 · 标准尺度 · 中立审慎 · 当前处理状态：${state.reviewStatus}</p></div></div><div class="actions">${B('返回审查记录',"nav('records')")}${B('保存进度',"toast('处理进度已保存（原型演示）')")}${B('交付与导出',"openModal('report')")}${B('完成审核',"finishReview()",'primary')}</div></div>
 <div class="work-grid two-column"><section class="work-panel"><div class="panel-head"><div><h2>合同正文</h2><span class="tiny">点击高亮条款，右侧显示问题详情</span></div><div class="row">${B('编辑',"openModal('edit')")}${B('导出 Word',"downloadText('当前稿')")}</div></div><div class="document-bar"><div class="choice">${[['marked','修订标记'],['current','当前稿'],['original','原始稿'],['compare','双栏对照']].map(([key,label])=>`<button class="${state.mode===key?'active':''}" onclick="setDetail('mode','${key}')">${label}</button>`).join('')}</div><span class="tiny">A4 预览 · 100%</span></div><div class="document-scroll"><div class="paper"><div class="doc-meta"><span>LEXISGRAPH · 合同正文</span><span>第 1 页 / 共 2 页</span></div><h2 class="doc-title">云服务采购协议</h2><p class="doc-paragraph">甲方：星河科技有限公司<br>乙方：远山云计算有限公司</p><p class="doc-paragraph"><b>第一条 服务内容</b><br>乙方向甲方提供云计算资源、系统维护及技术支持。服务内容及交付标准以附件为准。</p><p class="doc-paragraph"><b>第二条 服务期限</b><br>本协议自双方签署之日起生效，服务期限为十二个月。</p>${state.issues.map((x,n)=>`<div class="doc-clause ${n===state.selectedIssue?'selected':''}" onclick="focusIssue(${n})"><b>${x.clause}</b>${P(x.status==='待处理'?x.levelName:x.status,x.status==='已采纳'?'good':x.level)}<br>${esc(state.mode==='original'?x.old:x.status==='已采纳'?x.next:x.old)}${state.mode==='compare'?`<div class="diff-new">建议：${esc(x.next)}</div>`:''}</div>`).join('')}<p class="doc-paragraph"><b>第六条 争议解决</b><br>因本协议产生的争议，双方应先友好协商解决。</p></div></div><div class="document-bar"><span class="tiny">当前稿仅包含已采纳的修改</span><div class="row">${B('导出修订稿',"downloadText('修订稿')")}</div></div></section>
 <section class="work-panel combined-panel"><div class="panel-body"><div class="combined-summary"><div class="section-title"><h2>审查概览</h2>${P(state.reviewStatus,state.reviewStatus==='已完成'?'good':'wait')}</div><div class="issue-counts"><span><b>${pending}</b>待处理</span><span><b>${high}</b>高风险</span><span><b>${accepted} / ${rejected}</b>已采纳 / 已拒绝</span></div></div><div class="combined-list"><div class="section-title"><h2>问题导航</h2><span class="tiny">选择问题，查看下方详情</span></div>${state.issues.map((x,n)=>`<div class="work-issue ${n===state.selectedIssue?'selected':''}" tabindex="0" role="button" aria-label="查看${esc(x.title)}" onclick="focusIssue(${n})" onkeydown="if(event.key==='Enter')focusIssue(${n})"><span class="index">0${n+1}</span><div><h3>${esc(x.title)}</h3><p>${x.clause} · ${x.status}</p></div>${P(x.levelName,x.level)}</div>`).join('')}</div><div class="combined-detail"><div class="side-tab">${[['opinions','审查意见'],['requirements','要求核验'],['activity','处理记录']].map(([key,label])=>`<button class="${state.tab===key?'active':''}" onclick="setDetail('tab','${key}')">${label}</button>`).join('')}</div><div class="combined-detail-inner">${state.tab==='opinions'?`<div class="row">${P(issue.levelName,issue.level)} ${P(issue.status,issue.status==='已采纳'?'good':'wait')}</div><h2 class="opinion-title">${esc(issue.title)}</h2><p class="opinion-text">${issue.clause} · 建议 0${state.selectedIssue+1} / 0${state.issues.length}</p><div class="form-section">${sectionHead('原文证据')}<div class="evidence">${esc(issue.old)}</div></div><div class="form-section">${sectionHead('建议修订','红色为原文，绿色为建议')}<div class="diff-old">− ${esc(issue.old)}</div><div class="diff-new">＋ ${esc(issue.next)}</div></div><div class="form-section">${sectionHead('判断依据')}<p class="opinion-text">${esc(issue.reason)}</p></div><div class="decision-row">${B('采纳此条修改',"issueAction('已采纳')",'primary')}${B('拒绝',"issueAction('已拒绝')")}${B('调整建议',"openModal('rewrite')")}</div><div class="section">${B('批量采纳非高风险建议',"acceptLowRisk()")}</div>`:state.tab==='requirements'?`<h2>要求覆盖情况</h2><p class="opinion-text">逐项展示结论与需要人工判断的原因。</p><div class="status-line"><span>付款与验收挂钩</span>${P('待确认','medium')}</div><div class="status-line"><span>服务中断责任</span>${P('不符合','high')}</div><div class="status-line"><span>商业秘密保护</span>${P('待确认','medium')}</div><div class="section">${B('查看企业审查清单',"nav('checklists')")}</div>`:`<h2>处理记录</h2><div class="timeline">${state.issues.map(x=>`<div><strong>${esc(x.title)}</strong>${x.status} · 本次审查</div>`).join('')}</div><div class="section">${B('下载 JSON 审核记录',"downloadText('审核记录')")}</div>`}<div class="form-section">${sectionHead('交付')}<div class="row">${B('意见书预览',"openModal('report')")}${B('导出意见书',"downloadText('意见书')")}</div></div></div></div></div></section></div>`
}
render();

// Review delivery is a single action in the upper-right corner, available after completion.
const accordionWorkbench=renderWorkbench;
renderWorkbench=function(){
  const root=document.createElement('div');
  root.innerHTML=accordionWorkbench();
  root.querySelectorAll('.work-panel button').forEach(button=>{
    if(/编辑|调整建议|导出|下载/.test(button.textContent.trim()))button.remove();
  });
  root.querySelectorAll('.work-panel .row').forEach(row=>{if(!row.children.length)row.remove()});
  const topActions=root.querySelector('.work-top .actions');
  const completed=state.reviewStatus==='已完成';
  topActions.innerHTML=`${B('返回审查记录',"nav('records')")}${B('保存进度',"toast('处理进度已保存（原型演示）')")}${completed?P('审核已完成','good'):B('完成审核',"finishReview()",'primary')}<button class="btn ${completed?'primary':''}" ${completed?'':'disabled title="完成审核后可导出"'} onclick="openExportMenu()">导出</button>`;
  return root.innerHTML;
};
const guardedDownload=downloadText;
downloadText=function(name){
  if(state.page==='workbench'&&state.reviewStatus!=='已完成'){
    toast('完成审核后才能导出');return;
  }
  guardedDownload(name);
};
function openExportMenu(){
  if(state.reviewStatus!=='已完成'){toast('请先完成审核');return}
  document.getElementById('modal-body').innerHTML=`<div class="section-title"><h2>导出审核成果</h2><button class="btn" onclick="closeModal()">关闭</button></div><p class="muted">审核已完成。选择需要交付的内容。</p><div class="list section"><button class="list-item" onclick="closeModal();downloadText('当前稿')"><span><b>当前稿</b><br><span class="hint">包含已采纳建议的合同正文</span></span>↓</button><button class="list-item" onclick="closeModal();downloadText('修订稿')"><span><b>修订稿</b><br><span class="hint">展示原文与修改痕迹</span></span>↓</button><button class="list-item" onclick="closeModal();downloadText('意见书')"><span><b>审查意见书</b><br><span class="hint">问题、证据、建议与处理结果</span></span>↓</button><button class="list-item" onclick="closeModal();downloadText('审核记录')"><span><b>审核记录</b><br><span class="hint">本次审核的结构化记录</span></span>↓</button></div><div class="section notice">原型下载的是标明示例的 TXT 文件。</div>`;
  document.getElementById('modal').classList.remove('hide');
}
const previewModal=openModal;
openModal=function(type){
  if(type==='edit'||type==='rewrite'){toast('此原型的工作台不提供编辑');return}
  previewModal(type);
  if(type==='report')document.querySelectorAll('#modal-body button').forEach(button=>{if(button.textContent.includes('导出'))button.remove()});
};
render();

// The issue row is an accordion: its evidence, redline and actions open directly below it.
state.expandedIssue = null;
const twoColumnWorkbench = renderWorkbench;
renderWorkbench = function(){
  const root=document.createElement('div');
  root.innerHTML=twoColumnWorkbench();
  const list=root.querySelector('.combined-list');
  const detail=root.querySelector('.combined-detail');
  const tabs=detail.querySelector('.side-tab');
  list.prepend(tabs);
  const rows=[...list.querySelectorAll('.work-issue')];
  rows.forEach((row,index)=>{
    row.setAttribute('aria-expanded',String(state.tab==='opinions'&&state.expandedIssue===index));
    row.setAttribute('aria-controls',`issue-detail-${index}`);
    row.setAttribute('aria-label',`${state.issues[index].title}，${state.expandedIssue===index?'点击收起':'点击展开'}详情`);
    if(state.tab==='opinions'&&state.expandedIssue===index){
      row.classList.add('expanded');
      const expanded=document.createElement('div');
      expanded.className='issue-expanded';
      expanded.id=`issue-detail-${index}`;
      expanded.innerHTML=detail.querySelector('.combined-detail-inner').innerHTML;
      row.after(expanded);
    }else row.classList.remove('selected');
  });
  if(state.tab==='opinions')detail.remove();
  return root.innerHTML;
};
focusIssue=function(index){
  state.selectedIssue=index;
  state.expandedIssue=state.expandedIssue===index?null:index;
  state.tab='opinions';
  render();
  if(state.expandedIssue!==null){
    document.querySelector('.doc-clause.selected')?.scrollIntoView({behavior:'smooth',block:'center'});
  }
};
render();

// Keep the home, risk review and template validation as separate destinations.
menus.splice(0,1,['start','工作台首页','⌂'],['review-new','新建风险审查','✧'],['template-new','新建模板核验','☑']);
menus.splice(1,2);
if(['review-new','template-new'].includes(location.hash.slice(1)))state.page=location.hash.slice(1);
function renderStart(){return `<div class="hero"><div><span class="kicker">合同工作台</span><h1>今天要处理哪份合同？</h1><p>从明确的任务入口开始，已有工作可从记录继续。</p></div><div class="mini"><span class="hint">当前工作空间</span><strong>LexisGraph · 本地</strong><span class="hint">模型状态：按当前配置运行</span></div></div><div class="overview"><div class="metric"><div><small>进行中的审查</small><strong>1</strong><span class="hint">继续处理未决建议</span></div><span class="metric-icon">▤</span></div><div class="metric"><div><small>待人工确认</small><strong>2</strong><span class="hint">模板核验与要求覆盖</span></div><span class="metric-icon">◇</span></div><div class="metric"><div><small>最近的合同草稿</small><strong>1</strong><span class="hint">可导出或送审</span></div><span class="metric-icon">✎</span></div></div><div class="workspace-grid"><section class="card flow-card"><div class="section-title"><div><h2>开始新任务</h2><p class="section-caption">两类任务分别进入独立准备页，材料和条件更清晰。</p></div></div><div class="home-actions"><button class="path" onclick="nav('review-new')"><span class="path-icon">✧</span><b>新建风险审查 →</b><span>上传或粘贴合同，设置审查立场、清单和重点要求，随后进入工作台。</span></button><button class="path" onclick="nav('template-new')"><span class="path-icon">☑</span><b>新建模板核验 →</b><span>选择已发布的 DOCX 基准模板，上传待核验合同，逐项查看报告。</span></button></div></section><aside class="card home-recent"><div class="section-title"><h2>继续已有工作</h2>${B('全部记录',"nav('records')")}</div><div class="timeline"><div><strong>云服务采购协议 ${P('复核中','medium')}</strong>3 项建议待处理 · 今天 14:28</div><div><strong>技术保密协议 ${P('已完成','good')}</strong>查看审核结果 · 10 月 20 日</div><div><strong>办公设备采购合同 ${P('需人工确认','medium')}</strong>查看模板核验报告 · 10 月 18 日</div></div><div class="section">${B('继续审查云服务采购协议',"nav('workbench')",'primary')}</div></aside></div><div class="section card"><div class="section-title"><h2>常用管理</h2></div><div class="row">${B('合同起草',"nav('drafts')")}${B('合同模板',"nav('templates')")}${B('审查清单',"nav('checklists')")}${B('业务分类',"nav('categories')")}</div></div>`}
function taskGuide(kind){return `<aside class="card task-guide"><h2>${kind==='risk'?'风险审查说明':'模板核验说明'}</h2>${kind==='risk'?`<div class="helper-card"><b>输入材料</b><p>可上传 DOCX、文字型 PDF、TXT，也可以粘贴正文。</p></div><div class="helper-card"><b>审查视角</b><p>立场、尺度和企业清单会影响建议的判断方向；重点要求可单独填写。</p></div><div class="helper-card"><b>审查结果</b><p>工作台展示证据、建议和逐条处理状态，完成审核后才能导出。</p></div>`:`<div class="helper-card"><b>基准版本</b><p>仅使用已发布的 DOCX 模板规则，版本在本次核验中固定。</p></div><div class="helper-card"><b>核验范围</b><p>检查固定内容、必填项、长度、日期、金额与枚举规则。</p></div><div class="helper-card"><b>人工确认</b><p>无法可靠解析或判断的内容明确列为待人工确认。</p></div>`}<div class="section">${B('返回工作台首页',"nav('start')")}</div></aside>`}
function renderReviewNew(){return `<div class="task-page"><div class="catalog-hero"><div><span class="kicker">合同风险审查</span><h1>新建风险审查</h1><p>添加合同，再设置审查条件。准备完成后进入合同审查工作台。</p></div>${P('准备材料')}</div><div class="task-layout"><section class="card task-form">${detailedAiForm()}</section>${taskGuide('risk')}</div></div>`}
function renderTemplateNew(){return `<div class="task-page"><div class="catalog-hero"><div><span class="kicker">标准模板核验</span><h1>新建模板核验</h1><p>使用已发布的模板规则核对实际 DOCX，形成逐项核验报告。</p></div>${P('准备材料')}</div><div class="task-layout"><section class="card task-form">${detailedTemplateForm()}</section>${taskGuide('template')}</div></div>`}
const existingRender=render;
render=function(){
  if(state.page!=='review-new'&&state.page!=='template-new'){existingRender();return}
  document.getElementById('nav').innerHTML=menus.map(([key,name,icon])=>`<button class="${state.page===key?'active':''}" onclick="nav('${key}')"><i>${icon}</i>${name}</button>`).join('');
  document.getElementById('crumb').textContent=state.page==='review-new'?'新建风险审查':'新建模板核验';
  document.getElementById('view').innerHTML=state.page==='review-new'?renderReviewNew():renderTemplateNew();
};
const previousRecords=renderRecords;
renderRecords=function(){return previousRecords().replace("state.flow='ai';nav('start')","nav('review-new')")};
const previousValidations=renderValidations;
renderValidations=function(){return previousValidations().replace("state.flow='template';nav('start')","nav('template-new')")};
const previousTemplates=renderTemplates;
renderTemplates=function(){return previousTemplates().replace("state.flow='template';nav('start')","nav('template-new')")};
const previousDraftReview=draftReview;
draftReview=function(){if(!state.draftText.trim()){toast('请先生成或填写合同正文');return}state.contractText=state.draftText;state.source='paste';nav('review-new');toast('已将草稿带入风险审查准备页')};
const originalTaskGuide=taskGuide;
taskGuide=function(kind){return originalTaskGuide(kind).replace('返回工作台首页',kind==='risk'?'返回审查记录':'返回模板核验记录').replace("nav('start')",kind==='risk'?"nav('records')":"nav('validations')")};
records.splice(2,1);
const separatedReviewRecords=renderRecords;
renderRecords=function(){return separatedReviewRecords().replace('<strong>3</strong><span class="hint">包含历史审查与模板核验</span>',`<strong>${records.length}</strong><span class="hint">仅显示风险审查记录</span>`)};
render();
// 1. 为左侧导航增加视觉分组标题，降低认知负荷
const groupedRender = render;
render = function () {
  groupedRender();
  const navEl = document.getElementById('nav');
  if (!navEl) return;
  const groupTitles = {
    'start': '核心作业',
    'records': '记录与追踪',
    'templates': '标准资产库'
  };
  [...navEl.querySelectorAll('button')].forEach(btn => {
    const match = btn.getAttribute('onclick')?.match(/nav\('([^']+)'\)/);
    const key = match?.[1];
    if (key && groupTitles[key]) {
      const label = document.createElement('small');
      label.style.cssText = 'padding:12px 12px 4px;display:block;color:#64748b;font-size:10.5px;font-weight:700;letter-spacing:.08em';
      label.textContent = groupTitles[key];
      btn.before(label);
    }
  });
};

// 2. 审查工作台支持键盘上下键（↑ / ↓）快速切换风险条款
document.addEventListener('keydown', e => {
  if (state.page !== 'workbench' || ['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName)) return;
  if (e.key === 'ArrowDown' || e.key === 'j') {
    e.preventDefault();
    focusIssue((state.selectedIssue + 1) % state.issues.length);
  } else if (e.key === 'ArrowUp' || e.key === 'k') {
    e.preventDefault();
    focusIssue((state.selectedIssue - 1 + state.issues.length) % state.issues.length);
  }
});

render();