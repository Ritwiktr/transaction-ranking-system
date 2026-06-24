const API_BASE = window.API_BASE_URL;

const transactionForm = document.getElementById("transaction-form");
const summaryForm = document.getElementById("summary-form");
const transactionResult = document.getElementById("transaction-result");
const summaryResult = document.getElementById("summary-result");
const rankingBody = document.getElementById("ranking-body");
const rankingStatus = document.getElementById("ranking-status");
const idempotencyKeyInput = document.getElementById("idempotency-key");
const regenerateKeyBtn = document.getElementById("regenerate-key");
const runDemoBtn = document.getElementById("run-demo");
const demoStatus = document.getElementById("demo-status");

function generateIdempotencyKey() {
  return crypto.randomUUID();
}

function setIdempotencyKey() {
  idempotencyKeyInput.value = generateIdempotencyKey();
}

function showMessage(element, message, type = "info") {
  element.textContent = message;
  element.className = `result ${type}`;
  element.hidden = false;
}

function formatNumber(value) {
  return new Intl.NumberFormat().format(value);
}

async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || `Request failed (${response.status})`);
  }
  return { data, status: response.status };
}

async function submitTransaction(userId, amount, idempotencyKey) {
  return apiRequest("/transaction", {
    method: "POST",
    body: JSON.stringify({ userId, amount, idempotencyKey }),
  });
}

async function runDemoScenarios() {
  runDemoBtn.disabled = true;
  demoStatus.hidden = false;
  demoStatus.textContent = "Running demo scenarios…";
  demoStatus.className = "demo-status running";

  const runId = Date.now();
  const lines = [];

  try {
    // Scenario 1: quality user — 2 large transactions (200 pts, avg 100)
    for (let i = 0; i < 2; i += 1) {
      await submitTransaction("quality-demo", 100, `demo-${runId}-quality-${i}`);
    }
    lines.push("✓ Quality user: 2 × 100 pts");

    // Scenario 2: spammer — 10 small transactions (100 pts, avg 10)
    for (let i = 0; i < 10; i += 1) {
      await submitTransaction("spam-demo", 10, `demo-${runId}-spam-${i}`);
    }
    lines.push("✓ Spammer: 10 × 10 pts (same total, lower avg)");

    // Scenario 3: duplicate idempotency key — second call must not double-count
    const dupKey = `demo-${runId}-dup`;
    const first = await submitTransaction("dup-demo", 50, dupKey);
    const second = await submitTransaction("dup-demo", 50, dupKey);
    lines.push(
      second.data.duplicate
        ? "✓ Duplicate key rejected (balance unchanged)"
        : "✗ Duplicate key test failed"
    );
    lines.push(`  dup-demo balance stays at ${first.data.totalPoints} pts`);

    await loadRanking();

    const qualitySummary = await apiRequest("/summary/quality-demo");
    const spamSummary = await apiRequest("/summary/spam-demo");
    lines.push(
      `✓ Ranking: quality-demo #${qualitySummary.data.rank}, spam-demo #${spamSummary.data.rank}`
    );

    document.getElementById("summary-user-id").value = "quality-demo";
    showMessage(
      summaryResult,
      `${qualitySummary.data.userId}: Rank #${qualitySummary.data.rank} | ${formatNumber(qualitySummary.data.totalPoints)} points | Avg ${qualitySummary.data.averageTransactionAmount}`,
      "success"
    );

    demoStatus.textContent = lines.join("\n");
    demoStatus.className = "demo-status success";
  } catch (error) {
    demoStatus.textContent = `Demo failed: ${error.message}`;
    demoStatus.className = "demo-status error";
  } finally {
    runDemoBtn.disabled = false;
  }
}

transactionForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  transactionResult.hidden = true;

  const payload = {
    userId: document.getElementById("user-id").value.trim(),
    amount: Number(document.getElementById("amount").value),
    idempotencyKey: idempotencyKeyInput.value.trim(),
  };

  try {
    const { data, status } = await apiRequest("/transaction", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    const duplicateNote = data.duplicate ? " (duplicate request — no double count)" : "";
    showMessage(
      transactionResult,
      `Success${duplicateNote}: ${formatNumber(data.amount)} points for ${data.userId}. Total: ${formatNumber(data.totalPoints)} (${data.transactionCount} transactions).`,
      data.duplicate ? "warning" : "success"
    );

    if (status === 201) {
      setIdempotencyKey();
    }

    await loadRanking();
  } catch (error) {
    showMessage(transactionResult, error.message, "error");
  }
});

summaryForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  summaryResult.hidden = true;

  const userId = document.getElementById("summary-user-id").value.trim();
  try {
    const { data } = await apiRequest(`/summary/${encodeURIComponent(userId)}`);
    showMessage(
      summaryResult,
      `${data.userId}: Rank #${data.rank} | ${formatNumber(data.totalPoints)} points | ${data.transactionCount} transactions | Avg ${data.averageTransactionAmount} | Score ${data.rankingScore}`,
      "success"
    );
  } catch (error) {
    showMessage(summaryResult, error.message, "error");
  }
});

function renderRanking(rankings) {
  if (!rankings.length) {
    rankingBody.innerHTML = `<tr><td colspan="6" class="empty">No transactions yet. Submit the first one!</td></tr>`;
    return;
  }

  rankingBody.innerHTML = rankings
    .map(
      (entry) => `
      <tr>
        <td>#${entry.rank}</td>
        <td>${entry.userId}</td>
        <td>${formatNumber(entry.totalPoints)}</td>
        <td>${entry.transactionCount}</td>
        <td>${entry.averageTransactionAmount}</td>
        <td>${entry.rankingScore}</td>
      </tr>
    `
    )
    .join("");
}

async function loadRanking() {
  try {
    const { data } = await apiRequest("/ranking?limit=50");
    renderRanking(data.rankings);
    rankingStatus.textContent = `Updated ${new Date().toLocaleTimeString()}`;
  } catch (error) {
    rankingStatus.textContent = `Failed to load ranking: ${error.message}`;
  }
}

regenerateKeyBtn.addEventListener("click", setIdempotencyKey);
runDemoBtn.addEventListener("click", runDemoScenarios);
setIdempotencyKey();
loadRanking();
setInterval(loadRanking, 10000);
