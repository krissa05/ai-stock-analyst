/* ═══════════════════════════════════════════════
   AI STOCK ANALYST — app.js  (with charts + search)
═══════════════════════════════════════════════ */
const API = "http://localhost:8000";

let currentTicker = null;
let chatHistory   = [];
let charts        = {};

// ── DOM ────────────────────────────────────────
const messagesEl = document.getElementById("messages");
const inputEl    = document.getElementById("userInput");
const sendBtnEl  = document.getElementById("sendBtn");
const badgeEl    = document.getElementById("tickerBadge");
const panelEl    = document.getElementById("stockPanel");
const statusDot  = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");

// ══════════════════════════════════════════════
//  STOCK NAME → TICKER MAP  (NSE + global)
//  Users can type company names; we resolve the ticker
// ══════════════════════════════════════════════
const TICKER_MAP = {
  // ── NSE India ──────────────────────────────
  "reliance": "RELIANCE.NS", "reliance industries": "RELIANCE.NS",
  "tcs": "TCS.NS", "tata consultancy": "TCS.NS", "tata consultancy services": "TCS.NS",
  "infosys": "INFY.NS", "infy": "INFY.NS",
  "hdfc bank": "HDFCBANK.NS", "hdfcbank": "HDFCBANK.NS",
  "icici bank": "ICICIBANK.NS", "icicbank": "ICICIBANK.NS",
  "wipro": "WIPRO.NS",
  "hcl": "HCLTECH.NS", "hcl tech": "HCLTECH.NS", "hcltech": "HCLTECH.NS",
  "bajaj finance": "BAJFINANCE.NS", "bajfinance": "BAJFINANCE.NS",
  "kotak": "KOTAKBANK.NS", "kotak bank": "KOTAKBANK.NS", "kotakbank": "KOTAKBANK.NS",
  "axis bank": "AXISBANK.NS", "axisbank": "AXISBANK.NS",
  "sbi": "SBIN.NS", "state bank": "SBIN.NS", "state bank of india": "SBIN.NS",
  "adani enterprises": "ADANIENT.NS", "adanient": "ADANIENT.NS",
  "adani ports": "ADANIPORTS.NS",
  "adani green": "ADANIGREEN.NS",
  "adani power": "ADANIPOWER.NS",
  "tata motors": "TATAMOTORS.NS",
  "tata steel": "TATASTEEL.NS",
  "tata power": "TATAPOWER.NS",
  "sun pharma": "SUNPHARMA.NS", "sunpharma": "SUNPHARMA.NS",
  "dr reddy": "DRREDDY.NS", "dr reddy's": "DRREDDY.NS",
  "cipla": "CIPLA.NS",
  "divis": "DIVISLAB.NS", "divis lab": "DIVISLAB.NS",
  "titan": "TITAN.NS",
  "asian paints": "ASIANPAINT.NS",
  "itc": "ITC.NS",
  "nestle": "NESTLEIND.NS", "nestle india": "NESTLEIND.NS",
  "hindustan unilever": "HINDUNILVR.NS", "hul": "HINDUNILVR.NS",
  "maruti": "MARUTI.NS", "maruti suzuki": "MARUTI.NS",
  "m&m": "M&M.NS", "mahindra": "M&M.NS", "mahindra mahindra": "M&M.NS",
  "larsen": "LT.NS", "l&t": "LT.NS", "larsen toubro": "LT.NS",
  "ultratech": "ULTRACEMCO.NS", "ultratech cement": "ULTRACEMCO.NS",
  "grasim": "GRASIM.NS",
  "shree cement": "SHREECEM.NS",
  "ongc": "ONGC.NS",
  "ntpc": "NTPC.NS",
  "power grid": "POWERGRID.NS", "pgcil": "POWERGRID.NS",
  "coal india": "COALINDIA.NS",
  "bpcl": "BPCL.NS", "bharat petroleum": "BPCL.NS",
  "ioc": "IOC.NS", "indian oil": "IOC.NS",
  "zomato": "ZOMATO.NS",
  "nykaa": "NYKAA.NS", "fss": "NYKAA.NS",
  "paytm": "PAYTM.NS", "one97": "PAYTM.NS",
  "policybazaar": "POLICYBZR.NS", "pb fintech": "POLICYBZR.NS",
  "delhivery": "DELHIVERY.NS",
  "indigo": "INDIGO.NS", "interglobe": "INDIGO.NS",
  "spicejet": "SPICEJET.NS",
  "irctc": "IRCTC.NS",
  "irfc": "IRFC.NS",
  "bhel": "BHEL.NS",
  "sail": "SAIL.NS", "steel authority": "SAIL.NS",
  "jsw steel": "JSWSTEEL.NS",
  "hindalco": "HINDALCO.NS",
  "vedanta": "VEDL.NS",
  "bajaj auto": "BAJAJ-AUTO.NS",
  "hero motocorp": "HEROMOTOCO.NS", "hero moto": "HEROMOTOCO.NS",
  "eicher": "EICHERMOT.NS", "royal enfield": "EICHERMOT.NS",
  "motherson": "MOTHERSON.NS",
  "mrf": "MRF.NS",
  "apollo tyres": "APOLLOTYRE.NS",
  "pidilite": "PIDILITIND.NS", "fevicol": "PIDILITIND.NS",
  "berger paints": "BERGEPAINT.NS",
  "havells": "HAVELLS.NS",
  "voltas": "VOLTAS.NS",
  "crompton": "CROMPTON.NS",
  "dixon tech": "DIXON.NS", "dixon": "DIXON.NS",
  "amber enterprises": "AMBER.NS",
  "waaree": "WAAREE.NS", "waaree energies": "WAAREE.NS",
  "premier energies": "PREMIERENE.NS",
  "kaynes": "KAYNES.NS", "kaynes tech": "KAYNES.NS",
  "ideaforge": "IDEAFORGE.NS",
  "rategain": "RATEGAIN.NS",
  "mamaearth": "HONASA.NS", "honasa": "HONASA.NS",
  "ola electric": "OLAELEC.NS",
  "bajaj housing": "BAJAJHFL.NS",
  "jio financial": "JIOFIN.NS",
  "one97 communications": "PAYTM.NS",
  "eternal": "ETERNAL.NS",
  "swiggy": "SWIGGY.NS",
  "hyundai india": "HYUNDAI.NS",
  "tata technologies": "TATATECH.NS",
  // ── US Stocks ──────────────────────────────
  "apple": "AAPL", "aapl": "AAPL",
  "nvidia": "NVDA", "nvda": "NVDA",
  "microsoft": "MSFT", "msft": "MSFT",
  "google": "GOOGL", "alphabet": "GOOGL", "googl": "GOOGL",
  "amazon": "AMZN", "amzn": "AMZN",
  "meta": "META", "facebook": "META",
  "tesla": "TSLA", "tsla": "TSLA",
  "berkshire": "BRK-B", "berkshire hathaway": "BRK-B",
  "jpmorgan": "JPM", "jp morgan": "JPM",
  "visa": "V",
  "mastercard": "MA",
  "netflix": "NFLX",
  "amd": "AMD", "advanced micro": "AMD",
  "intel": "INTC",
  "qualcomm": "QCOM",
  "broadcom": "AVGO",
  "tsmc": "TSM",
  "palantir": "PLTR",
  "snowflake": "SNOW",
  "coinbase": "COIN",
  // ── Korean ─────────────────────────────────
  "samsung": "005930.KS", "samsung electronics": "005930.KS",
  "lg": "066570.KS", "lg electronics": "066570.KS",
  "hyundai": "005380.KS",
  "sk hynix": "000660.KS",
  // ── Japanese ───────────────────────────────
  "toyota": "7203.T",
  "sony": "6758.T",
  "softbank": "9984.T",
  // ── UK ─────────────────────────────────────
  "shell": "SHEL",
  "bp": "BP",
  "hsbc": "HSBC",
  // ── Crypto ETFs / popular ──────────────────
  "bitcoin etf": "IBIT",
  "spy": "SPY", "s&p 500 etf": "SPY",
  "qqq": "QQQ", "nasdaq etf": "QQQ",
};

