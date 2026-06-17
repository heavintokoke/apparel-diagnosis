const modules = window.APPAREL_MODULES || [];

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

let activeModuleId = "enterprise-diagnosis";
let dataCenterMaterials = [];
let toastTimer = null;

function siteBasePath() {
  const marker = "/modules/01-enterprise-diagnosis/";
  const markerIndex = location.pathname.indexOf(marker);
  if (markerIndex >= 0) {
    return location.pathname.slice(0, markerIndex + 1);
  }
  if (location.pathname.endsWith("/")) {
    return location.pathname;
  }
  return location.pathname.replace(/[^/]*$/, "");
}

function resolveAppLink(path) {
  const value = String(path || "").trim();
  if (!value) return "";
  if (/^[a-z][a-z0-9+.-]*:/i.test(value) || value.startsWith("#")) return value;
  const clean = value.replace(/^\/+/, "");
  if (location.protocol === "file:") {
    return `http://127.0.0.1:8770/${clean}`;
  }
  if (["127.0.0.1", "localhost", "::1"].includes(location.hostname)) {
    return `/${clean}`;
  }
  return `${siteBasePath()}${clean}`;
}

function normalizeStaticLinks() {
  $$("[data-app-link]").forEach((link) => {
    link.href = resolveAppLink(link.dataset.appLink || link.getAttribute("href"));
  });
}

function statusLabel(status) {
  return status === "ready" ? "可使用" : "待开放";
}

function renderSideModuleList() {
  const container = $("#sideModuleList");
  if (!container) return;
  container.innerHTML = modules.map((item) => {
    const active = item.id === activeModuleId ? "active" : "";
    const content = `<strong>${item.title}</strong>`;
    if (item.link) {
      return `<a class="${active}" href="${resolveAppLink(item.link)}" data-side-module-id="${item.id}">${content}</a>`;
    }
    return `<button class="${active}" type="button" data-side-module-id="${item.id}">${content}</button>`;
  }).join("");

  $$("#sideModuleList button[data-side-module-id]").forEach((button) => {
    button.addEventListener("click", () => {
      if (location.hash !== "#dashboard") {
        history.replaceState(null, "", "#dashboard");
        window.dispatchEvent(new HashChangeEvent("hashchange"));
      }
      selectModule(button.dataset.sideModuleId);
    });
  });
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  }[char]));
}

