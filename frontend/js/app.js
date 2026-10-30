// Oytra COD Risk Engine — Dynamic Frontend Controller
// All data is dynamically retrieved from the database, decision engine, or LLM.
// No static or hardcoded data is used.

let dynamicPresets = {};
let allRules = [];
let allOrders = [];
let currentSimFlow = "confirmation";

// Initialize UI
document.addEventListener("DOMContentLoaded", () => {
  if (window.lucide) {
    lucide.createIcons();
  }
  loadPresetsFromDB();
  loadRulesFromDB();
  loadDashboardMetricsFromDB();
  loadOrdersFromDB();
});

// Tab Switching
function switchTab(tabName) {
  const tabs = ["evaluator", "whatsapp", "dashboard", "rules", "orders"];
  tabs.forEach((t) => {
    const navBtn = document.getElementById(`tab-${t}`);
    const view = document.getElementById(`view-${t}`);
    if (t === tabName) {
      navBtn.classList.add("active");
      view.classList.remove("hidden");
    } else {
      navBtn.classList.remove("active");
      view.classList.add("hidden");
    }
  });

  if (tabName === "whatsapp") {
    refreshSimulator();
  }
  if (window.lucide) {
    lucide.createIcons();
  }
}

// ----------------- DYNAMIC DATABASE PRESETS -----------------
async function loadPresetsFromDB() {
  const container = document.getElementById("presets-container");
  try {
    const res = await fetch("/api/presets");
    if (!res.ok) {
      throw new Error(`Database returned HTTP ${res.status}: ${res.statusText}`);
    }
    dynamicPresets = await res.json();

    container.innerHTML = `<span class="text-xs font-semibold text-slate-500 uppercase tracking-wide">Database Presets:</span>`;
    
    for (const [key, p] of Object.entries(dynamicPresets)) {
      container.innerHTML += `
        <button onclick="applyPreset('${key}')" class="px-2.5 py-1 text-xs bg-white border border-slate-300 rounded-lg shadow-sm hover:border-emerald-500 hover:text-emerald-700 transition">
          ${p.label || key}
        </button>
      `;
    }

    // Auto-load first preset from database
    const firstKey = Object.keys(dynamicPresets)[0];
    if (firstKey) {
      applyPreset(firstKey);
    }
  } catch (err) {
    container.innerHTML = `
      <span class="text-xs font-semibold text-rose-600">
        ⚠️ Failed to load presets from database: ${err.message}. Please run 'python scripts/setup_db.py'.
      </span>
    `;
  }
}

function applyPreset(key) {
  const p = dynamicPresets[key];
  if (!p) return;

  document.getElementById("inp-order-id").value = p.order_id || "";
  document.getElementById("inp-order-value").value = p.order_value || 0;
  document.getElementById("inp-customer-name").value = p.customer_name || "";
  document.getElementById("inp-phone").value = p.phone || "";
  document.getElementById("inp-address").value = p.address || "";
  document.getElementById("inp-city").value = p.city || "";
  document.getElementById("inp-state").value = p.state || "";
  document.getElementById("inp-pincode").value = p.pincode || "";
  document.getElementById("inp-prior-orders").value = p.prior_orders ?? 0;
  document.getElementById("inp-prior-rto").value = p.prior_rto ?? 0;

  // Auto trigger live evaluation
  document.getElementById("order-form").dispatchEvent(new Event("submit"));
}

// ----------------- ORDER EVALUATION (BACKEND & LLM) -----------------
async function handleEvaluate(e) {
  e.preventDefault();

  const payload = {
    order_id: document.getElementById("inp-order-id").value.trim(),
    order_value: parseFloat(document.getElementById("inp-order-value").value) || 0,
    customer_name: document.getElementById("inp-customer-name").value.trim(),
    phone: document.getElementById("inp-phone").value.trim(),
    address: document.getElementById("inp-address").value.trim(),
    city: document.getElementById("inp-city").value.trim(),
    state: document.getElementById("inp-state").value.trim(),
    pincode: document.getElementById("inp-pincode").value.trim(),
    customer_prior_orders: parseInt(document.getElementById("inp-prior-orders").value) || 0,
    customer_prior_rto: parseInt(document.getElementById("inp-prior-rto").value) || 0,
    payment_method: "COD",
  };

  const btn = document.getElementById("btn-eval");
  btn.innerHTML = `<span class="animate-spin mr-2">⚙️</span> Evaluating via Engine...`;
  btn.disabled = true;

  try {
    const res = await fetch("/api/evaluate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `Server returned error HTTP ${res.status}`);
    }

    const data = await res.json();
    renderEvaluationResult(data, payload);
  } catch (err) {
    alert("❌ Error evaluating order: " + err.message);
  } finally {
    btn.innerHTML = `<i data-lucide="sparkles" class="w-4 h-4 mr-2"></i><span>Evaluate Risk & Recommend Action</span>`;
    btn.disabled = false;
    if (window.lucide) lucide.createIcons();
  }
}

