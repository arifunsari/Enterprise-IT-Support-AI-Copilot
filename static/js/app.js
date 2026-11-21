const chat = document.getElementById('chat');
const form = document.getElementById('chatForm');
const question = document.getElementById('question');
const trace = document.getElementById('trace');
const sourceUsed = document.getElementById('sourceUsed');

function escapeHtml(s=''){return s.replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));}
function formatText(s=''){return escapeHtml(s).replace(/\n/g,'<br>');}
function addMessage(role, text, source='', citations=[]){
  const wrap=document.createElement('div'); wrap.className=`message ${role}`;
  const citeHtml=citations.length?`<div class="citations"><strong>Sources</strong><br>${citations.map(c=>c.url?`<a href="${escapeHtml(c.url)}" target="_blank" rel="noopener">${escapeHtml(c.title)}</a>`:escapeHtml(c.title)).join('<br>')}</div>`:'';
  wrap.innerHTML=`<div class="avatar">AI</div><div class="bubble">${formatText(text)}${source?`<div class="answer-source">Source: ${escapeHtml(source)}</div>`:''}${citeHtml}</div>`;
  chat.appendChild(wrap); chat.scrollTop=chat.scrollHeight; return wrap;
}
function renderTrace(items=[]){trace.innerHTML=items.length?items.map(x=>`<div class="trace-item">${escapeHtml(x)}</div>`).join(''):'<div class="empty">No trace.</div>';}
function updateAssistantMessage(wrap, text, source='', citations=[]){
  const citeHtml=citations.length?`<div class="citations"><strong>Sources</strong><br>${citations.map(c=>c.url?`<a href="${escapeHtml(c.url)}" target="_blank" rel="noopener">${escapeHtml(c.title)}</a>`:escapeHtml(c.title)).join('<br>')}</div>`:'';
  wrap.querySelector('.bubble').innerHTML=`${formatText(text)}${source?`<div class="answer-source">Source: ${escapeHtml(source)}</div>`:''}${citeHtml}`;
  chat.scrollTop=chat.scrollHeight;
}
async function askAgent(q){
  addMessage('user',q); question.value=''; renderTrace(['Running LangGraph workflow...']); sourceUsed.textContent='Running';
  const btn=form.querySelector('button'); btn.disabled=true;
  try{
    const res=await fetch('/api/chat/stream',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q})});
    if(!res.ok){const data=await res.json(); throw new Error(data.detail||'Request failed');}
    const message=addMessage('assistant',''); let answer=''; let complete=false; const reader=res.body.getReader(); const decoder=new TextDecoder(); let buffer='';
    const handleBlock=block=>{
      const line=block.split('\n').find(item=>item.startsWith('data:'));
      if(!line) return;
      const event=JSON.parse(line.slice(5).trim());
      if(event.type==='token'){answer+=event.token; updateAssistantMessage(message,answer);}
      else if(event.type==='complete'){complete=true; updateAssistantMessage(message,event.answer||answer,event.source_used,event.citations||[]); renderTrace(event.trace||[]); sourceUsed.textContent=event.source_used||'Unknown';}
      else if(event.type==='error') throw new Error(event.detail||'Request failed');
    };
    while(true){const {value,done}=await reader.read(); if(done) break; buffer+=decoder.decode(value,{stream:true}).replace(/\r\n/g,'\n'); let boundary; while((boundary=buffer.indexOf('\n\n'))>=0){handleBlock(buffer.slice(0,boundary)); buffer=buffer.slice(boundary+2);}}
    buffer+=decoder.decode(); if(buffer.trim()) handleBlock(buffer);
    if(!complete) throw new Error('The response stream ended unexpectedly.');
  }catch(e){addMessage('assistant',`Error: ${e.message}`); renderTrace(['Request failed']); sourceUsed.textContent='Error';}
  finally{btn.disabled=false;}
}
form.addEventListener('submit',e=>{e.preventDefault(); const q=question.value.trim(); if(q) askAgent(q);});
document.querySelectorAll('.example').forEach(b=>b.addEventListener('click',()=>askAgent(b.textContent.trim())));

const modal=document.getElementById('uploadModal');
document.getElementById('openUpload').onclick=()=>modal.classList.remove('hidden');
document.getElementById('closeUpload').onclick=()=>modal.classList.add('hidden');
document.getElementById('uploadBtn').onclick=async()=>{
  const file=document.getElementById('fileInput').files[0]; const key=document.getElementById('adminKey').value; const status=document.getElementById('uploadStatus');
  if(!file){status.textContent='Choose a file first.'; return;}
  status.textContent='Indexing document...'; const fd=new FormData(); fd.append('file',file);
  try{const r=await fetch('/api/ingest',{method:'POST',headers:{'X-Admin-Key':key},body:fd}); const d=await r.json(); if(!r.ok) throw new Error(d.detail||'Upload failed'); status.textContent=`Indexed ${d.file}: ${d.chunks} chunks.`;}catch(e){status.textContent=`Error: ${e.message}`;}
};
