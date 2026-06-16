// FUTMANAGER — frontend hub
const $ = (s) => document.querySelector(s);
const api = (p, opt) => fetch(p, opt).then(r => r.json());

let STATE = null;

// ─── Boot ────────────────────────────────────────────────────────────────────
async function boot() {
  showSaves();
}

// ─── Saves ─────────────────────────────────────────────────────────────────────
async function showSaves() {
  $("#hub").classList.add("hidden");
  $("#newcareer").classList.add("hidden");
  $("#saves").classList.remove("hidden");
  const list = await api("/api/saves");
  const box = $("#saves-list");
  if (!list.length) {
    box.innerHTML = `<div class="saves-empty">Nenhum jogo salvo. Comece um novo!</div>`;
  } else {
    box.innerHTML = list.map(s => {
      const col = clubColor(s.club);
      const st = s.status === "sacked" ? " · demitido" : "";
      return `<div class="save-item" data-slug="${s.slug}">
        <div class="save-crest" style="background:${col}">${abbr(s.club)}</div>
        <div class="save-info">
          <div class="save-club">${s.club}</div>
          <div class="save-meta">👔 ${s.coach} · temp ${s.season} · rep ${s.reputation} · 🏆${s.titles}${st}</div>
        </div>
        <button class="save-del" data-del="${s.slug}" title="apagar">🗑️</button>
      </div>`;
    }).join("");
    box.querySelectorAll(".save-item").forEach(el => {
      el.onclick = async (e) => {
        if (e.target.dataset.del) return;
        await api("/api/save/load", { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ slug: el.dataset.slug }) });
        STATE = await api("/api/state");
        showHub();
      };
    });
    box.querySelectorAll(".save-del").forEach(b => {
      b.onclick = async (e) => {
        e.stopPropagation();
        if (!confirm("Apagar este jogo salvo?")) return;
        await api("/api/save/delete", { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ slug: b.dataset.del }) });
        showSaves();
      };
    });
  }
  $("#saves-new").onclick = showNewCareer;
}

function clubColor(name) {
  // hue determinístico simples (espelha o backend)
  let h = 0; for (const ch of name) h = (h * 31 + ch.charCodeAt(0)) % 360;
  return `hsl(${h},60%,42%)`;
}

// ─── Nova carreira ─────────────────────────────────────────────────────────────
async function showNewCareer() {
  $("#hub").classList.add("hidden");
  $("#saves").classList.add("hidden");
  $("#newcareer").classList.remove("hidden");
  const leagues = await api("/api/leagues");
  const ls = $("#nc-league");
  ls.innerHTML = leagues.map(l => `<option value="${l.id}">${l.name} (${l.country}) — ${l.n} clubes</option>`).join("");
  await loadClubs(ls.value);
  ls.onchange = () => loadClubs(ls.value);
  $("#nc-start").onclick = startCareer;
}

async function loadClubs(leagueId) {
  const clubs = await api("/api/clubs?league=" + leagueId);
  $("#nc-club").innerHTML = clubs.map(c => `<option value="${c.id}">${c.name} (prest. ${c.prestige})</option>`).join("");
}

async function startCareer() {
  const club_id = $("#nc-club").value;
  const coach_name = $("#nc-name").value.trim() || "Técnico";
  const r = await api("/api/career/new", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ club_id, coach_name })
  });
  if (r.ok) { STATE = await api("/api/state"); showHub(); }
}

// ─── Hub ───────────────────────────────────────────────────────────────────────
function showHub() {
  $("#newcareer").classList.add("hidden");
  $("#saves").classList.add("hidden");
  $("#hub").classList.remove("hidden");
  renderBanner();
  bindNav();
  $("#top-saves").onclick = showSaves;
  loadView("elenco");
}

function renderBanner() {
  const s = STATE, cl = s.club;
  document.documentElement.style.setProperty("--club-color", cl.colors.primary);
  document.documentElement.style.setProperty("--club-accent", cl.colors.accent);
  $("#top-coach").textContent = "👔 " + s.coach;
  $("#top-season").textContent = "Temporada " + s.season;
  $("#club-crest").textContent = abbr(cl.name);
  $("#club-name").textContent = cl.name;
  $("#club-prestige").textContent = "Prestígio " + cl.prestige + " · " + cap(s.tactic_style) + " · " + s.formation;
  $("#st-money").textContent = s.money_fmt;
  $("#st-titles").textContent = "🏆 " + s.titles;
  $("#st-rep").textContent = s.reputation + "/100";
  $("#st-rep").style.color = s.reputation >= 60 ? "#2ea043" : (s.reputation >= 40 ? "#e3b341" : "#d9544d");
  $("#st-meta").textContent = (s.expectation || "?") + "º";
}

function bindNav() {
  document.querySelectorAll(".nav").forEach(b => {
    b.onclick = () => {
      document.querySelectorAll(".nav").forEach(x => x.classList.remove("active"));
      b.classList.add("active");
      loadView(b.dataset.view);
    };
  });
}

// ─── Views ─────────────────────────────────────────────────────────────────────
async function loadView(view) {
  const panel = $("#panel");
  if (view === "elenco") return renderSquad(panel);
  if (view === "escalacao") return renderLineup(panel);
  if (view === "tabela") return renderTable(panel);
  if (view === "jogar") return renderPlay(panel);
  if (view === "financas") return renderFinance(panel);
  if (view === "estadio-ct") return renderStadium(panel);
  if (view === "mercado") return renderMarket(panel);
  if (view === "buscar-time") return renderSearchTeam(panel);
  if (view === "scout") return renderScout(panel);
  if (view === "historico") return renderHistory(panel);
  panel.innerHTML = `<div class="placeholder">🚧 "${cap(view)}" — em construção no front web.<br>
    Disponível no modo terminal por enquanto.</div>`;
}

