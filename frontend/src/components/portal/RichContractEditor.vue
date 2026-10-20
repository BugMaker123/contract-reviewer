<script setup>
import { ref, onMounted, watch, nextTick } from 'vue';
const props = defineProps({html:{type:String,default:''},text:{type:String,default:''},disabled:Boolean});
const emit = defineEmits(['update:html','text-change']);
const editor = ref(null); let lastHtml = null;
const tags = new Set(['P','DIV','SPAN','B','STRONG','I','EM','U','S','SUB','SUP','H1','H2','H3','H4','H5','H6','UL','OL','LI','TABLE','THEAD','TBODY','TFOOT','TR','TD','TH','BLOCKQUOTE','PRE','BR','FONT']);
const excluded = new Set(['SCRIPT','STYLE','IFRAME','OBJECT','EMBED','SVG','MATH','IMG','LINK','META']);
const styleNames = ['font-weight','font-style','font-size','font-family','color','background-color','text-align','text-decoration','margin-left'];
const sanitize = value => {
  const source = document.createElement('template'); source.innerHTML = value;
  const output = document.createElement('div');
  const copy = (node,parent) => {
    if (node.nodeType === Node.TEXT_NODE) { parent.append(document.createTextNode(node.textContent)); return; }
    if (node.nodeType !== Node.ELEMENT_NODE || excluded.has(node.tagName)) return;
    if (!tags.has(node.tagName)) { for (const child of node.childNodes) copy(child,parent); return; }
    const clean = document.createElement(node.tagName === 'FONT' ? 'span' : node.tagName.toLowerCase());
    for (const name of styleNames) {
      const value = node.style.getPropertyValue(name);
      if (value && !/url|expression|@|[<>]/i.test(value)) clean.style.setProperty(name,value);
    }
    if (node.tagName === 'FONT') {
      const sizes = {1:'8pt',2:'10pt',3:'12pt',4:'14pt',5:'18pt',6:'24pt',7:'36pt'};
      if (sizes[node.getAttribute('size')]) clean.style.fontSize = sizes[node.getAttribute('size')];
    }
    for (const name of ['colspan','rowspan']) if (/^[1-9]\d{0,2}$/.test(node.getAttribute(name) || '')) clean.setAttribute(name,node.getAttribute(name));
    if (node.getAttribute('align') && ['left','right','center','justify'].includes(node.getAttribute('align'))) clean.style.textAlign = node.getAttribute('align');
    for (const child of node.childNodes) copy(child,clean);
    parent.append(clean);
  };
  for (const child of source.content.childNodes) copy(child,output);
  return output.innerHTML;
};
const sync = () => {
  lastHtml = editor.value.innerHTML;
  emit('update:html',lastHtml);
  emit('text-change',editor.value.innerText.replace(/\u00a0/g,' '));
};
const insert = html => {
  editor.value.focus();
  const selection = window.getSelection();
  if (!selection.rangeCount || !editor.value.contains(selection.anchorNode)) {
    const range = document.createRange(); range.selectNodeContents(editor.value); range.collapse(false); selection.removeAllRanges(); selection.addRange(range);
  }
  const range = selection.getRangeAt(0); range.deleteContents();
  const fragment = range.createContextualFragment(html); const last = fragment.lastChild;
  range.insertNode(fragment); if (last) { range.setStartAfter(last); range.collapse(true); selection.removeAllRanges(); selection.addRange(range); }
  sync();
};
const paste = event => {
  event.preventDefault();
  const html = event.clipboardData.getData('text/html');
  if (html) insert(sanitize(html));
  else { const div = document.createElement('div'); div.textContent = event.clipboardData.getData('text/plain'); insert(div.innerHTML.replace(/\n/g,'<br>')); }
};
const command = (name,value=null) => { editor.value.focus(); document.execCommand(name,false,value); sync(); };
const restore = () => {
  if (!editor.value || props.html === lastHtml) return;
  if (props.html) editor.value.innerHTML = sanitize(props.html);
  else { editor.value.textContent = props.text; }
  lastHtml = editor.value.innerHTML;
};
onMounted(restore);
watch(() => props.html,() => nextTick(restore));
</script>
<template>
  <section class="rich-contract-editor">
    <div class="rich-contract-toolbar" role="toolbar" aria-label="正文格式">
      <button type="button" @mousedown.prevent @click="command('bold')" :disabled="disabled" aria-label="加粗"><b>B</b></button>
      <button type="button" @mousedown.prevent @click="command('italic')" :disabled="disabled" aria-label="斜体"><i>I</i></button>
      <button type="button" @mousedown.prevent @click="command('underline')" :disabled="disabled" aria-label="下划线"><u>U</u></button>
      <button type="button" @mousedown.prevent @click="command('insertUnorderedList')" :disabled="disabled">项目列表</button>
      <button type="button" @mousedown.prevent @click="command('insertOrderedList')" :disabled="disabled">编号列表</button>
      <button type="button" @mousedown.prevent @click="command('justifyCenter')" :disabled="disabled">居中</button>
      <button type="button" @mousedown.prevent @click="command('justifyLeft')" :disabled="disabled">左对齐</button>
      <select aria-label="正文字号" @change="command('fontSize',$event.target.value)" :disabled="disabled"><option value="3">12 pt</option><option value="4">14 pt</option><option value="5">18 pt</option><option value="6">24 pt</option></select>
    </div>
    <div ref="editor" role="textbox" aria-label="合同正文" aria-multiline="true" :contenteditable="!disabled" class="rich-contract-content" data-placeholder="在此粘贴合同正文，保留常用文字、段落及表格样式…" @input="sync" @paste="paste" @drop.prevent />
    <p class="text-xs text-slate-400 mt-2">支持加粗、字号、颜色、段落、列表及表格。复杂页眉页脚和精确版式请上传 DOCX。</p>
  </section>
</template>
