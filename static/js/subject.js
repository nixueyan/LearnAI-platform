let currentChapterId = null;
let currentChapterTitle = "";

function switchTab(tabName) {
  document.querySelectorAll(".tab-pane").forEach(pane => pane.classList.remove("active"));
  document.querySelectorAll(".tab-button").forEach(btn => btn.classList.remove("active"));
  const tabPane = document.getElementById('tab-'+tabName);
  if (tabPane) tabPane.classList.add("active");
  document.querySelectorAll(".tab-button").forEach(btn => {
    const oc = btn.getAttribute("onclick") || "";
    if (oc.includes("'"+tabName+"'") || oc.includes('"'+tabName+'"')) {
      btn.classList.add("active");
    }
  });
  if (tabName === 'mindmap') {
    var sid = new URLSearchParams(window.location.search).get('id') || '1';
    loadMindMap(sid);
  }
  if (tabName === 'ppt') {
    loadPPTs();
  }
}

// ===== 公共资源：共享 PPT 列表（测试阶段，无需登录）=====
async function loadPPTs() {
  const box = document.getElementById('ppt-list');
  if (!box) return;
  box.innerHTML = '<p class="muted">加载中…</p>';
  let items = [];
  try {
    const r = await fetch('/api/ppts');
    if (!r.ok) throw new Error('HTTP ' + r.status);
    items = await r.json();
  } catch (e) {
    box.innerHTML = '<p class="muted" style="color:#e74c3c">⚠️ 加载失败：' + e.message + '</p>';
    return;
  }
  if (!items || items.length === 0) {
    box.innerHTML = '<p class="muted">暂无共享 PPT。</p>';
    return;
  }
  box.innerHTML = '';
  items.forEach(function (it) {
    const sizeKB = it.size ? (it.size / 1024).toFixed(0) + ' KB' : '';
    const label = (it.name || 'PPT').replace(/\.pptx$/i, '');
    const card = document.createElement('div');
    card.style.cssText = 'border:1px solid var(--border-color);border-radius:12px;padding:16px;background:var(--bg-primary);box-shadow:0 2px 8px rgba(0,0,0,.06);display:flex;flex-direction:column;gap:10px;';
    card.innerHTML =
      '<div style="font-size:28px;">📊</div>' +
      '<div style="font-weight:600;font-size:15px;">' + label + '</div>' +
      '<div class="muted" style="font-size:12px;color:#888;">' + sizeKB + '</div>' +
      '<a href="' + it.url + '" target="_blank" download style="display:inline-block;text-align:center;padding:8px 12px;border-radius:8px;background:var(--button-primary,#4CAF82);color:#fff;text-decoration:none;font-size:13px;">⬇ 下载 / 查看</a>';
    box.appendChild(card);
  });
}

// ===== 资源生成 =====
async function generateResources() {
  if (!currentChapterId) {
    renderMessage("请先选择章节", "resource-message");
    return;
  }
  const types = Array.from(document.querySelectorAll("input[name='res-type']:checked")).map(cb => cb.value);
  if (types.length === 0) {
    renderMessage("请至少选择一种资源类型", "resource-message");
    return;
  }
  const btn = document.getElementById("btn-generate-resource");
  const loading = document.getElementById("resource-loading");
  if (btn) btn.disabled = true;
  if (loading) loading.style.display = "inline";
  try {
    const results = await request(`/chapters/${currentChapterId}/resources/generate`, {
      method: "POST",
      body: JSON.stringify({ resource_types: types, provider: document.getElementById("ai-provider")?.value || "xunfei" }),
    });
    await loadChapterResources(currentChapterId, currentChapterTitle);
    renderMessage(`✅ 已生成 ${results.length} 个资源并存入公共库`, "resource-message");
  } catch (err) {
    renderMessage("生成失败: " + err.message, "resource-message");
  } finally {
    if (btn) btn.disabled = false;
    if (loading) loading.style.display = "none";
  }
}

// ===== 题库练习 =====
let currentQuizQuestions = [];

async function startWeakQuiz(){
  if(!currentChapterId){if(typeof renderMessage==='function')renderMessage('请先选择章节','quiz-message');return}
  var types=['选择题','填空题','计算题','证明题'];
  document.querySelectorAll('input[name="quiz-type"]').forEach(function(cb){cb.checked=false});
  types.forEach(function(t){var cb=document.querySelector('input[value="'+t+'"]');if(cb)cb.checked=true});
  document.getElementById('quiz-difficulty').value='简单';
  document.getElementById('quiz-count').value='5';
  startQuiz();
}