function resolveTickerFromText(text) {
  const lower = text.toLowerCase().trim();
  // Direct map lookup — try longest match first
  const sorted = Object.keys(TICKER_MAP).sort((a, b) => b.length - a.length);
  for (const key of sorted) {
    if (lower.includes(key)) return TICKER_MAP[key];
  }
  return null;
}

// ── Formatting ─────────────────────────────────
function mdToHtml(text) {
  return text
    .replace(/^## (.*)/gm, '<h3 style="color:var(--accent);margin:.6rem 0 .3rem;font-size:.95rem">$1</h3>')
    .replace(/^---$/gm, '<hr style="border-color:var(--border);margin:.5rem 0">')
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    .replace(/`(.*?)`/g, "<code>$1</code>")
    .replace(/^- (.*)/gm, '<div style="margin:.15rem 0;padding-left:.8rem">• $1</div>')
    .replace(/\n/g, "<br>");
}

function fmtPrice(n) {
  if (!n && n !== 0) return "—";
  return "₹" + Number(n).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtNum(n) {
  if (n >= 1e7) return (n / 1e7).toFixed(2) + "Cr";
  if (n >= 1e5) return (n / 1e5).toFixed(2) + "L";
  if (n >= 1000) return (n / 1000).toFixed(1) + "K";
  return n;
}

// ── Messages ───────────────────────────────────
function hideWelcome() {
  const w = document.getElementById("welcomeScreen");
  if (w) w.remove();
}

function addMsg(role, content) {
  hideWelcome();
  const wrap   = document.createElement("div");
  wrap.className = `msg ${role === "user" ? "user" : "bot"}`;

  const av = document.createElement("div");
  av.className = "msg-avatar";
  av.textContent = role === "user" ? "👤" : "📈";

  const body   = document.createElement("div");
  body.className = "msg-body";

  const bubble = document.createElement("div");
  bubble.className = "msg-bubble";
  bubble.innerHTML = role === "user" ? content.replace(/</g,"&lt;") : mdToHtml(content);

  const time = document.createElement("div");
  time.className = "msg-time";
  time.textContent = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  body.appendChild(bubble);
  body.appendChild(time);
  wrap.appendChild(av);
  wrap.appendChild(body);
  messagesEl.appendChild(wrap);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function showTyping() {
  const wrap = document.createElement("div");
  wrap.className = "msg bot"; wrap.id = "typing-indicator";
  const av = document.createElement("div");
  av.className = "msg-avatar"; av.textContent = "📈";
  const body = document.createElement("div");
  body.className = "msg-body";
  const bubble = document.createElement("div");
  bubble.className = "msg-bubble";
  bubble.innerHTML = `<div class="typing-dots"><span></span><span></span><span></span></div>`;
  body.appendChild(bubble);
  wrap.appendChild(av); wrap.appendChild(body);
  messagesEl.appendChild(wrap);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function hideTyping() { document.getElementById("typing-indicator")?.remove(); }
function setLoading(on) { sendBtnEl.disabled = on; inputEl.disabled = on; }
function setStatus(state) {
  statusDot.className  = `status-dot ${state}`;
  statusText.textContent = state === "online" ? "Connected" : state === "error" ? "Error" : "Connecting…";
}

// ── Chart helpers ──────────────────────────────
function destroyChart(id) {
  if (charts[id]) { charts[id].destroy(); delete charts[id]; }
}

// ══════════════════════════════════════════════
//  SIDEBAR SEARCH BOX  (injected into DOM)
// ══════════════════════════════════════════════
function buildSearchBox() {
  const searchHtml = `
    <div class="search-box-wrap">
      <input
        type="text"
        id="stockSearchInput"
        class="stock-search-input"
        placeholder="Search stock or company…"
        autocomplete="off"
        spellcheck="false"
      />
      <div id="searchDropdown" class="search-dropdown hidden"></div>
    </div>`;

  // Insert after the market status bar
  const mktStatus = document.getElementById("mktStatus");
  if (mktStatus) {
    mktStatus.insertAdjacentHTML("afterend", searchHtml);
  }

  const sInput = document.getElementById("stockSearchInput");
  const sDrop  = document.getElementById("searchDropdown");

  sInput.addEventListener("input", () => {
    const val = sInput.value.trim().toLowerCase();
    if (val.length < 1) { sDrop.classList.add("hidden"); return; }

    const results = [];
    for (const [name, ticker] of Object.entries(TICKER_MAP)) {
      if (name.includes(val) || ticker.toLowerCase().includes(val)) {
        results.push({ name, ticker });
      }
    }

    // Deduplicate by ticker
    const seen = new Set();
    const unique = results.filter(r => {
      if (seen.has(r.ticker)) return false;
      seen.add(r.ticker); return true;
    }).slice(0, 8);

    if (!unique.length) {
      sDrop.innerHTML = `<div class="search-dd-empty">No match — try typing the NSE ticker directly (e.g. WAAREE.NS)</div>`;
    } else {
      sDrop.innerHTML = unique.map(r => `
        <div class="search-dd-item" data-ticker="${r.ticker}">
          <span class="search-dd-ticker">${r.ticker}</span>
          <span class="search-dd-name">${r.name.replace(/\b\w/g, c => c.toUpperCase())}</span>
        </div>`).join("");

      sDrop.querySelectorAll(".search-dd-item").forEach(el => {
        el.addEventListener("click", () => {
          const t = el.dataset.ticker;
          sInput.value = "";
          sDrop.classList.add("hidden");
          quickAnalyze(t);
        });
      });
    }
    sDrop.classList.remove("hidden");
  });

  sInput.addEventListener("keydown", e => {
    if (e.key === "Escape") { sDrop.classList.add("hidden"); sInput.value = ""; }
    if (e.key === "Enter") {
      // If user typed a raw ticker like WAAREE.NS or AAPL, use it directly
      const raw = sInput.value.trim().toUpperCase();
      if (raw.length >= 2) {
        sInput.value = "";
        sDrop.classList.add("hidden");
        quickAnalyze(raw);
      }
    }
  });

  document.addEventListener("click", e => {
    if (!e.target.closest(".search-box-wrap")) sDrop.classList.add("hidden");
  });
}

// ── Stock panel with charts ────────────────────
async function loadStockPanel(ticker) {
  panelEl.innerHTML = `<div class="panel-loading">
    <div class="panel-loading-dot"></div>
    <span>Fetching ${ticker}…</span>
  </div>`;
  Object.keys(charts).forEach(k => destroyChart(k));

  try {
    const res = await fetch(`${API}/api/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ticker }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || "API error");
    const d = await res.json();

    const chgColor  = d.change_1d >= 0 ? "var(--accent2)" : "var(--danger)";
    const chgArrow  = d.change_1d >= 0 ? "▲" : "▼";
    const vColor    = d.verdict === "BUY" ? "var(--bull)" : d.verdict === "SELL" ? "var(--danger)" : "var(--warn)";
    const bColor    = d.bias === "BULLISH" ? "var(--bull)" : d.bias === "BEARISH" ? "var(--danger)" : "var(--warn)";
    const rsiColor  = d.rsi > 70 ? "var(--danger)" : d.rsi < 30 ? "var(--bull)" : "var(--text)";
    const adxLabel  = d.adx > 40 ? "Strong" : d.adx > 20 ? "Moderate" : "Weak";

    panelEl.innerHTML = `
      <div style="margin-bottom:8px">
        <div class="panel-symbol">${d.ticker}</div>
        <div style="font-size:.72rem;color:var(--text-dim);margin-top:1px">${d.name || ""}</div>
      </div>
      <div class="panel-price">${fmtPrice(d.price)}</div>
      <div class="panel-change ${d.change_1d >= 0 ? 'up' : 'down'}">
        ${chgArrow} ${Math.abs(d.change_1d).toFixed(2)}%
        <span style="color:var(--text-muted);margin-left:4px">(1d)</span>
        <span style="margin-left:6px;color:${d.change_10d>=0?'var(--bull)':'var(--danger)'}">
          ${d.change_10d>=0?'▲':'▼'} ${Math.abs(d.change_10d).toFixed(2)}% (10d)
        </span>
      </div>

      <div style="margin:8px 0;display:flex;align-items:center;gap:6px">
        <span style="font-family:var(--font-mono);font-size:.62rem;color:var(--text-dim)">Signal:</span>
        <span class="signal-badge ${d.verdict?.toLowerCase()}">${d.verdict}</span>
        <span style="font-family:var(--font-mono);font-size:.55rem;color:var(--text-muted)">${d.confidence || ""} · ${d.bull_signals||0}↑ ${d.bear_signals||0}↓</span>
      </div>

      <div class="panel-divider"></div>

      <div class="panel-grid">
        <div class="panel-kv">
          <span class="panel-kv-label">RSI (14)</span>
          <span class="panel-kv-val" style="color:${rsiColor}">${d.rsi}</span>
        </div>
        <div class="panel-kv">
          <span class="panel-kv-label">Bias</span>
          <span class="panel-kv-val" style="color:${bColor}">${d.bias}</span>
        </div>
        <div class="panel-kv">
          <span class="panel-kv-label">MACD</span>
          <span class="panel-kv-val" style="color:${d.macd>d.signal?'var(--bull)':'var(--danger)'}">
            ${d.macd > d.signal ? '↑ Bull' : '↓ Bear'}
          </span>
        </div>
        <div class="panel-kv">
          <span class="panel-kv-label">Stoch %K</span>
          <span class="panel-kv-val" style="color:${d.stoch_k>80?'var(--danger)':d.stoch_k<20?'var(--bull)':'var(--text)'}">
            ${d.stoch_k}
          </span>
        </div>
        <div class="panel-kv">
          <span class="panel-kv-label">ADX</span>
          <span class="panel-kv-val">${d.adx} <span style="font-size:.56rem;color:var(--text-dim)">${adxLabel}</span></span>
        </div>
        <div class="panel-kv">
          <span class="panel-kv-label">ATR</span>
          <span class="panel-kv-val">${fmtPrice(d.atr)}</span>
        </div>
        <div class="panel-kv">
          <span class="panel-kv-label">VWAP</span>
          <span class="panel-kv-val" style="color:${d.price>d.vwap?'var(--bull)':'var(--danger)'}">
            ${fmtPrice(d.vwap)}
          </span>
        </div>
        <div class="panel-kv">
          <span class="panel-kv-label">Fund Score</span>
          <span class="panel-kv-val">${d.fund_score}/8</span>
        </div>
        <div class="panel-kv">
          <span class="panel-kv-label">Entry</span>
          <span class="panel-kv-val">${fmtPrice(d.entry)}</span>
        </div>
        <div class="panel-kv">
          <span class="panel-kv-label">Stop Loss</span>
          <span class="panel-kv-val" style="color:var(--danger)">${fmtPrice(d.sl)}</span>
        </div>
        <div class="panel-kv">
          <span class="panel-kv-label">Target 1</span>
          <span class="panel-kv-val" style="color:var(--bull)">${fmtPrice(d.tp1)}</span>
        </div>
        <div class="panel-kv">
          <span class="panel-kv-label">Target 2</span>
          <span class="panel-kv-val" style="color:var(--accent2)">${fmtPrice(d.tp2)}</span>
        </div>
        <div class="panel-kv">
          <span class="panel-kv-label">R:R (T1)</span>
          <span class="panel-kv-val" style="color:${d.rr1>=1.5?'var(--bull)':'var(--warn)'}">1:${d.rr1}</span>
        </div>
        <div class="panel-kv">
          <span class="panel-kv-label">Support</span>
          <span class="panel-kv-val">${fmtPrice(d.support)}</span>
        </div>
        <div class="panel-kv">
          <span class="panel-kv-label">Resistance</span>
          <span class="panel-kv-val">${fmtPrice(d.resistance)}</span>
        </div>
        <div class="panel-kv">
          <span class="panel-kv-label">Volume</span>
          <span class="panel-kv-val" style="color:${d.vol_spike?'var(--warn)':'var(--text)'}">
            ${fmtNum(d.cur_volume)} ${d.vol_spike ? '⚡' : ''}
          </span>
        </div>
      </div>

      <!-- ── CHARTS ── -->
      <div class="chart-section-label">PRICE + MA + BOLLINGER</div>
      <div class="chart-wrap"><canvas id="priceChart"></canvas></div>

      <div class="chart-section-label">VOLUME</div>
      <div class="chart-wrap" style="height:80px"><canvas id="volChart"></canvas></div>

      <div class="chart-section-label">RSI (14)</div>
      <div class="chart-wrap" style="height:90px"><canvas id="rsiChart"></canvas></div>

      <div class="chart-section-label">MACD</div>
      <div class="chart-wrap" style="height:90px"><canvas id="macdChart"></canvas></div>
    `;

    setTimeout(() => renderCharts(d), 50);

  } catch (err) {
    panelEl.innerHTML = `
      <div class="panel-empty">
        <div class="panel-empty-icon">⚠</div>
        <div style="color:var(--danger);font-size:.75rem">${err.message}</div>
        <div style="color:var(--text-muted);font-size:.68rem;margin-top:6px">
          Try format: WAAREE.NS · TCS.NS · AAPL
        </div>
      </div>`;
  }
}

function renderCharts(d) {
  const labels = d.chart_data.map(c => c.date.slice(5));
  const closes = d.chart_data.map(c => c.close);
  const opens  = d.chart_data.map(c => c.open);
  const vols   = d.chart_data.map(c => c.volume);

  const gridColor = "rgba(31,42,60,0.8)";
  const textColor = "#5a6a82";
  const baseOpts  = {
    responsive: true, maintainAspectRatio: false, animation: false,
    plugins: { legend: { display: false }, tooltip: {
      mode: "index", intersect: false,
      backgroundColor: "#111520", borderColor: "#1f2a3c", borderWidth: 1,
      titleColor: "#c9d5e8", bodyColor: "#5a6a82"
    }},
    scales: {
      x: { ticks: { color: textColor, font: { size: 9 }, maxTicksLimit: 10 }, grid: { color: gridColor } },
      y: { ticks: { color: textColor, font: { size: 9 } }, grid: { color: gridColor }, position: "right" }
    }
  };

  destroyChart("price");
  const pCtx = document.getElementById("priceChart")?.getContext("2d");
  if (pCtx) {
    charts["price"] = new Chart(pCtx, {
      type: "line",
      data: {
        labels,
        datasets: [
          { label: "Close",    data: closes,          borderColor: "#c9d5e8", borderWidth: 1.5, pointRadius: 0, tension: 0.1, fill: false, order: 1 },
          { label: "MA20",     data: d.ma20_series,   borderColor: "#00d4ff", borderWidth: 1,   pointRadius: 0, tension: 0.1, fill: false, order: 2 },
          { label: "MA50",     data: d.ma50_series,   borderColor: "#f0c040", borderWidth: 1,   pointRadius: 0, tension: 0.1, fill: false, order: 3 },
          { label: "BB Upper", data: d.bbu_series,    borderColor: "rgba(255,77,109,0.4)", borderWidth: 1, borderDash: [3,3], pointRadius: 0, fill: false, order: 4 },
          { label: "BB Lower", data: d.bbl_series,    borderColor: "rgba(0,229,160,0.4)", borderWidth: 1, borderDash: [3,3], pointRadius: 0,
            fill: { target: "-1", above: "rgba(0,229,160,0.03)", below: "rgba(255,77,109,0.03)" }, order: 5 },
        ]
      },
      options: { ...baseOpts }
    });
  }

  destroyChart("vol");
  const vCtx = document.getElementById("volChart")?.getContext("2d");
  if (vCtx) {
    const volColors = closes.map((c, i) => i === 0 ? "#00ffa3" : c >= opens[i] ? "#00ffa3" : "#ff4d6d");
    charts["vol"] = new Chart(vCtx, {
      type: "bar",
      data: { labels, datasets: [{ label: "Volume", data: vols, backgroundColor: volColors, borderWidth: 0 }] },
      options: { ...baseOpts, scales: { ...baseOpts.scales,
        y: { ...baseOpts.scales.y, ticks: { ...baseOpts.scales.y.ticks, callback: v => fmtNum(v) } } } }
    });
  }

  destroyChart("rsi");
  const rCtx = document.getElementById("rsiChart")?.getContext("2d");
  if (rCtx && d.rsi_series?.length) {
    charts["rsi"] = new Chart(rCtx, {
      type: "line",
      data: {
        labels: labels.slice(-d.rsi_series.length),
        datasets: [
          { label: "RSI",  data: d.rsi_series,                             borderColor: "#00d4ff", borderWidth: 1.5, pointRadius: 0, fill: false },
          { label: "OB",   data: Array(d.rsi_series.length).fill(70),      borderColor: "rgba(255,77,109,0.4)", borderWidth: 1, borderDash: [4,4], pointRadius: 0, fill: false },
          { label: "OS",   data: Array(d.rsi_series.length).fill(30),      borderColor: "rgba(0,229,160,0.4)",  borderWidth: 1, borderDash: [4,4], pointRadius: 0, fill: false },
        ]
      },
      options: { ...baseOpts, scales: { ...baseOpts.scales, y: { ...baseOpts.scales.y, min: 0, max: 100 } } }
    });
  }

  destroyChart("macd");
  const mCtx = document.getElementById("macdChart")?.getContext("2d");
  if (mCtx && d.macd_series?.length) {
    const histColors = d.hist_series.map(v => v >= 0 ? "rgba(0,229,160,0.6)" : "rgba(255,77,109,0.6)");
    charts["macd"] = new Chart(mCtx, {
      type: "bar",
      data: {
        labels: labels.slice(-d.macd_series.length),
        datasets: [
          { type: "bar",  label: "Histogram", data: d.hist_series,  backgroundColor: histColors, order: 2 },
          { type: "line", label: "MACD",      data: d.macd_series,  borderColor: "#00d4ff", borderWidth: 1.5, pointRadius: 0, fill: false, order: 1 },
          { type: "line", label: "Signal",    data: d.sig_series,   borderColor: "#ff4d6d", borderWidth: 1,   pointRadius: 0, fill: false, order: 1 },
        ]
      },
      options: { ...baseOpts }
    });
  }
}

// ══════════════════════════════════════════════
//  TICKER DETECTION  (from chat message)
// ══════════════════════════════════════════════
// ── Ticker detection ──────────────────────────────────────────────────────
// RULE: Only extract a ticker if the message is CLEARLY asking about a stock.
// Never pick up normal English words like "correctly", "stop", "high", etc.

const QUESTION_WORDS = new Set([
  "WHAT","HOW","WHY","WHO","WHEN","WHERE","IS","ARE","CAN","DOES","DO",
  "SHOULD","TELL","EXPLAIN","TEACH","SHOW","GIVE","HELP","DEFINE","DESCRIBE",
  "DIFFERENCE","BETWEEN","MEAN","MEANS","WORK","WORKS","USE","USES"
]);

// Words that look like tickers but are common English
const ALWAYS_SKIP = new Set([
  "THE","AND","FOR","RSI","MACD","BUY","SELL","HOW","WHAT","WHY","WHO",
  "GIVE","SHOW","TELL","FULL","JUST","GET","SET","USE","CAN","ARE","THIS",
  "THAT","FROM","WITH","STOP","LOSS","RISK","GOOD","HIGH","LOW","NSE","BSE",
  "SEBI","SMA","EMA","ANALYZE","ANALYSIS","TRADE","SETUP","TREND","ATR",
  "ADX","VWAP","OBV","STOCH","VOLUME","CHART","STOCK","MARKET","ABOUT",
  "PLEASE","EXPLAIN","SIGNAL","INDICATOR","PRICE","WANT","KNOW","TODAY",
  "RIGHT","NOW","CORRECTLY","PROPERLY","ACTUALLY","REALLY","QUICKLY","SIMPLY",
  "BASIC","BEST","GOOD","GREAT","LIKE","JUST","ALSO","ONLY","EVEN","STILL",
  "VERY","MUCH","MORE","MOST","LESS","SOME","MANY","EACH","BOTH","EITHER",
  "INTO","ONTO","OVER","UNDER","ABOVE","BELOW","AFTER","BEFORE","DURING",
  "ENTRY","EXIT","PROFIT","LOSS","GAIN","RETURN","LONG","SHORT","CALL","PUT",
  "INTRADAY","SWING","POSITION","PORTFOLIO","SECTOR","INDEX","RATIO","BAND",
  "CROSS","SIGNAL","BREAK","BOUNCE","SUPPORT","RESIST","TREND","MOVE","PUSH",
  "STRONG","WEAK","BULL","BEAR","PIVOT","LEVEL","ZONE","AREA","RANGE","FLAT",
  "OPEN","CLOSE","HIGH","LOW","DAILY","WEEKLY","MONTHLY","YEARLY","PERCENT",
  "NEVER","ALWAYS","OFTEN","SOMETIMES","USUALLY","MOSTLY","MAINLY","MAINLY",
  "ATR","ADX","OBV","VWAP","MACD","RSI","EMA","SMA","BB","STOCH","OBOS"
]);

// Phrases that clearly indicate a general education question (no ticker needed)
const GENERAL_QUESTION_PATTERNS = [
  /^(what|how|why|when|where|explain|tell me|teach|define|describe|help)/i,
  /(is rsi|is macd|is vwap|is atr|is adx|is stoch|is obv|is a stop|is a target)/i,
  /(stop loss|risk reward|risk.to.reward|r:r|r\/r)/i,
  /(how (do|does|to|can|should)|what (is|are|does))/i,
  /(explain|understand|learn|teach|help me)/i,
];

function isGeneralQuestion(text) {
  return GENERAL_QUESTION_PATTERNS.some(p => p.test(text));
}

function detectTicker(text) {
  // 1. If this looks like a general education question, don't extract any ticker
  if (isGeneralQuestion(text)) return null;

  // 2. Try name-to-ticker map (e.g. "waaree", "samsung", "reliance")
  const fromMap = resolveTickerFromText(text);
  if (fromMap) return fromMap;

  // 3. Explicit suffix patterns are always safe: WAAREE.NS, 005930.KS, AAPL.BO
  const withSuffix = text.match(/\b([A-Z0-9]{2,12}\.(NS|BO|KS|T|L|HK|AX))\b/gi);
  if (withSuffix && withSuffix.length > 0) return withSuffix[0].toUpperCase();

  // 4. Bare tickers only if message strongly implies stock analysis
  const analysisIntent = /\b(analyze|analysis|buy|sell|hold|verdict|technical|chart|price of|check|look up|data for|what about)\b/i.test(text);
  if (analysisIntent) {
    const bare = text.toUpperCase().match(/\b([A-Z]{2,6})\b/g) || [];
    for (const m of bare) {
      if (!ALWAYS_SKIP.has(m) && m.length >= 2 && m.length <= 6) return m;
    }
  }

  return null;
}

// ── Send message ───────────────────────────────
async function sendMessage() {
  const text = inputEl.value.trim();
  if (!text) return;

  const found = detectTicker(text);
  if (found) {
    currentTicker = found;
    badgeEl.textContent = currentTicker;
    badgeEl.classList.remove("hidden");
    loadStockPanel(currentTicker);
  }

  addMsg("user", text);
  chatHistory.push({ role: "user", content: text });
  inputEl.value = "";
  inputEl.style.height = "auto";
  setLoading(true);
  showTyping();

  try {
    const res = await fetch(`${API}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, ticker: currentTicker, history: chatHistory.slice(-12) }),
    });
    hideTyping();
    if (!res.ok) throw new Error((await res.json()).detail || `HTTP ${res.status}`);
    const data = await res.json();
    addMsg("assistant", data.reply);
    chatHistory.push({ role: "assistant", content: data.reply });
    setStatus("online");
  } catch (err) {
    hideTyping();
    addMsg("assistant", `⚠ **Error:** ${err.message}\n\nMake sure the backend is running on port 8000.`);
    setStatus("error");
  } finally {
    setLoading(false);
    inputEl.focus();
  }
}

function sendQuick(text) { inputEl.value = text; sendMessage(); }

function quickAnalyze(ticker) {
  sendQuick(`Analyze ${ticker} — give me full technical analysis, trade setup, and your verdict.`);
}

// ── Input auto-resize & keyboard shortcut ──────
inputEl?.addEventListener("input", function () {
  this.style.height = "auto";
  this.style.height = Math.min(this.scrollHeight, 140) + "px";
});
inputEl?.addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});

// ── Health check ───────────────────────────────
async function checkHealth() {
  try {
    const res = await fetch(`${API}/api/health`);
    setStatus(res.ok ? "online" : "error");
  } catch { setStatus("error"); }
}

// ── Init ───────────────────────────────────────
window.addEventListener("DOMContentLoaded", () => {
  buildSearchBox();
  checkHealth();
  inputEl?.focus();
});