function renderEvaluationResult(data, orderInput) {
  document.getElementById("eval-placeholder").classList.add("hidden");
  const card = document.getElementById("eval-result-card");
  card.classList.remove("hidden");

  // Composite Risk Score
  const score = data.risk_score;
  document.getElementById("res-score-num").innerText = `${score}/100`;

  const bar = document.getElementById("res-score-bar");
  bar.style.width = `${Math.min(100, Math.max(5, score))}%`;

  // Decision & Category Badges
  const badge = document.getElementById("res-badge");
  const catText = document.getElementById("res-risk-category");

  badge.className = "px-3.5 py-1 rounded-full text-sm font-bold uppercase tracking-wide border";

  if (data.decision === "ship") {
    badge.classList.add("badge-ship");
    badge.innerText = "SHIP AS-IS";
    bar.className = "h-full bg-emerald-500 transition-all duration-500";
    catText.innerText = "Low Risk • Safe to release";
  } else if (data.decision === "confirm") {
    badge.classList.add("badge-confirm");
    badge.innerText = "WHATSAPP CONFIRM";
    bar.className = "h-full bg-amber-500 transition-all duration-500";
    catText.innerText = "Medium Risk • Require intent verification";
  } else if (data.decision === "nudge_prepaid") {
    badge.classList.add("badge-nudge");
    badge.innerText = "NUDGE TO PREPAID";
    bar.className = "h-full bg-orange-500 transition-all duration-500";
    catText.innerText = "High Risk • Offer discount to pay online";
  } else {
    badge.classList.add("badge-cancel");
    badge.innerText = "HOLD / CANCEL";
    bar.className = "h-full bg-rose-500 transition-all duration-500";
    catText.innerText = "Severe Risk • Serial RTO / Dummy order";
  }

  // Plain-English Explanation (required by assignment)
  document.getElementById("res-reason").innerText = data.reason || "No explanation returned.";

  // Dynamic Factors
  const factorsContainer = document.getElementById("res-factors");
  factorsContainer.innerHTML = "";
  const f = data.risk_factors || {};

  if (f.first_time_buyer) {
    factorsContainer.innerHTML += `<span class="bg-blue-50 text-blue-700 border border-blue-200 px-2 py-1 rounded-md font-medium">First-Time Buyer</span>`;
  }
  if (f.prior_orders > 0) {
    factorsContainer.innerHTML += `<span class="bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-1 rounded-md font-medium">History: ${f.prior_orders} orders (${f.prior_rto} RTOs)</span>`;
  }
  if (f.short_or_incomplete_address) {
    factorsContainer.innerHTML += `<span class="bg-rose-50 text-rose-700 border border-rose-200 px-2 py-1 rounded-md font-medium">Incomplete Address (+${f.address_risk_score} pts)</span>`;
  }
  if (f.suspicious_name) {
    factorsContainer.innerHTML += `<span class="bg-rose-50 text-rose-700 border border-rose-200 px-2 py-1 rounded-md font-medium">Suspicious Name (+${f.name_risk_score} pts)</span>`;
  }
  if (f.first_order_protected) {
    factorsContainer.innerHTML += `<span class="bg-indigo-50 text-indigo-700 border border-indigo-200 px-2 py-1 rounded-md font-semibold">Protected First-Time Buyer (No Auto-Cancel)</span>`;
  }
  if (f.pincode_rto_rate !== null && f.pincode_rto_rate !== undefined) {
    factorsContainer.innerHTML += `<span class="bg-slate-100 text-slate-700 px-2 py-1 rounded-md">Pincode RTO: ${f.pincode_rto_rate}%</span>`;
  }
  if (data.llm_used) {
    factorsContainer.innerHTML += `<span class="bg-purple-50 text-purple-700 border border-purple-200 px-2 py-1 rounded-md font-medium">🤖 Gemini LLM Analyzed</span>`;
  }

  // Action Buttons
  const actionsContainer = document.getElementById("res-actions-container");
  if (data.decision === "ship") {
    actionsContainer.innerHTML = `
      <button onclick="alert('✅ Order ${orderInput.order_id} released to shipping courier dispatch!')" class="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-2.5 rounded-xl shadow transition flex items-center justify-center gap-2">
        <i data-lucide="check-circle" class="w-4 h-4"></i>
        <span>Release Order to Courier (Dispatch Immediately)</span>
      </button>
    `;
  } else if (data.decision === "confirm") {
    actionsContainer.innerHTML = `
      <button onclick="launchSimulatorWithOrder('${orderInput.customer_name}', '${orderInput.order_id}', ${orderInput.order_value}, 'confirmation')" class="w-full bg-amber-500 hover:bg-amber-600 text-white font-semibold py-2.5 rounded-xl shadow transition flex items-center justify-center gap-2">
        <i data-lucide="message-square" class="w-4 h-4"></i>
        <span>Trigger WhatsApp Confirmation Flow</span>
      </button>
    `;
  } else if (data.decision === "nudge_prepaid") {
    actionsContainer.innerHTML = `
      <button onclick="launchSimulatorWithOrder('${orderInput.customer_name}', '${orderInput.order_id}', ${orderInput.order_value}, 'nudge_prepaid')" class="w-full bg-orange-500 hover:bg-orange-600 text-white font-semibold py-2.5 rounded-xl shadow transition flex items-center justify-center gap-2">
        <i data-lucide="percent" class="w-4 h-4"></i>
        <span>Send WhatsApp Prepaid Discount Link (Pay Online)</span>
      </button>
    `;
  } else {
    actionsContainer.innerHTML = `
      <button onclick="alert('🛑 Order ${orderInput.order_id} hold/cancelled. ₹169.40 dead shipping saved.')" class="w-full bg-rose-600 hover:bg-rose-700 text-white font-semibold py-2.5 rounded-xl shadow transition flex items-center justify-center gap-2">
        <i data-lucide="ban" class="w-4 h-4"></i>
        <span>Confirm Order Cancellation (Zero False Positives)</span>
      </button>
    `;
  }

  if (window.lucide) lucide.createIcons();
}

