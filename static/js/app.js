const API_BASE = "/api";

// ===== 用户会话管理 =====
function getCurrentUser() {
  try {
    const data = localStorage.getItem("learnai_user");
    return data ? JSON.parse(data) : null;
  } catch {
    return null;
  }
}

function setCurrentUser(user) {
  localStorage.setItem("learnai_user", JSON.stringify(user));
  refreshCurrentUser();
}

function clearCurrentUser() {
  localStorage.removeItem("learnai_user");
}

let currentUser = getCurrentUser();
let currentUserId = currentUser?.id || 1;
let currentUsername = currentUser?.username || "学生";
function refreshCurrentUser(){
  var u = getCurrentUser();
  if(u&&u.id){currentUser=u;currentUserId=u.id;currentUsername=u.username||"学生"}
}

// ===== 导航栏生成 =====
function renderNavbar() {
  // 如果已有 navbar 则跳过
  if (document.querySelector(".top-nav")) return;

  const nav = document.createElement("nav");
  nav.className = "top-nav";

  var u = getCurrentUser();
  var displayName = (u&&u.name) || (u&&u.username) || '学生';
  var initial = displayName.charAt(0).toUpperCase();

  const isDark = document.documentElement.classList.contains("dark-mode");

  nav.innerHTML = `
    <div class="nav-left">
      <a class="nav-logo" href="index.html">
        <span>📚</span> LearnAI
      </a>
    </div>
    <div class="nav-right">
      <button class="nav-theme-btn" id="nav-theme-btn" title="切换主题">${isDark ? "☀️" : "🌙"}</button>
      <div class="nav-avatar-wrapper">
        <div class="nav-avatar" id="nav-avatar" title="${displayName}">${initial}</div>
        <div class="nav-user-dropdown" id="nav-dropdown">
          <div class="nav-dropdown-userinfo">
            <div class="nav-dropdown-name">${displayName}</div>
            <div class="nav-dropdown-email">LearnAI 用户</div>
          </div>
          <a class="nav-dropdown-item" href="profile.html">👤 个人主页</a>
          <div class="nav-dropdown-divider"></div>
          <div class="nav-dropdown-item" id="nav-logout">🚪 退出登录</div>
        </div>
      </div>
    </div>
  `;

  document.body.prepend(nav);
  document.body.classList.add("has-nav");

  // 头像点击 -> 下拉菜单
  document.getElementById("nav-avatar").addEventListener("click", (e) => {
    e.stopPropagation();
    document.getElementById("nav-dropdown").classList.toggle("show");
  });

  // 点击其他地方关闭
  document.addEventListener("click", () => {
    document.getElementById("nav-dropdown").classList.remove("show");
  });

  // 主题切换
  document.getElementById("nav-theme-btn").addEventListener("click", (e) => {
    e.stopPropagation();
    toggleTheme();
  });

  // 退出登录
  document.getElementById("nav-logout").addEventListener("click", () => {
    clearCurrentUser();
    localStorage.removeItem("theme");
    window.location.href = "login.html";
  });
}

// Prefilled subsections mapping: chapterId -> [{id, title, content}, ...]
const subsectionMap = {};

function generateSubsectionsForChapter(chapter) {
  const baseTitle = chapter.title || "章节";
  const items = [];
  for (let i = 1; i <= 3; i++) {
    const sid = `${chapter.id}-${i}`;
    items.push({
      id: sid,
      title: `${chapter.order}.${i} ${baseTitle} 小节 ${i}`,
      content: `本小节为 ${baseTitle} 的第 ${i} 小节，包含关键概念、示例题与解答要点。\n\n学习要点：1) 理解定义；2) 掌握证明思路；3) 练习典型例题。\n\n示例题：请计算...（示例解析略）。`
    });
  }
  return items;
}

function initTheme() {
  const savedTheme = localStorage.getItem("theme");
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const theme = savedTheme || (prefersDark ? "dark" : "light");

  if (theme === "dark") {
    document.documentElement.classList.add("dark-mode");
  } else {
    document.documentElement.classList.remove("dark-mode");
  }
  updateThemeButtons();
}

function toggleTheme() {
  const isDark = document.documentElement.classList.toggle("dark-mode");
  localStorage.setItem("theme", isDark ? "dark" : "light");
  updateThemeButtons();
}

