let currentResult = null;
let currentRunId = null;
let dataCenterMaterials = [];

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

function show(selector) { $(selector).classList.remove('hidden'); }
function hide(selector) { $(selector).classList.add('hidden'); }

function siteBasePath() {
  const marker = '/modules/01-enterprise-diagnosis/';
  const markerIndex = location.pathname.indexOf(marker);
  if (markerIndex >= 0) {
    return location.pathname.slice(0, markerIndex + 1);
  }
  if (location.pathname.endsWith('/')) {
    return location.pathname;
  }
  return location.pathname.replace(/[^/]*$/, '');
}

function resolveAppLink(path) {
  const value = String(path || '').trim();
  if (!value) return '';
  if (/^[a-z][a-z0-9+.-]*:/i.test(value) || value.startsWith('#')) return value;
  const clean = value.replace(/^\/+/, '');
  if (location.protocol === 'file:') {
    return `http://127.0.0.1:8770/${clean}`;
  }
  if (['127.0.0.1', 'localhost', '::1'].includes(location.hostname)) {
    return `/${clean}`;
  }
  return `${siteBasePath()}${clean}`;
}

function resolveHomeLink(hash = '') {
  if (location.protocol === 'file:') {
    return `http://127.0.0.1:8770/${hash}`;
  }
  if (['127.0.0.1', 'localhost', '::1'].includes(location.hostname)) {
    return `/${hash}`;
  }
  return `${siteBasePath()}${hash}`;
}

function normalizeStaticLinks() {
  $$('[data-home-link]').forEach((link) => {
    link.href = resolveHomeLink(link.dataset.homeLink || '');
  });
}

const routeSections = ['upload', 'summary', 'report', 'flows', 'sections', 'departments', 'missing', 'aiAssist', 'plan'];

function routeForHash() {
  const hash = location.hash.replace('#', '') || 'upload';
  if (hash === 'materialCenter') return 'upload';
  if (routeSections.includes(hash)) return hash;
  return 'upload';
}

function applyWorkspaceRoute() {
  let active = routeForHash();
  if (!currentResult && active !== 'upload') {
    active = 'upload';
  }
  routeSections.forEach((id) => {
    const node = $(`#${id}`);
    if (!node) return;
    const shouldShow = id === active || (currentResult && active !== 'upload' && id === 'summary');
    node.classList.toggle('route-hidden', !shouldShow);
  });
  $$('.workspace-nav a[href^="#"]').forEach((link) => {
    const rawHash = location.hash.replace('#', '') || 'upload';
    const target = link.getAttribute('href').replace('#', '');
    const isActive = target === rawHash || (rawHash !== 'materialCenter' && target === active);
    link.classList.toggle('active', isActive);
  });
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[char]));
}

function renderSystemModuleList() {
  const container = $('#diagnosisSideModuleList');
  if (!container) return;
  const modules = window.APPAREL_MODULES || [];
  container.innerHTML = modules.map((item) => {
    const active = item.id === 'enterprise-diagnosis' ? 'active' : '';
    const disabled = item.link ? '' : 'disabled';
    const content = `<strong>${escapeHtml(item.title)}</strong>`;
    if (item.link) {
      return `<a class="${active}" href="${resolveAppLink(item.link)}" data-module-id="${escapeHtml(item.id)}">${content}</a>`;
    }
    return `<button class="${disabled}" type="button" title="模块待开放" data-module-id="${escapeHtml(item.id)}">${content}</button>`;
  }).join('');
}

function renderModuleSwitcher() {
  const switcher = $('#moduleSwitcher');
  if (!switcher) return;
  const modules = window.APPAREL_MODULES || [];
  switcher.innerHTML = modules.map((item) => {
    const selected = item.id === 'enterprise-diagnosis' ? ' selected' : '';
    const disabled = item.link ? '' : ' disabled';
    const value = item.link ? resolveAppLink(item.link) : '';
    return `<option value="${escapeHtml(value)}"${selected}${disabled}>${escapeHtml(item.title)}</option>`;
  }).join('');
  switcher.addEventListener('change', () => {
    if (switcher.value) window.location.href = switcher.value;
  });
}