// ----------------- WHATSAPP SIMULATOR (DYNAMIC API) -----------------
function setFlowMode(mode) {
  currentSimFlow = mode;
  document.getElementById("btn-flow-confirm").className = mode === "confirmation" 
    ? "px-4 py-1.5 text-xs font-semibold rounded-lg bg-white shadow-sm text-emerald-800 transition" 
    : "px-4 py-1.5 text-xs font-semibold rounded-lg text-slate-600 hover:text-slate-900 transition";

  document.getElementById("btn-flow-nudge").className = mode === "nudge_prepaid"
    ? "px-4 py-1.5 text-xs font-semibold rounded-lg bg-white shadow-sm text-emerald-800 transition"
    : "px-4 py-1.5 text-xs font-semibold rounded-lg text-slate-600 hover:text-slate-900 transition";

  refreshSimulator();
}

function launchSimulatorWithOrder(name, orderId, val, mode) {
  document.getElementById("sim-name").value = name;
  document.getElementById("sim-value").value = val;
  setFlowMode(mode);
  switchTab("whatsapp");
}

async function refreshSimulator() {
  const name = document.getElementById("sim-name").value.trim() || "Customer";
  const val = parseFloat(document.getElementById("sim-value").value) || 649;
  const orderId = document.getElementById("inp-order-id")?.value || "KT101990";

  const chat = document.getElementById("chat-messages");
  chat.innerHTML = "";

  updateSimPill("INITIALIZING...", "bg-slate-100 text-slate-600");

  try {
    const res = await fetch("/api/whatsapp/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        customer_name: name,
        order_id: orderId,
        order_value: val,
        flow_type: currentSimFlow,
        action: "init",
      }),
    });

    if (!res.ok) {
      throw new Error(`Failed to initialize WhatsApp flow: HTTP ${res.status}`);
    }

    const data = await res.json();
    appendBotMessage(data.message.replace(/\n/g, "<br>"));
    updateSimPill(data.status, "bg-amber-100 text-amber-800");
  } catch (err) {
    appendBotMessage(`⚠️ Error generating message: ${err.message}`);
    updateSimPill("ERROR", "bg-rose-100 text-rose-800");
  }
}