// ─── Escalação ─────────────────────────────────────────────────────────────────
const FORMATION_SLOTS = {
  "4-4-2": [
    {pos:"GK",label:"GOL",x:50,y:92},
    {pos:"DF",label:"ZG",x:20,y:74}, {pos:"DF",label:"ZG",x:40,y:74}, {pos:"DF",label:"ZG",x:60,y:74}, {pos:"DF",label:"ZG",x:80,y:74},
    {pos:"MF",label:"MC",x:20,y:52}, {pos:"MF",label:"MC",x:40,y:52}, {pos:"MF",label:"MC",x:60,y:52}, {pos:"MF",label:"MC",x:80,y:52},
    {pos:"FW",label:"CA",x:35,y:22}, {pos:"FW",label:"CA",x:65,y:22}
  ],
  "4-3-3": [
    {pos:"GK",label:"GOL",x:50,y:92},
    {pos:"DF",label:"ZG",x:20,y:74}, {pos:"DF",label:"ZG",x:40,y:74}, {pos:"DF",label:"ZG",x:60,y:74}, {pos:"DF",label:"ZG",x:80,y:74},
    {pos:"MF",label:"VOL",x:30,y:52}, {pos:"MF",label:"MC",x:50,y:52}, {pos:"MF",label:"MEI",x:70,y:52},
    {pos:"FW",label:"PE",x:20,y:22}, {pos:"FW",label:"CA",x:50,y:22}, {pos:"FW",label:"PD",x:80,y:22}
  ],
  "4-2-3-1": [
    {pos:"GK",label:"GOL",x:50,y:92},
    {pos:"DF",label:"ZG",x:20,y:74}, {pos:"DF",label:"ZG",x:40,y:74}, {pos:"DF",label:"ZG",x:60,y:74}, {pos:"DF",label:"ZG",x:80,y:74},
    {pos:"MF",label:"VOL",x:35,y:58}, {pos:"MF",label:"VOL",x:65,y:58},
    {pos:"MF",label:"MEI",x:20,y:40}, {pos:"MF",label:"MEI",x:50,y:40}, {pos:"MF",label:"MEI",x:80,y:40},
    {pos:"FW",label:"CA",x:50,y:22}
  ],
  "3-5-2": [
    {pos:"GK",label:"GOL",x:50,y:92},
    {pos:"DF",label:"ZG",x:30,y:74}, {pos:"DF",label:"ZG",x:50,y:74}, {pos:"DF",label:"ZG",x:70,y:74},
    {pos:"MF",label:"MC",x:20,y:52}, {pos:"MF",label:"MC",x:40,y:52}, {pos:"MF",label:"MC",x:60,y:52}, {pos:"MF",label:"MC",x:80,y:52},
    {pos:"MF",label:"MEI",x:35,y:36}, {pos:"FW",label:"CA",x:65,y:36},
    {pos:"FW",label:"CA",x:50,y:22}
  ],
  "5-3-2": [
    {pos:"GK",label:"GOL",x:50,y:92},
    {pos:"DF",label:"LE",x:12,y:74}, {pos:"DF",label:"ZG",x:32,y:74}, {pos:"DF",label:"ZG",x:50,y:74}, {pos:"DF",label:"ZG",x:68,y:74}, {pos:"DF",label:"LD",x:88,y:74},
    {pos:"MF",label:"VOL",x:30,y:52}, {pos:"MF",label:"MC",x:50,y:52}, {pos:"MF",label:"MEI",x:70,y:52},
    {pos:"FW",label:"CA",x:35,y:22}, {pos:"FW",label:"CA",x:65,y:22}
  ],
  "3-4-3": [
    {pos:"GK",label:"GOL",x:50,y:92},
    {pos:"DF",label:"ZG",x:25,y:74}, {pos:"DF",label:"ZG",x:50,y:74}, {pos:"DF",label:"ZG",x:75,y:74},
    {pos:"MF",label:"MEI",x:20,y:52}, {pos:"MF",label:"VOL",x:40,y:52}, {pos:"MF",label:"MC",x:60,y:52}, {pos:"MF",label:"MEI",x:80,y:52},
    {pos:"FW",label:"PE",x:20,y:22}, {pos:"FW",label:"CA",x:50,y:22}, {pos:"FW",label:"PD",x:80,y:22}
  ],
  "4-5-1": [
    {pos:"GK",label:"GOL",x:50,y:92},
    {pos:"DF",label:"ZG",x:20,y:74}, {pos:"DF",label:"ZG",x:40,y:74}, {pos:"DF",label:"ZG",x:60,y:74}, {pos:"DF",label:"ZG",x:80,y:74},
    {pos:"MF",label:"MEI",x:15,y:52}, {pos:"MF",label:"VOL",x:32,y:52}, {pos:"MF",label:"MC",x:50,y:52}, {pos:"MF",label:"MEI",x:68,y:52}, {pos:"MF",label:"MEI",x:85,y:52},
    {pos:"FW",label:"CA",x:50,y:22}
  ]
};

