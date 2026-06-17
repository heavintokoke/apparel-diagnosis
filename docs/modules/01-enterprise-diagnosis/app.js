let currentResult = null;
let currentRunId = null;
const STATIC_PREVIEW = true;

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

function show(selector) { $(selector).classList.remove('hidden'); }
function hide(selector) { $(selector).classList.add('hidden'); }

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[char]));
}

async function checkHealth() {
  if (STATIC_PREVIEW) {
    $('#healthDot').className = 'dot ok';
    $('#healthText').textContent = '静态预览版：示例诊断报告已加载';
    return;
  }
  try {
    const response = await fetch('/api/health');
    const data = await response.json();
    $('#healthDot').className = 'dot ok';
    $('#healthText').textContent = data.knowledge || '知识库已加载';
  } catch (error) {
    $('#healthDot').className = 'dot err';
    $('#healthText').textContent = '知识库加载失败';
  }
}

function selectedFilesText(files) {
  if (!files.length) return '尚未选择文件';
  return Array.from(files).map(file => `${file.name} (${Math.ceil(file.size / 1024)} KB)`).join('、');
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
  if (STATIC_PREVIEW) {
    $('#docxLink').href = '#';
    $('#pdfLink').href = '#';
  }
  ['#summary', '#report', '#flows', '#sections', '#departments', '#missing', '#aiAssist', '#plan'].forEach(show);
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
  if (STATIC_PREVIEW) {
    if (showSuccess) alert('当前是静态预览版，修改只会临时显示在本页面；正式保存需要部署后端。');
    return true;
  }
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

async function loadResultFromQuery() {
  if (STATIC_PREVIEW) {
    const response = await fetch('demo-result.json');
    const result = await response.json();
    renderResult(result);
    location.hash = location.hash || '#summary';
    return;
  }
  const params = new URLSearchParams(location.search);
  const runId = params.get('run_id');
  if (!runId) return;
  try {
    const response = await fetch(`/api/result/${encodeURIComponent(runId)}`);
    const result = await response.json();
    renderResult(result);
    location.hash = location.hash || '#summary';
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
  if (STATIC_PREVIEW) {
    alert('当前是静态预览版，只展示界面和示例报告；上传资料诊断需要部署后端后使用。');
    return;
  }
  const files = $('#files').files;
  if (!files.length) {
    alert('请先选择企业资料文件。');
    return;
  }
  const formData = new FormData();
  Array.from(files).forEach(file => formData.append('files', file));
  $('#analyzeBtn').disabled = true;
  show('#progress');
  try {
    const response = await fetch('/api/analyze', { method: 'POST', body: formData });
    const data = await response.json();
    if (!data.ok) throw new Error(data.error || '分析失败');
    renderResult(data.result);
    location.hash = '#summary';
  } catch (error) {
    alert(error.message);
  } finally {
    $('#analyzeBtn').disabled = false;
    hide('#progress');
  }
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

['#docxLink', '#pdfLink'].forEach((selector) => {
  $(selector).addEventListener('click', (event) => {
    if (!STATIC_PREVIEW) return;
    event.preventDefault();
    alert('当前是静态预览版，导出 Word/PDF 需要部署后端后使用。');
  });
});

checkHealth();
loadResultFromQuery();