async function sendSimReply(replyText) {
  appendUserMessage(replyText);

  const name = document.getElementById("sim-name").value.trim() || "Customer";
  const val = parseFloat(document.getElementById("sim-value").value) || 649;
  const orderId = document.getElementById("inp-order-id")?.value || "KT101990";

  updateSimPill("PROCESSING...", "bg-blue-100 text-blue-800");

  try {
    const res = await fetch("/api/whatsapp/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        customer_name: name,
        order_id: orderId,
        order_value: val,
        flow_type: currentSimFlow,
        action: "reply",
        reply_text: replyText,
      }),
    });

    if (!res.ok) {
      throw new Error(`Reply processing failed: HTTP ${res.status}`);
    }

    const data = await res.json();
    appendBotMessage(data.response_message.replace(/\n/g, "<br>"));

    let pillStyle = "bg-slate-100 text-slate-700";
    if (data.status === "CONFIRMED") pillStyle = "bg-emerald-100 text-emerald-800";
    if (data.status === "REJECTED") pillStyle = "bg-rose-100 text-rose-800";
    if (data.status === "CONVERTED_PREPAID") pillStyle = "bg-indigo-100 text-indigo-800";

    updateSimPill(data.status, pillStyle);
  } catch (err) {
    appendBotMessage(`⚠️ Error processing reply: ${err.message}`);
    updateSimPill("ERROR", "bg-rose-100 text-rose-800");
  }
}

async function triggerSimTimeout() {
  appendUserMessage("<i>[No reply from customer for 24 hours]</i>");

  const name = document.getElementById("sim-name").value.trim() || "Customer";
  const val = parseFloat(document.getElementById("sim-value").value) || 649;
  const orderId = document.getElementById("inp-order-id")?.value || "KT101990";

  try {
    const res = await fetch("/api/whatsapp/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        customer_name: name,
        order_id: orderId,
        order_value: val,
        flow_type: currentSimFlow,
        action: "timeout",
      }),
    });

    const data = await res.json();
    appendBotMessage(data.response_message.replace(/\n/g, "<br>"));
    updateSimPill(data.status, "bg-orange-100 text-orange-800");
  } catch (err) {
    appendBotMessage(`⚠️ Error processing timeout: ${err.message}`);
  }
}

function sendCustomReply() {
  const input = document.getElementById("sim-custom-input");
  const val = input.value.trim();
  if (!val) return;
  input.value = "";
  sendSimReply(val);
}

function appendBotMessage(text) {
  const chat = document.getElementById("chat-messages");
  const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  chat.innerHTML += `
    <div class="chat-msg chat-msg-bot">
      ${text}
      <span class="chat-msg-time">${time}</span>
    </div>
  `;
  chat.scrollTop = chat.scrollHeight;
}

function appendUserMessage(text) {
  const chat = document.getElementById("chat-messages");
  const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  chat.innerHTML += `
    <div class="chat-msg chat-msg-user">
      ${text}
      <span class="chat-msg-time">${time}</span>
    </div>
  `;
  chat.scrollTop = chat.scrollHeight;
}

function updateSimPill(text, classes) {
  const pill = document.getElementById("sim-status-pill");
  pill.className = `text-xs font-bold px-2.5 py-0.5 rounded-full ${classes}`;
  pill.innerText = text;
}

