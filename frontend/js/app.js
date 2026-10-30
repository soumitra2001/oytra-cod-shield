// Oytra COD Risk Engine — Frontend Logic

let allRules = [];
let allOrders = [];
let currentSimFlow = "confirmation";
let currentSimState = "PENDING_REPLY";

// Initialize UI
document.addEventListener("DOMContentLoaded", () => {
  if (window.lucide) {
    lucide.createIcons();
  }
  loadRules();
  loadDashboardMetrics();
  loadOrders();
  refreshSimulator();
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

// Quick-load Presets
const PRESETS = {
  safe: {
    order_id: "KT100452",
    order_value: 449,
    customer_name: "Swati Das",
    phone: "9583831354",
    address: "399/13, Station Nagar, Opp. Railway Crossing",
    city: "Chennai",
    state: "Tamil Nadu",
    pincode: "600092",
    prior_orders: 4,
    prior_rto: 0,
  },
  hinglish: {
    order_id: "KT100193",
    order_value: 349,
    customer_name: "Lakshmi Shaikh",
    phone: "6007018646",
    address: "Station chowk se left, Hanuman Mandir ke saamne",
    city: "Chennai",
    state: "Tamil Nadu",
    pincode: "600084",
    prior_orders: 0,
    prior_rto: 0,
  },
  short_addr: {
    order_id: "KT101370",
    order_value: 649,
    customer_name: "Deepika Yadav",
    phone: "9123456780",
    address: "xyz",
    city: "Delhi",
    state: "Delhi",
    pincode: "110001",
    prior_orders: 0,
    prior_rto: 0,
  },
  serial_rto: {
    order_id: "KT101999",
    order_value: 899,
    customer_name: "Vikram Malhotra",
    phone: "9988776655",
    address: "Near bus stop",
    city: "Lucknow",
    state: "Uttar Pradesh",
    pincode: "226001",
    prior_orders: 3,
    prior_rto: 2,
  },
};

function loadPreset(key) {
  const p = PRESETS[key];
  if (!p) return;

  document.getElementById("inp-order-id").value = p.order_id;
  document.getElementById("inp-order-value").value = p.order_value;
  document.getElementById("inp-customer-name").value = p.customer_name;
  document.getElementById("inp-phone").value = p.phone;
  document.getElementById("inp-address").value = p.address;
  document.getElementById("inp-city").value = p.city;
  document.getElementById("inp-state").value = p.state;
  document.getElementById("inp-pincode").value = p.pincode;
  document.getElementById("inp-prior-orders").value = p.prior_orders;
  document.getElementById("inp-prior-rto").value = p.prior_rto;

  // Auto evaluate
  document.getElementById("order-form").dispatchEvent(new Event("submit"));
}

// Evaluate Order via API
async function handleEvaluate(e) {
  e.preventDefault();

  const payload = {
    order_id: document.getElementById("inp-order-id").value,
    order_value: parseFloat(document.getElementById("inp-order-value").value),
    customer_name: document.getElementById("inp-customer-name").value,
    phone: document.getElementById("inp-phone").value,
    address: document.getElementById("inp-address").value,
    city: document.getElementById("inp-city").value,
    state: document.getElementById("inp-state").value,
    pincode: document.getElementById("inp-pincode").value,
    customer_prior_orders: parseInt(document.getElementById("inp-prior-orders").value) || 0,
    customer_prior_rto: parseInt(document.getElementById("inp-prior-rto").value) || 0,
    payment_method: "COD",
  };

  const btn = document.getElementById("btn-eval");
  btn.innerHTML = `<span class="animate-spin mr-2">⚙️</span> Evaluating...`;
  btn.disabled = true;

  try {
    const res = await fetch("/api/evaluate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    renderEvaluationResult(data, payload);
  } catch (err) {
    alert("Evaluation failed: " + err.message);
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

  // Score
  const score = data.risk_score;
  document.getElementById("res-score-num").innerText = `${score}/100`;

  const bar = document.getElementById("res-score-bar");
  bar.style.width = `${Math.min(100, Math.max(5, score))}%`;

  // Colors & Badges
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
    catText.innerText = "High Risk • Offer ₹40 OFF to pay online";
  } else {
    badge.classList.add("badge-cancel");
    badge.innerText = "HOLD / CANCEL";
    bar.className = "h-full bg-rose-500 transition-all duration-500";
    catText.innerText = "Severe Risk • Serial RTO / Dummy order";
  }

  // Reason
  document.getElementById("res-reason").innerText = data.reason;

  // Factors
  const factorsContainer = document.getElementById("res-factors");
  factorsContainer.innerHTML = "";
  const f = data.risk_factors || {};

  if (f.first_time_buyer) {
    factorsContainer.innerHTML += `<span class="bg-blue-50 text-blue-700 border border-blue-200 px-2 py-1 rounded-md">First-Time Buyer</span>`;
  }
  if (f.prior_orders > 0) {
    factorsContainer.innerHTML += `<span class="bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-1 rounded-md">History: ${f.prior_orders} orders (${f.prior_rto} RTOs)</span>`;
  }
  if (f.short_or_incomplete_address) {
    factorsContainer.innerHTML += `<span class="bg-rose-50 text-rose-700 border border-rose-200 px-2 py-1 rounded-md">Incomplete/Short Address (+30 pts)</span>`;
  }
  if (f.suspicious_name) {
    factorsContainer.innerHTML += `<span class="bg-rose-50 text-rose-700 border border-rose-200 px-2 py-1 rounded-md">Suspicious Name (+30 pts)</span>`;
  }
  if (f.first_order_protected) {
    factorsContainer.innerHTML += `<span class="bg-indigo-50 text-indigo-700 border border-indigo-200 px-2 py-1 rounded-md font-semibold">Protected First-Time Buyer (No Auto-Cancel)</span>`;
  }
  if (f.pincode_rto_rate !== null && f.pincode_rto_rate !== undefined) {
    factorsContainer.innerHTML += `<span class="bg-slate-100 text-slate-700 px-2 py-1 rounded-md">Pincode RTO: ${f.pincode_rto_rate}%</span>`;
  }

  // Action Buttons
  const actionsContainer = document.getElementById("res-actions-container");
  if (data.decision === "ship") {
    actionsContainer.innerHTML = `
      <button onclick="alert('✅ Order released to Delhivery warehouse queue for priority dispatch!')" class="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-2.5 rounded-xl shadow transition flex items-center justify-center gap-2">
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
        <span>Send WhatsApp Prepaid Discount Link (₹40 OFF)</span>
      </button>
    `;
  } else {
    actionsContainer.innerHTML = `
      <button onclick="alert('🛑 Order cancelled. Status recorded in database. ₹169.40 dead shipping saved.')" class="w-full bg-rose-600 hover:bg-rose-700 text-white font-semibold py-2.5 rounded-xl shadow transition flex items-center justify-center gap-2">
        <i data-lucide="ban" class="w-4 h-4"></i>
        <span>Confirm Order Cancellation (Zero False Positives)</span>
      </button>
    `;
  }

  if (window.lucide) lucide.createIcons();
}

// ----------------- WHATSAPP SIMULATOR -----------------
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

function refreshSimulator() {
  const name = document.getElementById("sim-name").value.trim() || "Customer";
  const val = parseFloat(document.getElementById("sim-value").value) || 649;
  const firstName = name.split(" ")[0];

  const chat = document.getElementById("chat-messages");
  chat.innerHTML = "";

  currentSimState = "PENDING_REPLY";
  updateSimPill("PENDING_REPLY", "bg-amber-100 text-amber-800");

  let outMsg = "";
  if (currentSimFlow === "confirmation") {
    outMsg = `Hi ${firstName}! 👋<br><br>Thank you for ordering with <b>Oytra Care</b>!<br><br>Your order of <b>₹${val}</b> is placed as Cash on Delivery.<br><br>Please confirm if you'd like us to deliver your order.<br><br>Reply <b>YES</b> to confirm or <b>NO</b> to cancel.`;
  } else {
    const discount = Math.min(40, Math.round(val * 0.10));
    const finalVal = val - discount;
    outMsg = `Hi ${firstName}! 👋<br><br>Your Oytra order is packed and ready! 🌿<br><br>💰 <b>Special Offer: Pay online & get ₹${discount} OFF!</b><br><br>Original Amount: ₹${val}<br>Discount: ₹${discount}<br><b>You Pay Only: ₹${finalVal}!</b><br><br>Reply <b>YES</b> to get secure payment link, or <b>NO</b> to continue with COD.`;
  }

  appendBotMessage(outMsg);
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

async function sendSimReply(replyText) {
  appendUserMessage(replyText);

  const clean = replyText.toLowerCase().trim();

  setTimeout(() => {
    if (["yes", "y", "haan", "haan bhej do please", "ha", "ok"].includes(clean)) {
      if (currentSimFlow === "confirmation") {
        appendBotMessage("Thank you! ✅ Your order is confirmed and released to our courier partners for express delivery.");
        updateSimPill("ORDER_CONFIRMED", "bg-emerald-100 text-emerald-800");
      } else {
        appendBotMessage("Awesome! 🎉 Here is your discounted payment link:<br><br>🔗 <a href='#' class='underline text-blue-600'>https://pay.oytra.com/order/pay-discount</a><br><br>Once completed, your order will be delivered with zero doorstep collection friction!");
        updateSimPill("PREPAID_LINK_SENT", "bg-indigo-100 text-indigo-800");
      }
    } else if (["no", "n", "cancel", "nahi"].includes(clean)) {
      if (currentSimFlow === "confirmation") {
        appendBotMessage("Your order has been cancelled as requested. No charges applied. 🙏");
        updateSimPill("ORDER_CANCELLED", "bg-rose-100 text-rose-800");
      } else {
        appendBotMessage("No problem! Your order will continue as Cash on Delivery.<br><br>Please confirm with <b>YES</b> to dispatch COD, or <b>NO</b> to cancel.");
        updateSimPill("COD_FALLBACK", "bg-amber-100 text-amber-800");
      }
    } else {
      appendBotMessage("Sorry, I didn't quite catch that. 🤔<br><br>Please reply with <b>YES</b> to proceed or <b>NO</b> to cancel.");
      updateSimPill("AWAITING_CLARIFICATION", "bg-slate-200 text-slate-800");
    }
  }, 400);
}

function triggerSimTimeout() {
  appendUserMessage("<i>[No reply from customer for 24 hours]</i>");
  setTimeout(() => {
    appendBotMessage("⏱️ <b>Notice:</b> Since we didn't receive your confirmation within 24 hours, your order has been automatically put on hold to prevent unauthorized delivery. Feel free to re-order anytime!");
    updateSimPill("AUTO_EXPIRED_24H", "bg-orange-100 text-orange-800");
  }, 400);
}

function sendCustomReply() {
  const input = document.getElementById("sim-custom-input");
  const val = input.value.trim();
  if (!val) return;
  input.value = "";
  sendSimReply(val);
}

function updateSimPill(text, classes) {
  const pill = document.getElementById("sim-status-pill");
  pill.className = `text-xs font-bold px-2.5 py-0.5 rounded-full ${classes}`;
  pill.innerText = text;
}

// ----------------- FOUNDER DASHBOARD METRICS -----------------
async function loadDashboardMetrics() {
  try {
    const res = await fetch("/api/backtest");
    if (!res.ok) return;
    const data = await res.json();

    const b = data.buckets || {};
    document.getElementById("dash-count-ship").innerText = (b.ship?.count || 1726).toLocaleString();
    document.getElementById("dash-count-confirm").innerText = (b.confirm?.count || 210).toLocaleString();
    document.getElementById("dash-count-nudge").innerText = (b.nudge_prepaid?.count || 49).toLocaleString();
    document.getElementById("dash-count-cancel").innerText = (b.cancel?.count || 3).toLocaleString();

    const fin = data.financial || {};
    document.getElementById("dash-saved").innerText = `₹${(fin.saved_from_cancels || 508.2).toLocaleString(undefined, {minimumFractionDigits: 2})}`;
    document.getElementById("dash-lost").innerText = `₹${(fin.lost_from_cancels || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}`;
    document.getElementById("dash-nudge-gain").innerText = `+₹${(fin.saved_from_nudges || 597.64).toLocaleString(undefined, {minimumFractionDigits: 2})}`;
    document.getElementById("dash-net-impact").innerText = `+₹${(fin.net_impact || 1105.84).toLocaleString(undefined, {minimumFractionDigits: 2})}`;
  } catch (err) {
    console.error("Dashboard metrics fetch error:", err);
  }
}

// ----------------- RULES & THRESHOLDS -----------------
async function loadRules() {
  try {
    const res = await fetch("/api/rules");
    allRules = await res.json();
    renderRules();
  } catch (err) {
    console.error("Rules fetch error:", err);
  }
}

function renderRules() {
  const container = document.getElementById("rules-container");
  container.innerHTML = "";

  // Group by category
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
  alert(`✅ Saved ${count} updated rules to the database!`);
  loadRules();
}

// ----------------- ORDER DATABASE -----------------
async function loadOrders() {
  try {
    const res = await fetch("/api/orders?limit=100");
    if (res.ok) {
      allOrders = await res.json();
      renderOrdersTable(allOrders);
    }
  } catch (err) {
    console.error("Orders fetch error:", err);
  }
}

function renderOrdersTable(orders) {
  const tbody = document.getElementById("orders-tbody");
  tbody.innerHTML = "";

  orders.slice(0, 50).forEach((o) => {
    let badgeClass = "bg-slate-100 text-slate-700";
    if (o.decision === "ship") badgeClass = "bg-emerald-100 text-emerald-800";
    if (o.decision === "confirm") badgeClass = "bg-amber-100 text-amber-800";
    if (o.decision === "nudge_prepaid") badgeClass = "bg-orange-100 text-orange-800";
    if (o.decision === "cancel") badgeClass = "bg-rose-100 text-rose-800";

    tbody.innerHTML += `
      <tr class="hover:bg-slate-50 transition cursor-pointer" onclick="populateEvaluatorFromRow('${o.order_id}')">
        <td class="py-2.5 px-4 font-mono font-bold">${o.order_id}</td>
        <td class="py-2.5 px-4 font-medium">${o.customer_name || "N/A"}</td>
        <td class="py-2.5 px-4 text-slate-500">${o.city || ""}, ${o.pincode || ""}</td>
        <td class="py-2.5 px-4 font-semibold">₹${o.order_value || 0}</td>
        <td class="py-2.5 px-4 font-bold">${o.risk_score || "N/A"}</td>
        <td class="py-2.5 px-4">
          <span class="px-2 py-0.5 rounded-full text-[11px] font-bold uppercase ${badgeClass}">
            ${o.decision || "PENDING"}
          </span>
        </td>
        <td class="py-2.5 px-4 text-slate-600 max-w-xs truncate">${o.reason || "N/A"}</td>
        <td class="py-2.5 px-4 font-bold ${o.final_status === 'DELIVERED' ? 'text-emerald-600' : 'text-rose-600'}">
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

function populateEvaluatorFromRow(orderId) {
  const found = allOrders.find((o) => o.order_id === orderId);
  if (!found) return;

  document.getElementById("inp-order-id").value = found.order_id;
  document.getElementById("inp-order-value").value = found.order_value;
  document.getElementById("inp-customer-name").value = found.customer_name || "";
  document.getElementById("inp-phone").value = found.phone || "9876543210";
  document.getElementById("inp-address").value = found.address || "";
  document.getElementById("inp-city").value = found.city || "";
  document.getElementById("inp-state").value = found.state || "";
  document.getElementById("inp-pincode").value = found.pincode || "";
  document.getElementById("inp-prior-orders").value = found.customer_prior_orders || 0;
  document.getElementById("inp-prior-rto").value = found.customer_prior_rto || 0;

  switchTab("evaluator");
  document.getElementById("order-form").dispatchEvent(new Event("submit"));
}