async function startQuiz() {
  const types = Array.from(document.querySelectorAll("input[name='quiz-type']:checked")).map(cb => cb.value);
  const difficulty = document.getElementById("quiz-difficulty").value;
  const count = parseInt(document.getElementById("quiz-count").value);
  if (!currentChapterId) { renderMessage("请先选择章节", "quiz-message"); return; }
  if (types.length === 0) { renderMessage("请选择至少一种题型", "quiz-message"); return; }
  try {
    const result = await request("/quiz/generate", {
      method: "POST",
      body: JSON.stringify({ chapter_id: currentChapterId, question_types: types, difficulty: difficulty, count: count }),
    });
    if (!result.questions || result.questions.length === 0) {
      renderMessage("该章节暂无符合条件题目，请调整筛选条件", "quiz-message"); return;
    }
    currentQuizQuestions = result.questions;
    document.getElementById("quiz-setup").style.display = "none";
    var quizContent = document.getElementById("quiz-content");
    quizContent.style.display = "block";
    quizContent.style.maxHeight = "none";
    quizContent.style.overflowY = "visible";
    var output = document.getElementById("quiz-output");
    output.innerHTML = "";
    if (result.questions.length < count) {
      var hint = document.createElement("div");
      hint.style.cssText = "padding:10px 16px;background:var(--info-bg);border-radius:8px;margin-bottom:16px;color:var(--info-text);font-size:13px;";
      hint.textContent = "💡 该章节仅有 " + result.questions.length + " 道符合条件的题目（共请求 " + count + " 道）";
      output.appendChild(hint);
    }
    renderQuizQuestions(result.questions, output);
  } catch (err) {
    renderMessage(err.message, "quiz-message");
  }
}

async function submitQuizAnswers() {
  var answers = [], questionIds = [];
  for (var i = 0; i < currentQuizQuestions.length; i++) {
    var q = currentQuizQuestions[i];
    questionIds.push(q.id);
    if (q.question_type === "选择题" && q.options) {
      var selected = document.querySelector('input[name="q-' + q.id + '"]:checked');
      answers.push(selected ? selected.value : "");
    } else {
      var input = document.getElementById("answer-" + q.id);
      answers.push(input ? input.value : "");
    }
  }
  try {
    var result = await request("/quiz/submit?user_id=" + currentUserId, {
      method: "POST",
      body: JSON.stringify({ chapter_id: currentChapterId, question_ids: questionIds, answers: answers }),
    });
    var rec = result.record, details = result.details || [];
    var output = document.getElementById("quiz-output");
    output.innerHTML =
      '<div style="text-align:center;margin-bottom:20px;">' +
        '<div style="font-size:48px;font-weight:bold;color:' + (rec.score >= rec.total_questions / 2 ? 'var(--button-primary)' : '#ef4444') + ';">' + rec.score + '/' + rec.total_questions + '</div>' +
        '<div style="color:var(--text-secondary);">得分</div>' +
      '</div>';
    for (var i = 0; i < details.length; i++) {
      var d = details[i];
      var divEl = document.createElement("div");
      divEl.className = "quiz-item";
      divEl.style.borderLeftColor = d.is_correct ? "var(--button-primary)" : "#ef4444";
      divEl.innerHTML =
        '<div class="quiz-question">' +
          '<span style="color:' + (d.is_correct ? 'var(--button-primary)' : '#ef4444') + ';">' + (d.is_correct ? '✅' : '❌') + '</span> ' +
          (i + 1) + '. [' + d.question_type + '] ' + d.content +
        '</div>' +
        '<div style="margin-top:8px;font-size:13px;">' +
          '<div>你的答案：<strong style="color:' + (d.is_correct ? 'var(--button-primary)' : '#ef4444') + ';">' + (d.your_answer || '（未作答）') + '</strong></div>' +
          (!d.is_correct ? '<div>正确答案：<strong style="color:var(--button-primary);">' + d.correct_answer + '</strong></div>' : '') +
          (d.explanation ? '<div style="margin-top:8px;padding:8px;background:var(--info-bg);border-radius:6px;color:var(--info-text);">💡 ' + d.explanation + '</div>' : '') +
        '</div>';
      output.appendChild(divEl);
    }
    if (window.renderMathInElement) {
      try { renderMathInElement(output, {delimiters:[{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false}]}); } catch(e){}
    }
    var retryBtn = document.createElement("button");
    retryBtn.className = "btn";
    retryBtn.textContent = "🔄 再来一次";
    retryBtn.style.marginTop = "16px";
    retryBtn.onclick = function() {
      document.getElementById("quiz-setup").style.display = "block";
      document.getElementById("quiz-content").style.display = "none";
      document.getElementById("quiz-output").innerHTML = "";
      currentQuizQuestions = [];
    };
    output.appendChild(retryBtn);
    loadQuizHistory();
    loadWrongQuestions();
    if (typeof loadDashboard === 'function') loadDashboard();
  } catch (err) {
    renderMessage(err.message, "quiz-message");
  }
}

// ===== 全局笔记本浮窗 =====
let allNotesCache = [];