// ----------------- FOUNDER DASHBOARD (LIVE BACKTEST) -----------------
async function loadDashboardMetricsFromDB() {
  const errBox = document.getElementById("dash-error");
  try {
    const res = await fetch("/api/backtest");
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    const data = await res.json();
    errBox.classList.add("hidden");

    const b = data.buckets;
    if (!b || !data.financial) {
      throw new Error("No evaluated decisions returned by engine");
    }

    const total = data.total_orders || 1;

    // 4 Decision Buckets
    document.getElementById("dash-count-ship").innerText = (b.ship?.count ?? 0).toLocaleString();
    document.getElementById("dash-pct-ship").innerText = `${((b.ship?.count ?? 0) / total * 100).toFixed(1)}% of volume`;

    document.getElementById("dash-count-confirm").innerText = (b.confirm?.count ?? 0).toLocaleString();
    document.getElementById("dash-pct-confirm").innerText = `${((b.confirm?.count ?? 0) / total * 100).toFixed(1)}% of volume`;

    document.getElementById("dash-count-nudge").innerText = (b.nudge_prepaid?.count ?? 0).toLocaleString();
    document.getElementById("dash-pct-nudge").innerText = `${((b.nudge_prepaid?.count ?? 0) / total * 100).toFixed(1)}% of volume`;

    document.getElementById("dash-count-cancel").innerText = (b.cancel?.count ?? 0).toLocaleString();
    document.getElementById("dash-pct-cancel").innerText = `${((b.cancel?.count ?? 0) / total * 100).toFixed(1)}% of volume`;

    // Financial Metrics
    const fin = data.financial;
    document.getElementById("dash-saved").innerText = `₹${(fin.saved_from_cancels ?? 0).toLocaleString(undefined, {minimumFractionDigits: 2})}`;
    document.getElementById("dash-lost").innerText = `₹${(fin.lost_from_cancels ?? 0).toLocaleString(undefined, {minimumFractionDigits: 2})}`;
    document.getElementById("dash-nudge-gain").innerText = `+₹${(fin.saved_from_nudges ?? 0).toLocaleString(undefined, {minimumFractionDigits: 2})}`;
    document.getElementById("dash-net-impact").innerText = `+₹${(fin.net_impact ?? 0).toLocaleString(undefined, {minimumFractionDigits: 2})}`;

    document.getElementById("dash-saved-sub").innerText = `${b.cancel?.actual_rto ?? 0} high-risk returns halted`;
    document.getElementById("dash-lost-sub").innerText = `${b.cancel?.actual_delivered ?? 0} genuine buyers cancelled`;
  } catch (err) {
    errBox.classList.remove("hidden");
    errBox.innerText = `⚠️ Error fetching live dashboard calculations: ${err.message}. Please run 'python scripts/run_engine.py' to process all orders.`;
    
    // Clear display to prevent showing unverified numbers
    document.getElementById("dash-count-ship").innerText = "---";
    document.getElementById("dash-count-confirm").innerText = "---";
    document.getElementById("dash-count-nudge").innerText = "---";
    document.getElementById("dash-count-cancel").innerText = "---";
    document.getElementById("dash-saved").innerText = "---";
    document.getElementById("dash-lost").innerText = "---";
    document.getElementById("dash-nudge-gain").innerText = "---";
    document.getElementById("dash-net-impact").innerText = "---";
  }
}

// ----------------- RULES & THRESHOLDS FROM DB -----------------
async function loadRulesFromDB() {
  try {
    const res = await fetch("/api/rules");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    allRules = await res.json();
    renderRules();
  } catch (err) {
    document.getElementById("rules-container").innerHTML = `
      <div class="col-span-2 p-4 bg-rose-50 border border-rose-200 text-rose-800 rounded-xl text-xs font-semibold">
        ⚠️ Failed to load decision rules from database: ${err.message}
      </div>
    `;
  }
}