async function renderLineup(panel) {
  let L = await api("/api/lineup");
  if (!L.ok) { panel.innerHTML = `<div class="placeholder">Inicie uma carreira para montar a escalação.</div>`; return; }

  // pool de todos os jogadores do clube
  const allPlayers = [...L.xi, ...L.bench];
  const allById = Object.fromEntries(allPlayers.map(p => [p.id, p]));

  let current = {
    formation: L.formation,
    style: L.style,
    xi: L.xi.map(p => p.id),
    positions: L.positions || {},
    selectedSlot: null
  };
  let selectedBenchId = null;

  function slotsFor(formation) {
    return FORMATION_SLOTS[formation] || FORMATION_SLOTS["4-3-3"];
  }

  function benchPlayers() {
    const xiSet = new Set(current.xi.filter(Boolean));
    return allPlayers.filter(p => !xiSet.has(p.id));
  }

  function playerById(id) {
    return allById[id];
  }

  function avgXi() {
    const ids = current.xi.filter(Boolean);
    if (!ids.length) return 0;
    const sum = ids.reduce((a, id) => a + (playerById(id)?.ovr || 0), 0);
    return (sum / ids.length).toFixed(1);
  }

  function validateXi() {
    const slots = slotsFor(current.formation);
    const ids = current.xi.filter(Boolean);
    const ok = ids.length === slots.length && new Set(ids).size === ids.length;
    return { ok, msg: ok ? "ok" : `escale ${slots.length} jogadores` };
  }

  function render() {
    const slots = slotsFor(current.formation);
    const bench = benchPlayers();
    const slotHtml = slots.map((s, i) => {
      const pid = current.xi[i];
      const p = pid ? playerById(pid) : null;
      const cls = p ? "filled" : "empty";
      const sel = current.selectedSlot === i ? " selected" : "";
      const inner = p
        ? `<span class="slot-pos">${s.label}</span><span class="slot-name" title="${p.name}">${p.name.split(" ").pop()}</span><span class="slot-ovr">${p.ovr}</span>`
        : `+`;
      return `<div class="slot ${cls}${sel}" style="left:${s.x}%;top:${s.y}%" data-slot="${i}">${inner}</div>`;
    }).join("");

    const MAX_BENCH = 12;
    const bench = benchPlayers().slice(0, MAX_BENCH);
    const extra = benchPlayers().length - MAX_BENCH;
    const benchRows = bench.map(p => {
      const sel = selectedBenchId === p.id ? " selected" : "";
      const star = p.star_player ? ' <span title="⭐ Futura promessa">⭐</span>' : '';
      const wonder = (p.potential && p.potential - p.ovr >= 8 && p.age <= 21) ? ' <span title="Wonderkid">🌟</span>' : '';
      return `<div class="bench-row${sel}" data-id="${p.id}">
        <span class="tag-pos ${p.pos}">${p.pos}</span>
        <span class="b-name">${p.name}${star}${wonder} <small>${p.role_label}</small></span>
        <span class="b-ovr">${p.ovr}</span>
      </div>`;
    }).join("");

    const v = validateXi();
    const validBadge = v.ok
      ? `<span class="lineup-valid">✓ ${v.msg}</span>`
      : `<span class="lineup-invalid">⚠ ${v.msg}</span>`;

    const styleOptions = ["equilibrado","ofensivo","defensivo"].map(s =>
      `<option value="${s}" ${current.style===s?"selected":""}>${cap(s)}</option>`).join("");
    const formOptions = L.formations.map(f =>
      `<option value="${f}" ${current.formation===f?"selected":""}>${f}</option>`).join("");

    panel.innerHTML = `
      <h2>📋 Escalação</h2>
      <div class="lineup-bar">
        <label>Formação <select id="lf-form">${formOptions}</select></label>
        <label>Estilo <select id="lf-style">${styleOptions}</select></label>
        <span class="lineup-avg">OVR médio: <b id="lf-avg">${avgXi()}</b></span>
        ${validBadge}
      </div>
      <div class="pitch-wrap">
        <div class="pitch">
          <div class="pitch-area bottom"></div>
          <div class="pitch-center"></div>
          <div class="pitch-area top"></div>
          ${slotHtml}
        </div>
        <div class="lineup-bench">
          <h4>Reservas ${bench.length}/${MAX_BENCH}${extra > 0 ? ` <span style="color:var(--c-yellow)">(+${extra} fora do banco)</span>` : ''}</h4>
          ${benchRows}
        </div>
      </div>
      <div class="lineup-actions">
        <button id="lf-auto">🔄 Auto-escalar</button>
        <button id="lf-save" class="btn-save">💾 Salvar escalação</button>
      </div>
      <p style="margin-top:10px;color:var(--txt-dim);font-size:12px">
        Clique no slot do campo e depois no reserva para trocar. Use Auto-escalar para preencher pela formação.
      </p>`;

    // Bind formação
    $("#lf-form").onchange = async (e) => {
      current.formation = e.target.value;
      current.selectedSlot = null;
      selectedBenchId = null;
      const r = await api("/api/lineup/auto", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({formation: current.formation})});
      if (r.ok) {
        const slots = slotsFor(current.formation);
        current.xi = r.xi.slice(0, slots.length);
        while (current.xi.length < slots.length) current.xi.push(null);
      }
      render();
    };

    // Bind estilo
    $("#lf-style").onchange = (e) => { current.style = e.target.value; };

    // Bind slots
    panel.querySelectorAll(".slot").forEach(el => {
      el.onclick = () => {
        const idx = parseInt(el.dataset.slot);
        // Se há um reserva selecionado, coloca ele no slot clicado
        if (selectedBenchId !== null) {
          current.xi[idx] = selectedBenchId;
          selectedBenchId = null;
          current.selectedSlot = null;
          render();
          return;
        }
        if (current.selectedSlot === null) {
          current.selectedSlot = idx;
          render();
          return;
        }
        if (current.selectedSlot === idx) {
          current.selectedSlot = null;
          render();
          return;
        }
        // troca entre slots
        const tmp = current.xi[current.selectedSlot];
        current.xi[current.selectedSlot] = current.xi[idx];
        current.xi[idx] = tmp;
        current.selectedSlot = null;
        render();
      };
    });

    // Bind banco
    panel.querySelectorAll(".bench-row").forEach(el => {
      el.onclick = () => {
        const id = parseInt(el.dataset.id);
        selectedBenchId = selectedBenchId === id ? null : id;
        render();
      };
    });

    // Auto
    $("#lf-auto").onclick = async () => {
      const r = await api("/api/lineup/auto", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({formation: current.formation})});
      if (r.ok) {
        const slots = slotsFor(current.formation);
        current.xi = r.xi.slice(0, slots.length);
        while (current.xi.length < slots.length) current.xi.push(null);
        render();
      }
    };

    // Save
    $("#lf-save").onclick = async () => {
      const ids = current.xi.filter(Boolean);
      const r = await api("/api/lineup/save", {
        method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify({formation: current.formation, style: current.style, xi: ids, positions: current.positions})
      });
      if (r.ok) {
        $("#lf-save").textContent = "✅ Salvo";
        setTimeout(() => $("#lf-save").textContent = "💾 Salvar escalação", 1200);
      } else {
        alert(r.msg || "Erro ao salvar");
      }
    };
  }

  render();
}

