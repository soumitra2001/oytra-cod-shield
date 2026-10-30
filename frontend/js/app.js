// Oytra COD Risk Engine — Dynamic Frontend Controller
// All data is dynamically retrieved from the database, decision engine, or LLM.
// No static or demo records are shown.

let allRules = [];
let allOrders = [];
let createdOrders = [];
let currentModalOrder = null;
let currentModalFlow = "confirmation";

// Initialize UI
document.addEventListener("DOMContentLoaded", () => {
  if (window.lucide) {
    lucide.createIcons();
  }
  regenerateOrderId();
  loadRulesFromDB();
  loadDashboardMetricsFromDB();
  loadOrdersFromDB();
  loadCreatedOrdersFromDB();
});

function regenerateOrderId() {
  const randNum = Math.floor(102000 + Math.random() * 90000);
  const inp = document.getElementById("inp-order-id");
  if (inp) {
    inp.value = `KT${randNum}`;
  }
}

// Tab Switching
function switchTab(tabName) {
  const tabs = ["evaluator", "created", "dashboard", "rules", "orders"];
  tabs.forEach((t) => {
    const navBtn = document.getElementById(`tab-${t}`);
    const view = document.getElementById(`view-${t}`);
    if (navBtn && view) {
      if (t === tabName) {
        navBtn.classList.add("active");
        view.classList.remove("hidden");
      } else {
        navBtn.classList.remove("active");
        view.classList.add("hidden");
      }
    }
  });

  if (tabName === "evaluator") {
    if (!document.getElementById("inp-order-id").value) {
      regenerateOrderId();
    }
  }
  if (tabName === "created") {
    loadCreatedOrdersFromDB();
  }
  if (tabName === "dashboard") {
    loadDashboardMetricsFromDB();
  }
  if (window.lucide) {
    lucide.createIcons();
  }
}

// ----------------- ORDER CREATION & EVALUATION -----------------
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
    payment_method: "COD",
  };

  const btn = document.getElementById("btn-eval");
  btn.innerHTML = `<span class="animate-spin mr-2">⚙️</span> Evaluating Risk via Engine...`;
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

    // Reset form inputs & prepare next auto Order ID
    document.getElementById("order-form").reset();
    regenerateOrderId();

    // Refresh created orders table
    await loadCreatedOrdersFromDB();

    // Switch directly to the Created Orders tab
    switchTab("created");

    // Open the order details modal with WhatsApp simulator immediately
    setTimeout(() => {
      openOrderModal(data.order_id);
    }, 200);

  } catch (err) {
    alert("❌ Error evaluating order: " + err.message);
  } finally {
    btn.innerHTML = `<i data-lucide="sparkles" class="w-4 h-4 mr-2"></i><span>Create & Evaluate Order</span>`;
    btn.disabled = false;
    if (window.lucide) lucide.createIcons();
  }
}