function updateThemeButtons() {
  const isDark = document.documentElement.classList.contains("dark-mode");
  const emoji = isDark ? "☀️" : "🌙";
  const btns = document.querySelectorAll("#theme-toggle, #nav-theme-btn");
  btns.forEach(btn => { if (btn) btn.textContent = emoji; });
}
window.addEventListener("DOMContentLoaded", () => {
  refreshCurrentUser();
  initTheme();
  const noNavPages = ["login.html", "onboarding.html"];
  const currentPage = window.location.pathname.split("/").pop() || "index.html";
  
  // 如果不需要登录的页面，跳过
  if (noNavPages.includes(currentPage)) {
    return;
  }
  
  const user = getCurrentUser();
  if (!user || !user.id) {
    window.location.href = "login.html";
    return;
  }
  
  // 渲染导航栏
  renderNavbar();
});

;

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || response.statusText);
  }
  return response.json();
}

function queryParam(name) {
  const params = new URLSearchParams(window.location.search);
  return params.get(name);
}

function renderMessage(message, containerId) {
  const container = document.getElementById(containerId);
  if (container) {
    container.textContent = message;
    container.classList.remove("hidden");
    container.style.display = "block";
    setTimeout(() => {
      container.style.display = "none";
      container.classList.add("hidden");
    }, 4500);
  }
}