// ─── Jogar ───────────────────────────────────────────────────────────────────
async function renderPlay(panel) {
  const nx = await api("/api/next");
  panel.innerHTML = `
    <h2>▶️ Jogar</h2>
    <div class="next-box">
      <div class="next-label">Próximo: <b>${nx.label || "—"}</b></div>
      <button id="play-btn" class="btn-primary" style="width:auto;padding:12px 28px">▶️ Jogar rodada</button>
    </div>
    <div id="play-result"></div>`;
  $("#play-btn").onclick = () => runLiveMatch(panel);
}

async function runLiveMatch(panel) {
  panel.innerHTML = `
    <h2>▶️ Jogar</h2>
    <div id="live-root"></div>`;
  const root = $("#live-root");
  root.innerHTML = `<div class="placeholder">⏳ Carregando partidas...</div>`;

  const r = await api("/api/play/live", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
  if (!r.ok) {
    root.innerHTML = `<div class="placeholder">Não foi possível jogar a rodada.</div>`;
    return;
  }

  STATE = await api("/api/state");
  renderBanner();

  const your = r.matches.find(m => m.is_player) || r.matches[0];
  const others = r.matches.filter(m => !m.is_player);

  let events = [...(your.events || [])].sort((a, b) => a.m - b.m);
  let shown = 0;
  let homeGoals = 0, awayGoals = 0;

  function renderScore() {
    return `
      <div class="live-match">
        <div class="live-teams">
          <div class="live-team">
            <div class="live-abbr">${your.h_abbr}</div>
            <div class="live-name" title="${your.home}">${your.home}</div>
          </div>
          <div class="live-score">${homeGoals} × ${awayGoals}</div>
          <div class="live-team">
            <div class="live-abbr">${your.a_abbr}</div>
            <div class="live-name" title="${your.away}">${your.away}</div>
          </div>
        </div>
        <div class="live-minute" id="live-min">0'</div>
        <div class="live-events" id="live-events"></div>
        <div class="live-controls" id="live-controls">
          <button id="live-next" class="btn-primary" style="width:auto;padding:10px 22px">▶️ Avançar</button>
        </div>
      </div>`;
  }

  function eventIcon(kind) {
    if (kind === "goal") return "⚽";
    if (kind === "yellow") return "🟨";
    if (kind === "red") return "🟥";
    if (kind === "injury") return "🚑";
    if (kind === "sub") return "🔄";
    return "•";
  }

  function renderEventRow(e) {
    const cls = e.kind;
    return `<div class="live-event ${cls}">
      <span class="min">${e.m}'</span>
      <span class="icon">${eventIcon(e.kind)}</span>
      <span class="text">${e.team === "H" ? your.home : your.away}: ${e.text}</span>
    </div>`;
  }

  root.innerHTML = renderScore();
  const eventsBox = $("#live-events");
  const minBox = $("#live-min");

  function updateGoals() {
    // recalcula gols a partir dos eventos já mostrados
    homeGoals = 0; awayGoals = 0;
    for (let i = 0; i < shown; i++) {
      const e = events[i];
      if (e.kind === "goal") e.team === "H" ? homeGoals++ : awayGoals++;
    }
    root.querySelector(".live-score").textContent = `${homeGoals} × ${awayGoals}`;
  }

  async function step() {
    if (shown >= events.length) {
      minBox.textContent = "Fim de jogo";
      $("#live-controls").innerHTML = `<div class="live-finished">✅ Rodada ${r.round}/${r.n} finalizada</div>
        <button id="live-table" class="btn-primary" style="width:auto;margin-top:12px;padding:10px 22px">📊 Ver classificação</button>`;
      $("#live-table").onclick = () => renderPlayResultFull(panel, r);
      return;
    }
    const e = events[shown++];
    minBox.textContent = e.m + "'";
    eventsBox.insertAdjacentHTML("afterbegin", renderEventRow(e));
    updateGoals();
  }

  $("#live-next").onclick = step;

  // avança automaticamente até o próximo gol ou até 90'
  async function autoPlay() {
    while (shown < events.length) {
      await step();
      const last = events[shown - 1];
      if (last.kind === "goal" || last.m >= 90) break;
      await new Promise(res => setTimeout(res, 250));
    }
  }
  autoPlay();

  // Se houver outros jogos, mostra abaixo
  if (others.length) {
    root.insertAdjacentHTML("beforeend", `<h3 style="margin:18px 0 10px;color:var(--txt-dim);font-size:14px">Outros jogos</h3>
      <div class="other-matches" id="other-matches"></div>`);
    $("#other-matches").innerHTML = others.map(m => {
      const ev = (m.events || []).filter(e => e.kind === "goal");
      const hg = ev.filter(e => e.team === "H").length;
      const ag = ev.filter(e => e.team === "A").length;
      return `<div class="other-match">
        <div>${m.h_abbr} × ${m.a_abbr}</div>
        <div class="res">${hg} × ${ag}</div>
      </div>`;
    }).join("");
  }
}

function renderPlayResultFull(panel, r) {
  const rows = r.table.map(t => `
    <tr class="${t.is_player ? 'row-player' : ''} ${t.zone === 'cl' ? 'zone-cl' : (t.zone === 'rel' ? 'zone-rel' : '')}">
      <td class="pos-cell">${t.pos}</td>
      <td>${t.name}${t.is_player ? ' ◀' : ''}</td>
      <td class="center">${t.played}</td>
      <td class="center">${t.wins}</td>
      <td class="center">${t.draws}</td>
      <td class="center">${t.losses}</td>
      <td class="center">${t.gf}</td>
      <td class="center">${t.ga}</td>
      <td class="center">${t.gd >= 0 ? '+' : ''}${t.gd}</td>
      <td class="center ovr">${t.points}</td>
    </tr>`).join("");
  panel.innerHTML = `
    <h2>📊 Classificação — Rodada ${r.round}/${r.n}</h2>
    <table>
      <thead><tr><th>#</th><th>Clube</th><th class="center">J</th><th class="center">V</th>
        <th class="center">E</th><th class="center">D</th><th class="center">GP</th>
        <th class="center">GC</th><th class="center">SG</th><th class="center">Pts</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
    <p style="margin-top:12px;color:var(--txt-dim);font-size:12px">
      <span style="color:#2ea043">▌</span> Libertadores &nbsp;
      <span style="color:#d9544d">▌</span> Rebaixamento &nbsp; ◀ você</p>`;
}

function renderPlayResult(r) {
  if (r.kind === "league") {
    const yr = r.your ? `<div class="res-your">📋 ${r.your.home} <b>${r.your.hg} x ${r.your.ag}</b> ${r.your.away}</div>` : "";
    const rows = r.table.map(t => `<tr class="${t.is_player ? 'row-player' : ''}">
      <td>${t.pos}</td><td>${t.name}</td><td class="center ovr">${t.pts}</td><td class="center">${t.j}</td></tr>`).join("");
    return `<div class="res-card"><h3>Rodada ${r.round}/${r.n} — você ${r.pos}º</h3>${yr}
      <table style="margin-top:8px"><thead><tr><th>#</th><th>Clube</th><th class="center">Pts</th><th class="center">J</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }
  if (r.kind === "copa") {
    const lines = r.lines.map(l => `<div class="res-line">${l.trim()}</div>`).join("");
    let foot = "";
    if (r.champion) foot = `<div class="res-champ">🏆 Campeão: ${r.champion}${r.won ? " — VOCÊ! 🎉" : ""}</div>`;
    else if (r.advanced) foot = `<div class="res-ok">✅ Você avançou! +€4M</div>`;
    else if (r.eliminated) foot = `<div class="res-bad">❌ Eliminado.</div>`;
    return `<div class="res-card"><h3>🏆 ${r.comp_name} — ${r.stage}</h3>${lines}${foot}</div>`;
  }
  if (r.kind === "estadual") {
    const groups = Object.entries(r.groups).map(([g, rows]) =>
      `<div class="res-line"><b>Grupo ${g}:</b> ${rows.map(x => `${x.name.split(' ').pop()}${x.is_player ? '◀' : ''}(${x.pts})`).join("  ")}</div>`).join("");
    const ko = r.log.map(b => `<pre class="res-pre">${b}</pre>`).join("");
    return `<div class="res-card"><h3>🏆 ${r.name}</h3>${groups}${ko}
      <div class="res-champ">Campeão: ${r.champion} · você: ${r.player_stage}${r.prize ? ` · +€${(r.prize/1e6).toFixed(1)}M` : ""}</div></div>`;
  }
  if (r.kind === "season_end") {
    const f = r.fin, rep = r.rep;
    let sack = "";
    if (r.sacked) sack = r.rehired ? `<div class="res-ok">🚪 Demitido — contratado pelo ${r.rehired}!</div>`
                                   : `<div class="res-bad">🚪 DEMITIDO — carreira encerrada.</div>`;
    return `<div class="res-card"><h3>🏁 Fim de temporada — ${r.champion} campeão · você ${r.pos}º</h3>
      <div class="res-line">💰 Saldo: ${f.net >= 0 ? '+' : '−'}€${Math.abs(f.net/1e6).toFixed(1)}M · caixa €${(f.money_after/1e6).toFixed(1)}M</div>
      <div class="res-line">👔 Reputação: ${rep.old_rep} → ${rep.new_rep}</div>${sack}</div>`;
  }
  return "";
}

async function renderSquad(panel) {
  const sq = await api("/api/squad");
  const rows = sq.map(p => {
    const starBadge = p.star_player ? ' <span title="⭐ Estrela do clube">⭐</span>' : '';
    const potStar = (p.potential && p.potential - p.overall >= 8 && p.age <= 21) ? ' <span class="star" title="Wonderkid">⭐</span>' : '';
    const loan = p.loan ? ' 🔁' : '';
    const pot = (p.potential && p.potential > p.overall) ? `<span class="pot">${p.potential}</span>` : '—';
    let marketBtn = '';
    if (!p.loan) {
      const selVal = p.transfer_listed ? 'sale' : (p.loan_listed ? 'loan' : 'none');
      marketBtn = `<select class="market-sel" data-id="${p.id}" title="Mercado">
        <option value="none" ${selVal==='none'?'selected':''}>Indisp.</option>
        <option value="sale" ${selVal==='sale'?'selected':''}>À venda</option>
        <option value="loan" ${selVal==='loan'?'selected':''}>Empréstimo</option>
      </select>`;
    }
    return `<tr>
      <td><span class="tag-pos ${p.position}">${p.position}</span></td>
      <td>${p.name}${starBadge}${potStar}${loan}</td>
      <td class="center">${p.age}</td>
      <td class="center ovr">${p.overall}</td>
      <td class="center">${pot}</td>
      <td class="right">${p.value_fmt}</td>
      <td class="right">${p.wage_fmt}</td>
      <td class="center">${p.contract || '—'}</td>
      <td>${marketBtn}</td>
    </tr>`;
  }).join("");
  const avg = sq.length ? (sq.reduce((a, p) => a + p.overall, 0) / sq.length).toFixed(1) : 0;
  const squadCap = 30;
  const overCap = sq.length > squadCap ? ` <span style="color:var(--c-red)">(EXCEDE LIMITE DE ${squadCap})</span>` : '';
  panel.innerHTML = `
    <h2>Elenco — ${STATE.club.name} <span style="color:var(--txt-dim);font-weight:400">(${sq.length}/${squadCap} jogadores · OVR médio ${avg})${overCap}</span></h2>
    <table>
      <thead><tr><th>Pos</th><th>Nome</th><th class="center">Id</th><th class="center">OVR</th>
        <th class="center">POT</th><th class="right">Valor</th><th class="right">Salário</th><th class="center">Contr.</th><th>Mercado</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;

  // Bind selects
  panel.querySelectorAll('.market-sel').forEach(sel => {
    sel.onchange = async (e) => {
      const pid = parseInt(e.target.dataset.id);
      const status = e.target.value;
      const r = await api('/api/player/market', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({player_id:pid, status}) });
      if (r.ok) {
        e.target.style.borderColor = status==='none' ? '' : '#e3b341';
      } else {
        alert(r.msg || 'Erro');
        e.target.value = selVal; // revert
      }
    };
  });
}

async function renderTable(panel) {
  const t = await api("/api/table");
  if (!t.rows.length) {
    panel.innerHTML = `<div class="placeholder">Sem classificação ainda. Jogue uma temporada.</div>`;
    return;
  }
  const rows = t.rows.map(r => `
    <tr class="${r.is_player ? 'row-player' : ''} ${r.zone === 'cl' ? 'zone-cl' : (r.zone === 'rel' ? 'zone-rel' : '')}">
      <td class="pos-cell">${r.pos}</td>
      <td><span class="color-bar" style="background:${r.colors.primary}"></span>${r.name}${r.is_player ? ' ◀' : ''}</td>
      <td class="center">${r.played}</td><td class="center">${r.wins}</td>
      <td class="center">${r.draws}</td><td class="center">${r.losses}</td>
      <td class="center">${r.gf}</td><td class="center">${r.ga}</td>
      <td class="center">${r.gd >= 0 ? '+' : ''}${r.gd}</td>
      <td class="center ovr">${r.points}</td>
    </tr>`).join("");
  panel.innerHTML = `
    <h2>Classificação — Temporada ${t.season}</h2>
    <table>
      <thead><tr><th>#</th><th>Clube</th><th class="center">J</th><th class="center">V</th>
        <th class="center">E</th><th class="center">D</th><th class="center">GP</th>
        <th class="center">GC</th><th class="center">SG</th><th class="center">Pts</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
    <p style="margin-top:12px;color:var(--txt-dim);font-size:12px">
      <span style="color:#2ea043">▌</span> Libertadores &nbsp;
      <span style="color:#d9544d">▌</span> Rebaixamento &nbsp; ◀ você</p>`;
}


// ─── Finanças ────────────────────────────────────────────────────────────────
async function renderFinance(panel) {
  const d = await api("/api/finance");
  if (!d.ok) { panel.innerHTML = `<div class="placeholder">Inicie uma carreira.</div>`; return; }
  const t = d.ticket;
  const histRows = d.history.map(h => `
    <tr>
      <td>${h.season}</td><td class="center">${h.pos}</td><td class="center">${h.titles}</td>
      <td>${h.revenue_fmt}</td><td>${h.cost_fmt}</td><td class="${h.net>=0?'green':'red'}">${h.net_fmt}</td>
      <td>${h.money_after_fmt}</td>
    </tr>`).join("");
  panel.innerHTML = `
    <h2>💰 Finanças</h2>
    <div class="finance-cards" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:18px">
      <div class="res-card"><div style="font-size:12px;color:var(--txt-dim)">Caixa</div><div style="font-size:22px;font-weight:800">${d.money_fmt}</div></div>
      <div class="res-card"><div style="font-size:12px;color:var(--txt-dim)">Folha salarial/ano</div><div style="font-size:22px;font-weight:800">${d.wage_bill_fmt}</div></div>
      <div class="res-card"><div style="font-size:12px;color:var(--txt-dim)">Orçamento</div><div style="font-size:22px;font-weight:800">${d.budget_fmt}</div></div>
      <div class="res-card"><div style="font-size:12px;color:var(--txt-dim)">Receita de ingressos</div><div style="font-size:22px;font-weight:800">${t.revenue_fmt}</div></div>
    </div>
    <div class="res-card" style="margin-bottom:18px">
      <h3>🎟️ Ingressos</h3>
      <p>Preço atual: <b>€${t.price}</b> · base: €${t.base} · Público: ${t.public} (${t.fill}% de lotação)</p>
    </div>
    <h3>📈 Histórico por temporada</h3>
    <table>
      <thead><tr><th>Temp</th><th class="center">Pos</th><th class="center">Tít</th><th>Receita</th><th>Custo</th><th>Saldo</th><th>Caixa final</th></tr></thead>
      <tbody>${histRows}</tbody>
    </table>`;
}

// ─── Estádio & CT ─────────────────────────────────────────────────────────────
async function renderStadium(panel) {
  const d = await api("/api/stadium");
  if (!d.ok) { panel.innerHTML = `<div class="placeholder">Inicie uma carreira.</div>`; return; }
  panel.innerHTML = `
    <h2>🏟️ Estádio & CT</h2>
    <div class="res-card" style="margin-bottom:14px">
      <h3>🏟️ Estádio</h3>
      <p>Capacidade: <b>${d.capacity.toLocaleString()}</b></p>
      <p>Preço do ingresso: <b>€${d.price}</b> · base sugerido: €${d.base}</p>
      <p>Público estimado: <b>${d.public.toLocaleString()}</b> (${d.fill}% de lotação)</p>
      <p>Receita estimada: <b>${d.revenue_fmt}</b></p>
      <p>Torcidômetro: <b>${d.fan_mood}%</b></p>
      <div style="margin-top:10px;display:flex;gap:8px;align-items:center">
        <input id="st-price" type="number" value="${d.price}" min="1" max="3000" style="width:90px;padding:8px;border-radius:6px;border:1px solid var(--line);background:var(--bg2);color:var(--txt)">
        <button id="st-save" class="btn-primary" style="width:auto;padding:10px 18px">Salvar ingresso</button>
      </div>
    </div>
    <div class="res-card">
      <h3>🏋️ Centro de Treinamento</h3>
      <p>Nível: <b>${d.training}/5</b></p>
      <p>Custo anual: <b>${d.training_cost_fmt}</b></p>
      <p>Foco: <b>${cap(d.training_focus)}</b></p>
      <div style="margin-top:10px;display:flex;gap:8px;align-items:center;flex-wrap:wrap">
        <label>Nível: <input id="st-train" type="range" min="1" max="5" value="${d.training}" style="width:140px"></label>
        <span id="st-train-val" style="font-weight:800">${d.training}</span>
        <select id="st-focus" style="padding:8px;border-radius:6px;border:1px solid var(--line);background:var(--bg2);color:var(--txt)">
          ${d.training_focuses.map(f => `<option value="${f}" ${f===d.training_focus?'selected':''}>${cap(f)}</option>`).join('')}
        </select>
        <button id="st-save-ct" class="btn-primary" style="width:auto;padding:10px 18px">Salvar CT</button>
      </div>
    </div>`;
  $("#st-train").oninput = (e) => $("#st-train-val").textContent = e.target.value;
  $("#st-save").onclick = async () => {
    const price = parseInt($("#st-price").value);
    const r = await api("/api/stadium/save", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({price, training: d.training, focus: d.training_focus})});
    if (r.ok) renderStadium(panel);
  };
  $("#st-save-ct").onclick = async () => {
    const training = parseInt($("#st-train").value);
    const focus = $("#st-focus").value;
    const r = await api("/api/stadium/save", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({price: d.price, training, focus})});
    if (r.ok) renderStadium(panel);
  };
}