// ----------------- CREATED ORDERS TAB -----------------
async function loadCreatedOrdersFromDB() {
  const tbody = document.getElementById("created-orders-tbody");
  if (!tbody) return;

  try {
    const res = await fetch("/api/orders/created");
    if (!res.ok) throw new Error("Could not fetch created orders");
    createdOrders = await res.json();

    const badge = document.getElementById("created-orders-badge");
    if (badge) {
      badge.innerText = createdOrders.length;
    }

    renderCreatedOrdersTable(createdOrders);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="9" class="p-6 text-center text-rose-500 font-semibold">⚠️ Failed to load created orders: ${err.message}</td></tr>`;
  }
}

function renderCreatedOrdersTable(orders) {
  const tbody = document.getElementById("created-orders-tbody");
  if (!tbody) return;
  tbody.innerHTML = "";

  if (orders.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="9" class="p-8 text-center text-slate-400">
          <p class="font-medium text-slate-600">No Orders Created Yet</p>
          <p class="text-xs text-slate-400 mt-1">Go to the <a href="javascript:switchTab('evaluator')" class="text-emerald-600 font-semibold underline">Create Order</a> tab to evaluate and persist orders.</p>
        </td>
      </tr>
    `;
    return;
  }

  orders.forEach((o) => {
    let badgeClass = "bg-slate-100 text-slate-700";
    if (o.decision === "ship") badgeClass = "bg-emerald-100 text-emerald-800";
    if (o.decision === "confirm") badgeClass = "bg-amber-100 text-amber-800";
    if (o.decision === "nudge_prepaid") badgeClass = "bg-orange-100 text-orange-800";
    if (o.decision === "cancel") badgeClass = "bg-rose-100 text-rose-800";

    const hasWhatsApp = o.decision === "confirm" || o.decision === "nudge_prepaid";

    tbody.innerHTML += `
      <tr class="hover:bg-slate-50 transition cursor-pointer" onclick="openOrderModal('${o.order_id}')">
        <td class="py-3 px-4 font-mono font-bold text-emerald-700 hover:underline">#${o.order_id}</td>
        <td class="py-3 px-4 font-semibold text-slate-900">${o.customer_name || "N/A"}</td>
        <td class="py-3 px-4 text-slate-500">${o.city || ""}, ${o.state || ""}</td>
        <td class="py-3 px-4 font-bold text-slate-800">₹${o.order_value || 0}</td>
        <td class="py-3 px-4 font-extrabold text-slate-900">${o.risk_score !== null ? o.risk_score + '/100' : '---'}</td>
        <td class="py-3 px-4">
          <span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase ${badgeClass}">
            ${o.decision ? o.decision.replace('_', ' ') : 'PENDING'}
          </span>
        </td>
        <td class="py-3 px-4 text-slate-600 max-w-xs truncate text-[11px]">${o.reason || "Evaluated by engine"}</td>
        <td class="py-3 px-4">
          <span class="font-bold text-[11px] px-2 py-0.5 rounded-md ${getStatusClass(o.final_status)}">
            ${o.final_status || "PENDING"}
          </span>
        </td>
        <td class="py-3 px-4 text-center" onclick="event.stopPropagation()">
          <button onclick="openOrderModal('${o.order_id}')" class="px-2.5 py-1 text-xs font-semibold ${hasWhatsApp ? 'bg-emerald-600 hover:bg-emerald-700 text-white' : 'bg-slate-100 hover:bg-slate-200 text-slate-700'} rounded-lg transition inline-flex items-center gap-1 shadow-sm">
            ${hasWhatsApp ? '<i data-lucide="message-square" class="w-3 h-3"></i><span>WhatsApp</span>' : '<span>Inspect</span>'}
          </button>
        </td>
      </tr>
    `;
  });

  if (window.lucide) lucide.createIcons();
}

function getStatusClass(status) {
  if (!status) return "bg-slate-100 text-slate-600";
  if (status.includes("CONFIRM") || status.includes("APPROVED") || status.includes("DELIVERED") || status.includes("PREPAID")) {
    return "bg-emerald-50 text-emerald-700 border border-emerald-200";
  }
  if (status.includes("PENDING")) {
    return "bg-amber-50 text-amber-700 border border-amber-200";
  }
  return "bg-rose-50 text-rose-700 border border-rose-200";
}

function filterCreatedOrdersTable() {
  const query = document.getElementById("created-order-search").value.toLowerCase().trim();
  const filtered = createdOrders.filter((o) => {
    return (
      !query ||
      (o.customer_name && o.customer_name.toLowerCase().includes(query)) ||
      (o.order_id && o.order_id.toLowerCase().includes(query)) ||
      (o.city && o.city.toLowerCase().includes(query))
    );
  });
  renderCreatedOrdersTable(filtered);
}