async function createNoteFromFloat() {
  const panel = document.getElementById("notebook-float");
  if (panel) panel.style.display = "none";
  openNoteModal(null, "", "", currentChapterId || 1);
}

function toggleNotebook() {
  const panel = document.getElementById("notebook-float");
  if (!panel) return;
  const isOpen = panel.style.display === "flex";
  panel.style.display = isOpen ? "none" : "flex";
  if (!isOpen) loadAllNotes();
}

async function loadAllNotes() {
  try {
    allNotesCache = await request(`/notes/${currentUserId}`);
    renderNotebookList(allNotesCache);
  } catch (e) {
    document.getElementById("notebook-float-body").innerHTML = "<p style='color:var(--text-secondary);'>加载失败</p>";
  }
}

function renderNotebookList(notes) {
  const body = document.getElementById("notebook-float-body");
  if (!body) return;
  if (notes.length === 0) {
    body.innerHTML = "<p style='color:var(--text-secondary);text-align:center;padding:20px;'>暂无笔记</p>";
    return;
  }
  // 用 data-note-id 存 id，点击时从缓存取数据，避免内容含引号/反引号导致 JS 崩溃
  body.innerHTML = notes.map(n => `
    <div class="notebook-float-item" data-note-id="${n.id}">
      <div class="notebook-float-item-title">${n.title || "无标题"}</div>
      <div class="notebook-float-item-preview">${(n.content || "").substring(0, 60)}</div>
    </div>
  `).join("");
  body.querySelectorAll(".notebook-float-item").forEach(el => {
    el.addEventListener("click", function() {
      const nid = parseInt(this.dataset.noteId);
      const note = allNotesCache.find(n => n.id === nid);
      if (note) openNoteFromFloat(note.id, note.title || "", note.content || "", note.chapter_id);
    });
  });
}

function openNoteFromFloat(noteId, title, content, chapterId) {
  const panel = document.getElementById("notebook-float");
  if (panel) panel.style.display = "none";
  openNoteModal(noteId, title, content, chapterId);
}

function searchNotebook() {
  const kw = document.getElementById("notebook-search").value.toLowerCase();
  const filtered = allNotesCache.filter(n =>
    (n.title || "").toLowerCase().includes(kw) ||
    (n.content || "").toLowerCase().includes(kw)
  );
  renderNotebookList(filtered);
}

// ===== 答题历史 =====
async function loadQuizHistory() {
  const historyDiv = document.getElementById("quiz-history");
  if (!historyDiv || !currentChapterId) return;
  try {
    const records = await request(`/quiz/history/${currentUserId}`);
    const chapterRecords = records.filter(r => r.chapter_id === currentChapterId).slice(0, 10);
    if (chapterRecords.length === 0) {
      historyDiv.innerHTML = "<p style='color:var(--text-secondary);'>暂无练习记录</p>"; return;
    }
    var html = "<h4 style='margin-top:20px;'>📊 历史记录</h4>";
    html += "<div style='overflow-x:auto'><table style='width:100%;border-collapse:collapse;font-size:13px'>";
    html += "<tr style='color:var(--text-secondary);border-bottom:2px solid var(--border-color)'><th style='text-align:left;padding:8px'>时间</th><th style='text-align:left;padding:8px'>章节</th><th style='text-align:center;padding:8px'>题数</th><th style='text-align:center;padding:8px'>得分</th><th style='text-align:right;padding:8px'>操作</th></tr>";
    chapterRecords.forEach(r => {
      var pct = Math.round((r.score / r.total_questions) * 100);
      var scoreColor = pct >= 80 ? 'var(--button-primary)' : pct >= 60 ? '#e8a838' : '#ef4444';
      var d = new Date(r.created_at);
      var dateStr = d.getFullYear()+'-'+(d.getMonth()+1)+'-'+d.getDate()+' '+d.toLocaleTimeString().substring(0,5);
      html += "<tr style='border-bottom:1px solid var(--border-color)'>";
      html += "<td style='padding:8px;color:var(--text-secondary)'>"+dateStr+"</td>";
      html += "<td style='padding:8px'>章节 #"+r.chapter_id+"</td>";
      html += "<td style='text-align:center;padding:8px'>"+r.total_questions+"题</td>";
      html += "<td style='text-align:center;padding:8px;font-weight:bold;color:"+scoreColor+"'>"+r.score+"/"+r.total_questions+" ("+pct+"%)</td>";
      html += "<td style='text-align:right;padding:8px'><button class='btn' data-record-id='"+r.id+"' style='padding:2px 10px;font-size:11px'>查看错题</button></td>";
      html += "</tr>";
    });
    html += "</table></div>";
    historyDiv.innerHTML = html;
    // 用事件绑定替代内联 onclick
    historyDiv.querySelectorAll("button[data-record-id]").forEach(btn => {
      btn.addEventListener("click", function() {
        retryWrongFromHistory(parseInt(this.dataset.recordId));
      });
    });
  } catch (e) {}
}