// ─── Mercado ──────────────────────────────────────────────────────────────────
async function renderMarket(panel) {
  panel.innerHTML = `<h2>💰 Mercado</h2><div class="placeholder">⏳ Carregando...</div>`;
  const d = await api("/api/market?limit=100");
  if (!d.ok) { panel.innerHTML = `<div class="placeholder">Inicie uma carreira.</div>`; return; }
  panel.innerHTML = `
    <h2>💰 Mercado</h2>
    <div class="res-card" style="margin-bottom:14px;display:flex;gap:12px;flex-wrap:wrap;align-items:center">
      <span>Caixa: <b>${d.money_fmt}</b></span>
      <label>Posição: <select id="mk-pos"><option value="">Todas</option><option value="GK">GOL</option><option value="DF">ZAG</option><option value="MF">MEI</option><option value="FW">ATA</option></select></label>
      <label>Máx preço: <input id="mk-price" type="number" placeholder="€" style="width:90px"></label>
      <label>Min OVR: <input id="mk-ovr" type="number" value="60" min="40" max="99" style="width:60px"></label>
      <label><input id="mk-sale" type="checkbox"> À venda</label>
      <button id="mk-search" class="btn-primary" style="width:auto;padding:10px 18px">Buscar</button>
    </div>
    <div id="mk-list" class="squad-list"></div>`;
  function row(p) {
    return `<div class="squad-row">
      <span class="tag-pos ${p.pos}">${p.pos}</span>
      <span class="sq-name">${p.name} <small>${p.role_label} · ${p.age} anos · ${p.nat}</small></span>
      <span class="sq-club" style="color:var(--txt-dim)">${p.club}</span>
      <span class="sq-ovr">OVR ${p.ovr} · POT ${p.pot}</span>
      <span class="sq-value">${p.asking_fmt}</span>
      <button class="btn-primary mk-buy" data-id="${p.id}" data-asking="${p.asking}" style="width:auto;padding:6px 12px;font-size:12px">Comprar</button>
    </div>`;
  }
  $("#mk-list").innerHTML = d.players.map(row).join("");
  $("#mk-search").onclick = async () => {
    const pos = $("#mk-pos").value || null;
    const maxp = $("#mk-price").value ? parseInt($("#mk-price").value) : null;
    const mino = parseInt($("#mk-ovr").value) || 0;
    const sale = $("#mk-sale").checked;
    const qs = new URLSearchParams({limit: "100", min_ovr: mino, max_ovr: "99", ...(pos && {position: pos}), ...(maxp && {max_price: maxp}), ...(sale && {only_transfer: "1"})});
    const d2 = await api(`/api/market?${qs}`);
    $("#mk-list").innerHTML = d2.players.map(row).join("");
    bindBuy();
  };
  function bindBuy() {
    panel.querySelectorAll(".mk-buy").forEach(b => {
      b.onclick = async () => {
        const id = parseInt(b.dataset.id);
        const asking = parseInt(b.dataset.asking);
        const r = await api("/api/market/buy", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({player_id: id, price: asking})});
        alert(r.msg || (r.ok ? "Contratado!" : "Negócio recusado."));
        if (r.ok) renderMarket(panel);
      };
    });
  }
  bindBuy();
}

