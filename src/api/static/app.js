const runButton = document.getElementById("runButton");
const sourceText = document.getElementById("sourceText");
const localeInput = document.getElementById("locale");
const statusEl = document.getElementById("status");
const runCsvButton = document.getElementById("runCsvButton");
const csvFileInput = document.getElementById("csvFile");
const csvTextColumnInput = document.getElementById("csvTextColumn");
const csvLocaleInput = document.getElementById("csvLocale");
const csvStatusEl = document.getElementById("csvStatus");

const originalView = document.getElementById("originalView");
const highlightedView = document.getElementById("highlightedView");
const syntheticView = document.getElementById("syntheticView");
const entitiesView = document.getElementById("entitiesView");

function setStatus(message, type) {
  statusEl.textContent = message;
  statusEl.className = `status ${type}`;
}

function setCsvStatus(message, type) {
  csvStatusEl.textContent = message;
  csvStatusEl.className = `status ${type}`;
}

function renderEntities(entities) {
  if (!entities.length) {
    entitiesView.className = "entity-list empty";
    entitiesView.textContent = "No entities detected.";
    return;
  }

  entitiesView.className = "entity-list";
  entitiesView.innerHTML = entities
    .map(
      (entity) => `
        <div class="entity-chip">
          <span class="entity-label">${entity.label}</span>
          <span class="entity-value">${entity.text}</span>
          <span class="entity-confidence">${(entity.confidence * 100).toFixed(0)}%</span>
        </div>
      `
    )
    .join("");
}

async function runPipeline() {
  const text = sourceText.value.trim();
  const locale = localeInput.value.trim() || "en-IN";

  if (!text) {
    setStatus("Please enter text before running.", "error");
    return;
  }

  runButton.disabled = true;
  setStatus("Processing...", "idle");

  try {
    const response = await fetch("/process", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, locale }),
    });

    if (!response.ok) {
      let message = `Request failed with status ${response.status}`;
      try {
        const payload = await response.json();
        if (payload && payload.detail) {
          message = payload.detail;
        }
      } catch {
        // Ignore JSON parse issues and keep default message.
      }
      throw new Error(message);
    }

    const data = await response.json();

    originalView.textContent = data.original_text;
    highlightedView.textContent = data.agent1.highlighted_text;
    syntheticView.textContent = data.agent2.transformed_text;
    originalView.classList.remove("empty");
    highlightedView.classList.remove("empty");
    syntheticView.classList.remove("empty");

    renderEntities(data.agent1.entities);

    const fallbackMsg = data.agent2.used_fallback ? "Fallback mode used." : "Context-aware mode used.";
    setStatus(`Done. ${fallbackMsg}`, "success");
  } catch (error) {
    setStatus(error.message || "Something went wrong.", "error");
  } finally {
    runButton.disabled = false;
  }
}

runButton.addEventListener("click", runPipeline);

async function runCsvPipeline() {
  const file = csvFileInput.files[0];
  const textColumn = csvTextColumnInput.value.trim() || "auto";
  const locale = csvLocaleInput.value.trim() || "en-IN";

  if (!file) {
    setCsvStatus("Please choose a CSV file before converting.", "error");
    return;
  }

  runCsvButton.disabled = true;
  setCsvStatus("Converting CSV...", "idle");

  try {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("text_column", textColumn);
    formData.append("locale", locale);

    const response = await fetch("/process-csv", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      let message = `CSV conversion failed with status ${response.status}`;
      try {
        const payload = await response.json();
        if (payload && payload.detail) {
          message = payload.detail;
        }
      } catch {
        // Ignore JSON parse issues and keep default message.
      }
      throw new Error(message);
    }

    const blob = await response.blob();
    const downloadUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    const disposition = response.headers.get("Content-Disposition") || "";
    const match = disposition.match(/filename="([^"]+)"/);
    const filename = match ? match[1] : "converted_synthetic.csv";

    link.href = downloadUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(downloadUrl);

    setCsvStatus(`Done. Downloaded ${filename}`, "success");
  } catch (error) {
    setCsvStatus(error.message || "CSV conversion failed.", "error");
  } finally {
    runCsvButton.disabled = false;
  }
}

runCsvButton.addEventListener("click", runCsvPipeline);