// ----------------- ORDER DETAILS & EMBEDDED WHATSAPP MODAL -----------------
async function openOrderModal(orderId) {
  try {
    const res = await fetch(`/api/orders/${orderId}`);
    if (!res.ok) throw new Error("Could not fetch order details from database");
    const o = await res.json();
    currentModalOrder = o;

    document.getElementById("modal-order-id").innerText = `#${o.order_id}`;
    document.getElementById("modal-order-sub").innerText = `Placed on ${o.order_datetime || "Today"} • Payment: COD`;
    document.getElementById("modal-customer").innerText = o.customer_name || "N/A";
    document.getElementById("modal-phone").innerText = o.phone || "N/A";
    document.getElementById("modal-location").innerText = `${o.city || ""}, ${o.state || ""} (${o.pincode || ""})`;
    document.getElementById("modal-value").innerText = `₹${o.order_value || 0}`;
    document.getElementById("modal-address").innerText = o.address || "N/A";
    document.getElementById("modal-score").innerText = `${o.risk_score ?? "---"}/100`;

    const statusBadge = document.getElementById("modal-status-badge");
    statusBadge.innerText = o.final_status || "PENDING";
    statusBadge.className = `px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${getStatusClass(o.final_status)}`;

    document.getElementById("modal-reason").innerText = o.reason || "No explanation recorded.";

    // Score bar
    const bar = document.getElementById("modal-score-bar");
    const scoreVal = o.risk_score || 0;
    bar.style.width = `${Math.min(100, Math.max(5, scoreVal))}%`;

    // Decision badge
    const badge = document.getElementById("modal-decision-badge");
    badge.className = "px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wide border";
    if (o.decision === "ship") {
      badge.classList.add("bg-emerald-100", "text-emerald-800", "border-emerald-300");
      badge.innerText = "SHIP AS-IS";
      bar.className = "h-full bg-emerald-500";
    } else if (o.decision === "confirm") {
      badge.classList.add("bg-amber-100", "text-amber-800", "border-amber-300");
      badge.innerText = "WHATSAPP CONFIRM";
      bar.className = "h-full bg-amber-500";
    } else if (o.decision === "nudge_prepaid") {
      badge.classList.add("bg-orange-100", "text-orange-800", "border-orange-300");
      badge.innerText = "NUDGE TO PREPAID";
      bar.className = "h-full bg-orange-500";
    } else {
      badge.classList.add("bg-rose-100", "text-rose-800", "border-rose-300");
      badge.innerText = "HOLD / CANCEL";
      bar.className = "h-full bg-rose-500";
    }

    // Factors badges
    const factorsContainer = document.getElementById("modal-factors");
    factorsContainer.innerHTML = "";
    const f = o.risk_factors || {};
    if (f.first_time_buyer) {
      factorsContainer.innerHTML += `<span class="bg-blue-50 text-blue-700 border border-blue-200 px-2 py-0.5 rounded font-medium">First-Time Buyer</span>`;
    }
    if (f.prior_orders > 0) {
      factorsContainer.innerHTML += `<span class="bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded font-medium">History: ${f.prior_orders} orders (${f.prior_rto} RTOs)</span>`;
    }
    if (f.short_or_incomplete_address) {
      factorsContainer.innerHTML += `<span class="bg-rose-50 text-rose-700 border border-rose-200 px-2 py-0.5 rounded font-medium">Incomplete Address (+${f.address_risk_score} pts)</span>`;
    }
    if (f.first_order_protected) {
      factorsContainer.innerHTML += `<span class="bg-indigo-50 text-indigo-700 border border-indigo-200 px-2 py-0.5 rounded font-semibold">Protected First-Time Buyer</span>`;
    }
    if (f.pincode_rto_rate !== null && f.pincode_rto_rate !== undefined) {
      factorsContainer.innerHTML += `<span class="bg-slate-100 text-slate-700 px-2 py-0.5 rounded">Pincode RTO: ${f.pincode_rto_rate}%</span>`;
    }
    if (o.llm_used) {
      factorsContainer.innerHTML += `<span class="bg-purple-50 text-purple-700 border border-purple-200 px-2 py-0.5 rounded font-medium">🤖 LLM Analyzed</span>`;
    }

    // Contextual Right Column Switching
    const waContainer = document.getElementById("modal-whatsapp-container");
    const shipContainer = document.getElementById("modal-ship-container");
    const cancelContainer = document.getElementById("modal-cancel-container");

    if (o.decision === "confirm" || o.decision === "nudge_prepaid") {
      waContainer.classList.remove("hidden");
      shipContainer.classList.add("hidden");
      cancelContainer.classList.add("hidden");

      currentModalFlow = o.decision === "nudge_prepaid" ? "nudge_prepaid" : "confirmation";
      initModalWhatsAppChat(o);
    } else if (o.decision === "ship") {
      waContainer.classList.add("hidden");
      shipContainer.classList.remove("hidden");
      cancelContainer.classList.add("hidden");
    } else {
      waContainer.classList.add("hidden");
      shipContainer.classList.add("hidden");
      cancelContainer.classList.remove("hidden");
    }

    document.getElementById("order-modal").classList.remove("hidden");
    if (window.lucide) lucide.createIcons();
  } catch (err) {
    alert("Error loading order: " + err.message);
  }
}

function closeOrderModal() {
  document.getElementById("order-modal").classList.add("hidden");
  currentModalOrder = null;
}