function retryWrongFromHistory(recordId){
  request('/quiz/history/'+currentUserId).then(function(records){
    var rec = records.find(function(r){return r.id===recordId});
    if(!rec)return;
    var wids=[];
    try{JSON.parse(rec.wrong_items||'[]').forEach(function(w){wids.push(w.question_id)})}catch(e){}
    if(wids.length===0)return;
    currentQuizQuestions=[];
    request('/quiz/generate',{method:'POST',body:JSON.stringify({chapter_id:currentChapterId,question_ids:wids,count:wids.length,difficulty:'',question_types:[]})}).then(function(r){
      if(!r.questions||r.questions.length===0)return;
      currentQuizQuestions=r.questions;
      document.getElementById('quiz-setup').style.display='none';
      var qc=document.getElementById('quiz-content');qc.style.display='block';qc.style.maxHeight='none';qc.style.overflowY='visible';
      var output=document.getElementById('quiz-output');
      output.innerHTML='<p style="color:var(--info-text);margin-bottom:12px">重练 '+r.questions.length+' 道错题</p>';
      renderQuizQuestions(r.questions,output);
    });
  });
}

// ===== 笔记 =====
async function addNote() {
  if (!currentChapterId) { renderMessage("请先选择章节", "notes-output"); return; }
  openNoteModal(null, "", "", currentChapterId);
}

async function loadNotes() {
  if (!currentChapterId) return;
  try {
    const notes = await request(`/notes/${currentUserId}?chapter_id=${currentChapterId}`);
    const output = document.getElementById("notes-output");
    output.innerHTML = "";
    if (notes.length === 0) {
      output.innerHTML = "<p>该章节暂无笔记，点击新建笔记开始记录。</p>"; return;
    }
    notes.forEach(note => {
      const noteDiv = document.createElement("div");
      noteDiv.className = "note-item";
      noteDiv.style.cursor = "pointer";
      noteDiv.dataset.noteId = note.id;
      noteDiv.innerHTML = `
        <div class="note-header">
          <span class="note-title">${note.title}</span>
          <span class="note-time">${new Date(note.updated_at).toLocaleString()}</span>
        </div>
        <div class="note-content" style="white-space:normal;max-height:60px;overflow:hidden;color:var(--text-secondary);font-size:13px;">${note.content || "（暂无内容）"}</div>
        <div class="note-actions">
          <button class="edit-btn" data-note-id="${note.id}">编辑</button>
          <button class="delete-btn" data-note-id="${note.id}">删除</button>
        </div>
      `;
      // 用闭包存 note 数据，不拼进 onclick
      const noteData = { id: note.id, title: note.title, content: note.content || "", chapter_id: note.chapter_id };
      noteDiv.querySelector(".edit-btn").addEventListener("click", e => {
        e.stopPropagation();
        openNoteModal(noteData.id, noteData.title, noteData.content, noteData.chapter_id);
      });
      noteDiv.querySelector(".delete-btn").addEventListener("click", e => {
        e.stopPropagation();
        deleteNote(noteData.id);
      });
      noteDiv.addEventListener("click", () => openNoteModal(noteData.id, noteData.title, noteData.content, noteData.chapter_id));
      output.appendChild(noteDiv);
    });
  } catch (err) {
    renderMessage(err.message, "notes-output");
  }
}