// ─── Buscar Time ──────────────────────────────────────────────────────────────
async function renderSearchTeam(panel) {
  panel.innerHTML = `
    <h2>🔍 Buscar Time</h2>
    <div class="res-card" style="margin-bottom:14px;display:flex;gap:10px">
      <input id="st-term" type="text" placeholder="Nome do clube..." style="flex:1;padding:10px;border-radius:6px;border:1px solid var(--line);background:var(--bg2);color:var(--txt)">
      <button id="st-search" class="btn-primary" style="width:auto;padding:10px 18px">Buscar</button>
    </div>
    <div id="st-results"></div>`;
  $("#st-search").onclick = async () => {
    const term = $("#st-term").value;
    const d = await api(`/api/search-clubs?term=${encodeURIComponent(term)}`);
    $("#st-results").innerHTML = d.clubs.map(c => `
      <div class="res-card club-card" data-id="${c.id}" style="cursor:pointer;margin-bottom:8px">
        <b>${c.name}</b> · prestígio ${c.prestige}
      </div>`).join("");
    panel.querySelectorAll(".club-card").forEach(el => {
      el.onclick = async () => {
        const id = parseInt(el.dataset.id);
        const s = await api(`/api/club-squad?id=${id}`);
        $("#st-results").innerHTML = `
          <h3>${s.club.name} · elenco (${s.count})</h3>
          <div class="squad-list">
            ${s.players.map(p => `
              <div class="squad-row">
                <span class="tag-pos ${p.pos}">${p.pos}</span>
                <span class="sq-name">${p.name} <small>${p.role_label} · ${p.age} anos</small></span>
                <span class="sq-ovr">OVR ${p.ovr} · POT ${p.pot}</span>
                <span class="sq-value">${p.value_fmt}</span>
              </div>`).join("")}
          </div>`;
      };
    });
  };
}