async function checkHealth() {
  try {
    const response = await fetch('/api/health');
    const data = await response.json();
    $('#healthDot').className = 'dot ok';
    const materialText = data.data_center ? `｜资料中心 ${data.data_center.ready}/${data.data_center.total} 可用` : '';
    $('#healthText').textContent = `${data.knowledge || '知识库已加载'}${materialText}`;
  } catch (error) {
    $('#healthDot').className = 'dot err';
    $('#healthText').textContent = '知识库加载失败';
  }
}

function selectedFilesText(files) {
  if (!files.length) return '尚未选择文件';
  return Array.from(files).map(file => `${file.name} (${Math.ceil(file.size / 1024)} KB)`).join('、');
}

function formatSize(bytes) {
  if (!bytes) return '0 KB';
  if (bytes < 1024 * 1024) return `${Math.ceil(bytes / 1024)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function formatDate(value) {
  if (!value) return '-';
  return String(value).replace('T', ' ').slice(0, 16);
}

function selectedMaterialIds() {
  return $$('#materialList input[type="checkbox"]:checked').map(node => node.value);
}

function renderMaterials() {
  const ready = dataCenterMaterials.filter(item => item.extract_status === 'ready');
  $('#materialSummary').textContent = `共有 ${dataCenterMaterials.length} 份资料，${ready.length} 份可用于诊断。`;
  if (!dataCenterMaterials.length) {
    $('#materialList').innerHTML = '<p class="empty-state">资料中心暂无资料。上传企业资料后，会自动沉淀到这里。</p>';
    return;
  }
  $('#materialList').innerHTML = dataCenterMaterials.map(item => `
    <label class="material-row ${item.extract_status !== 'ready' ? 'disabled' : ''}">
      <input type="checkbox" value="${escapeHtml(item.id)}" ${item.extract_status !== 'ready' ? 'disabled' : ''} />
      <span class="material-main">
        <strong>${escapeHtml(item.filename)}</strong>
        <span>${escapeHtml(item.file_type || '-')}｜${formatSize(item.size)}｜${formatDate(item.uploaded_at)}</span>
        ${item.text_preview ? `<em>${escapeHtml(item.text_preview)}</em>` : ''}
        ${item.extract_error ? `<em class="error-text">${escapeHtml(item.extract_error)}</em>` : ''}
      </span>
      <span class="material-tags">
        ${(item.categories || []).slice(0, 4).map(category => `<b>${escapeHtml(category)}</b>`).join('')}
      </span>
    </label>
  `).join('');
}

async function loadMaterials() {
  try {
    const response = await fetch('/api/materials');
    const data = await response.json();
    if (!data.ok) throw new Error(data.error || '资料中心读取失败');
    dataCenterMaterials = data.materials || [];
    renderMaterials();
  } catch (error) {
    $('#materialSummary').textContent = error.message || '资料中心读取失败';
    $('#materialList').innerHTML = '';
  }
}

function averageScore(result) {
  const sections = result.sections || [];
  if (!sections.length) return 0;
  return Math.round(sections.reduce((sum, item) => sum + Number(item.score || 0), 0) / sections.length);
}

function renderEditableList(containerSelector, values) {
  const container = $(containerSelector);
  container.innerHTML = '';
  (values || []).forEach((value) => {
    const textarea = document.createElement('textarea');
    textarea.rows = 2;
    textarea.value = value;
    container.appendChild(textarea);
  });
}

function readEditableList(containerSelector) {
  return $$(`${containerSelector} textarea`).map(node => node.value.trim()).filter(Boolean);
}

function riskClass(risk) {
  return risk === 'high' ? 'high' : risk === 'medium' ? 'medium' : 'low';
}

function statusClass(status) {
  return status === 'covered' ? 'covered' : 'missing';
}

function renderMainLines(result) {
  const container = $('#mainLineCards');
  container.innerHTML = (result.main_lines || []).map(line => `
    <article class="main-line-card">
      <div class="top">
        <div>
          <h3>${escapeHtml(line.name)}</h3>
          <span class="risk ${riskClass(line.risk)}">${escapeHtml(line.risk_label)}</span>
        </div>
        <div class="score">${line.score ?? '-'}</div>
      </div>
      <p class="question">${escapeHtml(line.question || '')}</p>
      <p>${escapeHtml(line.judgment || line.description || '')}</p>
      <div class="tag-row">
        ${(line.linked_sections || []).slice(0, 8).map(section => `
          <span>${escapeHtml(section.number)}. ${escapeHtml(section.title)}</span>
        `).join('')}
      </div>
      ${line.next_actions?.length ? `
        <ul class="mini-list">${line.next_actions.slice(0, 3).map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul>
      ` : ''}
    </article>
  `).join('');
}

function renderFlows(result) {
  const container = $('#flowCards');
  container.innerHTML = (result.flow_charts || []).map(flow => `
    <article class="flow-card">
      <div class="flow-head">
        <div>
          <h3>${escapeHtml(flow.name)}</h3>
          <span class="risk ${riskClass(flow.risk)}">${escapeHtml(flow.risk_label)}</span>
        </div>
        <div class="score">${flow.score ?? '-'}</div>
      </div>
      <div class="flow-steps">
        ${(flow.steps || []).map(step => `<span>${escapeHtml(step)}</span>`).join('')}
      </div>
      <p><strong>改善重点：</strong>${escapeHtml(flow.improvement_focus || '')}</p>
      ${flow.weak_points?.length ? `
        <div class="weak-points">
          ${flow.weak_points.map(point => `
            <div>
              <strong>${escapeHtml(point.section)}</strong>
              <span>${escapeHtml(point.risk_label)}｜${escapeHtml(point.score)}</span>
              <p>${escapeHtml(point.finding)}</p>
            </div>
          `).join('')}
        </div>
      ` : ''}
    </article>
  `).join('');
}

function renderSections(result) {
  const filter = $('#riskFilter').value;
  const container = $('#sectionCards');
  const sections = (result.sections || []).filter(section => filter === 'all' || section.risk === filter);
  container.innerHTML = sections.map(section => `
    <details class="section-card">
      <summary>
        <div>
          <h3>${section.number}. ${escapeHtml(section.title)}</h3>
          <span class="risk ${riskClass(section.risk)}">${escapeHtml(section.risk_label)}</span>
        </div>
        <div class="score">${section.score}</div>
      </summary>
      <p>${escapeHtml(section.finding)}</p>
      <div class="section-meta">
        <span>负责人：${escapeHtml(section.owner)}</span>
        <span>诊断项覆盖：${Math.round((section.coverage || 0) * 100)}%</span>
        <span>指标覆盖：${Math.round((section.metric_coverage || 0) * 100)}%</span>
      </div>
      ${section.focus ? `<p class="focus-text">${escapeHtml(section.focus)}</p>` : ''}
      ${section.missing_items?.length ? `<ul class="mini-list">${section.missing_items.slice(0, 8).map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul>` : ''}
      <div class="detail-table">
        <table>
          <thead>
            <tr><th>诊断项</th><th>判断问题</th><th>状态</th><th>证据 / 缺失</th><th>建议动作</th></tr>
          </thead>
          <tbody>
            ${(section.items || []).map(item => `
              <tr>
                <td>${escapeHtml(item.name)}</td>
                <td>${escapeHtml(item.question)}</td>
                <td><span class="status ${statusClass(item.status)}">${escapeHtml(item.status_label)}</span></td>
                <td>${item.evidence?.length ? item.evidence.map(escapeHtml).join('<br>') : '未在资料中识别到证据'}</td>
                <td>${escapeHtml(item.improvement_action || '')}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
      ${section.metrics?.length ? `
        <div class="detail-table metric-detail">
          <table>
            <thead><tr><th>关键指标</th><th>意义</th><th>状态</th><th>建议责任人</th></tr></thead>
            <tbody>
              ${section.metrics.map(metric => `
                <tr>
                  <td>${escapeHtml(metric.name)}</td>
                  <td>${escapeHtml(metric.meaning)}</td>
                  <td><span class="status ${statusClass(metric.status)}">${escapeHtml(metric.status_label)}</span></td>
                  <td>${escapeHtml(metric.suggested_owner || section.owner)}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      ` : ''}
    </details>
  `).join('');
}

function renderDepartments(result) {
  const container = $('#departmentCards');
  container.innerHTML = (result.department_issues || []).map(dept => `
    <article class="department-card">
      <div class="top">
        <div>
          <h3>${escapeHtml(dept.department)}</h3>
          <span class="risk ${riskClass(dept.risk)}">${escapeHtml(dept.risk_label)}</span>
        </div>
        <div class="score">${dept.score ?? '-'}</div>
      </div>
      <p class="owner-line">建议责任人：${escapeHtml(dept.owner)}</p>
      <p>${escapeHtml(dept.next_action || '')}</p>
      <div class="tag-row">
        ${(dept.linked_sections || []).slice(0, 6).map(item => `<span>${escapeHtml(item)}</span>`).join('')}
      </div>
      ${dept.issues?.length ? `
        <ul class="mini-list">${dept.issues.slice(0, 4).map(issue => `<li>${escapeHtml(issue.problem)}<br><span>${escapeHtml(issue.action)}</span></li>`).join('')}</ul>
      ` : '<p class="muted">当前资料中未识别到高优先级问题。</p>'}
    </article>
  `).join('');
}

function renderMissingData(result) {
  const rows = result.missing_data || [];
  $('#missingRows').innerHTML = rows.slice(0, 60).map(item => `
    <tr>
      <td>${escapeHtml(item.section)}</td>
      <td>${escapeHtml(item.metric)}</td>
      <td>${escapeHtml(item.meaning)}</td>
      <td>${escapeHtml(item.suggested_owner)}</td>
    </tr>
  `).join('');
}

function renderPlan(result) {
  const container = $('#planList');
  const template = $('#planTemplate');
  container.innerHTML = '';
  (result.ninety_day_plan || []).forEach((item, index) => {
    const node = template.content.cloneNode(true);
    node.querySelector('.priority').textContent = item.priority || index + 1;
    node.querySelectorAll('[data-key]').forEach(input => {
      input.value = item[input.dataset.key] || '';
    });
    node.querySelector('.remove-plan').addEventListener('click', (event) => {
      event.target.closest('.plan-card').remove();
      renumberPlans();
    });
    container.appendChild(node);
  });
}

function renumberPlans() {
  $$('#planList .plan-card').forEach((card, index) => {
    card.querySelector('.priority').textContent = index + 1;
  });
}

function readPlan() {
  return $$('#planList .plan-card').map((card, index) => {
    const item = { priority: index + 1 };
    card.querySelectorAll('[data-key]').forEach(input => {
      item[input.dataset.key] = input.value.trim();
    });
    return item;
  });
}

function renderResult(result) {
  currentResult = result;
  currentRunId = result.run_id;
  $('#avgScore').textContent = averageScore(result);
  $('#highRisk').textContent = (result.sections || []).filter(section => section.risk === 'high').length;
  $('#missingCount').textContent = (result.missing_data || []).length;
  $('#fileCount').textContent = result.source_package?.stats?.file_count || result.uploaded_files?.length || 0;
  $('#mainLineRisk').textContent = (result.main_lines || []).filter(line => line.risk === 'high').length;
  $('#departmentIssueCount').textContent = (result.department_issues || []).reduce((sum, dept) => sum + Number(dept.issue_count || 0), 0);

  $('#companySnapshot').value = result.company_snapshot || '';
  $('#executiveSummary').value = result.executive_summary || '';
  $('#aiStatus').textContent = result.ai_status || '';
  $('#manualPrompt').value = result.manual_ai_prompt || '';
  renderEditableList('#coreFindings', result.core_findings || []);
  renderEditableList('#rootCauses', result.root_causes || []);
  renderMainLines(result);
  renderFlows(result);
  renderSections(result);
  renderDepartments(result);
  renderMissingData(result);
  renderPlan(result);

  $('#docxLink').href = `/api/report/${currentRunId}.docx`;
  $('#pdfLink').href = `/api/report/${currentRunId}.pdf`;
  ['#summary', '#report', '#flows', '#sections', '#departments', '#missing', '#aiAssist', '#plan'].forEach(show);
  applyWorkspaceRoute();
}

function collectResultEdits() {
  if (!currentResult) return null;
  currentResult.company_snapshot = $('#companySnapshot').value.trim();
  currentResult.executive_summary = $('#executiveSummary').value.trim();
  currentResult.core_findings = readEditableList('#coreFindings');
  currentResult.root_causes = readEditableList('#rootCauses');
  currentResult.ninety_day_plan = readPlan();
  return currentResult;
}

function parseJsonFromText(text) {
  const trimmed = text.trim().replace(/^```json\s*/i, '').replace(/^```\s*/i, '').replace(/```$/i, '').trim();
  try {
    return JSON.parse(trimmed);
  } catch (error) {
    const match = trimmed.match(/\{[\s\S]*\}/);
    if (!match) throw error;
    return JSON.parse(match[0]);
  }
}

function mergeByKey(existing, incoming, key) {
  if (!Array.isArray(incoming)) return existing;
  if (!Array.isArray(existing)) return incoming;
  const byKey = new Map(existing.map(item => [item?.[key], item]));
  incoming.forEach(item => {
    const itemKey = item?.[key];
    if (itemKey && byKey.has(itemKey)) {
      Object.assign(byKey.get(itemKey), item);
    } else if (itemKey) {
      byKey.set(itemKey, item);
    }
  });
  return Array.from(byKey.values());
}

function mergeAiResult(aiResult) {
  if (!currentResult) return;
  const directFields = [
    'company_snapshot',
    'executive_summary',
    'core_findings',
    'root_causes',
    'short_term_improvements',
    'medium_term_system_build',
    'long_term_growth_path',
    'missing_data'
  ];
  directFields.forEach(field => {
    if (Object.prototype.hasOwnProperty.call(aiResult, field)) currentResult[field] = aiResult[field];
  });
  currentResult.main_lines = mergeByKey(currentResult.main_lines, aiResult.main_lines, 'id');
  currentResult.flow_charts = mergeByKey(currentResult.flow_charts, aiResult.flow_charts, 'name');
  currentResult.department_issues = mergeByKey(currentResult.department_issues, aiResult.department_issues, 'department');
  if (Array.isArray(aiResult.ninety_day_plan)) {
    currentResult.ninety_day_plan = aiResult.ninety_day_plan.map((item, index) => ({ priority: index + 1, ...item }));
  }
  currentResult.mode = 'manual_chatgpt_enhanced';
  currentResult.ai_status = '已合并 ChatGPT 半自动增强结果。';
  renderResult(currentResult);
}

async function saveCurrentResult(showSuccess = true) {
  const result = collectResultEdits();
  if (!result || !currentRunId) return false;
  const response = await fetch(`/api/result/${currentRunId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ result })
  });
  const data = await response.json();
  if (!data.ok) {
    alert(data.error || '保存失败');
    return false;
  }
  if (showSuccess) alert('已保存当前修改，导出的 Word/PDF 会使用最新内容。');
  return true;
}

async function runAnalyzeRequest(fetchOptions) {
  $('#analyzeBtn').disabled = true;
  $('#analyzeSelectedBtn').disabled = true;
  show('#progress');
  try {
    const response = await fetch('/api/analyze', fetchOptions);
    const data = await response.json();
    if (!data.ok) throw new Error(data.error || '分析失败');
    renderResult(data.result);
    await loadMaterials();
    await checkHealth();
    location.hash = '#report';
    applyWorkspaceRoute();
  } catch (error) {
    alert(error.message);
  } finally {
    $('#analyzeBtn').disabled = false;
    $('#analyzeSelectedBtn').disabled = false;
    hide('#progress');
  }
}

async function loadResultFromQuery() {
  const params = new URLSearchParams(location.search);
  const runId = params.get('run_id');
  if (!runId) return;
  try {
    const response = await fetch(`/api/result/${encodeURIComponent(runId)}`);
    const result = await response.json();
    renderResult(result);
    location.hash = location.hash || '#report';
    applyWorkspaceRoute();
  } catch (error) {
    $('#healthDot').className = 'dot err';
    $('#healthText').textContent = '历史诊断结果加载失败';
  }
}

$('#files').addEventListener('change', (event) => {
  $('#fileList').textContent = selectedFilesText(event.target.files);
});

$('#uploadForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  const files = $('#files').files;
  if (!files.length) {
    alert('请先选择企业资料文件。');
    return;
  }
  const formData = new FormData();
  Array.from(files).forEach(file => formData.append('files', file));
  await runAnalyzeRequest({ method: 'POST', body: formData });
});

$('#refreshMaterialsBtn').addEventListener('click', async () => {
  await loadMaterials();
});

$('#selectAllMaterialsBtn').addEventListener('click', () => {
  $$('#materialList input[type="checkbox"]:not(:disabled)').forEach(node => {
    node.checked = true;
  });
});

$('#analyzeSelectedBtn').addEventListener('click', async () => {
  const materialIds = selectedMaterialIds();
  if (!materialIds.length) {
    alert('请先在资料中心选择可用资料。');
    return;
  }
  await runAnalyzeRequest({
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ material_ids: materialIds })
  });
});

$('#riskFilter').addEventListener('change', () => {
  if (currentResult) renderSections(currentResult);
});

$('#saveBtn').addEventListener('click', async () => {
  await saveCurrentResult(true);
});

$('#addPlanBtn').addEventListener('click', () => {
  const result = collectResultEdits() || { ninety_day_plan: [] };
  result.ninety_day_plan.push({
    priority: result.ninety_day_plan.length + 1,
    problem: '',
    goal: '',
    action: '',
    owner: '',
    timeframe: '',
    check_metric: '',
    review_mechanism: ''
  });
  currentResult = result;
  renderPlan(result);
});

$('#copyPromptBtn').addEventListener('click', async () => {
  const prompt = $('#manualPrompt').value;
  if (!prompt) return;
  try {
    await navigator.clipboard.writeText(prompt);
    $('#mergeStatus').textContent = '提示词已复制。';
  } catch (error) {
    $('#manualPrompt').select();
    document.execCommand('copy');
    $('#mergeStatus').textContent = '提示词已复制。';
  }
});

$('#mergeAiBtn').addEventListener('click', async () => {
  try {
    const aiResult = parseJsonFromText($('#manualResponse').value);
    mergeAiResult(aiResult);
    await saveCurrentResult(false);
    $('#mergeStatus').textContent = '已合并并保存 ChatGPT 结果。';
  } catch (error) {
    $('#mergeStatus').textContent = '无法解析 JSON，请检查 ChatGPT 返回内容。';
  }
});

normalizeStaticLinks();
renderSystemModuleList();
renderModuleSwitcher();
checkHealth();
loadMaterials();
loadResultFromQuery();
window.addEventListener('hashchange', applyWorkspaceRoute);
applyWorkspaceRoute();