function openNoteModal(noteId, title, content, chapterId) {
  const old = document.getElementById("note-edit-modal");
  if (old) old.remove();
  const modal = document.createElement("div");
  modal.id = "note-edit-modal";
  modal.style.cssText = `
    position:fixed;top:60px;right:10px;width:420px;height:600px;
    background:var(--bg-primary);border-radius:16px;
    box-shadow:0 8px 32px rgba(0,0,0,0.3);z-index:9999;
    display:flex;flex-direction:column;border:1px solid var(--border-color);
    resize:both;overflow:hidden;min-width:300px;min-height:200px;
  `;
  modal.innerHTML = `
    <div id="note-modal-drag-bar" style="
      padding:14px 20px;cursor:grab;border-radius:16px 16px 0 0;
      background:var(--bg-secondary);display:flex;justify-content:space-between;align-items:center;
      border-bottom:1px solid var(--border-color);user-select:none;">
      <span style="font-weight:600;color:var(--text-primary);">📝 ${noteId ? "编辑笔记" : "新建笔记"}</span>
      <button id="note-modal-close" style="background:none;border:none;font-size:20px;cursor:pointer;color:var(--text-secondary);">×</button>
    </div>
    <div style="padding:16px 20px;display:flex;flex-direction:column;gap:10px;flex:1;overflow:hidden;">
      <input id="note-modal-title" type="text" placeholder="笔记标题" style="width:100%;flex-shrink:0;"/>
      <textarea id="note-modal-content" placeholder="笔记内容（支持 Markdown）" style="flex:1;width:100%;resize:none;font-family:inherit;padding:10px;border-radius:8px;border:1px solid var(--border-color);background:var(--bg-secondary);color:var(--text-primary);"></textarea>
      <div style="display:flex;justify-content:flex-end;gap:8px;flex-shrink:0;">
        <button class="btn-secondary" id="note-modal-cancel">取消</button>
        <button id="note-modal-save">保存</button>
      </div>
    </div>
  `;
  document.body.appendChild(modal);
  // 用 JS 设值，避免 HTML 属性注入
  document.getElementById("note-modal-title").value = title;
  document.getElementById("note-modal-content").value = content;
  document.getElementById("note-modal-title").focus();
  document.getElementById("note-modal-close").onclick = () => modal.remove();
  document.getElementById("note-modal-cancel").onclick = () => modal.remove();
  document.getElementById("note-modal-save").onclick = () => saveNote(noteId, chapterId);
  // 拖动
  const dragBar = document.getElementById("note-modal-drag-bar");
  let isDragging = false, startX, startY, startLeft, startTop;
  dragBar.addEventListener("mousedown", e => {
    isDragging = true; startX = e.clientX; startY = e.clientY;
    const rect = modal.getBoundingClientRect();
    startLeft = rect.left; startTop = rect.top;
    modal.style.right = "auto"; modal.style.left = startLeft + "px"; modal.style.top = startTop + "px";
    dragBar.style.cursor = "grabbing"; e.preventDefault();
  });
  document.addEventListener("mousemove", e => {
    if (!isDragging) return;
    modal.style.left = (startLeft + e.clientX - startX) + "px";
    modal.style.top = (startTop + e.clientY - startY) + "px";
  });
  document.addEventListener("mouseup", () => { isDragging = false; dragBar.style.cursor = "grab"; });
}

async function saveNote(noteId, chapterId) {
  const title = document.getElementById("note-modal-title").value.trim();
  const content = document.getElementById("note-modal-content").value;
  if (!title) { alert("请输入笔记标题"); return; }
  try {
    if (noteId) {
      await request(`/notes/${currentUserId}/${noteId}`, { method: "PUT", body: JSON.stringify({ chapter_id: chapterId, title, content }) });
    } else {
      await request(`/notes/${currentUserId}`, { method: "POST", body: JSON.stringify({ chapter_id: chapterId, title, content }) });
    }
    document.getElementById("note-edit-modal").remove();
    loadNotes();
    if (typeof loadDashboard === 'function') loadDashboard();
  } catch (err) {
    renderMessage(err.message, "notes-output");
  }
}

async function deleteNote(noteId) {
  if (!confirm("确定删除这条笔记？")) return;
  try {
    await request(`/notes/${currentUserId}/${noteId}`, { method: "DELETE" });
    loadNotes();
  } catch (err) {
    renderMessage(err.message, "notes-output");
  }
}

// ===== AI 聊天 =====
async function sendAIMessage() {
  const prompt = document.getElementById("ai-prompt").value.trim();
  if (!prompt) return;
  const provider = document.getElementById("ai-provider")?.value || "xunfei";
  const agentRole = document.getElementById("ai-agent-role")?.value || "tutor";
  const chatBox = document.getElementById("chat-box");
  const userMsg = document.createElement("div");
  userMsg.className = "chat-message user";
  userMsg.textContent = prompt;
  chatBox.appendChild(userMsg);
  document.getElementById("ai-prompt").value = "";
  chatBox.scrollTop = chatBox.scrollHeight;
  const assistantMsg = document.createElement("div");
  assistantMsg.className = "chat-message assistant";
  assistantMsg.style.whiteSpace = "pre-wrap";
  assistantMsg.textContent = "";
  chatBox.appendChild(assistantMsg);
  chatBox.scrollTop = chatBox.scrollHeight;
  try {
    const response = await fetch("/api/ai/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": "Bearer " + (typeof getToken === "function" ? getToken() : "") },
      body: JSON.stringify({ user_id: currentUserId, chapter_id: currentChapterId, provider, agent_role: agentRole, prompt }),
    });
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.token) { assistantMsg.textContent += data.token; chatBox.scrollTop = chatBox.scrollHeight; }
          } catch (e) {}
        }
      }
    }
    if (!assistantMsg.textContent) assistantMsg.textContent = "(空响应)";
    loadAIHistory();
  } catch (err) {
    assistantMsg.textContent = "错误: " + err.message;
    assistantMsg.style.color = "#ef4444";
  }
}