// ----------------- MODAL WHATSAPP SIMULATOR ENGINE -----------------
async function initModalWhatsAppChat(order) {
  const chat = document.getElementById("modal-chat-messages");
  chat.innerHTML = "";

  const stateBadge = document.getElementById("modal-wa-state-badge");
  stateBadge.innerText = "INITIALIZING...";
  stateBadge.className = "text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600";

  try {
    const res = await fetch("/api/whatsapp/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        customer_name: order.customer_name || "Customer",
        order_id: order.order_id,
        order_value: order.order_value,
        flow_type: currentModalFlow,
        action: "init",
      }),
    });

    if (!res.ok) throw new Error("Could not initialize message");
    const data = await res.json();

    appendModalBotMessage(data.message.replace(/\n/g, "<br>"));
    stateBadge.innerText = data.status || "AWAITING_REPLY";
    stateBadge.className = "text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800";
  } catch (err) {
    appendModalBotMessage(`⚠️ Error: ${err.message}`);
    stateBadge.innerText = "ERROR";
  }
}

async function sendModalSimReply(replyText) {
  if (!currentModalOrder) return;
  appendModalUserMessage(replyText);

  const stateBadge = document.getElementById("modal-wa-state-badge");
  stateBadge.innerText = "PROCESSING...";
  stateBadge.className = "text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-100 text-blue-800";

  try {
    const res = await fetch("/api/whatsapp/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        customer_name: currentModalOrder.customer_name || "Customer",
        order_id: currentModalOrder.order_id,
        order_value: currentModalOrder.order_value,
        flow_type: currentModalFlow,
        action: "reply",
        reply_text: replyText,
      }),
    });

    if (!res.ok) throw new Error("Failed to process reply");
    const data = await res.json();

    appendModalBotMessage(data.response_message.replace(/\n/g, "<br>"));

    let pillStyle = "bg-slate-100 text-slate-700";
    let statusText = data.status;

    if (data.status === "CONFIRMED") {
      pillStyle = "bg-emerald-100 text-emerald-800";
      statusText = "CONFIRMED";
    } else if (data.status === "CUSTOMER_CANCELLED" || data.status === "REJECTED") {
      pillStyle = "bg-rose-100 text-rose-800";
      statusText = "CUSTOMER_CANCELLED";
    } else if (data.status === "CONVERTED_PREPAID") {
      pillStyle = "bg-indigo-100 text-indigo-800";
      statusText = "CONVERTED_PREPAID";
    }

    stateBadge.innerText = statusText;
    stateBadge.className = `text-[10px] font-bold px-2 py-0.5 rounded-full ${pillStyle}`;

    const modalStatus = document.getElementById("modal-status-badge");
    modalStatus.innerText = statusText;
    modalStatus.className = `px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${getStatusClass(statusText)}`;

    // Refresh created orders table & founder dashboard in background
    loadCreatedOrdersFromDB();
    loadDashboardMetricsFromDB();
  } catch (err) {
    appendModalBotMessage(`⚠️ Error: ${err.message}`);
    stateBadge.innerText = "ERROR";
  }
}

async function triggerModalTimeout() {
  if (!currentModalOrder) return;
  appendModalUserMessage("<i>[No reply from customer for 24 hours]</i>");

  const stateBadge = document.getElementById("modal-wa-state-badge");
  stateBadge.innerText = "PROCESSING...";

  try {
    const res = await fetch("/api/whatsapp/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        customer_name: currentModalOrder.customer_name || "Customer",
        order_id: currentModalOrder.order_id,
        order_value: currentModalOrder.order_value,
        flow_type: currentModalFlow,
        action: "timeout",
      }),
    });

    const data = await res.json();
    appendModalBotMessage(data.response_message.replace(/\n/g, "<br>"));

    stateBadge.innerText = "AUTO_EXPIRED_24H";
    stateBadge.className = "text-[10px] font-bold px-2 py-0.5 rounded-full bg-orange-100 text-orange-800";

    const modalStatus = document.getElementById("modal-status-badge");
    modalStatus.innerText = "AUTO_EXPIRED_24H";
    modalStatus.className = `px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${getStatusClass("AUTO_EXPIRED_24H")}`;

    loadCreatedOrdersFromDB();
    loadDashboardMetricsFromDB();
  } catch (err) {
    appendModalBotMessage(`⚠️ Error: ${err.message}`);
  }
}

