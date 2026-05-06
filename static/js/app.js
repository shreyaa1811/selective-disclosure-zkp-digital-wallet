// static/js/app.js — ZKP Wallet Frontend

const API = "http://127.0.0.1:5000/api";
let lastPayment = null;
let activeTab = "visual";

// ── Utility ─────────────────────────────────────────────────────────────────

function toast(msg, type = "info") {
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = msg;
  document.getElementById("toastContainer").appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

function setTitle(t) {
  document.getElementById("outputTitle").textContent = t;
}

function showLoading(msg = "Generating ZK proofs...") {
  document.getElementById("visualOutput").innerHTML = `
    <div class="loading">
      <div class="spinner"></div>
      <span>${msg}</span>
    </div>`;
}

function setStatus(online) {
  const pill = document.getElementById("statusPill");
  pill.className = "status-pill" + (online ? " online" : "");
  pill.innerHTML = `<span class="dot"></span> ${online ? "WALLET ONLINE" : "OFFLINE"}`;
}

function unlockCard(id) {
  document.getElementById(id).setAttribute("data-locked", "false");
}

function switchTab(tab) {
  activeTab = tab;
  document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
  event.target.classList.add("active");
  document.getElementById("visualOutput").classList.toggle("hidden", tab !== "visual");
  document.getElementById("jsonOutput").classList.toggle("hidden", tab !== "json");
}

function updateRawJson(data) {
  document.getElementById("rawJson").textContent = JSON.stringify(data, null, 2);
}

function truncate(str, n = 24) {
  if (!str || str.length <= n) return str;
  return str.slice(0, n) + "…";
}

// ── Step 1: Setup ────────────────────────────────────────────────────────────

async function setup() {
  showLoading("Issuing KYC credential...");
  setTitle("Setting up wallet...");

  const body = {
    dob: document.getElementById("dob").value,
    balance: parseFloat(document.getElementById("balance").value),
    country: document.getElementById("country").value,
    merchants: document.getElementById("merchants").value.split(",").map(m => m.trim())
  };

  try {
    const res = await fetch(`${API}/setup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    const data = await res.json();
    updateRawJson(data);

    if (!data.success) throw new Error(data.error || "Setup failed");

    setStatus(true);
    unlockCard("payCard");
    unlockCard("auditCard");
    setTitle("KYC Credential Issued ✓");
    toast("Wallet initialized & KYC credential issued!", "success");

    renderSetupResult(data, body);
  } catch (e) {
    toast("Error: " + e.message, "error");
    setTitle("Setup failed");
  }
}

function renderSetupResult(data, body) {
  document.getElementById("proofChain").classList.add("hidden");
  document.getElementById("visualOutput").innerHTML = `
    <div class="kyc-block">
      <h4>⬡ IDENTITY PROVIDER OUTPUT</h4>
      <div class="kyc-row">
        <span class="kyc-key">Status</span>
        <span class="kyc-val green">✓ KYC VERIFIED</span>
      </div>
      <div class="kyc-row">
        <span class="kyc-key">Wallet ID</span>
        <span class="kyc-val accent">${data.wallet_id}</span>
      </div>
      <div class="kyc-row">
        <span class="kyc-key">Credential ID</span>
        <span class="kyc-val">${truncate(data.credential_id, 20)}</span>
      </div>
      <div class="kyc-row">
        <span class="kyc-key">Poseidon Commitment</span>
        <span class="kyc-val">${truncate(data.commitment, 22)}</span>
      </div>
      <div class="kyc-row">
        <span class="kyc-key">Issuer</span>
        <span class="kyc-val">${data.issuer}</span>
      </div>
      <div class="kyc-row">
        <span class="kyc-key">Country</span>
        <span class="kyc-val">${body.country}</span>
      </div>
      <div class="kyc-row">
        <span class="kyc-key">Balance</span>
        <span class="kyc-val green">$${body.balance.toFixed(2)}</span>
      </div>
    </div>

    <div class="proof-card pass" style="border-left-color: var(--accent)">
      <div class="proof-title">
        <span class="proof-name">What was stored in the credential?</span>
      </div>
      <div class="proof-claim">Poseidon(credential_id, nonce) → commitment</div>
      <div class="proof-data">
        Your name, DOB, and passport are NOT stored.<br>
        Only a cryptographic commitment is registered publicly.<br>
        The wallet holds (credential_id + nonce) privately.<br><br>
        commitment = ${truncate(data.commitment, 40)}
      </div>
    </div>`;
}

// ── Step 2: Pay ──────────────────────────────────────────────────────────────

async function pay(overrideMerchant = null) {
  const merchant = overrideMerchant || document.getElementById("merchantId").value;
  const amount = parseFloat(document.getElementById("amount").value);

  showLoading("Generating Groth16 ZK proofs...");
  setTitle(`Payment to ${merchant} — $${amount}`);

  try {
    const payRes = await fetch(`${API}/pay`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ merchant_id: merchant, amount })
    });
    const payment = await payRes.json();
    lastPayment = payment;
    updateRawJson(payment);

    // Auto-verify
    const verRes = await fetch(`${API}/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ payment })
    });
    const verification = await verRes.json();

    setTitle(verification.accepted ? `Payment Accepted ✓` : `Payment Rejected ✗`);
    toast(
      verification.accepted ? `Payment of $${amount} accepted!` : `Payment rejected — proof failed`,
      verification.accepted ? "success" : "error"
    );

    renderPaymentResult(payment, verification, merchant, amount);
    renderProofChain(payment.proofs, verification);
  } catch (e) {
    toast("Error: " + e.message, "error");
    setTitle("Payment failed");
  }
}