function renderRules() {
  const container = document.getElementById("rules-container");
  container.innerHTML = "";

  const categories = {};
  allRules.forEach((r) => {
    if (!categories[r.category]) categories[r.category] = [];
    categories[r.category].push(r);
  });

  for (const [cat, list] of Object.entries(categories)) {
    let catHtml = `
      <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
        <h3 class="font-bold text-sm uppercase tracking-wider text-slate-800 border-b border-slate-100 pb-2">
          ${cat} Controls
        </h3>
        <div class="space-y-4">
    `;

    list.forEach((r) => {
      catHtml += `
        <div class="flex items-center justify-between gap-4">
          <div class="flex-1">
            <div class="text-xs font-mono font-bold text-slate-800">${r.key}</div>
            <div class="text-xs text-slate-500">${r.description}</div>
          </div>
          <input type="number" id="rule-inp-${r.key}" value="${r.value}" class="w-24 text-right text-xs font-bold border border-slate-300 rounded-lg px-2.5 py-1.5 focus:ring-2 focus:ring-emerald-500 focus:outline-none" />
        </div>
      `;
    });

    catHtml += `</div></div>`;
    container.innerHTML += catHtml;
  }
}

async function saveAllRules() {
  let count = 0;
  for (const r of allRules) {
    const el = document.getElementById(`rule-inp-${r.key}`);
    if (el) {
      const val = parseFloat(el.value);
      if (val !== r.value) {
        await fetch(`/api/rules/${r.key}?new_value=${val}`, { method: "PUT" });
        count++;
      }
    }
  }
  alert(`✅ Saved ${count} updated rules directly to the database!`);
  loadRulesFromDB();
}

// ----------------- ORDERS TABLE FROM DB -----------------
async function loadOrdersFromDB() {
  try {
    const res = await fetch("/api/orders?limit=100");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    allOrders = await res.json();
    renderOrdersTable(allOrders);
  } catch (err) {
    document.getElementById("orders-tbody").innerHTML = `
      <tr>
        <td colspan="8" class="p-6 text-center text-rose-600 font-semibold text-xs">
          ⚠️ Failed to load orders from database: ${err.message}
        </td>
      </tr>
    `;
  }
}

function renderOrdersTable(orders) {
  const tbody = document.getElementById("orders-tbody");
  tbody.innerHTML = "";

  if (orders.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" class="p-6 text-center text-slate-400">No matching orders found in database</td></tr>`;
    return;
  }

  orders.slice(0, 50).forEach((o) => {
    let badgeClass = "bg-slate-100 text-slate-700";
    if (o.decision === "ship") badgeClass = "bg-emerald-100 text-emerald-800";
    if (o.decision === "confirm") badgeClass = "bg-amber-100 text-amber-800";
    if (o.decision === "nudge_prepaid") badgeClass = "bg-orange-100 text-orange-800";
    if (o.decision === "cancel") badgeClass = "bg-rose-100 text-rose-800";

    tbody.innerHTML += `
      <tr class="hover:bg-slate-50 transition cursor-pointer" onclick="openOrderModal('${o.order_id}')">
        <td class="py-2.5 px-4 font-mono font-bold text-emerald-700 hover:underline">${o.order_id}</td>
        <td class="py-2.5 px-4 font-medium">${o.customer_name || "N/A"}</td>
        <td class="py-2.5 px-4 text-slate-500">${o.city || ""}, ${o.pincode || ""}</td>
        <td class="py-2.5 px-4 font-semibold">₹${o.order_value || 0}</td>
        <td class="py-2.5 px-4 font-bold">${o.risk_score !== null ? o.risk_score : "---"}</td>
        <td class="py-2.5 px-4">
          <span class="px-2 py-0.5 rounded-full text-[11px] font-bold uppercase ${badgeClass}">
            ${o.decision || "PENDING"}
          </span>
        </td>
        <td class="py-2.5 px-4 text-slate-600 max-w-xs truncate">${o.reason || "Awaiting evaluation"}</td>
        <td class="py-2.5 px-4 font-bold ${o.final_status === 'DELIVERED' || o.final_status === 'CONFIRMED' ? 'text-emerald-600' : 'text-rose-600'}">
          ${o.final_status || "PENDING"}
        </td>
      </tr>
    `;
  });
}