function sendModalCustomReply() {
  const input = document.getElementById("modal-chat-input");
  const val = input.value.trim();
  if (!val) return;
  input.value = "";
  sendModalSimReply(val);
}

function appendModalBotMessage(html) {
  const chat = document.getElementById("modal-chat-messages");
  const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  chat.innerHTML += `
    <div class="chat-msg chat-msg-bot">
      ${html}
      <div class="chat-msg-time text-slate-400 text-right mt-1">${time}</div>
    </div>
  `;
  chat.scrollTop = chat.scrollHeight;
}

function appendModalUserMessage(html) {
  const chat = document.getElementById("modal-chat-messages");
  const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  chat.innerHTML += `
    <div class="chat-msg chat-msg-user">
      ${html}
      <div class="chat-msg-time text-slate-500 text-right mt-1">${time} ✓✓</div>
    </div>
  `;
  chat.scrollTop = chat.scrollHeight;
}

// ----------------- FOUNDER DASHBOARD METRICS -----------------
async function loadDashboardMetrics() {
  await loadDashboardMetricsFromDB();
}

async function loadDashboardMetricsFromDB() {
  const errorBanner = document.getElementById("dash-error");
  try {
    const res = await fetch("/api/backtest");
    if (!res.ok) throw new Error("Could not fetch metrics from backtest engine");
    const data = await res.json();

    errorBanner.classList.add("hidden");

    // 4 Decision Buckets
    const counts = data.decisions_count || {};
    const total = data.total_evaluated || 1;

    document.getElementById("dash-count-ship").innerText = counts.ship || 0;
    document.getElementById("dash-pct-ship").innerText = `${((counts.ship || 0) / total * 100).toFixed(1)}% of total orders`;

    document.getElementById("dash-count-confirm").innerText = counts.confirm || 0;
    document.getElementById("dash-pct-confirm").innerText = `${((counts.confirm || 0) / total * 100).toFixed(1)}% of total orders`;

    document.getElementById("dash-count-nudge").innerText = counts.nudge_prepaid || 0;
    document.getElementById("dash-pct-nudge").innerText = `${((counts.nudge_prepaid || 0) / total * 100).toFixed(1)}% of total orders`;

    document.getElementById("dash-count-cancel").innerText = counts.cancel || 0;
    document.getElementById("dash-pct-cancel").innerText = `${((counts.cancel || 0) / total * 100).toFixed(1)}% of total orders`;

    // Financial Impacts
    const fin = data.financials || {};
    document.getElementById("dash-saved").innerText = `+₹${Math.round(fin.avoided_rto_savings || 0).toLocaleString()}`;
    document.getElementById("dash-saved-sub").innerText = `${data.outcomes?.avoided_rtos || 0} serial returns stopped`;

    document.getElementById("dash-lost").innerText = `-₹${Math.round(fin.false_cancel_margin_loss || 0).toLocaleString()}`;
    document.getElementById("dash-lost-sub").innerText = `${data.outcomes?.false_cancellations || 0} genuine buyers cancelled`;

    document.getElementById("dash-nudge-gain").innerText = `+₹${Math.round(fin.prepaid_conversion_savings || 0).toLocaleString()}`;
    document.getElementById("dash-nudge-sub").innerText = `${data.outcomes?.prepaid_conversions || 0} orders converted to prepaid`;

    const net = Math.round(fin.net_financial_impact || 0);
    document.getElementById("dash-net-impact").innerText = `${net >= 0 ? "+" : ""}₹${net.toLocaleString()}`;
  } catch (err) {
    errorBanner.classList.remove("hidden");
    errorBanner.innerText = `⚠️ Failed to load metrics: ${err.message}. Ensure database is seeded.`;
  }
}