function formatSize(bytes) {
  if (!bytes) return "0 KB";
  if (bytes < 1024 * 1024) return `${Math.ceil(bytes / 1024)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function formatDate(value) {
  if (!value) return "-";
  return String(value).replace("T", " ").slice(0, 16);
}

function showToast(message) {
  let toast = $("#appToast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "appToast";
    toast.className = "app-toast";
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.classList.add("show");
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => {
    toast.classList.remove("show");
  }, 1800);
}

function renderModuleGrid() {
  $("#moduleGrid").innerHTML = modules.map((item) => `
    <article class="module-card ${item.id === activeModuleId ? "active" : ""}" data-module-id="${item.id}" tabindex="0">
      <div class="module-top">
        <span class="module-status ${item.status}">${statusLabel(item.status)}</span>
      </div>
      <h4>${item.title}</h4>
      <p>${item.summary}</p>
      <span class="stage">${item.link ? "进入模块" : "查看说明"}</span>
    </article>
  `).join("");

  $$("#moduleGrid .module-card").forEach((card) => {
    card.addEventListener("click", () => {
      const item = modules.find((module) => module.id === card.dataset.moduleId);
      if (window.matchMedia("(max-width: 760px)").matches && item?.link) {
        window.location.href = resolveAppLink(item.link);
        return;
      }
      if (window.matchMedia("(max-width: 760px)").matches && !item?.link) {
        showToast("该模块暂未开放");
        return;
      }
      selectModule(card.dataset.moduleId);
    });
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        const item = modules.find((module) => module.id === card.dataset.moduleId);
        if (window.matchMedia("(max-width: 760px)").matches && item?.link) {
          window.location.href = resolveAppLink(item.link);
          return;
        }
        if (window.matchMedia("(max-width: 760px)").matches && !item?.link) {
          showToast("该模块暂未开放");
          return;
        }
        selectModule(card.dataset.moduleId);
      }
    });
  });
}

function updateModuleAction(link, item, readyText) {
  if (!link) return;
  if (item.link) {
    link.href = resolveAppLink(item.link);
    link.textContent = readyText;
    link.classList.remove("disabled");
    link.removeAttribute("aria-disabled");
    link.removeAttribute("tabindex");
    return;
  }

  link.removeAttribute("href");
  link.textContent = "模块待开放";
  link.classList.add("disabled");
  link.setAttribute("aria-disabled", "true");
  link.setAttribute("tabindex", "-1");
}

function renderModuleHero(item) {
  $("#moduleHeroEyebrow").textContent = `经营模块 · ${statusLabel(item.status)}`;
  $("#moduleHeroTitle").textContent = item.title;
  $("#moduleHeroSummary").textContent = item.summary;
}

function renderDetail() {
  const item = modules.find((module) => module.id === activeModuleId) || modules[0];
  renderModuleHero(item);
  $("#detailTitle").textContent = item.title;
  $("#detailSummary").textContent = item.summary;
  $("#detailStatus").textContent = statusLabel(item.status);
  $("#detailInputs").textContent = item.inputs;
  $("#detailOutputs").textContent = item.outputs;

  updateModuleAction($("#primaryModuleAction"), item, "进入经营诊断系统");
  updateModuleAction($("#detailLink"), item, "进入模块");
}

function renderDataCenter() {
  const ready = dataCenterMaterials.filter((item) => item.extract_status === "ready");
  $("#dataCenterSummary").textContent = `共有 ${dataCenterMaterials.length} 份资料，${ready.length} 份已完成识别，可被各模块复用。`;
  if (!dataCenterMaterials.length) {
    $("#dataCenterList").innerHTML = '<p class="empty-state">资料中心暂无资料。请先进入经营诊断模块上传企业资料。</p>';
    return;
  }
  $("#dataCenterList").innerHTML = dataCenterMaterials.map((item) => `
    <article class="data-row ${item.extract_status !== "ready" ? "disabled" : ""}">
      <div>
        <strong>${escapeHtml(item.filename)}</strong>
        <span>${escapeHtml(item.file_type || "-")}｜${formatSize(item.size)}｜${formatDate(item.uploaded_at)}</span>
        ${item.text_preview ? `<p>${escapeHtml(item.text_preview)}</p>` : ""}
        ${item.extract_error ? `<p class="error-text">${escapeHtml(item.extract_error)}</p>` : ""}
      </div>
      <div class="data-tags">
        ${(item.categories || []).slice(0, 5).map((category) => `<span>${escapeHtml(category)}</span>`).join("")}
      </div>
    </article>
  `).join("");
}

async function loadDataCenter() {
  try {
    const response = await fetch("/api/materials");
    const data = await response.json();
    if (!data.ok) throw new Error(data.error || "资料中心读取失败");
    dataCenterMaterials = data.materials || [];
    renderDataCenter();
  } catch (error) {
    $("#dataCenterSummary").textContent = "资料中心需要启动本地服务后读取。";
    $("#dataCenterList").innerHTML = "";
  }
}

async function loadReports() {
  try {
    const response = await fetch("/api/reports");
    const data = await response.json();
    if (!data.ok) throw new Error(data.error || "报告中心读取失败");
    $("#reportCenterStatus").textContent = `已记录 ${data.counts.total} 份模块报告，导出的 Word/PDF 会登记到报告中心。`;
  } catch (error) {
    $("#reportCenterStatus").textContent = "报告中心需要启动本地服务后读取。";
  }
}

function selectModule(id) {
  activeModuleId = id;
  renderModuleGrid();
  renderSideModuleList();
  renderDetail();
}

function bindNav() {
  const links = $$("[data-view-link]");
  const sections = $$(".view-section");
  const activate = () => {
    const requested = location.hash.replace("#", "") || "dashboard";
    const current = sections.some((section) => section.id === requested) ? requested : "dashboard";
    sections.forEach((section) => section.classList.toggle("active", section.id === current));
    links.forEach((link) => link.classList.toggle("active", link.dataset.viewLink === current));
    if (requested !== current) {
      history.replaceState(null, "", `#${current}`);
    }
    if (window.matchMedia("(max-width: 760px)").matches) {
      window.scrollTo(0, 0);
    }
  };
  links.forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      const target = link.dataset.viewLink || "dashboard";
      if (location.hash !== `#${target}`) {
        history.pushState(null, "", `#${target}`);
      }
      activate();
    });
  });
  window.addEventListener("hashchange", activate);
  activate();
}

function bindDataCenter() {
  $("#refreshDataCenterBtn").addEventListener("click", async () => {
    await loadDataCenter();
    await loadReports();
  });
}

function init() {
  normalizeStaticLinks();
  renderSideModuleList();
  renderModuleGrid();
  renderDetail();
  bindNav();
  bindDataCenter();
  loadDataCenter();
  loadReports();
}

init();