function tryBlockedMerchant() {
  document.getElementById("merchantId").value = "casino_xyz";
  pay("casino_xyz");
}

function renderPaymentResult(payment, verification, merchant, amount) {
  const proofs = payment.proofs;
  const isCompiled = Object.values(proofs).some(p => p.status === "success");

  let html = "";

  // Overall result banner
  const accepted = verification.accepted;
  html += `
    <div class="proof-card ${accepted ? "pass" : "fail"}">
      <div class="proof-title">
        <span class="proof-name">${accepted ? "✓ Payment Accepted" : "✗ Payment Rejected"}</span>
        <span class="proof-badge ${accepted ? "badge-pass" : "badge-fail"}">
          ${accepted ? "ALL PROOFS VALID" : "PROOF FAILED"}
        </span>
      </div>
      <div class="proof-claim">Merchant: ${merchant} | Amount: $${amount}</div>
      <div class="proof-data">
        Wallet ID: ${payment.wallet_id}<br>
        Ed25519 Signature: ${accepted ? "✓ Valid" : "✗ Invalid"}<br>
        Remaining balance: $${payment.balance_remaining?.toFixed(2) ?? "N/A"}
      </div>
    </div>`;

  // Each ZK proof
  const proofMeta = {
    age_proof:      { label: "Age ≥ 18 Proof",       icon: "🔒", circuit: "AgeCheck.circom" },
    balance_proof:  { label: "Sufficient Balance Proof", icon: "💰", circuit: "BalanceCheck.circom" },
    kyc_proof:      { label: "KYC Verified Proof",    icon: "🪪", circuit: "KYCCheck.circom" },
    merchant_proof: { label: "Merchant Allowed Proof", icon: "🏪", circuit: "Policy Check" },
  };

  for (const [key, proof] of Object.entries(proofs)) {
    const meta = proofMeta[key] || { label: key, icon: "⬡", circuit: "" };
    const vp = verification.proof_results?.[key];
    const passed = vp?.passed ?? proof.result ?? false;
    const status = proof.status;
    const cls = passed ? "pass" : "fail";
    const badgeCls = passed ? "badge-pass" : "badge-fail";

    let detailHtml = `Circuit: ${meta.circuit}<br>Claim: ${proof.claim}<br>`;

    if (status === "success") {
      detailHtml += `Mode: <span style="color:var(--green)">REAL Groth16 zk-SNARK ✓</span><br>`;
      detailHtml += `Public signals: ${JSON.stringify(proof.public_signals)}<br>`;
      if (proof.proof) {
        detailHtml += `π_a: ${truncate(JSON.stringify(proof.proof.pi_a), 40)}<br>`;
        detailHtml += `π_b: ${truncate(JSON.stringify(proof.proof.pi_b), 40)}<br>`;
      }
    } else if (status === "not_compiled") {
      detailHtml += `Mode: <span style="color:var(--yellow)">Circuits not compiled yet (run setup.sh)</span><br>`;
      detailHtml += `Result: ${passed ? "✓ Would pass" : "✗ Would fail"}<br>`;
    } else {
      detailHtml += `Result: ${passed ? "✓ Pass" : "✗ Fail"}`;
    }

    if (proof.merchant_hash) detailHtml += `<br>Merchant hash: ${truncate(proof.merchant_hash, 32)}`;
    if (proof.expected_hash) detailHtml += `<br>Expected commitment: ${truncate(proof.expected_hash, 32)}`;

    html += `
      <div class="proof-card ${cls}">
        <div class="proof-title">
          <span class="proof-name">${meta.icon} ${meta.label}</span>
          <span class="proof-badge ${badgeCls}">${passed ? "PASS" : "FAIL"}</span>
        </div>
        <div class="proof-claim">${proof.claim}</div>
        <div class="proof-data">${detailHtml}</div>
      </div>`;
  }

  // Signature block
  html += `
    <div class="sig-block">
      <h5>Ed25519 Transaction Signature</h5>
      <div class="sig-val">${payment.signature}</div>
    </div>`;

  document.getElementById("visualOutput").innerHTML = html;
}