async function loadAIHistory() {
  const list = document.getElementById("ai-history-list");
  if (!list) return;
  try {
    const history = await request(`/ai/history/${currentUserId}?chapter_id=${currentChapterId || ""}`);
    list.innerHTML = "";
    if (!history.length) { list.innerHTML = "<p style='color:var(--text-secondary);font-size:12px;'>暂无对话</p>"; return; }
    history.forEach(h => {
      const div = document.createElement("div");
      div.style.cssText = "padding:8px;margin:4px 0;background:var(--info-bg);border-radius:6px;cursor:pointer;";
      div.innerHTML = `
        <div style="font-size:12px;color:var(--text-secondary);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${h.prompt}</div>
        <div style="font-size:11px;color:var(--text-secondary);margin-top:2px;">${new Date(h.created_at).toLocaleTimeString()}</div>
      `;
      div.addEventListener("click", () => {
        document.getElementById("ai-prompt").value = h.prompt;
        document.getElementById("ai-prompt").focus();
      });
      list.appendChild(div);
    });
  } catch (e) {}
}

// ===== 章节选择 =====
async function selectChapter(chapterId, element) {
  currentChapterId = chapterId;
  currentChapterTitle = element ? element.textContent.trim() : "";
  document.querySelectorAll(".chapter-item").forEach(item => item.classList.remove("active"));
  if (element) element.classList.add("active");
  await loadChapterResources(chapterId, element ? element.textContent : "");
  loadNotes();
  loadQuizHistory();
  loadAIHistory();
  loadWrongQuestions();
  try {
    await request(`/progress/${currentUserId}`, { method: "POST", body: JSON.stringify({ chapter_id: chapterId, status: "学习中" }) });
  } catch(e) {}
}

// ===== AI 浮窗 =====
// toggleAIFloat / sendAIFloatMessage 已在 app.js 中统一定义（真实调用 /api/ai/chat/stream），
// 此处不再重复定义，避免“同名函数后加载覆盖”导致的实现不一致。

// ===== AI 提示（修复：改用 data-hint-qid 属性查找按钮）=====
async function aiHint(questionId) {
  const btn = document.querySelector('button[data-hint-qid="' + questionId + '"]');
  if (!btn) return;
  const hintDiv = document.createElement('div');
  hintDiv.style.cssText = 'padding:10px;margin-top:6px;background:#f5f0e8;border-radius:8px;font-size:13px;color:#888;border-left:3px solid #e8a838';
  hintDiv.textContent = 'AI 思考中...';
  btn.parentNode.appendChild(hintDiv);
  try {
    var r = await request('/ai/chat', {
      method: 'POST',
      body: JSON.stringify({
        user_id: currentUserId, chapter_id: currentChapterId,
        provider: 'deepseek', agent_role: 'tutor',
        prompt: '请针对这道题目给一个学习提示，不要直接给答案。题目ID:' + questionId + '。请用"试试看...","注意..."这样的引导方式，帮助学生自己思考。'
      })
    });
    hintDiv.textContent = '💡 ' + r.answer;
    hintDiv.style.color = '#333';
  } catch(e) {
    hintDiv.textContent = '提示获取失败';
  }
}