// ─── Scout ────────────────────────────────────────────────────────────────────
async function renderScout(panel) {
  panel.innerHTML = `<h2>⭐ Scout</h2><div class="placeholder">⏳ Carregando...</div>`;
  const d = await api("/api/scout");
  if (!d.ok) { panel.innerHTML = `<div class="placeholder">Inicie uma carreira.</div>`; return; }
  panel.innerHTML = `
    <h2>⭐ Scout</h2>
    <div class="res-card" style="margin-bottom:14px;display:flex;gap:10px;align-items:center">
      <label>Min OVR: <input id="sc-ovr" type="number" value="70" min="50" max="99" style="width:60px"></label>
      <button id="sc-search" class="btn-primary" style="width:auto;padding:10px 18px">Buscar talentos</button>
    </div>
    <div id="sc-list" class="squad-list">
      ${d.players.map(p => `
        <div class="squad-row">
          <span class="tag-pos ${p.pos}">${p.pos}</span>
          <span class="sq-name">${p.name} <small>${p.role_label} · ${p.age} anos · ${p.nat} · ${p.club}</small></span>
          <span class="sq-ovr">OVR ${p.ovr} · POT ${p.pot}</span>
          <span class="sq-value">${p.asking_fmt}</span>
        </div>`).join("")}
    </div>`;
  $("#sc-search").onclick = async () => {
    const ovr = parseInt($("#sc-ovr").value) || 60;
    const d2 = await api(`/api/scout?min_ovr=${ovr}`);
    $("#sc-list").innerHTML = d2.players.map(p => `
      <div class="squad-row">
        <span class="tag-pos ${p.pos}">${p.pos}</span>
        <span class="sq-name">${p.name} <small>${p.role_label} · ${p.age} anos · ${p.nat} · ${p.club}</small></span>
        <span class="sq-ovr">OVR ${p.ovr} · POT ${p.pot}</span>
        <span class="sq-value">${p.asking_fmt}</span>
      </div>`).join("");
  };
}

