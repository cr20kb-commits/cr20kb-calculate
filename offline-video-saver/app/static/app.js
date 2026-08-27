(() => {
  "use strict";

  const text = {
    ru: {
      eyebrow: "Свой плейлист → компактный архив",
      title: "Скачать плейлист без лишнего веса",
      lead: "Вставьте ссылку. Сервис скачает ролики по одному, уменьшит их через HandBrake и отдаст одним ZIP — с телефона, планшета или компьютера.",
      accessTitle: "Доступ", accessKey: "Ключ доступа", enter: "Войти",
      playlistTitle: "Плейлист", playlistUrl: "Ссылка на YouTube-плейлист",
      profileTitle: "Размер и совместимость",
      rights: "Я подтверждаю право скачать эти материалы и не использую сервис для обхода DRM.",
      start: "Скачать и уменьшить", processing: "Обработка", stage: "Этап",
      items: "Ролики", resultSize: "Результат", saved: "Сэкономлено",
      downloadZip: "Скачать ZIP", newJob: "Новый плейлист",
      how1Title: "Одна ссылка", how1Text: "Публичный или доступный по ссылке плейлист. Без входа в Google.",
      how2Title: "Минимум временного места", how2Text: "Ролики обрабатываются по одному; исходник удаляется сразу.",
      how3Title: "Не перекодируем зря", how3Text: "Если исходный файл уже меньше результата HandBrake, остаётся исходник.",
      legal: "Только для материалов, которые вы вправе скачивать. Проект не обходит DRM и не поддерживает cookies.",
      maxItems: n => `до ${n} роликов`,
      unavailable: list => `Сервис не готов. Отсутствуют: ${list}.`,
      authFailed: "Неверный ключ доступа.",
      network: "Ошибка связи с сервером.",
      invalid: "Проверьте ссылку на YouTube-плейлист.",
      rightsRequired: "Подтвердите право на скачивание.",
      queueFull: "Очередь заполнена. Удалите завершённую задачу или повторите позже.",
      stageNames: {queued:"в очереди", scanning:"проверка плейлиста", downloading:"скачивание", encoding:"сжатие", ready:"готово", error:"ошибка"},
      truncated: "Плейлист обрезан по серверному лимиту.",
      failed: n => `Не удалось обработать: ${n}.`,
      ready: "Архив готов.",
    },
    en: {
      eyebrow: "Your playlist → compact archive",
      title: "Download a playlist without the extra weight",
      lead: "Paste one link. The service downloads videos one at a time, reduces them with HandBrake, and returns one ZIP — on a phone, tablet, or computer.",
      accessTitle: "Access", accessKey: "Access key", enter: "Sign in",
      playlistTitle: "Playlist", playlistUrl: "YouTube playlist link",
      profileTitle: "Size and compatibility",
      rights: "I confirm that I have the right to download these materials and will not use the service to bypass DRM.",
      start: "Download and reduce", processing: "Processing", stage: "Stage",
      items: "Videos", resultSize: "Result", saved: "Saved",
      downloadZip: "Download ZIP", newJob: "New playlist",
      how1Title: "One link", how1Text: "A public or unlisted playlist. No Google sign-in.",
      how2Title: "Low temporary storage", how2Text: "Videos are processed one at a time; each source is removed immediately.",
      how3Title: "No pointless transcoding", how3Text: "When the source is already smaller than HandBrake output, the source is kept.",
      legal: "Only for material you are entitled to download. This project does not bypass DRM or support cookies.",
      maxItems: n => `up to ${n} videos`,
      unavailable: list => `Service is not ready. Missing: ${list}.`,
      authFailed: "Wrong access key.",
      network: "Could not reach the server.",
      invalid: "Check the YouTube playlist link.",
      rightsRequired: "Confirm your right to download.",
      queueFull: "The queue is full. Remove a completed job or retry later.",
      stageNames: {queued:"queued", scanning:"scanning playlist", downloading:"downloading", encoding:"compressing", ready:"ready", error:"error"},
      truncated: "The playlist was truncated at the server limit.",
      failed: n => `Failed items: ${n}.`,
      ready: "Archive is ready.",
    },
  };

  const $ = id => document.getElementById(id);
  const els = {
    langButton: $("langButton"), systemNotice: $("systemNotice"),
    authCard: $("authCard"), authForm: $("authForm"), accessKey: $("accessKey"), authError: $("authError"),
    jobCard: $("jobCard"), jobForm: $("jobForm"), playlistUrl: $("playlistUrl"),
    profiles: $("profiles"), rightsConfirmed: $("rightsConfirmed"), startButton: $("startButton"),
    formError: $("formError"), limitBadge: $("limitBadge"),
    progressCard: $("progressCard"), jobTitle: $("jobTitle"), statusBadge: $("statusBadge"),
    progressBar: $("progressBar"), stageValue: $("stageValue"), itemsValue: $("itemsValue"),
    sizeValue: $("sizeValue"), savedValue: $("savedValue"), currentTitle: $("currentTitle"),
    warnings: $("warnings"), downloadButton: $("downloadButton"), newJobButton: $("newJobButton"),
    jobError: $("jobError"),
  };

  let lang = localStorage.getItem("ovs-language") || (navigator.language.startsWith("ru") ? "ru" : "en");
  let config = null;
  let pollTimer = null;
  let currentJob = null;

  function tr(key) { return text[lang][key]; }
  function show(el, visible = true) { el.classList.toggle("hidden", !visible); }
  function errorMessage(detail) {
    if (detail === "rights_confirmation_required") return tr("rightsRequired");
    if (detail === "queue_full") return tr("queueFull");
    if (String(detail).startsWith("playlist_") || detail === "profile_invalid") return tr("invalid");
    return typeof detail === "string" ? detail : tr("network");
  }
  function formatBytes(value) {
    if (!Number.isFinite(value) || value <= 0) return "—";
    const units = ["B", "KB", "MB", "GB", "TB"];
    let size = value, index = 0;
    while (size >= 1024 && index < units.length - 1) { size /= 1024; index += 1; }
    return `${size.toFixed(index ? 1 : 0)} ${units[index]}`;
  }
  async function api(path, options = {}) {
    const response = await fetch(path, {
      credentials: "same-origin",
      headers: {"Content-Type": "application/json", ...(options.headers || {})},
      ...options,
    });
    let body = {};
    try { body = await response.json(); } catch (_) {}
    if (!response.ok) {
      const err = new Error("api_error");
      err.status = response.status;
      err.detail = body.detail;
      throw err;
    }
    return body;
  }

  function applyLanguage() {
    document.documentElement.lang = lang;
    document.querySelectorAll("[data-i18n]").forEach(node => {
      const value = tr(node.dataset.i18n);
      if (typeof value === "string") node.textContent = value;
    });
    els.langButton.textContent = lang === "ru" ? "EN" : "RU";
    localStorage.setItem("ovs-language", lang);
    if (config) {
      els.limitBadge.textContent = tr("maxItems")(config.max_playlist_items);
      renderProfiles();
    }
    if (currentJob) renderJob(currentJob);
  }

  function renderProfiles() {
    els.profiles.replaceChildren();
    for (const [index, profile] of config.profiles.entries()) {
      const label = document.createElement("label");
      label.className = "profile";
      const input = document.createElement("input");
      input.type = "radio";
      input.name = "profile";
      input.value = profile.id;
      input.checked = profile.id === config.default_profile || (!index && !config.default_profile);
      const strong = document.createElement("strong");
      strong.textContent = profile[`label_${lang}`];
      const small = document.createElement("small");
      small.textContent = profile[`description_${lang}`];
      label.append(input, strong, small);
      els.profiles.append(label);
    }
  }

  function setFormBusy(value) {
    els.startButton.disabled = value;
    els.playlistUrl.disabled = value;
    els.rightsConfirmed.disabled = value;
    els.profiles.querySelectorAll("input").forEach(input => { input.disabled = value; });
  }

  function renderJob(job) {
    currentJob = job;
    const percent = Math.max(0, Math.min(100, Math.round((job.progress || 0) * 100)));
    els.statusBadge.textContent = `${percent}%`;
    els.progressBar.style.width = `${percent}%`;
    els.jobTitle.textContent = job.title || tr("processing");
    els.stageValue.textContent = tr("stageNames")[job.stage] || job.stage || "—";
    els.itemsValue.textContent = `${job.completed_items + job.failed_items} / ${job.total_items || 0}`;
    els.sizeValue.textContent = formatBytes(job.output_bytes);
    els.savedValue.textContent = formatBytes(job.saved_bytes);
    els.currentTitle.textContent = job.current_title || (job.status === "ready" ? tr("ready") : "");
    const notes = [];
    if (job.truncated) notes.push(tr("truncated"));
    if (job.failed_items) notes.push(tr("failed")(job.failed_items));
    if (job.warnings?.length) notes.push(...job.warnings);
    els.warnings.textContent = notes.join("\n");
    show(els.warnings, notes.length > 0);
    show(els.downloadButton, job.status === "ready");
    show(els.newJobButton, job.status === "ready" || job.status === "error");
    show(els.jobError, job.status === "error");
    els.jobError.textContent = job.error || "";
    if (job.status === "ready") els.downloadButton.href = `/api/jobs/${encodeURIComponent(job.id)}/download`;
  }

  async function pollJob(id) {
    clearTimeout(pollTimer);
    try {
      const job = await api(`/api/jobs/${encodeURIComponent(id)}`);
      renderJob(job);
      if (["queued", "scanning", "running"].includes(job.status)) {
        pollTimer = setTimeout(() => pollJob(id), 1200);
      }
    } catch (error) {
      els.jobError.textContent = error.status === 401 ? tr("authFailed") : tr("network");
      show(els.jobError);
      pollTimer = setTimeout(() => pollJob(id), 2500);
    }
  }

  async function init() {
    applyLanguage();
    try {
      config = await api("/api/config");
      els.limitBadge.textContent = tr("maxItems")(config.max_playlist_items);
      renderProfiles();
      if (!config.ready) {
        els.systemNotice.textContent = tr("unavailable")(config.missing_tools.join(", "));
        show(els.systemNotice);
        els.startButton.disabled = true;
      }
      show(els.authCard, config.auth_required);
      show(els.jobCard, !config.auth_required);
    } catch (_) {
      els.systemNotice.textContent = tr("network");
      show(els.systemNotice);
      els.startButton.disabled = true;
    }
  }

  els.langButton.addEventListener("click", () => {
    lang = lang === "ru" ? "en" : "ru";
    applyLanguage();
  });

  els.authForm.addEventListener("submit", async event => {
    event.preventDefault();
    show(els.authError, false);
    try {
      await api("/api/session", {method: "POST", body: JSON.stringify({key: els.accessKey.value})});
      els.accessKey.value = "";
      show(els.authCard, false);
      show(els.jobCard);
    } catch (_) {
      els.authError.textContent = tr("authFailed");
      show(els.authError);
    }
  });

  els.jobForm.addEventListener("submit", async event => {
    event.preventDefault();
    show(els.formError, false);
    const selected = els.profiles.querySelector("input:checked");
    setFormBusy(true);
    try {
      const job = await api("/api/jobs", {
        method: "POST",
        body: JSON.stringify({
          url: els.playlistUrl.value,
          profile: selected?.value || "compact",
          rights_confirmed: els.rightsConfirmed.checked,
        }),
      });
      show(els.progressCard);
      els.progressCard.scrollIntoView({behavior: "smooth", block: "start"});
      renderJob(job);
      pollJob(job.id);
    } catch (error) {
      els.formError.textContent = error.status === 401 ? tr("authFailed") : errorMessage(error.detail);
      show(els.formError);
      setFormBusy(false);
    }
  });

  els.newJobButton.addEventListener("click", async () => {
    clearTimeout(pollTimer);
    if (currentJob) {
      try { await api(`/api/jobs/${encodeURIComponent(currentJob.id)}`, {method: "DELETE"}); } catch (_) {}
    }
    currentJob = null;
    els.jobForm.reset();
    renderProfiles();
    show(els.progressCard, false);
    setFormBusy(false);
    els.playlistUrl.focus();
  });

  init();
})();
