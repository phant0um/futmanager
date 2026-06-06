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
  if (view === "tabela") return renderTable(panel);
  if (view === "jogar") return renderPlay(panel);
  panel.innerHTML = `<div class="placeholder">🚧 "${cap(view)}" — em construção no front web.<br>
    Disponível no modo terminal por enquanto.</div>`;
}

// ─── Jogar ───────────────────────────────────────────────────────────────────
async function renderPlay(panel, result) {
  const nx = await api("/api/next");
  let resHtml = "";
  if (result) resHtml = renderPlayResult(result);
  panel.innerHTML = `
    <h2>▶️ Jogar</h2>
    <div class="next-box">
      <div class="next-label">Próximo: <b>${nx.label || "—"}</b></div>
      <button id="play-btn" class="btn-primary" style="width:auto;padding:12px 28px">▶️ Jogar</button>
    </div>
    <div id="play-result">${resHtml}</div>`;
  $("#play-btn").onclick = async () => {
    $("#play-btn").disabled = true;
    $("#play-btn").textContent = "⏳ Simulando...";
    const r = await api("/api/play", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
    STATE = await api("/api/state");
    renderBanner();
    renderPlay(panel, r);
  };
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
    const star = (p.potential && p.potential - p.overall >= 8 && p.age <= 21) ? ' <span class="star">⭐</span>' : '';
    const loan = p.loan ? ' 🔁' : '';
    const pot = (p.potential && p.potential > p.overall) ? `<span class="pot">${p.potential}</span>` : '—';
    return `<tr>
      <td><span class="tag-pos ${p.position}">${p.position}</span></td>
      <td>${p.name}${star}${loan}</td>
      <td class="center">${p.age}</td>
      <td class="center ovr">${p.overall}</td>
      <td class="center">${pot}</td>
      <td class="right">${p.value_fmt}</td>
      <td class="right">${p.wage_fmt}</td>
      <td class="center">${p.contract || '—'}</td>
    </tr>`;
  }).join("");
  const avg = sq.length ? (sq.reduce((a, p) => a + p.overall, 0) / sq.length).toFixed(1) : 0;
  panel.innerHTML = `
    <h2>Elenco — ${STATE.club.name} <span style="color:var(--txt-dim);font-weight:400">(${sq.length} jogadores · OVR médio ${avg})</span></h2>
    <table>
      <thead><tr><th>Pos</th><th>Nome</th><th class="center">Id</th><th class="center">OVR</th>
        <th class="center">POT</th><th class="right">Valor</th><th class="right">Salário</th><th class="center">Contr.</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
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

// ─── Util ──────────────────────────────────────────────────────────────────────
const PREF = new Set(["cr","se","fc","ec","sc","ac","ca","rb","afc","ss","as","sl","rc","cf","us"]);
function abbr(name) {
  let t = name.split(" ").filter(Boolean);
  while (t.length && PREF.has(t[0].toLowerCase().replace(".", ""))) t.shift();
  return (t[0] || name).slice(0, 3).toUpperCase();
}
const cap = (s) => s ? s[0].toUpperCase() + s.slice(1) : s;

boot();