// ─── Histórico ─────────────────────────────────────────────────────────────────
async function renderHistory(panel) {
  const d = await api("/api/history");
  if (!d.ok) { panel.innerHTML = `<div class="placeholder">Inicie uma carreira.</div>`; return; }
  const rows = d.matches.map(m => `
    <tr class="${m.result==='V'?'row-player':(m.result==='D'?'zone-rel':'')}">
      <td class="center">${m.season}</td>
      <td class="center">${m.round}</td>
      <td>${m.home}</td>
      <td class="center ovr">${m.hg} × ${m.ag}</td>
      <td>${m.away}</td>
      <td class="center"><b>${m.result}</b></td>
      <td class="center">${m.cards}</td>
    </tr>`).join("");
  panel.innerHTML = `
    <h2>📜 Histórico de Partidas</h2>
    <table>
      <thead><tr><th class="center">Temp</th><th class="center">Rod</th><th>Mandante</th><th class="center">Placar</th><th>Visitante</th><th class="center">Res</th><th class="center">Cartões</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

// ─── Util ──────────────────────────────────────────────────────────────────────
// ─── Util ──────────────────────────────────────────────────────────────────────
const PREF = new Set(["cr","se","fc","ec","sc","ac","ca","rb","afc","ss","as","sl","rc","cf","us"]);
function abbr(name) {
  let t = name.split(" ").filter(Boolean);
  while (t.length && PREF.has(t[0].toLowerCase().replace(".", ""))) t.shift();
  return (t[0] || name).slice(0, 3).toUpperCase();
}
const cap = (s) => s ? s[0].toUpperCase() + s.slice(1) : s;

boot();