// ===== 错题回顾 =====
async function loadWrongQuestions() {
  var container = document.getElementById("wrong-questions-list");
  if (!container || !currentChapterId) return;
  try {
    var records = await request("/quiz/history/" + currentUserId);
    var chapterRecords = records.filter(function(r) { return r.chapter_id === currentChapterId; });
    var allWrong = [];
    chapterRecords.forEach(function(r) {
      try { var wrongs = JSON.parse(r.wrong_items || "[]"); wrongs.forEach(function(w) { w.quiz_date = r.created_at; allWrong.push(w); }); } catch(e) {}
    });
    if (allWrong.length === 0) {
      container.innerHTML = "<p style='color:var(--text-secondary);font-size:13px'>暂无错题，继续保持！</p>"; return;
    }
    var seen = {}, uniqueWrong = [];
    for (var i = allWrong.length-1; i >= 0; i--) {
      if (!seen[allWrong[i].question_id]) { seen[allWrong[i].question_id] = true; uniqueWrong.push(allWrong[i]); }
    }
    uniqueWrong.reverse();
    container.innerHTML = "<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px'><h4 style='margin:0'>❌ 错题回顾 (" + uniqueWrong.length + ")</h4><div style='display:flex;gap:8px'><button class='btn' id='btn-retry-selected' style='padding:4px 12px;font-size:12px'>重练选中</button><button class='btn' id='btn-retry-all' style='padding:4px 12px;font-size:12px;background:#e8a838'>全部重练</button></div></div>";
    document.getElementById('btn-retry-selected').addEventListener('click', retrySelectedWrong);
    document.getElementById('btn-retry-all').addEventListener('click', retryWrongQuestions);
    uniqueWrong.forEach(function(w) {
      var div = document.createElement("div");
      div.style.cssText = "padding:14px;margin:8px 0;background:var(--bg-primary);border-radius:10px;border:1px solid var(--border-color);border-left:4px solid #ef4444";
      div.innerHTML =
        "<div style='display:flex;align-items:start;gap:10px'>" +
          "<input type='checkbox' class='wrong-check' value='" + w.question_id + "' style='width:auto;margin-top:3px' />" +
          "<div style='flex:1'>" +
            "<div class='quiz-question' style='margin-bottom:8px'>" + (w.content || "题目") + "</div>" +
            "<div style='font-size:13px;margin-bottom:4px'><span style='color:#ef4444'>❌ 你的答案：<s>" + (w.your_answer || '未答') + "</s></span></div>" +
            "<div style='font-size:13px;margin-bottom:8px'><span style='color:var(--button-primary)'>✅ 正确答案：" + (w.correct_answer || '') + "</span></div>" +
            "<button class='btn btn-ai-explain' data-qid='" + w.question_id + "' style='padding:2px 10px;font-size:11px;background:#f0f0f0;color:#666;margin-right:6px'>📖 AI解析</button>" +
            "<button class='btn btn-ask-ai' data-qid='" + w.question_id + "' style='padding:2px 10px;font-size:11px;background:#f0f0f0;color:#666'>🤖 问AI</button>" +
            "<div id='ai-explain-" + w.question_id + "' style='display:none;margin-top:8px;padding:10px;background:var(--info-bg);border-radius:8px;font-size:13px;line-height:1.6'></div>" +
          "</div>" +
        "</div>";
      container.appendChild(div);
    });
    container.querySelectorAll('.btn-ai-explain').forEach(btn => {
      btn.addEventListener('click', function() { aiExplainWrong(parseInt(this.dataset.qid)); });
    });
    container.querySelectorAll('.btn-ask-ai').forEach(btn => {
      btn.addEventListener('click', function() { askAiAboutWrong(parseInt(this.dataset.qid)); });
    });
    if (window.renderMathInElement) {
      try { renderMathInElement(container, {delimiters:[{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false}]}); } catch(e) {}
    }
  } catch(e) {}
}

function retrySelectedWrong(){
  var ids = Array.from(document.querySelectorAll('.wrong-check:checked')).map(cb => parseInt(cb.value));
  if (ids.length === 0) return;
  request('/quiz/generate',{method:'POST',body:JSON.stringify({chapter_id:currentChapterId,question_ids:ids,count:ids.length,difficulty:'',question_types:[]})}).then(function(r){
    if(!r.questions||r.questions.length===0)return;
    currentQuizQuestions=r.questions;
    document.getElementById('quiz-setup').style.display='none';
    var qc=document.getElementById('quiz-content');qc.style.display='block';qc.style.maxHeight='none';qc.style.overflowY='visible';
    var output=document.getElementById('quiz-output');
    output.innerHTML='<p style="color:var(--info-text);margin-bottom:12px">重练 '+r.questions.length+' 道错题</p>';
    renderQuizQuestions(r.questions,output);
  });
}

async function aiExplainWrong(qid){
  var div = document.getElementById('ai-explain-'+qid);
  div.style.display = 'block';
  div.textContent = 'AI 分析中...';
  try {
    var r = await request('/ai/chat',{method:'POST',body:JSON.stringify({user_id:currentUserId,chapter_id:currentChapterId,provider:'deepseek',agent_role:'tutor',
      prompt:'请分析这道错题，给出详细解题步骤。题目ID:'+qid+'。请分步骤讲解：第一步该怎么做，第二步怎么做，最后总结考点。'})});
    div.innerHTML = '<strong>📌 AI 诊断：</strong>'+r.answer;
    if (window.renderMathInElement) try { renderMathInElement(div,{delimiters:[{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false}]}); } catch(e){}
  } catch(e) { div.textContent = '获取失败'; }
}

function askAiAboutWrong(qid){
  var floatEl = document.getElementById('ai-float');
  if (!floatEl || floatEl.style.display === 'none') toggleAIFloat();
  document.getElementById('ai-float-input').value = '这道题我做错了，能给我讲讲正确的做法吗？题目ID:'+qid;
  sendAIFloatMessage();
}