// ----------------- RULES & THRESHOLDS -----------------
async function loadRulesFromDB() {
  const container = document.getElementById("rules-container");
  try {
    const res = await fetch("/api/rules");
    if (!res.ok) throw new Error("Could not load rules");
    allRules = await res.json();

    container.innerHTML = "";
    allRules.forEach((r) => {
      container.innerHTML += `
        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3">
          <div class="flex items-start justify-between">
            <div>
              <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">${r.category || 'General'}</span>
              <h4 class="font-mono text-sm font-bold text-slate-800">${r.key}</h4>
            </div>
            <span class="bg-emerald-50 text-emerald-700 text-xs font-bold px-2 py-0.5 rounded border border-emerald-200">
              ${r.value}
            </span>
          </div>
          <p class="text-xs text-slate-500 leading-relaxed">${r.description || ""}</p>
          <div class="flex items-center gap-2 pt-2 border-t border-slate-100">
            <input type="number" id="inp-rule-${r.key}" value="${r.value}" step="any" class="w-28 text-xs font-mono border border-slate-300 rounded-lg px-2.5 py-1.5 focus:ring-2 focus:ring-emerald-500 focus:outline-none" />
            <button onclick="saveSingleRule('${r.key}')" class="px-3 py-1.5 text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition">
              Update
            </button>
          </div>
        </div>
      `;
    });
  } catch (err) {
    container.innerHTML = `<div class="p-6 text-rose-500 text-xs">⚠️ Failed to load rules: ${err.message}</div>`;
  }
}

async function saveSingleRule(ruleKey) {
  const val = parseFloat(document.getElementById(`inp-rule-${ruleKey}`).value);
  try {
    const res = await fetch(`/api/rules/${ruleKey}?new_value=${val}`, { method: "PUT" });
    if (!res.ok) throw new Error("Failed to update rule");
    alert(`✅ Rule '${ruleKey}' updated to ${val} in database!`);
    loadRulesFromDB();
  } catch (err) {
    alert("❌ Error: " + err.message);
  }
}

async function saveAllRules() {
  for (const r of allRules) {
    const el = document.getElementById(`inp-rule-${r.key}`);
    if (el) {
      const val = parseFloat(el.value);
      if (val !== r.value) {
        await fetch(`/api/rules/${r.key}?new_value=${val}`, { method: "PUT" });
      }
    }
  }
  alert("✅ All modified rules saved to database!");
  loadRulesFromDB();
}

// ----------------- HISTORICAL DATABASE EXPLORER -----------------
async function loadOrdersFromDB() {
  try {
    const res = await fetch("/api/orders?limit=200");
    if (!res.ok) throw new Error("Could not load orders");
    allOrders = await res.json();
    renderOrdersTable(allOrders);
  } catch (err) {
    const tbody = document.getElementById("orders-tbody");
    if (tbody) {
      tbody.innerHTML = `<tr><td colspan="8" class="p-6 text-center text-rose-500">Failed to load orders: ${err.message}</td></tr>`;
    }
  }
}

function renderOrdersTable(orders) {
  const tbody = document.getElementById("orders-tbody");
  if (!tbody) return;
  tbody.innerHTML = "";

  if (orders.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" class="p-6 text-center text-slate-400">No matching orders found in database</td></tr>`;
    return;
  }

  orders.slice(0, 100).forEach((o) => {
    let badgeClass = "bg-slate-100 text-slate-700";
    if (o.decision === "ship") badgeClass = "bg-emerald-100 text-emerald-800";
    if (o.decision === "confirm") badgeClass = "bg-amber-100 text-amber-800";
    if (o.decision === "nudge_prepaid") badgeClass = "bg-orange-100 text-orange-800";
    if (o.decision === "cancel") badgeClass = "bg-rose-100 text-rose-800";

    tbody.innerHTML += `
      <tr class="hover:bg-slate-50 transition cursor-pointer" onclick="openOrderModal('${o.order_id}')">
        <td class="py-2.5 px-4 font-mono font-bold text-emerald-700 hover:underline">#${o.order_id}</td>
        <td class="py-2.5 px-4 font-medium">${o.customer_name || "N/A"}</td>
        <td class="py-2.5 px-4 text-slate-500">${o.city || ""}, ${o.pincode || ""}</td>
        <td class="py-2.5 px-4 font-semibold">₹${o.order_value || 0}</td>
        <td class="py-2.5 px-4 font-bold">${o.risk_score !== null ? o.risk_score : "---"}</td>
        <td class="py-2.5 px-4">
          <span class="px-2 py-0.5 rounded-full text-[11px] font-bold uppercase ${badgeClass}">
            ${o.decision || "PENDING"}
          </span>
        </td>
        <td class="py-2.5 px-4 text-slate-600 max-w-xs truncate text-[11px]">${o.reason || "Awaiting evaluation"}</td>
        <td class="py-2.5 px-4 font-bold ${o.final_status === 'DELIVERED' || o.final_status === 'CONFIRMED' ? 'text-emerald-600' : 'text-rose-600'}">
          ${o.final_status || "PENDING"}
        </td>
      </tr>
    `;
  });
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