function renderProofChain(proofs, verification) {
  const chain = document.getElementById("proofChain");
  const steps = document.getElementById("chainSteps");
  chain.classList.remove("hidden");

  const items = [
    { label: "KYC", key: "kyc_proof" },
    { label: "Age ≥ 18", key: "age_proof" },
    { label: "Balance ≥ Amt", key: "balance_proof" },
    { label: "Merchant OK", key: "merchant_proof" },
    { label: "Signature", special: verification.signature_valid },
    { label: verification.accepted ? "ACCEPTED" : "REJECTED", final: true, accepted: verification.accepted }
  ];

  steps.innerHTML = items.map((item, i) => {
    let cls, label;
    if (item.final) {
      cls = item.accepted ? "pass" : "fail";
      label = item.label;
    } else if (item.special !== undefined) {
      cls = item.special ? "pass" : "fail";
      label = item.label;
    } else {
      const proof = proofs[item.key];
      const passed = verification.proof_results?.[item.key]?.passed ?? proof?.result ?? false;
      cls = passed ? "pass" : "fail";
      label = item.label;
    }

    return `
      <div class="chain-step">
        <div class="chain-node ${cls}">${label}</div>
        ${i < items.length - 1 ? '<span class="chain-arrow">→</span>' : ""}
      </div>`;
  }).join("");
}

// ── Step 3: Audit ────────────────────────────────────────────────────────────

async function requestAudit() {
  showLoading("Generating audit report...");
  setTitle("Audit Report (Aggregate Only)");
  document.getElementById("proofChain").classList.add("hidden");

  try {
    const res = await fetch(`${API}/audit`);
    const data = await res.json();
    updateRawJson(data);
    toast("Audit report generated.", "info");
    setTitle("Audit Report — Regulators Only");
    renderAuditResult(data);
  } catch (e) {
    toast("Error: " + e.message, "error");
  }
}

function renderAuditResult(data) {
  document.getElementById("visualOutput").innerHTML = `
    <div class="audit-block">
      <h4>⚖ REGULATOR AUDIT REPORT</h4>
      <div class="audit-stat">
        <span class="stat-label">Wallet ID</span>
        <span class="stat-val">${data.wallet_id}</span>
      </div>
      <div class="audit-stat">
        <span class="stat-label">Transaction Count</span>
        <span class="stat-val">${data.transaction_count}</span>
      </div>
      <div class="audit-stat">
        <span class="stat-label">Total Spent</span>
        <span class="stat-val">$${data.total_spent}</span>
      </div>
      <div class="audit-stat">
        <span class="stat-label">Max Single Transaction</span>
        <span class="stat-val">$${data.max_single_transaction}</span>
      </div>
      <div class="audit-stat">
        <span class="stat-label">All Under $10,000 Limit</span>
        <span class="stat-val ${data.all_under_10000 ? 'green' : ''}">${data.all_under_10000 ? '✓ YES' : '✗ NO'}</span>
      </div>
      <div class="audit-stat">
        <span class="stat-label">Wallet Signature Valid</span>
        <span class="stat-val ${data.signature_valid ? 'green' : ''}">${data.signature_valid ? '✓ YES' : '✗ NO'}</span>
      </div>
      <div class="privacy-note">
        ⚠ Per-transaction merchant IDs and exact history NOT disclosed.<br>
        Aggregates only — per design of the selective-disclosure protocol.
      </div>
    </div>

    <div class="sig-block">
      <h5>Wallet Ed25519 Signature (Non-Repudiation)</h5>
      <div class="sig-val">${data.wallet_signature}</div>
    </div>`;
}

// ── Reset ────────────────────────────────────────────────────────────────────

async function resetWallet() {
  await fetch(`${API}/reset`, { method: "POST" });
  setStatus(false);
  document.getElementById("payCard").setAttribute("data-locked", "true");
  document.getElementById("auditCard").setAttribute("data-locked", "true");
  document.getElementById("proofChain").classList.add("hidden");
  document.getElementById("visualOutput").innerHTML = `
    <div class="empty-state">
      <div class="empty-icon">⬡</div>
      <p>Wallet reset. Run setup to start again.</p>
    </div>`;
  setTitle("Awaiting operation...");
  toast("Wallet reset.", "info");
}

// ── Init ─────────────────────────────────────────────────────────────────────

(async () => {
  try {
    const res = await fetch(`${API}/status`);
    const data = await res.json();
    if (data.initialized) {
      setStatus(true);
      unlockCard("payCard");
      unlockCard("auditCard");
    }
  } catch {}
})();