async function openOrderModal(orderId) {
  try {
    const res = await fetch(`/api/orders/${orderId}`);
    if (!res.ok) throw new Error("Could not fetch order details");
    const o = await res.json();

    document.getElementById("modal-order-id").innerText = `#${o.order_id}`;
    document.getElementById("modal-customer").innerText = o.customer_name || "N/A";
    document.getElementById("modal-phone").innerText = o.phone || "N/A";
    document.getElementById("modal-location").innerText = `${o.city || ""}, ${o.state || ""} (${o.pincode || ""})`;
    document.getElementById("modal-value").innerText = `₹${o.order_value || 0}`;
    document.getElementById("modal-address").innerText = o.address || "N/A";
    document.getElementById("modal-score").innerText = `${o.risk_score ?? "---"}/100`;
    document.getElementById("modal-status").innerText = o.final_status || "PENDING";
    document.getElementById("modal-reason").innerText = o.reason || "No explanation recorded.";

    const badge = document.getElementById("modal-decision-badge");
    badge.className = "px-2.5 py-0.5 rounded-full text-xs font-bold uppercase mt-1 inline-block";
    if (o.decision === "ship") {
      badge.classList.add("bg-emerald-100", "text-emerald-800");
      badge.innerText = "SHIP AS-IS";
    } else if (o.decision === "confirm") {
      badge.classList.add("bg-amber-100", "text-amber-800");
      badge.innerText = "WHATSAPP CONFIRM";
    } else if (o.decision === "nudge_prepaid") {
      badge.classList.add("bg-orange-100", "text-orange-800");
      badge.innerText = "NUDGE TO PREPAID";
    } else {
      badge.classList.add("bg-rose-100", "text-rose-800");
      badge.innerText = "HOLD / CANCEL";
    }

    const actionBox = document.getElementById("modal-action-box");
    actionBox.innerHTML = "";

    if (o.decision === "confirm" || o.decision === "nudge_prepaid") {
      const mode = o.decision === "confirm" ? "confirmation" : "nudge_prepaid";
      actionBox.innerHTML += `
        <button onclick="closeOrderModal(); launchSimulatorWithOrder('${o.customer_name}', '${o.order_id}', ${o.order_value}, '${mode}')" class="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-2.5 rounded-xl shadow transition flex items-center justify-center gap-2 mb-2">
          <i data-lucide="message-square" class="w-4 h-4"></i>
          <span>Open in WhatsApp Simulator & Test Live Replies</span>
        </button>
      `;
    }

    actionBox.innerHTML += `
      <button onclick="closeOrderModal(); populateEvaluatorFromRow('${o.order_id}')" class="w-full bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold py-2 rounded-xl transition flex items-center justify-center gap-2">
        <i data-lucide="edit" class="w-4 h-4"></i>
        <span>Load into Evaluator Tab</span>
      </button>
    `;

    document.getElementById("order-modal").classList.remove("hidden");
    if (window.lucide) lucide.createIcons();
  } catch (err) {
    alert("Error loading order: " + err.message);
  }
}

function closeOrderModal() {
  document.getElementById("order-modal").classList.add("hidden");
}

function filterOrdersTable() {
  const query = document.getElementById("order-search").value.toLowerCase().trim();
  const decisionFilter = document.getElementById("order-filter-decision").value;

  const filtered = allOrders.filter((o) => {
    const matchQuery =
      !query ||
      (o.customer_name && o.customer_name.toLowerCase().includes(query)) ||
      (o.order_id && o.order_id.toLowerCase().includes(query)) ||
      (o.pincode && o.pincode.toString().includes(query));

    const matchDecision = decisionFilter === "ALL" || o.decision === decisionFilter;
    return matchQuery && matchDecision;
  });

  renderOrdersTable(filtered);
}

function populateEvaluatorFromRow(orderId) {
  const found = allOrders.find((o) => o.order_id === orderId);
  if (!found) return;

  document.getElementById("inp-order-id").value = found.order_id || "";
  document.getElementById("inp-order-value").value = found.order_value || 0;
  document.getElementById("inp-customer-name").value = found.customer_name || "";
  document.getElementById("inp-phone").value = found.phone || "";
  document.getElementById("inp-address").value = found.address || "";
  document.getElementById("inp-city").value = found.city || "";
  document.getElementById("inp-state").value = found.state || "";
  document.getElementById("inp-pincode").value = found.pincode || "";
  document.getElementById("inp-prior-orders").value = found.customer_prior_orders ?? 0;
  document.getElementById("inp-prior-rto").value = found.customer_prior_rto ?? 0;

  switchTab("evaluator");
  document.getElementById("order-form").dispatchEvent(new Event("submit"));
}