async function retryWrongQuestions() {
  var records = await request('/quiz/history/'+currentUserId);
  var chapterRecords = records.filter(r => r.chapter_id===currentChapterId);
  var wrongIds = [];
  chapterRecords.forEach(r => {
    try{ JSON.parse(r.wrong_items||'[]').forEach(w=>{ if(wrongIds.indexOf(w.question_id)===-1) wrongIds.push(w.question_id); }); }catch(e){}
  });
  if (wrongIds.length === 0) { renderMessage("暂无错题可练", "quiz-message"); return; }
  const result = await request("/quiz/generate", {
    method: "POST",
    body: JSON.stringify({ chapter_id: currentChapterId, question_ids: wrongIds, count: wrongIds.length, difficulty: "", question_types: [] }),
  });
  if (!result.questions || result.questions.length === 0) { renderMessage("错题加载失败", "quiz-message"); return; }
  currentQuizQuestions = result.questions;
  document.getElementById("quiz-setup").style.display = "none";
  var qc = document.getElementById("quiz-content"); qc.style.display = "block"; qc.style.maxHeight = "none"; qc.style.overflowY = "visible";
  var output = document.getElementById("quiz-output");
  output.innerHTML = "<p style='color:var(--info-text);margin-bottom:12px;'>重练 " + result.questions.length + " 道错题</p>";
  renderQuizQuestions(result.questions, output);
}

function renderQuizQuestions(questions, output) {
  for (var i = 0; i < questions.length; i++) {
    var q = questions[i];
    var qDiv = document.createElement("div");
    qDiv.className = "quiz-item";
    var optionsHtml = "";
    if (q.options) {
      try {
        var opts = JSON.parse(q.options);
        var optLetters = ["A","B","C","D","E","F"];
        for (var j = 0; j < opts.length; j++) {
          optionsHtml += '<div class="quiz-option"><input type="radio" name="q-' + q.id + '" value="' + optLetters[j] + '" id="q' + q.id + '-opt' + j + '" /><label for="q' + q.id + '-opt' + j + '" style="cursor:pointer;">' + opts[j] + '</label></div>';
        }
      } catch (e) {}
    }
    var inputHtml = q.question_type !== "选择题" ? '<input type="text" id="answer-' + q.id + '" placeholder="请输入答案" style="width:100%;" />' : "";
    // 提示按钮用 data-hint-qid，供 aiHint 函数通过属性查找
    qDiv.innerHTML = '<div class="quiz-question"><span style="color:var(--button-primary);">[' + q.difficulty + ']</span> <span style="color:var(--text-secondary);">' + q.question_type + '</span><br/>' + (i+1) + '. ' + q.content + '</div>' + optionsHtml + inputHtml + '<button class="btn" data-hint-qid="' + q.id + '" style="padding:2px 10px;font-size:11px;background:#f0f0f0;color:#666;margin-top:4px">💡 提示</button>';
    output.appendChild(qDiv);
  }
  // 统一绑定提示按钮事件
  output.querySelectorAll('button[data-hint-qid]').forEach(btn => {
    btn.addEventListener('click', function(e) {
      e.stopPropagation();
      aiHint(parseInt(this.dataset.hintQid));
    });
  });
  if (window.renderMathInElement) {
    try { renderMathInElement(output, {delimiters:[{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false}]}); } catch(e){}
  }
  var submitBtn = document.createElement("button");
  submitBtn.className = "btn";
  submitBtn.textContent = "提交答卷";
  submitBtn.style.marginTop = "16px";
  submitBtn.onclick = submitQuizAnswers;
  output.appendChild(submitBtn);
}

// ===== 思维导图 =====
var MINDMAP_IMAGES = { 1: 'images/0538daf251c3759f61d31a763f37b64e.jpg' };
var MINDMAP_NAMES = { 1: '高等数学', 2: '线性代数', 3: '概率论与数理统计' };

function loadMindMap(subjectId){
  var panel = document.getElementById('mindmap-content');
  if(!panel)return;
  var img = MINDMAP_IMAGES[subjectId];
  var name = MINDMAP_NAMES[subjectId] || '思维导图';
  if(img){
    var imgEl = document.createElement('img');
    imgEl.src = img; imgEl.alt = name + '思维导图';
    imgEl.style.cssText = 'max-width:100%;border-radius:8px;box-shadow:0 2px 12px rgba(0,0,0,.08);cursor:zoom-in';
    imgEl.onerror = function(){ this.parentElement.innerHTML = '<p class="muted" style="text-align:center;padding:40px">图片未找到</p>'; };
    imgEl.addEventListener('click', function() {
      var ov = document.createElement('div');
      ov.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.85);z-index:9999;display:flex;align-items:center;justify-content:center;cursor:zoom-out';
      var bigImg = document.createElement('img');
      bigImg.src = img; bigImg.style.cssText = 'max-width:95vw;max-height:95vh;border-radius:4px';
      ov.appendChild(bigImg);
      ov.addEventListener('click', function(){ ov.remove(); });
      document.body.appendChild(ov);
    });
    panel.innerHTML = '<h3 style="color:#e8a838;margin:0 0 16px">🧠 ' + name + ' 思维导图</h3>';
    var wrap = document.createElement('div'); wrap.style.textAlign = 'center';
    wrap.appendChild(imgEl); panel.appendChild(wrap);
  } else {
    panel.innerHTML = '<div style="text-align:center;padding:40px"><p class="muted" style="font-size:16px">该课程暂无思维导图</p></div>';
  }
}