async function loadSubjects() {
  const list = await request("/subjects");
  const wrapper = document.getElementById("subject-list");
  if (!wrapper) return;
  wrapper.innerHTML = "";
  list.forEach(subject => {
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <h3>${subject.name}</h3>
      <p>${subject.description}</p>
      <p class="badge">${subject.category}</p>
      <div style="margin-top: 16px; text-align:right;">
        <a href="subject.html?id=${subject.id}"><button>进入课程</button></a>
      </div>
    `;
    wrapper.appendChild(card);
  });
}

async function loadChapters(subjectId) {
  var chapters = await request('/subjects/' + subjectId + '/chapters');
  var list = document.getElementById('chapter-list');
  list.innerHTML = '';
  for (var i = 0; i < chapters.length; i++) {
    var ch = chapters[i];
    var item = document.createElement('div');
    item.className = 'chapter-item';
    item.style.cssText = 'display:flex;justify-content:space-between;align-items:center';
    item.innerHTML = '<span>' + ch.order + '. ' + ch.title + '</span><span style="font-size:10px;color:#aaa">▼</span>';
    item.onclick = function(chapter, el) {
      return function() {
        selectChapter(chapter.id, el);
        var subs = el.parentNode.querySelectorAll('.sub-item');
        var arrow = el.querySelector('span:last-child');
        if (subs.length > 0) {
          var shown = subs[0].style.display !== 'none';
          subs.forEach(function(s) { s.style.display = shown ? 'none' : 'block'; });
          arrow.textContent = shown ? '▶' : '▼';
        }
      };
    }(ch, item);
    list.appendChild(item);

    // 加载小节并渲染为子项
    try {
      var subs = await request('/chapters/' + ch.id + '/subsections').catch(function() { return []; });
      if (!subs || subs.length === 0) subs = [];
      subsectionMap[ch.id] = subs;
      for (var j = 0; j < subs.length; j++) {
        (function(sub, chId, parentEl) {
          var subItem = document.createElement('div');
          subItem.className = 'sub-item';
          subItem.style.cssText = 'padding:6px 12px 6px 28px;margin:2px 8px;border-radius:6px;cursor:pointer;font-size:12px;color:var(--text-secondary);display:none';
          subItem.textContent = '📄 ' + sub.title;
          subItem.onclick = function(e) {
            e.stopPropagation();
            // 高亮小节和父章节
            list.querySelectorAll('.sub-item,.chapter-item').forEach(function(el){el.classList.remove('active');el.style.background='';el.style.color=''});
            subItem.classList.add('active');
            subItem.style.background = 'var(--button-primary)';
            subItem.style.color = 'white';
            parentEl.classList.add('active');
            parentEl.style.background = 'var(--button-primary)';
            parentEl.style.color = 'white';
            // 存储上次打开的小节
            try { localStorage.setItem('learnai_last_sub', JSON.stringify({chapterId: chId, subId: sub.id})); } catch(e) {}
            // 显示小节内容
            var container = document.getElementById('resource-output');
            if (container) {
              container.innerHTML = '';
              var wrapper = document.createElement('div');
              wrapper.className = 'resource-item';
              wrapper.innerHTML = '<div class="resource-title">' + sub.title + '</div><div class="resource-desc" style="white-space:normal">';
              var desc = wrapper.querySelector('.resource-desc');
              var hasContent = sub.content && sub.content.length > 50 && sub.content.indexOf('示例解析略') === -1;
              if (hasContent && window.marked) desc.innerHTML = marked.parse(sub.content);
              else if (hasContent) desc.textContent = sub.content;
              else desc.innerHTML = '<p style="color:var(--text-secondary)">暂无详细内容</p>';
              container.appendChild(wrapper);
              if (window.renderMathInElement) try { renderMathInElement(desc, {delimiters: [{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false}]}); } catch(e) {}

              // 摘录到笔记按钮
              var clipBtn = document.createElement('button');
              clipBtn.style.cssText = 'margin-top:12px;margin-right:8px;background:#5a5f73;color:#fff;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px';
              clipBtn.textContent = '📋 摘录到笔记';
              clipBtn.onclick = function(ev){ ev.stopPropagation();
                var snippet = (sub.content||'').substring(0,500);
                var cid = (typeof currentChapterId!=='undefined'?currentChapterId:null) || chId || 1;
                request('/notes/'+currentUserId,{method:'POST',body:JSON.stringify({chapter_id:cid,title:'摘录: '+sub.title,content:'> 来源：'+sub.title+'\n\n'+snippet})}).then(function(){clipBtn.textContent='已摘录';clipBtn.disabled=true}).catch(function(){clipBtn.textContent='失败'});
              };
              wrapper.appendChild(clipBtn);

              // 标记已学按钮
              var spm = {};
              try { spm = JSON.parse(localStorage.getItem('learnai_sub_progress') || '{}'); } catch(e) {}
              var markBtn = document.createElement('button');
              markBtn.style.cssText = 'margin-top:12px;background:'+(spm[sub.id]?'#ccc':'var(--button-primary)')+';color:#fff;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px';
              markBtn.textContent = spm[sub.id] ? '✅ 已学' : '📖 标记已学';
              if(spm[sub.id]) markBtn.disabled = true;
              markBtn.onclick = function(ev){ ev.stopPropagation();
                var mspm = {};
                try { mspm = JSON.parse(localStorage.getItem('learnai_sub_progress') || '{}'); } catch(e) {}
                mspm[sub.id] = true;
                localStorage.setItem('learnai_sub_progress', JSON.stringify(mspm));
                markBtn.textContent = '✅ 已学';
                markBtn.disabled = true;
                markBtn.style.background = '#ccc';
                request('/progress/'+currentUserId,{method:'POST',body:JSON.stringify({chapter_id:chId,status:'学习中'})}).catch(function(){});
              };
              wrapper.appendChild(markBtn);
            }
          };
          list.appendChild(subItem);
        })(subs[j], ch.id, item);
      }
    } catch(e) {
      subsectionMap[ch.id] = [];
    }
  }
  if (chapters.length > 0) {
    // 展开第一章
    var firstCh = list.querySelector('.chapter-item');
    if (firstCh) firstCh.click();
  }
}

async function loadChapterResources(chapterId, chapterTitle) {
  var resources = await request('/chapters/'+chapterId+'/resources').catch(function(){return[]});
  // 确保小节数据已加载
  if (!subsectionMap[chapterId]) {
    try {
      var subs = await request('/chapters/'+chapterId+'/subsections').catch(function(){return[]});
      subsectionMap[chapterId] = subs;
    } catch(e) {
      subsectionMap[chapterId] = generateSubsectionsForChapter({id:chapterId,title:chapterTitle,order:0});
    }
  }
  // 小节 DOM 已由 loadChapters 渲染（含摘录+标记已学按钮），这里只负责自动还原
  var firstSub = document.querySelector('#chapter-list .sub-item');
  var restored = false;
  try {
    var last = localStorage.getItem('learnai_last_sub');
    if (last) {
      var info = JSON.parse(last);
      if (info.chapterId == chapterId) {
        var allSubs = document.querySelectorAll('#chapter-list .sub-item');
        allSubs.forEach(function(si){
          if (!restored && si.style.display !== 'none') { si.click(); restored = true; }
        });
      }
    }
  } catch(e) {}
  if (!restored && firstSub) {
    // 点击第一个可见小节
    var visSubs = document.querySelectorAll('#chapter-list .sub-item');
    for (var i=0;i<visSubs.length;i++) {
      if (visSubs[i].style.display !== 'none') { visSubs[i].click(); break; }
    }
  }
  // 资源生成面板
  var genPanel = document.getElementById('resource-generate-panel');
  var container = document.getElementById('resource-output');
  if (genPanel) genPanel.style.display = resources.length===0?'block':'none';
  if (resources.length===0 && container && !firstSub) {
    container.innerHTML = '<p style="color:var(--text-secondary)">该章节暂无小节内容，请在首页公共资源库浏览学习资料。</p>';
  }
}

// ===== 登录/注册 =====
async function initLoginPage() {
  const loginTab = document.getElementById("tab-login");
  const registerTab = document.getElementById("tab-register");
  const loginForm = document.getElementById("login-form");
  const registerForm = document.getElementById("register-form");

  loginTab.addEventListener("click", () => {
    loginTab.classList.add("active");
    registerTab.classList.remove("active");
    loginForm.classList.remove("hidden");
    registerForm.classList.add("hidden");
  });
  registerTab.addEventListener("click", () => {
    registerTab.classList.add("active");
    loginTab.classList.remove("active");
    loginForm.classList.add("hidden");
    registerForm.classList.remove("hidden");
  });

  loginForm.addEventListener("submit", async event => {
    event.preventDefault();
    const username = document.getElementById("login-username").value.trim();
    const password = document.getElementById("login-password").value.trim();
    if (!username || password.length < 6) {
      renderMessage("请输入正确用户名和至少6位密码。", "form-message");
      return;
    }
    try {
      const user = await request("/users/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      setCurrentUser({ id: user.id, username: user.username });
      window.location.href = "index.html";
    } catch (err) {
      renderMessage(err.message, "form-message");
    }
  });

  registerForm.addEventListener("submit", async event => {
    event.preventDefault();
    const username = document.getElementById("register-username").value.trim();
    const password = document.getElementById("register-password").value.trim();
    if (!username || password.length < 6) {
      renderMessage("请输入正确用户名和至少6位密码。", "form-message");
      return;
    }
    try {
      const user = await request("/users/register", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      setCurrentUser({ id: user.id, username: user.username });
      window.location.href = "onboarding.html";
    } catch (err) {
      renderMessage(err.message, "form-message");
    }
  });
}

// ===== 新手引导 =====
async function initOnboardingPage() {
  // 确保从 localStorage 拿到真正的用户 ID
  const user = getCurrentUser();
  if (!user || !user.id) {
    window.location.href = "login.html";
    return;
  }
  const userId = user.id;

  const form = document.getElementById("onboarding-form");
  form.addEventListener("submit", async event => {
    event.preventDefault();
    const data = {
      name: document.getElementById("name").value,
      grade: document.getElementById("grade").value,
      major: document.getElementById("major").value,
      interests: Array.from(document.querySelectorAll("input[name='interests']:checked")).map(i => i.value).join(","),
      goal: document.getElementById("goal").value,
    };
    try {
      await request(`/profiles/${userId}`, {
        method: "POST",
        body: JSON.stringify(data),
      });
      // 更新 localStorage 中的用户名（如果用户填了名字就用名字）
      if (data.name) {
        user.name = data.name;
        setCurrentUser(user);
      }
      window.location.href = "index.html";
    } catch (err) {
      renderMessage(err.message, "form-message");
    }
  });
}

// ===== 学科详情页初始化 =====
let targetChapterId = null;  // URL 参数指定的章节

async function initSubjectPage() {
  const subjectId = queryParam("id");
  targetChapterId = queryParam("chapter");
  if (!subjectId) {
    renderMessage("缺少学科参数。", "resource-message");
    return;
  }
  try {
    const subject = await request(`/subjects/${subjectId}`);
    if (subject) {
      document.getElementById("subject-name").textContent = subject.name;
      const metaElem = document.getElementById("subject-meta");
      if (metaElem) {
        metaElem.textContent = `${subject.category} · 8个章节 · ${subject.description || ""}`;
      }
      await loadChapters(subjectId);
      // 如果 URL 指定了章节，自动选中
      if (targetChapterId) {
        setTimeout(() => {
          const items = document.querySelectorAll(".chapter-item");
          items.forEach(item => {
            // 匹配 onclick 中的章节 ID
            const oc = item.getAttribute("onclick") || "";
            if (oc.includes(String(targetChapterId))) {
              item.click();
            }
          });
        }, 300);
      }
    }
  } catch (err) {
    console.error("加载学科失败:", err);
    renderMessage("加载学科数据失败", "resource-message");
  }
}
// ===== AI 浮窗控制 =====
function toggleAIFloat() {
  var el = document.getElementById('ai-float');
  if (!el) return;
  if (el.style.display === 'none' || el.style.display === '') {
    el.style.display = 'flex';
  } else {
    el.style.display = 'none';
  }
}

function sendAIFloatMessage() {
  var input = document.getElementById('ai-float-input');
  if (!input || !input.value.trim()) return;
  var msg = input.value.trim();
  input.value = '';
  var chat = document.getElementById('ai-float-chat');
  if (chat) {
    chat.innerHTML += '<div class="chat-message user" style="margin-bottom:12px;padding:10px 14px;border-radius:8px;max-width:85%;word-wrap:break-word;font-size:14px;line-height:1.6;background:var(--button-primary);color:white;align-self:flex-end;">' + msg + '</div>';
    chat.scrollTop = chat.scrollHeight;
  }
  // 模拟回复
  setTimeout(function() {
    if (chat) {
      chat.innerHTML += '<div class="chat-message assistant" style="margin-bottom:12px;padding:10px 14px;border-radius:8px;max-width:85%;word-wrap:break-word;font-size:14px;line-height:1.6;background:var(--bg-primary);border:1px solid var(--border-color);color:var(--text-primary);align-self:flex-start;">收到你的问题："' + msg + '"，我还在学习中，请稍后再试。</div>';
      chat.scrollTop = chat.scrollHeight;
    }
  }, 500);
}

// ===== 笔记本浮窗控制 =====
function toggleNotebook() {
  var el = document.getElementById('notebook-float');
  if (!el) return;
  if (el.style.display === 'none' || el.style.display === '') {
    el.style.display = 'flex';
    loadNotebookFloat();
  } else {
    el.style.display = 'none';
  }
}

function loadNotebookFloat() {
  var container = document.getElementById('notebook-float-body');
  if (!container) return;
  // 从 localStorage 加载笔记
  var notes = JSON.parse(localStorage.getItem('quick_notes') || '[]');
  if (notes.length === 0) {
    container.innerHTML = '<div style="color:var(--text-secondary); font-size:13px; text-align:center; padding:20px;">暂无笔记</div>';
    return;
  }
  container.innerHTML = notes.slice(-5).reverse().map(function(note, index) {
    return '<div style="padding:10px 12px; margin:6px 0; background:var(--info-bg); border-radius:8px; border-left:3px solid var(--button-primary); cursor:pointer; font-size:13px;">' +
      '<div style="color:var(--text-primary);">' + note.content + '</div>' +
      '<div style="font-size:11px; color:var(--text-secondary); margin-top:4px;">' + new Date(note.time).toLocaleString() + '</div>' +
      '</div>';
  }).join('');
}

function searchNotebook() {
  // 简单搜索功能
  var kw = document.getElementById('notebook-search').value.toLowerCase();
  var container = document.getElementById('notebook-float-body');
  if (!container) return;
  var notes = JSON.parse(localStorage.getItem('quick_notes') || '[]');
  var filtered = notes.filter(function(n) {
    return n.content.toLowerCase().indexOf(kw) >= 0;
  });
  if (filtered.length === 0) {
    container.innerHTML = '<div style="color:var(--text-secondary); font-size:13px; text-align:center; padding:20px;">没有找到匹配的笔记</div>';
    return;
  }
  container.innerHTML = filtered.slice(-5).reverse().map(function(note) {
    return '<div style="padding:10px 12px; margin:6px 0; background:var(--info-bg); border-radius:8px; border-left:3px solid var(--button-primary); font-size:13px;">' +
      '<div style="color:var(--text-primary);">' + note.content + '</div>' +
      '<div style="font-size:11px; color:var(--text-secondary); margin-top:4px;">' + new Date(note.time).toLocaleString() + '</div>' +
      '</div>';
  }).join('');
}

function createNoteFromFloat() {
  var content = prompt('请输入笔记内容：');
  if (!content || !content.trim()) return;
  var notes = JSON.parse(localStorage.getItem('quick_notes') || '[]');
  notes.push({content: content.trim(), time: Date.now()});
  localStorage.setItem('quick_notes', JSON.stringify(notes));
  loadNotebookFloat();
  // 同时保存到服务器
  try {
    request('/notes/' + currentUserId, {
      method: 'POST',
      body: JSON.stringify({
        chapter_id: 1,
        title: '快速笔记',
        content: content.trim()
      })
    }).catch(function(){});
  } catch(e) {}
}