"""
FUTMANAGER — GUI nativa (Tkinter, stdlib).
Janela desktop. Zero servidor, zero browser. Reusa gameapi (motor I/O-free).
Uso:  python3 -m gui.app   ou   python3 gui/app.py
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import gameapi as G

# ─── Tema (claro, alto contraste) ────────────────────────────────────────────
BG = "#eef1ef"      # fundo geral (cinza-claro)
BG2 = "#ffffff"     # topbar / sidebar / inputs
PANEL = "#ffffff"   # cards / tabelas
PANEL2 = "#e4eae6"  # botão secundário / cabeçalho tabela
LINE = "#cdd6d1"    # bordas
GREEN = "#1f8f3a"   # botões / acentos
GREEN_D = "#15692b" # hover / linha do jogador
GOLD = "#9a6b00"    # destaque dourado (escuro p/ ler em branco)
TXT = "#16201b"     # texto principal (quase preto)
DIM = "#5b6e64"     # texto secundário
RED = "#c0392b"
F = "Helvetica"


def with_conn(fn):
    c = G.conn()
    try:
        return fn(c)
    finally:
        c.close()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FUTMANAGER")
        self.geometry("1080x720")
        self.minsize(940, 620)
        self.configure(bg=BG)
        self._init_style()
        self.view = "jogar"
        self.root_frame = tk.Frame(self, bg=BG)
        self.root_frame.pack(fill="both", expand=True)
        self.show_saves()

    def _init_style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("Dark.Treeview", background=PANEL, fieldbackground=PANEL,
                    foreground=TXT, rowheight=26, borderwidth=0, font=(F, 12))
        s.configure("Dark.Treeview.Heading", background=PANEL2, foreground=DIM,
                    font=(F, 10, "bold"), borderwidth=0, relief="flat")
        s.map("Dark.Treeview", background=[("selected", GREEN_D)],
              foreground=[("selected", "#ffffff")])
        s.configure("TCombobox", fieldbackground=BG2, background=PANEL2, foreground=TXT,
                    arrowcolor=TXT)

    # ─── helpers de UI ────────────────────────────────────────────────────────
    def _clear(self):
        for w in self.root_frame.winfo_children():
            w.destroy()

    def _btn(self, parent, text, cmd, bg=GREEN, fg="#fff", **kw):
        # tk.Button no Aqua (macOS) ignora bg/activebackground (fica cinza nativo)
        # mas respeita fg — resultava em texto branco sobre fundo claro, ilegível.
        # Label clicável respeita as cores em qualquer plataforma.
        kw.setdefault("padx", 14)
        kw.setdefault("pady", 8)
        active_bg = kw.pop("activebackground", GREEN_D)
        active_fg = kw.pop("activeforeground", fg)
        b = tk.Label(parent, text=text, bg=bg, fg=fg, font=(F, 12, "bold"),
                     cursor="hand2", **kw)
        b.bind("<Enter>", lambda e: b.configure(bg=active_bg, fg=active_fg))
        b.bind("<Leave>", lambda e: b.configure(bg=bg, fg=fg))
        b.bind("<Button-1>", lambda e: cmd())
        return b

    # ════════════════════════════════════════════════════════════════════════
    #  TELA SAVES
    # ════════════════════════════════════════════════════════════════════════
    def show_saves(self):
        self._clear()
        wrap = tk.Frame(self.root_frame, bg=BG)
        wrap.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(wrap, text="⚽ FUTMANAGER", fg=GREEN, bg=BG, font=(F, 30, "bold")).pack(pady=(0, 2))
        tk.Label(wrap, text="gestão de futebol", fg=DIM, bg=BG, font=(F, 13)).pack(pady=(0, 18))

        box = tk.Frame(wrap, bg=PANEL, padx=22, pady=20, highlightbackground=LINE,
                       highlightthickness=1)
        box.pack()
        tk.Label(box, text="CARREGAR JOGO", fg=DIM, bg=PANEL, font=(F, 10, "bold")).pack(anchor="w")

        saves = G.api_saves()
        lst = tk.Frame(box, bg=PANEL)
        lst.pack(fill="x", pady=8)
        if not saves:
            tk.Label(lst, text="Nenhum jogo salvo ainda.", fg=DIM, bg=PANEL,
                     font=(F, 12), pady=14).pack()
        for sv in saves:
            self._save_row(lst, sv)

        self._btn(box, "+ Novo jogo", self.show_new_career).pack(fill="x", pady=(10, 0))

    def _save_row(self, parent, sv):
        row = tk.Frame(parent, bg=BG2, padx=12, pady=10, highlightbackground=LINE,
                       highlightthickness=1, width=420)
        row.pack(fill="x", pady=4)
        label = sv.get("club", "?")
        meta = (f"{sv.get('coach','?')} · temp. {sv.get('season','?')} · "
                f"{sv.get('titles',0)} títulos"
                + (" · DEMITIDO" if sv.get("status") == "sacked" else ""))
        info = tk.Frame(row, bg=BG2)
        info.pack(side="left", fill="x", expand=True)
        tk.Label(info, text=label, fg=TXT, bg=BG2, font=(F, 13, "bold"), anchor="w").pack(anchor="w")
        tk.Label(info, text=meta, fg=DIM, bg=BG2, font=(F, 11), anchor="w").pack(anchor="w")
        self._btn(row, "Jogar", lambda s=sv: self._load_save(s["slug"]),
                  bg=GREEN, padx=10, pady=4).pack(side="right", padx=(6, 0))
        self._btn(row, "✕", lambda s=sv: self._del_save(s["slug"]),
                  bg=PANEL2, fg=DIM, padx=8, pady=4).pack(side="right")

    def _load_save(self, slug):
        G.save_load(slug)
        self.view = "jogar"
        self.show_hub()

    def _del_save(self, slug):
        if messagebox.askyesno("Apagar jogo", "Apagar este save? Não dá pra desfazer."):
            G.save_delete(slug)
            self.show_saves()

    # ════════════════════════════════════════════════════════════════════════
    #  NOVA CARREIRA
    # ════════════════════════════════════════════════════════════════════════
    def show_new_career(self):
        self._clear()
        wrap = tk.Frame(self.root_frame, bg=BG)
        wrap.place(relx=0.5, rely=0.5, anchor="center")
        box = tk.Frame(wrap, bg=PANEL, padx=28, pady=24, highlightbackground=LINE,
                       highlightthickness=1)
        box.pack()
        tk.Label(box, text="Novo jogo", fg=GREEN, bg=PANEL, font=(F, 20, "bold")).pack(pady=(0, 16))

        leagues = with_conn(G.api_leagues)
        self._lg_map = {f"{l['name']} ({l['country']})": l["id"] for l in leagues}

        tk.Label(box, text="LIGA", fg=DIM, bg=PANEL, font=(F, 10, "bold")).pack(anchor="w")
        self.cb_league = ttk.Combobox(box, values=list(self._lg_map.keys()), state="readonly",
                                      width=34, font=(F, 12))
        self.cb_league.pack(pady=(2, 12), fill="x")
        self.cb_league.bind("<<ComboboxSelected>>", lambda e: self._reload_clubs())

        tk.Label(box, text="CLUBE", fg=DIM, bg=PANEL, font=(F, 10, "bold")).pack(anchor="w")
        self.cb_club = ttk.Combobox(box, values=[], state="readonly", width=34, font=(F, 12))
        self.cb_club.pack(pady=(2, 12), fill="x")

        tk.Label(box, text="SEU NOME (técnico)", fg=DIM, bg=PANEL, font=(F, 10, "bold")).pack(anchor="w")
        self.en_coach = tk.Entry(box, bg=BG2, fg=TXT, insertbackground=TXT, font=(F, 12),
                                 relief="flat", width=34)
        self.en_coach.pack(pady=(2, 16), fill="x", ipady=5)

        self._btn(box, "Começar carreira", self._do_create).pack(fill="x")
        self._btn(box, "← Voltar", self.show_saves, bg=PANEL2, fg=DIM).pack(fill="x", pady=(8, 0))

        # pré-seleciona Brasileirão se existir
        br = next((k for k in self._lg_map if "(BR)" in k), None)
        if br:
            self.cb_league.set(br)
            self._reload_clubs()

    def _reload_clubs(self):
        lid = self._lg_map.get(self.cb_league.get())
        if not lid:
            return
        clubs = with_conn(lambda c: G.api_clubs(c, lid))
        self._cl_map = {f"{cl['name']}  (prestígio {cl['prestige']})": cl["id"] for cl in clubs}
        self.cb_club["values"] = list(self._cl_map.keys())
        if clubs:
            self.cb_club.current(0)

    def _do_create(self):
        cid = getattr(self, "_cl_map", {}).get(self.cb_club.get())
        if not cid:
            messagebox.showwarning("Falta clube", "Escolha um clube.")
            return
        name = self.en_coach.get().strip() or "Técnico"
        r = G.create_career(cid, name)
        if not r.get("ok"):
            messagebox.showerror("Erro", r.get("error", "falha ao criar"))
            return
        self.view = "jogar"
        self.show_hub()

    # ════════════════════════════════════════════════════════════════════════
    #  HUB (topbar + banner + sidebar + painel)
    # ════════════════════════════════════════════════════════════════════════
    def show_hub(self):
        self._clear()
        st = with_conn(G.api_state)
        if not st.get("has_career"):
            self.show_saves()
            return
        self.state_cache = st

        # topbar
        top = tk.Frame(self.root_frame, bg=BG2, height=44)
        top.pack(fill="x")
        tk.Label(top, text="⚽ FUTMANAGER", fg=GREEN, bg=BG2, font=(F, 14, "bold")).pack(side="left", padx=14)
        tk.Label(top, text=st["coach"], fg=TXT, bg=BG2, font=(F, 12, "bold")).pack(side="left")
        tk.Label(top, text=f"Temporada {st['season']}", fg=DIM, bg=BG2, font=(F, 11)).pack(side="right", padx=14)
        self._btn(top, "📂 Trocar jogo", self.show_saves, bg=PANEL2, fg=TXT,
                  padx=10, pady=3).pack(side="right", pady=6)

        # banner do clube
        prim, acc = G.club_hex(st["club"]["name"])
        ban = tk.Frame(self.root_frame, bg=prim, height=72)
        ban.pack(fill="x")
        ban.pack_propagate(False)
        left = tk.Frame(ban, bg=prim)
        left.pack(side="left", padx=18)
        crest = tk.Label(left, text=st["club"]["name"][:2].upper(), bg=acc, fg="#fff",
                         font=(F, 16, "bold"), width=3, height=1)
        crest.pack(side="left", pady=14)
        nm = tk.Frame(left, bg=prim)
        nm.pack(side="left", padx=12)
        tk.Label(nm, text=st["club"]["name"], fg="#fff", bg=prim, font=(F, 17, "bold")).pack(anchor="w")
        tk.Label(nm, text=f"prestígio {st['club']['prestige']} · {st['seasons_played']} temporadas",
                 fg="#dfeee5", bg=prim, font=(F, 10)).pack(anchor="w")
        stats = tk.Frame(ban, bg=prim)
        stats.pack(side="right", padx=20)
        self._stat(stats, "CAIXA", st["money_fmt"], GREEN if st["money"] >= 0 else RED)
        self._stat(stats, "REPUTAÇÃO", f"{st['reputation']}", GOLD)
        self._stat(stats, "TÍTULOS", f"{st['titles']}", "#fff")

        # corpo: sidebar + painel
        body = tk.Frame(self.root_frame, bg=BG)
        body.pack(fill="both", expand=True)
        side = tk.Frame(body, bg=BG2, width=190)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        nav = [("jogar", "▶  Jogar"), ("inbox", "📨  Inbox"), ("elenco", "👥  Elenco"),
               ("tabela", "📊  Classificação"),
               ("escalacao", "📋  Escalação"), ("mercado", "💰  Mercado"),
               ("contratos", "📝  Contratos"), ("estadio", "🏟  Estádio & CT")]
        self._nav_btns = {}
        for key, lbl in nav:
            b = tk.Label(side, text=lbl, anchor="w", padx=18, pady=11, cursor="hand2")
            b.bind("<Enter>", lambda e, k=key: self._nav_hover(k, True))
            b.bind("<Leave>", lambda e, k=key: self._nav_hover(k, False))
            b.bind("<Button-1>", lambda e, k=key: self._nav(k))
            b.pack(fill="x", padx=6, pady=2)
            self._nav_btns[key] = b
        self._refresh_nav_styles()

        self.panel = tk.Frame(body, bg=BG)
        self.panel.pack(side="left", fill="both", expand=True)
        self._render_panel()

    def _stat(self, parent, label, val, color):
        f = tk.Frame(parent, bg=parent["bg"])
        f.pack(side="left", padx=12)
        tk.Label(f, text=label, fg="#cfe3d8", bg=parent["bg"], font=(F, 9, "bold")).pack(anchor="e")
        tk.Label(f, text=val, fg=color, bg=parent["bg"], font=(F, 16, "bold")).pack(anchor="e")

    def _nav_style(self, key, hover=False):
        active = key == self.view
        if active:
            return GREEN_D, "#fff", (F, 12, "bold")
        return (PANEL2 if hover else BG2), TXT, (F, 12, "normal")

    def _refresh_nav_styles(self):
        for key, b in self._nav_btns.items():
            bg, fg, font = self._nav_style(key)
            b.configure(bg=bg, fg=fg, font=font)

    def _nav_hover(self, key, entering):
        b = self._nav_btns.get(key)
        if not b:
            return
        bg, fg, font = self._nav_style(key, hover=entering)
        b.configure(bg=bg, fg=fg, font=font)

    def _nav(self, key):
        # Troca só o painel — recriar o hub inteiro (banner, sidebar, api_state)
        # a cada clique causava o delay perceptível na navegação. Mas sempre
        # re-renderiza o painel (mesmo se já é a view atual): dados mudam
        # entre cliques (ex: jogou rodada, classificação tem que atualizar).
        self.view = key
        self._refresh_nav_styles()
        for w in self.panel.winfo_children():
            w.destroy()
        self._render_panel()

    def _panel_title(self, text):
        tk.Label(self.panel, text=text, fg=TXT, bg=BG, font=(F, 17, "bold")).pack(anchor="w", padx=24, pady=(18, 10))

    def _render_panel(self):
        v = self.view
        if v == "jogar":
            self._panel_jogar()
        elif v == "inbox":
            self._panel_inbox()
        elif v == "elenco":
            self._panel_elenco()
        elif v == "tabela":
            self._panel_tabela()
        elif v == "escalacao":
            self._panel_escalacao()
        elif v == "mercado":
            self._panel_mercado()
        elif v == "contratos":
            self._panel_contratos()
        elif v == "estadio":
            self._panel_estadio()
        elif v == "player":
            self._panel_player(self._player_id)
        elif v == "compare":
            self._panel_compare()

    # ─── JOGAR ─────────────────────────────────────────────────────────────────
    def _panel_jogar(self):
        self._panel_title("Próximo compromisso")
        nxt = with_conn(G.api_next)
        box = tk.Frame(self.panel, bg=PANEL, padx=20, pady=16, highlightbackground=LINE,
                       highlightthickness=1)
        box.pack(fill="x", padx=24)
        kind = nxt.get("kind")
        tk.Label(box, text=nxt.get("label", "—"), fg=TXT, bg=PANEL, font=(F, 14),
                 wraplength=560, justify="left").pack(side="left", fill="x", expand=True)
        if kind in ("estadual", "copa", "league", "season_end"):
            txt = "Processar entressafra" if kind == "season_end" else "Jogar ▶"
            self._btn(box, txt, self._do_play).pack(side="right")
        else:
            tk.Label(box, text="Sem jogos pendentes.", fg=DIM, bg=PANEL, font=(F, 12)).pack(side="right")

        self.result_box = tk.Frame(self.panel, bg=BG)
        self.result_box.pack(fill="both", expand=True, padx=24, pady=12)

    def _do_play(self):
        kind = with_conn(G.api_next).get("kind")
        if kind == "league":
            r = with_conn(lambda c: G.play_round_live(c))
            self._start_live(r["matches"], r["table"], f"Rodada {r['round']}/{r['n']}")
            return
        if kind == "estadual":
            r = with_conn(lambda c: G.play_estadual_live(c))
            if r.get("matchdays"):
                self._start_estadual_live(r)
                return
            res = r
        elif kind == "copa":
            r = with_conn(lambda c: G.play_copa_live(c))
            if r.get("matches"):
                self._copa = r
                self._start_live(r["matches"], None,
                                 f"{r['comp_name']} — {r['stage']}", on_done=self._copa_summary)
                return
            res = r
        else:
            res = with_conn(G.api_play)
        self.show_hub()
        if self.view != "jogar":
            return
        self._show_result(res)

    # ─── Partida ao vivo (rodada inteira, ~90s) ────────────────────────────────
    def _start_live(self, matches, table, title, on_done=None):
        """Anima a rodada: relógio 0→90' em ~90s, placares ao vivo, feed de lances."""
        self._live = {"matches": matches, "table": table, "title": title,
                      "minute": 0, "score": [[0, 0] for _ in matches],
                      "by_min": {}, "after": None, "on_done": on_done}
        for idx, m in enumerate(matches):
            for e in m["events"]:
                self._live["by_min"].setdefault(e["m"], []).append((idx, e))

        box = self.result_box
        for w in box.winfo_children():
            w.destroy()

        head = tk.Frame(box, bg=BG)
        head.pack(fill="x")
        tk.Label(head, text=title, fg=GREEN, bg=BG, font=(F, 15, "bold")).pack(side="left")
        self.lbl_clock = tk.Label(head, text="0'", fg=TXT, bg=BG, font=(F, 20, "bold"))
        self.lbl_clock.pack(side="left", padx=16)
        self._btn(head, "⏩ Pular", self._live_skip, bg=PANEL2, fg=TXT, pady=4).pack(side="right")

        body = tk.Frame(box, bg=BG)
        body.pack(fill="both", expand=True, pady=8)
        # scoreboard (esquerda)
        sb = tk.Frame(body, bg=PANEL, highlightbackground=LINE, highlightthickness=1)
        sb.pack(side="left", fill="both", expand=True, padx=(0, 8))
        tk.Label(sb, text="JOGOS DA RODADA", fg=DIM, bg=PANEL, font=(F, 10, "bold")).pack(anchor="w", padx=10, pady=6)
        self._score_lbls = []
        for idx, m in enumerate(matches):
            bgc = PANEL2 if m["is_player"] else PANEL
            row = tk.Frame(sb, bg=bgc)
            row.pack(fill="x", padx=6, pady=1)
            lbl = tk.Label(row, bg=bgc, fg=TXT, font=("Menlo", 12),
                           anchor="w", text=self._score_text(idx))
            lbl.pack(side="left", fill="x", expand=True, padx=6, pady=3)
            self._score_lbls.append(lbl)
        # feed (direita)
        ff = tk.Frame(body, bg=PANEL, highlightbackground=LINE, highlightthickness=1, width=300)
        ff.pack(side="left", fill="both", expand=True, padx=(8, 0))
        tk.Label(ff, text="LANCES", fg=DIM, bg=PANEL, font=(F, 10, "bold")).pack(anchor="w", padx=10, pady=6)
        self.feed = tk.Text(ff, bg=PANEL, fg=TXT, font=("Menlo", 11), relief="flat",
                            wrap="word", highlightthickness=0, state="disabled")
        self.feed.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self._live_tick()

    def _score_text(self, idx):
        m = self._live["matches"][idx]
        hs, as_ = self._live["score"][idx]
        star = " ◀ você" if m["is_player"] else ""
        return f"{m['h_abbr']} {hs}–{as_} {m['a_abbr']}{star}"

    def _feed_add(self, line):
        self.feed.config(state="normal")
        self.feed.insert("end", line + "\n")
        self.feed.see("end")
        self.feed.config(state="disabled")

    def _live_tick(self):
        L = self._live
        mn = L["minute"]
        self.lbl_clock.config(text=f"{mn}'")
        for idx, e in L["by_min"].get(mn, []):
            m = L["matches"][idx]
            if e["kind"] == "goal":
                if e["team"] == "H": L["score"][idx][0] += 1
                else: L["score"][idx][1] += 1
                self._score_lbls[idx].config(text=self._score_text(idx))
                hs, as_ = L["score"][idx]
                self._feed_add(f"{mn:>2}' ⚽ {m['h_abbr']} {hs}–{as_} {m['a_abbr']}")
            elif e["kind"] == "red":
                self._feed_add(f"{mn:>2}' 🟥 {e['text']}")
            elif m["is_player"] and e["kind"] in ("yellow", "injury", "chance"):
                self._feed_add(f"{mn:>2}' {e['text']}")
        if mn >= 90:
            self._live_finish()
            return
        L["minute"] += 1
        L["after"] = self.after(1000, self._live_tick)  # ~1s por minuto ≈ 90s

    def _live_skip(self):
        L = self._live
        if L["after"]:
            self.after_cancel(L["after"])
            L["after"] = None
        # processa todos os minutos restantes instantaneamente (sem feed spam)
        for mn in range(L["minute"], 91):
            for idx, e in L["by_min"].get(mn, []):
                if e["kind"] == "goal":
                    if e["team"] == "H": L["score"][idx][0] += 1
                    else: L["score"][idx][1] += 1
        for idx in range(len(L["matches"])):
            self._score_lbls[idx].config(text=self._score_text(idx))
        L["minute"] = 90
        self.lbl_clock.config(text="90'")
        self._live_finish()

    def _live_finish(self):
        L = self._live
        if L["after"]:
            self.after_cancel(L["after"]); L["after"] = None
        if L.get("on_done"):
            L["on_done"]()
            return
        # mostra classificação completa + botão continuar
        box = self.result_box
        for w in box.winfo_children():
            w.destroy()
        tk.Label(box, text="Classificação", fg=GREEN, bg=BG, font=(F, 15, "bold")).pack(anchor="w")
        self._render_full_table(box, L["table"])
        self._btn(box, "Continuar ▶", lambda: (self.show_hub()), bg=GREEN).pack(anchor="w", pady=10)

    def _copa_summary(self):
        r = self._copa
        box = self.result_box
        for w in box.winfo_children():
            w.destroy()
        card = tk.Frame(box, bg=PANEL, padx=18, pady=14, highlightbackground=LINE, highlightthickness=1)
        card.pack(fill="both", expand=True)
        tk.Label(card, text=f"{r['comp_name']} — {r['stage']}", fg=GREEN, bg=PANEL,
                 font=(F, 16, "bold")).pack(anchor="w")
        for m in r["matches"]:
            extra = ""
            if m.get("pens"):
                extra = f"  ({m['pens'][0]}-{m['pens'][1]} pên → {m['winner']})"
            star = "  ◀" if m["is_player"] else ""
            tk.Label(card, text=f"{m['h_abbr']} {m['hg']}–{m['ag']} {m['a_abbr']}{extra}{star}",
                     fg=(GOLD if m["is_player"] else TXT), bg=PANEL, font=("Menlo", 12)).pack(anchor="w")
        if r.get("champion"):
            tk.Label(card, text=f"🏆 Campeão: {r['champion']}", fg=GOLD, bg=PANEL,
                     font=(F, 13, "bold")).pack(anchor="w", pady=(8, 0))
        if r.get("won"):
            tk.Label(card, text="🎉 VOCÊ É CAMPEÃO!", fg=GREEN, bg=PANEL, font=(F, 13, "bold")).pack(anchor="w")
        elif r.get("advanced"):
            tk.Label(card, text="✅ Classificado.", fg=GREEN, bg=PANEL, font=(F, 12)).pack(anchor="w", pady=(6, 0))
        elif r.get("eliminated"):
            tk.Label(card, text="❌ Eliminado.", fg=RED, bg=PANEL, font=(F, 12, "bold")).pack(anchor="w", pady=(6, 0))
        self._btn(card, "Continuar ▶", self.show_hub, bg=GREEN).pack(anchor="w", pady=(10, 0))

    # ─── Estadual ao vivo (rodada a rodada) ────────────────────────────────────
    def _start_estadual_live(self, r):
        self._est = {"mds": r["matchdays"], "i": 0, "summary": r}
        self._est_play()

    def _est_play(self):
        e = self._est
        i = e["i"]
        if i >= len(e["mds"]):
            self._est_summary()
            return
        md = e["mds"][i]
        title = f"{e['summary']['name']} · {md['label']}"
        self._start_live(md["matches"], None, title, on_done=self._est_after)

    def _est_after(self):
        e = self._est
        e["i"] += 1
        last = e["i"] >= len(e["mds"])
        bar = tk.Frame(self.result_box, bg=BG)
        bar.pack(fill="x", pady=8)
        txt = "Ver resumo ▶" if last else "Próxima rodada ▶"
        self._btn(bar, txt, self._est_play, bg=GREEN).pack(side="right")

    def _est_summary(self):
        r = self._est["summary"]
        box = self.result_box
        for w in box.winfo_children():
            w.destroy()
        card = tk.Frame(box, bg=PANEL, padx=18, pady=14, highlightbackground=LINE, highlightthickness=1)
        card.pack(fill="both", expand=True)
        tk.Label(card, text=r["name"], fg=GREEN, bg=PANEL, font=(F, 16, "bold")).pack(anchor="w")
        tk.Label(card, text=f"🏆 Campeão: {r['champion']}", fg=GOLD, bg=PANEL,
                 font=(F, 14, "bold")).pack(anchor="w", pady=(6, 2))
        tk.Label(card, text=f"Sua campanha: {r['player_stage']}"
                 + (f"  ·  prêmio {G.fmt_money(r['prize'])}" if r["prize"] else ""),
                 fg=TXT, bg=PANEL, font=(F, 12)).pack(anchor="w")
        # tabelas de grupo
        gr = tk.Frame(card, bg=PANEL)
        gr.pack(fill="x", pady=10)
        for gname, rows in r.get("groups", {}).items():
            col = tk.Frame(gr, bg=PANEL)
            col.pack(side="left", padx=10, anchor="n")
            tk.Label(col, text=f"Grupo {gname}", fg=DIM, bg=PANEL, font=(F, 10, "bold")).pack(anchor="w")
            for rr in rows:
                c = GOLD if rr["is_player"] else TXT
                tk.Label(col, text=f"{rr['name'][:14]:<14} {rr['pts']}", fg=c, bg=PANEL,
                         font=("Menlo", 10)).pack(anchor="w")
        self._btn(card, "Continuar ▶", self.show_hub, bg=GREEN).pack(anchor="w", pady=(10, 0))

    def _render_full_table(self, parent, table):
        cols = ("pos", "name", "j", "v", "e", "d", "gp", "gc", "sg", "pts", "ca", "cv")
        heads = ("#", "Clube", "J", "V", "E", "D", "GP", "GC", "SG", "Pts", "🟨", "🟥")
        widths = (34, 170, 36, 36, 36, 36, 42, 42, 42, 46, 40, 40)
        frame = tk.Frame(parent, bg=BG)
        frame.pack(fill="both", expand=True, pady=6)
        tv = ttk.Treeview(frame, columns=cols, show="headings", style="Dark.Treeview", height=14)
        for c, h, w in zip(cols, heads, widths):
            tv.heading(c, text=h)
            tv.column(c, width=w, anchor=("w" if w >= 150 else "center"), stretch=False)
        for r in table:
            tags = []
            if r["is_player"]:
                tags.append("me")
            elif r["zone"] == "cl":
                tags.append("cl")
            elif r["zone"] == "rel":
                tags.append("rel")
            tv.insert("", "end", tags=tuple(tags), values=(
                r["pos"], r["name"], r["played"], r["wins"], r["draws"], r["losses"],
                r["gf"], r["ga"], r["gd"], r["points"], r.get("yellows", 0), r.get("reds", 0)))
        tv.tag_configure("me", background=GREEN_D, foreground="#fff")
        tv.tag_configure("cl", foreground=GREEN)
        tv.tag_configure("rel", foreground=RED)
        sb = ttk.Scrollbar(frame, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        tv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    def _show_result(self, res):
        box = self.result_box
        for w in box.winfo_children():
            w.destroy()
        k = res.get("kind")
        card = tk.Frame(box, bg=PANEL, padx=18, pady=14, highlightbackground=LINE, highlightthickness=1)
        card.pack(fill="both", expand=True)
        if k == "league":
            self._res_league(card, res)
        elif k == "copa":
            self._res_copa(card, res)
        elif k == "estadual":
            self._res_estadual(card, res)
        elif k == "season_end":
            self._res_season(card, res)

    def _res_league(self, c, r):
        tk.Label(c, text=f"Rodada {r['round']}/{r['n']}", fg=GREEN, bg=PANEL,
                 font=(F, 15, "bold")).pack(anchor="w")
        y = r.get("your")
        if y:
            tk.Label(c, text=f"  {y['home']}  {y['hg']} x {y['ag']}  {y['away']}", fg=TXT, bg=PANEL,
                     font=(F, 15, "bold")).pack(anchor="w", pady=8)
        tk.Label(c, text="Líderes:", fg=DIM, bg=PANEL, font=(F, 11, "bold")).pack(anchor="w", pady=(6, 2))
        for row in r.get("table", []):
            col = GOLD if row["is_player"] else TXT
            tk.Label(c, text=f"  {row['pos']:>2}. {row['name']:<22} {row['pts']:>3} pts ({row['j']}j)",
                     fg=col, bg=PANEL, font=("Menlo", 11)).pack(anchor="w")

    def _res_copa(self, c, r):
        tk.Label(c, text=f"{r['comp_name']} — {r['stage']}", fg=GREEN, bg=PANEL,
                 font=(F, 15, "bold")).pack(anchor="w")
        for ln in r.get("lines", []):
            tk.Label(c, text=f"  {ln}", fg=TXT, bg=PANEL, font=("Menlo", 11)).pack(anchor="w")
        if r.get("champion"):
            tk.Label(c, text=f"🏆 Campeão: {r['champion']}", fg=GOLD, bg=PANEL,
                     font=(F, 13, "bold")).pack(anchor="w", pady=(8, 0))
        if r.get("won"):
            tk.Label(c, text="🎉 VOCÊ É CAMPEÃO!", fg=GREEN, bg=PANEL, font=(F, 13, "bold")).pack(anchor="w")
        elif r.get("advanced"):
            tk.Label(c, text="✅ Classificado para a próxima fase.", fg=GREEN, bg=PANEL,
                     font=(F, 12)).pack(anchor="w", pady=(6, 0))
        elif r.get("eliminated"):
            tk.Label(c, text="❌ Eliminado.", fg=RED, bg=PANEL, font=(F, 12, "bold")).pack(anchor="w", pady=(6, 0))

    def _res_estadual(self, c, r):
        tk.Label(c, text=f"{r['name']}", fg=GREEN, bg=PANEL, font=(F, 15, "bold")).pack(anchor="w")
        for ln in r.get("log", []):
            tk.Label(c, text=f"  {ln}", fg=TXT, bg=PANEL, font=("Menlo", 11), justify="left",
                     wraplength=640).pack(anchor="w")
        tk.Label(c, text=f"🏆 Campeão estadual: {r['champion']}", fg=GOLD, bg=PANEL,
                 font=(F, 13, "bold")).pack(anchor="w", pady=(8, 0))
        tk.Label(c, text=f"Sua campanha: {r['player_stage']}"
                 + (f"  ·  prêmio {G.fmt_money(r['prize'])}" if r["prize"] else ""),
                 fg=TXT, bg=PANEL, font=(F, 12)).pack(anchor="w")

    def _res_season(self, c, r):
        tk.Label(c, text="Fim de temporada", fg=GREEN, bg=PANEL, font=(F, 15, "bold")).pack(anchor="w")
        tk.Label(c, text=f"Campeão: {r['champion']}   ·   você: {r['pos']}º", fg=TXT, bg=PANEL,
                 font=(F, 13)).pack(anchor="w", pady=4)
        if r.get("won_title"):
            tk.Label(c, text="🏆 VOCÊ FOI CAMPEÃO!", fg=GOLD, bg=PANEL, font=(F, 13, "bold")).pack(anchor="w")
        promo = r.get("promo")
        if promo:
            txt = (f"⬆️  ACESSO! Você sobe para a {promo['league_name']}"
                   if promo["promoted"] else
                   f"⬇️  Rebaixado para a {promo['league_name']}.")
            tk.Label(c, text=txt, fg=(GREEN if promo["promoted"] else RED), bg=PANEL,
                     font=(F, 13, "bold")).pack(anchor="w", pady=(4, 0))
        fin = r.get("fin", {})
        if fin:
            tk.Label(c, text="Finanças:", fg=DIM, bg=PANEL, font=(F, 11, "bold")).pack(anchor="w", pady=(8, 2))
            for k, lbl in [("sponsor", "Patrocínio"), ("gate", "Bilheteria"), ("prize", "Premiação"),
                           ("wages", "Salários"), ("fines", "Multas"), ("net", "Saldo")]:
                if k in fin:
                    v = fin[k]
                    col = RED if (k in ("wages", "fines") or v < 0) else TXT
                    tk.Label(c, text=f"  {lbl:<12} {G.fmt_money(v)}", fg=col, bg=PANEL,
                             font=("Menlo", 11)).pack(anchor="w")
        rep = r.get("rep", {})
        if r.get("sacked"):
            if r.get("rehired"):
                tk.Label(c, text=f"⚠ Demitido — recontratado por {r['rehired']}.", fg=GOLD, bg=PANEL,
                         font=(F, 12, "bold")).pack(anchor="w", pady=(8, 0))
            else:
                tk.Label(c, text="❌ Você foi DEMITIDO e está sem clube.", fg=RED, bg=PANEL,
                         font=(F, 12, "bold")).pack(anchor="w", pady=(8, 0))
        elif rep:
            tk.Label(c, text=f"Reputação: {rep.get('new_rep', '?')}", fg=GOLD, bg=PANEL,
                     font=(F, 12)).pack(anchor="w", pady=(8, 0))
        if r.get("newgens"):
            tk.Label(c, text=f"🌱 {r['newgens']} novos jogadores surgiram nas categorias de base.",
                     fg=DIM, bg=PANEL, font=(F, 11)).pack(anchor="w", pady=(6, 0))
        if r.get("ai_transfers"):
            tk.Label(c, text=f"🔄 {r['ai_transfers']} transferências movimentaram o mercado — rivais reforçaram seus elencos.",
                     fg=DIM, bg=PANEL, font=(F, 11)).pack(anchor="w", pady=(6, 0))

    # ─── INBOX ───────────────────────────────────────────────────────────────
    def _panel_inbox(self):
        data = with_conn(G.api_inbox)
        msgs = data["messages"]
        title = "Inbox" + (f" — {data['unread']} não lidas" if data["unread"] else "")
        self._panel_title(title)
        if not msgs:
            tk.Label(self.panel, text="Nada por aqui ainda — avisos do conselho, relatórios "
                                       "de olheiro e resumos de temporada aparecem aqui.",
                     fg=DIM, bg=BG, font=(F, 12)).pack(anchor="w", padx=24, pady=8)
            return
        if data["unread"]:
            with_conn(lambda c: G.api_inbox_mark_read(c))

        wrap = tk.Frame(self.panel, bg=BG)
        wrap.pack(fill="both", expand=True, padx=24, pady=8)
        canvas = tk.Canvas(wrap, bg=BG, highlightthickness=0)
        sb = ttk.Scrollbar(wrap, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=BG)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        for m in msgs:
            card = tk.Frame(inner, bg=PANEL, highlightbackground=LINE, highlightthickness=1)
            card.pack(fill="x", pady=5, ipady=2)
            head = tk.Frame(card, bg=PANEL)
            head.pack(fill="x", padx=14, pady=(10, 2))
            badge = "" if m["read"] else "🔵 "
            tk.Label(head, text=f"{badge}{m['kind_label']}  ·  {m['title']}", fg=GOLD if not m["read"] else TXT,
                     bg=PANEL, font=(F, 12, "bold")).pack(side="left")
            tk.Label(head, text=f"rodada {m['round']}", fg=DIM, bg=PANEL, font=(F, 10)).pack(side="right")
            tk.Label(card, text=m["body"], fg=TXT, bg=PANEL, font=(F, 11),
                     wraplength=620, justify="left").pack(anchor="w", padx=14, pady=(0, 10))

    # ─── ELENCO ──────────────────────────────────────────────────────────────
    def _panel_elenco(self):
        self._panel_title("Elenco")
        offers = with_conn(G.api_incoming_offers)
        if offers:
            box = tk.Frame(self.panel, bg=PANEL)
            box.pack(fill="x", padx=24, pady=(0, 12))
            tk.Label(box, text="📨 Propostas recebidas", fg=GOLD, bg=PANEL,
                     font=(F, 12, "bold")).pack(anchor="w", padx=12, pady=(8, 4))
            for o in offers:
                row = tk.Frame(box, bg=PANEL)
                row.pack(fill="x", padx=12, pady=4)
                tk.Label(row, text=f"{o['club_name']} oferece {o['amount_fmt']} por "
                                   f"{o['player_name']} (OVR {o['overall']})",
                         fg=TXT, bg=PANEL, font=(F, 11)).pack(side="left")
                self._btn(row, "Recusar", lambda o=o: self._respond_offer(o, False),
                          bg=BG2, fg=TXT).pack(side="right", padx=(6, 0))
                self._btn(row, "Aceitar", lambda o=o: self._respond_offer(o, True),
                          bg=GREEN).pack(side="right")
            tk.Frame(box, bg=PANEL, height=8).pack()
        squad = with_conn(G.api_squad)
        cols = ("pos", "name", "age", "ovr", "pot", "fit", "form", "value", "wage", "contract")
        tv = self._table(cols, ("POS", "Jogador", "Idade", "OVR", "POT", "Condição", "Forma",
                                "Valor", "Salário", "Contrato"),
                         widths=(50, 200, 55, 50, 50, 75, 60, 90, 90, 80))
        for p in squad:
            tags = []
            if p["loan"]:
                tags.append("loan")
            if p["fitness"] < 50:
                tags.append("tired")
            tv.insert("", "end", iid=str(p["id"]), tags=tuple(tags), values=(
                p["role"], p["name"], p["age"], p["overall"], p["potential"] or "—",
                f"{p['fitness']}%", f"{p['form']:.2f}",
                p["value_fmt"], p["wage_fmt"], p["contract"] or "—"))
        tv.tag_configure("loan", foreground=DIM)
        tv.tag_configure("tired", foreground=RED)
        tv.bind("<Double-1>", lambda e: self._open_player_from(tv, "elenco"))
        tk.Label(self.panel, text="Duplo-clique num jogador = perfil completo.",
                 fg=DIM, bg=BG, font=(F, 11)).pack(anchor="w", padx=24, pady=(0, 8))

    def _respond_offer(self, o, accept):
        verb = "aceitar" if accept else "recusar"
        msg = (f"Vender {o['player_name']} ao {o['club_name']} por {o['amount_fmt']}?"
               if accept else f"Recusar proposta do {o['club_name']} por {o['player_name']}?")
        if not messagebox.askyesno("Proposta", msg):
            return
        r = with_conn(lambda c: G.api_respond_offer(c, o["player_id"], o["club_id"], accept))
        messagebox.showinfo("Proposta", r["msg"])
        if r["ok"]:
            self.show_hub()

    # ─── PERFIL DE JOGADOR ───────────────────────────────────────────────────
    def _open_player_from(self, tv, return_view):
        sel = tv.selection() or ((tv.focus(),) if tv.focus() else ())
        if not sel:
            return
        self._open_player(int(sel[0]), return_view)

    def _open_player(self, player_id, return_view=None):
        self._player_return = return_view or self.view
        self._player_id = player_id
        self.view = "player"
        for w in self.panel.winfo_children():
            w.destroy()
        self._render_panel()

    def _panel_player(self, player_id):
        p = with_conn(lambda c: G.api_player_detail(c, player_id))
        if not p:
            self._panel_title("Jogador não encontrado")
            return

        bar = tk.Frame(self.panel, bg=BG)
        bar.pack(fill="x", padx=24, pady=(18, 0))
        self._btn(bar, "← Voltar", lambda: self._nav(self._player_return),
                  bg=PANEL2, fg=TXT).pack(side="left")

        head = tk.Frame(self.panel, bg=BG)
        head.pack(fill="x", padx=24, pady=(12, 6))
        tk.Label(head, text=p["name"], fg=TXT, bg=BG, font=(F, 19, "bold")).pack(anchor="w")
        sub = (f"{p['role_label']} ({p['position']})  ·  {p['age']} anos  ·  {p['nationality'] or '—'}  ·  "
               f"{p['club_name']}  ·  OVR {p['overall']}  ·  POT {p['potential'] or '—'}")
        tk.Label(head, text=sub, fg=DIM, bg=BG, font=(F, 12)).pack(anchor="w", pady=(2, 0))
        if not p["is_own"] and not (p["transfer_listed"] or p["loan_listed"]):
            tk.Label(head, text="🔍 Atributos abaixo são estimativas do seu olheirado — "
                                "escale um olheiro pra confirmar (dourado = confirmado).",
                     fg=GOLD, bg=BG, font=(F, 10, "italic")).pack(anchor="w", pady=(4, 0))

        # ── Status / contrato ──
        info = tk.Frame(self.panel, bg=PANEL)
        info.pack(fill="x", padx=24, pady=(6, 12))
        flags = []
        if p["transfer_listed"]:
            flags.append("À venda")
        if p["loan_listed"]:
            flags.append("Empréstimo disponível")
        line = (f"Valor: {p['value_fmt']}   ·   Salário: {p['wage_fmt']}   ·   "
                f"Contrato até {p['contract'] or '—'}   ·   Condição: {p['fitness']}%   ·   "
                f"Forma: {p['form']:.2f}")
        if flags:
            line += "   ·   " + " / ".join(flags)
        tk.Label(info, text=line, fg=TXT, bg=PANEL, font=(F, 11)).pack(anchor="w", padx=12, pady=10)

        # ── Lesão ativa (só elenco próprio) ──
        inj = p.get("injury")
        if inj:
            care = tk.Frame(self.panel, bg=PANEL)
            care.pack(fill="x", padx=24, pady=(0, 12))
            txt = (f"🚑 {inj['kind']} — recuperação: {inj['weeks_left']}/{inj['weeks_total']} "
                   f"semanas restantes" + (" (operado)" if inj["surgery"] else ""))
            tk.Label(care, text=txt, fg=RED, bg=PANEL, font=(F, 11, "bold")) \
                .pack(anchor="w", padx=12, pady=(10, 2))
            if inj["can_surgery"]:
                sub = (f"🏥 Cirurgia: {inj['surgery_cost_fmt']}, reduz para ~{inj['surgery_weeks_after']} "
                       f"semanas (economiza {inj['surgery_weeks_saved']}) — risco de complicação {inj['surgery_risk_pct']}%")
                tk.Label(care, text=sub, fg=DIM, bg=PANEL, font=(F, 10)).pack(anchor="w", padx=12)
                self._btn(care, "Decidir pela cirurgia", lambda: self._decide_surgery(inj["id"], player_id),
                          bg=PANEL2, fg=TXT).pack(anchor="w", padx=12, pady=(6, 10))
            else:
                tk.Label(care, text="", bg=PANEL).pack(pady=(0, 4))

        # ── Treino — feedback explicativo (só elenco próprio) ──
        tr = p.get("training")
        if tr:
            tk.Label(self.panel, text="📈 Treino", fg=TXT, bg=BG, font=(F, 13, "bold")) \
                .pack(anchor="w", padx=24, pady=(4, 6))
            tbox = tk.Frame(self.panel, bg=PANEL)
            tbox.pack(fill="x", padx=24, pady=(0, 12))
            head_txt = (f"Foco do CT: {tr['focus_label']}  ·  Nível {tr['level']}/5"
                        + (f"  ·  beneficia: {', '.join(tr['boosted_attrs'])}"
                           if tr["focus"] != "geral" and tr["boosted_attrs"] else ""))
            tk.Label(tbox, text=head_txt, fg=DIM, bg=PANEL, font=(F, 10)) \
                .pack(anchor="w", padx=12, pady=(10, 2))
            trend_color = {"subindo": GREEN, "caindo": RED}.get(tr["trend"], TXT)
            tk.Label(tbox, text=tr["text"], fg=trend_color, bg=PANEL,
                     font=(F, 11), wraplength=620, justify="left").pack(anchor="w", padx=12, pady=(0, 10))

        # ── Relações (squad dynamics — só elenco próprio) ──
        rels = p.get("relations") or []
        if rels:
            tk.Label(self.panel, text="🤝 Relações no elenco", fg=TXT, bg=BG, font=(F, 13, "bold")) \
                .pack(anchor="w", padx=24, pady=(4, 6))
            box = tk.Frame(self.panel, bg=PANEL)
            box.pack(fill="x", padx=24, pady=(0, 12))
            for r in rels:
                color = GOLD if r["affinity"] >= 0 else RED
                sign = "+" if r["affinity"] >= 0 else ""
                txt = f"{r['label']} — {r['other_name']}  ({sign}{r['affinity']})"
                row = tk.Frame(box, bg=PANEL)
                row.pack(fill="x", padx=12, pady=4)
                tk.Label(row, text=txt, fg=color, bg=PANEL, font=(F, 11)).pack(side="left")
                self._btn(row, "Ver perfil", lambda pid=r["other_id"]: self._open_player(pid),
                          bg=PANEL2, fg=TXT).pack(side="right")

        # ── Atributos (com masking) ──
        tk.Label(self.panel, text="Atributos", fg=TXT, bg=BG, font=(F, 13, "bold")) \
            .pack(anchor="w", padx=24, pady=(4, 6))
        grid = tk.Frame(self.panel, bg=BG)
        grid.pack(fill="x", padx=24)
        for i, a in enumerate(p["attrs"]):
            row, col = divmod(i, 3)
            cell = tk.Frame(grid, bg=PANEL)
            cell.grid(row=row, column=col, sticky="ew", padx=(0 if col == 0 else 8, 0), pady=4)
            grid.grid_columnconfigure(col, weight=1)
            tk.Label(cell, text=a["label"], fg=DIM, bg=PANEL, font=(F, 10)) \
                .pack(anchor="w", padx=10, pady=(6, 0))
            val_color = GOLD if a.get("confirmed") else (TXT if a["known"] else DIM)
            tk.Label(cell, text=str(a["value"]), fg=val_color, bg=PANEL,
                     font=(F, 14, "bold")).pack(anchor="w", padx=10, pady=(0, 6))

        # ── Ações ──
        act = tk.Frame(self.panel, bg=BG)
        act.pack(fill="x", padx=24, pady=(16, 18))
        if not p["is_own"]:
            self._btn(act, "Ir para Mercado e negociar", lambda: self._nav("mercado"),
                      bg=GREEN).pack(side="left")
            if p.get("can_scout"):
                self._btn(act, f"🔎 Escalar olheiro ({p['scout_cost_fmt']})",
                          lambda: self._scout_player(p), bg=PANEL2, fg=TXT).pack(side="left", padx=(8, 0))
        self._btn(act, "⚖ Comparar com…", lambda: self._open_compare(p["id"]),
                  bg=PANEL2, fg=TXT).pack(side="left", padx=(8, 0))
        if p["is_own"]:
            self._btn(act, "Colocar/tirar da lista de transferências",
                      lambda: self._toggle_listed(p), bg=PANEL2, fg=TXT).pack(side="left")

        self._render_notes(player_id)

    _NOTE_TAGS = ("alvo", "revender", "risco", "monitorar")

    def _render_notes(self, player_id):
        tk.Label(self.panel, text="Notas", fg=TXT, bg=BG, font=(F, 13, "bold")) \
            .pack(anchor="w", padx=24, pady=(4, 6))
        notes = with_conn(lambda c: G.api_player_notes(c, player_id))

        add = tk.Frame(self.panel, bg=BG)
        add.pack(fill="x", padx=24, pady=(0, 6))
        en = tk.Entry(add, bg=BG2, fg=TXT, insertbackground=TXT, font=(F, 11), relief="flat")
        en.pack(side="left", fill="x", expand=True, ipady=4)
        cb = ttk.Combobox(add, values=("—",) + self._NOTE_TAGS, state="readonly", width=10, font=(F, 10))
        cb.set("—")
        cb.pack(side="left", padx=(6, 0))

        def add_note():
            txt = en.get().strip()
            if not txt:
                return
            tag = cb.get() if cb.get() != "—" else None
            with_conn(lambda c: G.api_add_note(c, player_id, txt, tag))
            self._open_player(player_id, self._player_return)
        self._btn(add, "+ Nota", add_note, bg=PANEL2, fg=TXT).pack(side="left", padx=(6, 0))

        if not notes:
            tk.Label(self.panel, text="Sem notas — anote alvos de venda, riscos, "
                                       "jogadores pra monitorar etc.",
                     fg=DIM, bg=BG, font=(F, 10, "italic")).pack(anchor="w", padx=24, pady=(0, 14))
            return
        for n in notes:
            row = tk.Frame(self.panel, bg=PANEL)
            row.pack(fill="x", padx=24, pady=2)
            tag_txt = f"[{n['tag']}] " if n["tag"] else ""
            tk.Label(row, text=f"{tag_txt}{n['text']}", fg=TXT, bg=PANEL, font=(F, 10),
                     wraplength=560, justify="left").pack(side="left", padx=10, pady=6, fill="x", expand=True)
            self._btn(row, "✕", lambda nid=n["id"]: self._del_note(player_id, nid),
                      bg=PANEL, fg=DIM).pack(side="right", padx=(0, 6))
        tk.Frame(self.panel, bg=BG, height=10).pack()

    def _del_note(self, player_id, note_id):
        with_conn(lambda c: G.api_delete_note(c, note_id))
        self._open_player(player_id, self._player_return)

    # ─── COMPARAÇÃO DE JOGADORES ─────────────────────────────────────────────
    def _open_compare(self, player_id):
        self._cmp_return = self._player_return if self.view == "player" else self.view
        self._cmp_a = player_id
        squad = with_conn(G.api_squad)
        cands = [s for s in squad if s["id"] != player_id]
        if not cands:
            messagebox.showinfo("Comparar", "Seu elenco não tem outro jogador pra comparar.")
            return
        a = with_conn(lambda c: G.api_player_detail(c, player_id))
        same_pos = [s for s in cands if s["position"] == a["position"]]
        self._cmp_b = (same_pos or cands)[0]["id"]
        self._cmp_squad = cands
        self.view = "compare"
        for w in self.panel.winfo_children():
            w.destroy()
        self._render_panel()

    def _panel_compare(self):
        a = with_conn(lambda c: G.api_player_detail(c, self._cmp_a))
        b = with_conn(lambda c: G.api_player_detail(c, self._cmp_b))

        bar = tk.Frame(self.panel, bg=BG)
        bar.pack(fill="x", padx=24, pady=(18, 0))
        self._btn(bar, "← Voltar", lambda: self._nav(self._cmp_return),
                  bg=PANEL2, fg=TXT).pack(side="left")

        self._panel_title(f"Comparação — {a['name']}  ×  {b['name']}")

        sel = tk.Frame(self.panel, bg=BG)
        sel.pack(fill="x", padx=24, pady=(0, 8))
        tk.Label(sel, text="Comparar com:", fg=DIM, bg=BG, font=(F, 11)).pack(side="left")
        names = {f"{s['name']} ({s['position']}, OVR {s['overall']})": s["id"] for s in self._cmp_squad}
        cb = ttk.Combobox(sel, values=list(names.keys()), state="readonly", width=34, font=(F, 11))
        cur = next((k for k, v in names.items() if v == self._cmp_b), None)
        if cur:
            cb.set(cur)
        cb.pack(side="left", padx=8)

        def on_pick(_e=None):
            self._cmp_b = names[cb.get()]
            for w in self.panel.winfo_children():
                w.destroy()
            self._render_panel()
        cb.bind("<<ComboboxSelected>>", on_pick)

        head = tk.Frame(self.panel, bg=BG)
        head.pack(fill="x", padx=24, pady=(8, 4))
        for col, p in ((0, a), (1, b)):
            f = tk.Frame(head, bg=PANEL)
            f.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 8, 0))
            head.grid_columnconfigure(col, weight=1)
            tk.Label(f, text=p["name"], fg=TXT, bg=PANEL, font=(F, 13, "bold")).pack(anchor="w", padx=12, pady=(8, 0))
            tk.Label(f, text=f"{p['position']} · {p['age']}a · {p['club_name']} · OVR {p['overall']} · "
                            f"POT {p['potential'] or '—'} · {p['value_fmt']}",
                     fg=DIM, bg=PANEL, font=(F, 10)).pack(anchor="w", padx=12, pady=(0, 8))

        tk.Label(self.panel, text="Atributos (▲ = melhor; cinza = não conhecido o suficiente p/ comparar)",
                 fg=DIM, bg=BG, font=(F, 10)).pack(anchor="w", padx=24, pady=(10, 4))
        amap = {x["key"]: x for x in a["attrs"]}
        bmap = {x["key"]: x for x in b["attrs"]}
        from engine.knowledge import ATTRS, ATTR_LABELS
        for key in ATTRS:
            av, bv = amap[key], bmap[key]
            row = tk.Frame(self.panel, bg=BG)
            row.pack(fill="x", padx=24, pady=2)
            tk.Label(row, text=ATTR_LABELS[key], fg=TXT, bg=BG, font=(F, 11), width=14, anchor="w") \
                .pack(side="left")
            both_known = isinstance(av["value"], int) and isinstance(bv["value"], int)
            ca = cb_ = TXT
            mark_a = mark_b = ""
            if both_known:
                if av["value"] > bv["value"]:
                    ca, mark_a = GREEN, " ▲"
                elif bv["value"] > av["value"]:
                    cb_, mark_b = GREEN, " ▲"
            else:
                ca = cb_ = DIM
            tk.Label(row, text=f"{av['value']}{mark_a}", fg=ca, bg=BG, font=(F, 11, "bold"),
                     width=10, anchor="w").pack(side="left")
            tk.Label(row, text=f"{bv['value']}{mark_b}", fg=cb_, bg=BG, font=(F, 11, "bold"),
                     width=10, anchor="w").pack(side="left")

    def _scout_player(self, p):
        if not messagebox.askyesno("Olheiro", f"Mandar olheiro investigar {p['name']}?\n"
                                               f"Custo: {p['scout_cost_fmt']}"):
            return
        r = with_conn(lambda c: G.api_scout_player(c, p["id"]))
        messagebox.showinfo("Relatório de scouting", r["msg"])
        if r.get("ok"):
            self._open_player(p["id"], self._player_return)

    def _decide_surgery(self, injury_id, player_id):
        if not messagebox.askyesno("Cirurgia",
                "Autorizar cirurgia? Reduz o tempo de recuperação, mas custa caro\n"
                "e tem risco de complicação (pode demorar mais que o previsto)."):
            return
        r = with_conn(lambda c: G.api_decide_surgery(c, injury_id))
        messagebox.showinfo("Departamento médico", r["msg"])
        if r.get("ok"):
            self._open_player(player_id, self._player_return)

    def _toggle_listed(self, p):
        new_state = not p["transfer_listed"]
        r = with_conn(lambda c: G.api_set_transfer_listed(c, p["id"], new_state))
        if r and r.get("ok"):
            self._open_player(p["id"], self._player_return)

    # ─── TABELA ──────────────────────────────────────────────────────────────
    def _panel_tabela(self):
        comps = with_conn(G.api_competitions)
        if not hasattr(self, "_tabela_comp") or self._tabela_comp not in [x["key"] for x in comps]:
            self._tabela_comp = comps[0]["key"] if comps else "brasileirao"

        head = tk.Frame(self.panel, bg=BG)
        head.pack(fill="x", padx=24, pady=(18, 0))
        tk.Label(head, text="Classificação", fg=TXT, bg=BG, font=(F, 17, "bold")).pack(side="left")
        if len(comps) > 1:
            cb = ttk.Combobox(head, values=[x["label"] for x in comps], state="readonly",
                              width=20, font=(F, 11))
            by_label = {x["label"]: x["key"] for x in comps}
            cb.set(next(x["label"] for x in comps if x["key"] == self._tabela_comp))
            def on_pick(e):
                self._tabela_comp = by_label[cb.get()]
                self._nav("tabela")
            cb.bind("<<ComboboxSelected>>", on_pick)
            cb.pack(side="right")

        key = self._tabela_comp
        if key == "brasileirao":
            self._render_tabela_brasileirao()
        elif key == "estadual":
            self._render_tabela_estadual()
        elif key.startswith("copa_"):
            self._render_tabela_copa(key[len("copa_"):])

    def _render_tabela_brasileirao(self):
        data = with_conn(G.api_table)
        if not data["rows"]:
            tk.Label(self.panel, text="Tabela ainda não iniciada (jogue a 1ª rodada).",
                     fg=DIM, bg=BG, font=(F, 12)).pack(padx=24, pady=12)
            return
        wrap = tk.Frame(self.panel, bg=BG)
        wrap.pack(fill="both", expand=True, padx=24)
        self._render_full_table(wrap, data["rows"])

    def _render_tabela_estadual(self):
        data = with_conn(G.api_estadual_table)
        if not data.get("ok"):
            tk.Label(self.panel, text="Estadual ainda não disputado nesta temporada.",
                     fg=DIM, bg=BG, font=(F, 12)).pack(padx=24, pady=12)
            return
        wrap = tk.Frame(self.panel, bg=BG)
        wrap.pack(fill="both", expand=True, padx=24, pady=(8, 0))
        tk.Label(wrap, text=f"{data['name']} — fase de grupos  ·  campeão: {data.get('champion') or '?'}",
                 fg=GOLD, bg=BG, font=(F, 12, "bold")).pack(anchor="w", pady=(0, 10))
        grid = tk.Frame(wrap, bg=BG)
        grid.pack(fill="both", expand=True)
        for i, (letter, rows) in enumerate(sorted(data["groups"].items())):
            col = tk.Frame(grid, bg=PANEL)
            col.grid(row=i // 2, column=i % 2, padx=8, pady=8, sticky="nsew")
            grid.columnconfigure(i % 2, weight=1)
            tk.Label(col, text=f"Grupo {letter}", fg=TXT, bg=PANEL2,
                     font=(F, 12, "bold")).pack(fill="x", ipady=6)
            for r in rows:
                fg = GREEN_D if r["is_player"] else TXT
                tk.Label(col, text=f"{r['name']}   {r['pts']} pts  (SG {r['gd']:+d})",
                         fg=fg, bg=PANEL, font=(F, 11, "bold" if r["is_player"] else "normal"),
                         anchor="w").pack(fill="x", padx=12, pady=2)

    def _render_tabela_copa(self, comp):
        data = with_conn(lambda c: G.api_copa_bracket(c, comp))
        if not data.get("ok") or not data["stages"]:
            tk.Label(self.panel, text="Chaveamento ainda não sorteado.",
                     fg=DIM, bg=BG, font=(F, 12)).pack(padx=24, pady=12)
            return
        wrap = tk.Frame(self.panel, bg=BG)
        wrap.pack(fill="both", expand=True, padx=24, pady=(8, 0))
        tk.Label(wrap, text=data["name"], fg=GOLD, bg=BG, font=(F, 12, "bold")).pack(anchor="w", pady=(0, 10))
        for stage in data["stages"]:
            tk.Label(wrap, text=stage["name"], fg=TXT, bg=BG, font=(F, 12, "bold")).pack(anchor="w", pady=(8, 4))
            for m in stage["matches"]:
                fg = GREEN_D if m["is_player"] else TXT
                txt = f"{m['home']}  {m['score']}  {m['away']}"
                if m["played"]:
                    txt += f"   →  {m['winner']}"
                tk.Label(wrap, text=txt, fg=fg, bg=PANEL,
                         font=(F, 11, "bold" if m["is_player"] else "normal"),
                         anchor="w").pack(fill="x", pady=1)

    # ─── ESCALAÇÃO ─────────────────────────────────────────────────────────────
    def _panel_escalacao(self):
        self._panel_title("Escalação")
        data = with_conn(G.api_lineup)
        if not data.get("ok"):
            tk.Label(self.panel, text="Elenco insuficiente.", fg=DIM, bg=BG, font=(F, 12)).pack(padx=24)
            return
        self._lineup = data
        self._xi_ids = [p["id"] for p in data["xi"]]

        ctrl = tk.Frame(self.panel, bg=BG)
        ctrl.pack(fill="x", padx=24)
        tk.Label(ctrl, text="Formação:", fg=DIM, bg=BG, font=(F, 11)).pack(side="left")
        self.cb_form = ttk.Combobox(ctrl, values=data["formations"], state="readonly", width=8, font=(F, 12))
        self.cb_form.set(data["formation"])
        self.cb_form.pack(side="left", padx=(4, 16))
        self.cb_form.bind("<<ComboboxSelected>>", lambda e: self._change_formation())

        tk.Label(ctrl, text="Estilo:", fg=DIM, bg=BG, font=(F, 11)).pack(side="left")
        self.cb_style = ttk.Combobox(ctrl, values=["ofensivo", "equilibrado", "defensivo"],
                                     state="readonly", width=12, font=(F, 12))
        self.cb_style.set(data["style"])
        self.cb_style.pack(side="left", padx=4)

        self.lbl_avg = tk.Label(ctrl, text="", fg=GOLD, bg=BG, font=(F, 12, "bold"))
        self.lbl_avg.pack(side="right")

        self._by_id = {p["id"]: p for p in data["xi"] + data["bench"]}
        self._sel_id = None  # titular selecionado no campo

        body = tk.Frame(self.panel, bg=BG)
        body.pack(fill="both", expand=True, padx=24, pady=10)
        # ── campo (esquerda)
        self.pitch = tk.Frame(body, bg="#2f7d3a", highlightbackground=LINE, highlightthickness=1)
        self.pitch.pack(side="left", fill="both", expand=True, padx=(0, 10))
        # ── reservas (direita)
        rf = tk.Frame(body, bg=BG, width=260)
        rf.pack(side="left", fill="both")
        rf.pack_propagate(False)
        tk.Label(rf, text="RESERVAS", fg=DIM, bg=BG, font=(F, 11, "bold")).pack(anchor="w")
        tk.Label(rf, text="clique um titular no campo, depois um reserva", fg=DIM, bg=BG,
                 font=(F, 9)).pack(anchor="w")
        self.lb_bench = tk.Listbox(rf, bg=PANEL, fg=TXT, font=("Menlo", 12), relief="flat",
                                   selectbackground=GREEN_D, activestyle="none",
                                   highlightthickness=1, highlightbackground=LINE)
        self.lb_bench.pack(fill="both", expand=True, pady=4)
        self.lb_bench.bind("<Double-1>", lambda e: self._bench_into_pitch())

        actions = tk.Frame(self.panel, bg=BG)
        actions.pack(fill="x", padx=24, pady=(0, 14))
        self._btn(actions, "↧ Colocar reserva no titular selecionado", self._bench_into_pitch,
                  bg=PANEL2, fg=TXT).pack(side="left")
        self._btn(actions, "💾 Salvar escalação", self._save_lineup).pack(side="right")
        self._refresh_pitch()

    # rows do campo: GK embaixo, depois DF, MF, FW (ataque em cima)
    def _xi_by_row(self):
        rows = {"GK": [], "DF": [], "MF": [], "FW": []}
        for pid in self._xi_ids:
            p = self._by_id.get(pid)
            if p:
                rows.setdefault(p["pos"], rows["MF"]).append(p)
        return rows

    def _refresh_pitch(self):
        for w in self.pitch.winfo_children():
            w.destroy()
        rows = self._xi_by_row()
        order = [("FW", rows["FW"]), ("MF", rows["MF"]), ("DF", rows["DF"]), ("GK", rows["GK"])]
        for _, players in order:
            line = tk.Frame(self.pitch, bg="#2f7d3a")
            line.pack(expand=True, fill="x", pady=6)
            inner = tk.Frame(line, bg="#2f7d3a")
            inner.pack(anchor="center")
            for p in players:
                self._pitch_token(inner, p)
        # reservas
        self.lb_bench.delete(0, "end")
        self._bench_order = [pid for pid in self._by_id if pid not in self._xi_ids]
        self._bench_order.sort(key=lambda i: ("GK DF MF FW".index(self._by_id[i]["pos"])
                                              if self._by_id[i]["pos"] in "GK DF MF FW" else 9,
                                              -self._by_id[i]["ovr"]))
        for pid in self._bench_order:
            p = self._by_id[pid]
            self.lb_bench.insert("end", f"{p['role']:<3} {p['name'][:18]:<18} {p['ovr']}")
        avg = round(sum(self._by_id[i]["ovr"] for i in self._xi_ids) / 11, 1) if len(self._xi_ids) == 11 else 0
        self.lbl_avg.config(text=f"Média do XI: {avg}")

    def _pitch_token(self, parent, p):
        # Cartão claro sobre o gramado escuro — alto contraste, lê de longe
        # (era verde-escuro sobre verde-escuro, quase ilegível). Selecionado
        # vira dourado, igual ao destaque já usado no resto da GUI.
        selected = p["id"] == self._sel_id
        bg = GOLD if selected else PANEL
        fg = TXT
        last = p["name"].split()[-1][:11]
        fit = p.get("fitness", 100)
        dot = "🟢" if fit >= 75 else ("🟡" if fit >= 50 else "🔴")
        b = tk.Button(parent, text=f"{last}\n{p['role']} · {p['ovr']}  {dot}{fit}%",
                      command=lambda i=p["id"]: self._select_slot(i),
                      bg=bg, fg=fg, font=(F, 10, "bold"), relief="flat", bd=0,
                      width=12, height=2, cursor="hand2",
                      activebackground=GOLD, activeforeground=TXT,
                      highlightthickness=2, highlightbackground="#173a1d")
        b.pack(side="left", padx=6)

    def _select_slot(self, pid):
        self._sel_id = None if self._sel_id == pid else pid
        self._refresh_pitch()

    def _bench_into_pitch(self):
        if self._sel_id is None:
            messagebox.showinfo("Escalar", "Clique primeiro num titular no campo (fica dourado).")
            return
        bs = self.lb_bench.curselection()
        if not bs:
            messagebox.showinfo("Escalar", "Selecione um reserva na lista à direita.")
            return
        in_id = self._bench_order[bs[0]]
        self._xi_ids = [in_id if i == self._sel_id else i for i in self._xi_ids]
        self._sel_id = None
        self._refresh_pitch()

    def _change_formation(self):
        f = self.cb_form.get()
        self._xi_ids = with_conn(lambda c: G.auto_lineup_ids(c, f))
        self._sel_id = None
        self._refresh_pitch()

    def _save_lineup(self):
        if len(self._xi_ids) != 11:
            messagebox.showwarning("XI inválido", "Precisa de exatamente 11 titulares.")
            return
        f, style, ids = self.cb_form.get(), self.cb_style.get(), self._xi_ids
        with_conn(lambda c: G.save_lineup(c, f, style, ids))
        messagebox.showinfo("Salvo", "Escalação salva.")

    # ─── MERCADO ─────────────────────────────────────────────────────────────
    def _panel_mercado(self):
        self._panel_title("Mercado de transferências")
        # ── linha 1 de filtros
        f1 = tk.Frame(self.panel, bg=BG)
        f1.pack(fill="x", padx=24)
        tk.Label(f1, text="Posição:", fg=DIM, bg=BG, font=(F, 11)).pack(side="left")
        self.cb_mpos = ttk.Combobox(f1, values=["Todas", "GK", "DF", "MF", "FW"],
                                    state="readonly", width=6, font=(F, 12))
        self.cb_mpos.set("Todas"); self.cb_mpos.pack(side="left", padx=(4, 12))
        tk.Label(f1, text="Nacionalidade:", fg=DIM, bg=BG, font=(F, 11)).pack(side="left")
        nats = ["Todas"] + with_conn(G.api_nationalities)
        self.cb_mnat = ttk.Combobox(f1, values=nats, state="readonly", width=8, font=(F, 12))
        self.cb_mnat.set("Todas"); self.cb_mnat.pack(side="left", padx=(4, 12))
        tk.Label(f1, text="Idade até:", fg=DIM, bg=BG, font=(F, 11)).pack(side="left")
        self.en_mage = tk.Entry(f1, bg=BG2, fg=TXT, insertbackground=TXT, font=(F, 12),
                                relief="flat", width=4)
        self.en_mage.pack(side="left", padx=(4, 12), ipady=3)
        tk.Label(f1, text="OVR mín:", fg=DIM, bg=BG, font=(F, 11)).pack(side="left")
        self.en_movr = tk.Entry(f1, bg=BG2, fg=TXT, insertbackground=TXT, font=(F, 12),
                                relief="flat", width=4)
        self.en_movr.pack(side="left", padx=(4, 12), ipady=3)
        tk.Label(f1, text="Valor até (M€):", fg=DIM, bg=BG, font=(F, 11)).pack(side="left")
        self.en_mvalue = tk.Entry(f1, bg=BG2, fg=TXT, insertbackground=TXT, font=(F, 12),
                                  relief="flat", width=6)
        self.en_mvalue.pack(side="left", padx=(4, 12), ipady=3)
        # ── linha 2: checkboxes + ação
        f2 = tk.Frame(self.panel, bg=BG)
        f2.pack(fill="x", padx=24, pady=(6, 4))
        self.var_transfer = tk.BooleanVar()
        self.var_loan = tk.BooleanVar()
        tk.Checkbutton(f2, text="Só lista de transferência (V)", variable=self.var_transfer,
                       bg=BG, fg=TXT, selectcolor=BG2, activebackground=BG,
                       font=(F, 11), bd=0, highlightthickness=0).pack(side="left")
        tk.Checkbutton(f2, text="Só lista de empréstimo (E)", variable=self.var_loan,
                       bg=BG, fg=TXT, selectcolor=BG2, activebackground=BG,
                       font=(F, 11), bd=0, highlightthickness=0).pack(side="left", padx=(12, 0))
        self._btn(f2, "🔍 Filtrar", self._load_market, bg=GREEN, pady=4).pack(side="left", padx=12)
        self.lbl_money = tk.Label(f2, text="", fg=GREEN, bg=BG, font=(F, 13, "bold"))
        self.lbl_money.pack(side="right")

        cols = ("name", "pos", "nat", "age", "ovr", "pot", "club", "asking", "clause", "flags")
        self._mkt_heads = {"name": "Jogador", "pos": "POS", "nat": "Nac", "age": "Idade",
                           "ovr": "OVR", "pot": "POT", "club": "Clube", "asking": "Pede",
                           "clause": "Cláusula", "flags": "Lista"}
        widths = (170, 46, 50, 50, 46, 46, 140, 84, 84, 50)
        self.tv_market = self._sortable_table(cols, widths, self._mkt_heads, self._sort_market)
        self.tv_market.bind("<Double-1>", lambda e: self._negotiate())
        act = tk.Frame(self.panel, bg=BG)
        act.pack(fill="x", padx=24, pady=(0, 14))
        tk.Label(act, text="Duplo-clique = negociar.  V=à venda  E=empréstimo.  Clique no cabeçalho p/ ordenar.",
                 fg=DIM, bg=BG, font=(F, 11)).pack(side="left")
        self._btn(act, "Vender do elenco…", self._sell_dialog, bg=PANEL2, fg=TXT).pack(side="right")
        self._btn(act, "Ver perfil", lambda: self._open_player_from(self.tv_market, "mercado"),
                  bg=PANEL2, fg=TXT).pack(side="right", padx=(0, 6))
        self._mkt_sort = ("ovr", True)
        self._load_market()

    def _int_or(self, entry, default):
        try:
            return int(entry.get().strip())
        except (ValueError, AttributeError):
            return default

    def _load_market(self):
        pos = self.cb_mpos.get()
        nat = self.cb_mnat.get()
        value_m = self._int_or(self.en_mvalue, 0)
        kw = dict(
            position=None if pos == "Todas" else pos,
            nationality=None if nat == "Todas" else nat,
            max_age=self._int_or(self.en_mage, 99),
            min_ovr=self._int_or(self.en_movr, 0),
            max_price=value_m * 1_000_000 if value_m > 0 else None,
            only_transfer=self.var_transfer.get(),
            only_loan=self.var_loan.get(),
        )
        data = with_conn(lambda c: G.api_market(c, **kw))
        self._mkt_rows = data["players"]
        self.lbl_money.config(text=f"Caixa: {data['money_fmt']}  ·  {data['count']} jogadores")
        self._render_market()

    def _render_market(self):
        self._market = {str(p["id"]): p for p in self._mkt_rows}
        key, rev = self._mkt_sort
        keymap = {"name": "name", "pos": "role", "nat": "nat", "age": "age", "ovr": "ovr",
                  "pot": "pot", "club": "club", "asking": "asking", "clause": "clause", "flags": "flags"}
        kf = keymap.get(key, "ovr")
        rows = sorted(self._mkt_rows, key=lambda p: (p.get(kf) is None, p.get(kf)), reverse=rev)
        for i in self.tv_market.get_children():
            self.tv_market.delete(i)
        for p in rows:
            self.tv_market.insert("", "end", iid=str(p["id"]), values=(
                p["name"], p["role"], p["nat"], p["age"], p["ovr"], p["pot"] or "—",
                p["club"], p["asking_fmt"], p["clause_fmt"], p["flags"]))

    def _sort_market(self, col):
        key, rev = self._mkt_sort
        self._mkt_sort = (col, not rev if key == col else True)
        self._render_market()

    def _negotiate(self):
        sel = self.tv_market.selection()
        if not sel:
            return
        p = self._market[sel[0]]
        # Empréstimo é negócio diferente — sem taxa de compra/agente, banca
        # % do salário + valor mensal ao clube dono. Listado só p/ empréstimo
        # não pode passar pelo fluxo de transferência definitiva.
        if p["loan_listed"] and not p["transfer_listed"]:
            self._negotiate_loan(p)
            return
        if p["loan_listed"] and p["transfer_listed"]:
            choice = messagebox.askyesnocancel(
                "Tipo de proposta",
                f"{p['name']} está disponível tanto para venda quanto para empréstimo.\n\n"
                "Sim = transferência definitiva\nNão = empréstimo\nCancelar = voltar")
            if choice is None:
                return
            if choice is False:
                self._negotiate_loan(p)
                return
        offer = simpledialog.askinteger(
            "Negociar", f"{p['name']} ({p['ovr']}) — {p['club']}\n\n"
            f"Valor: {p['value_fmt']}\nPede: {p['asking_fmt']}\nCláusula: {p['clause_fmt']}\n\n"
            "Sua oferta (€):", parent=self, minvalue=0, initialvalue=p["asking"])
        if offer is None:
            return
        r = with_conn(lambda c: G.api_offer(c, p["id"], offer))
        res = r["result"]
        if res in ("accept", "clause"):
            tag = "cláusula atingida" if res == "clause" else "oferta aceita"
            if messagebox.askyesno("Acordo com o clube",
                                   f"{tag.capitalize()}! {p['club']} topa vender {p['name']} "
                                   f"por {r['value_fmt']}.\n\nPassar pra etapa seguinte "
                                   f"(jogador + agente)?"):
                self._negotiate_terms(p, r["value"])
        elif res == "counter":
            if messagebox.askyesno("Contraproposta",
                    f"{p['club']} recusou, mas aceita por {r['value_fmt']}.\n\n"
                    f"Topar e seguir pra negociação com jogador/agente?"):
                self._negotiate_terms(p, r["value"])
        else:
            messagebox.showinfo("Recusado", f"{p['club']} recusou a oferta. Pede ao menos {r and G.fmt_money(r['asking'])}.")

    def _negotiate_loan(self, p):
        """Empréstimo: negócio diferente da transferência — sem taxa de
        compra nem agente. Você banca um % do salário (pago ao clube dono)
        + um valor mensal fixo. Cobertura total precisa bater o mínimo
        exigido pra qualidade do jogador (engine.transfer.loan_min_coverage)."""
        t = with_conn(lambda c: G.api_loan_terms(c, p["id"]))
        if not t.get("ok"):
            messagebox.showinfo("Empréstimo", t.get("msg", "Indisponível."))
            return
        wage_pct = simpledialog.askinteger(
            "Empréstimo — % do salário",
            f"{t['name']} (OVR {t['overall']}) — salário atual {t['wage_fmt']}/ano\n\n"
            f"Cobertura mínima exigida pelo clube dono: {t['min_coverage']}%\n"
            "(% do salário bancado + taxa mensal anualizada ÷ salário)\n\n"
            "Quanto % do salário você banca (0-100)?",
            parent=self, minvalue=0, maxvalue=100, initialvalue=50)
        if wage_pct is None:
            return
        monthly_fee_k = simpledialog.askinteger(
            "Empréstimo — taxa mensal",
            f"Taxa mensal a pagar ao clube dono (em €K, pode ser 0):",
            parent=self, minvalue=0, initialvalue=0)
        if monthly_fee_k is None:
            return
        monthly_fee = monthly_fee_k * 1000
        yr_cost = int((t["wage"] or 0) * wage_pct / 100 + monthly_fee * 12)
        if not messagebox.askyesno(
                "Confirmar proposta de empréstimo",
                f"Propor empréstimo de {t['name']}:\n\n"
                f"Você banca {wage_pct}% do salário + {G.fmt_money(monthly_fee)}/mês ao clube dono\n"
                f"Custo estimado: ~{G.fmt_money(yr_cost)}/ano\n\n"
                "Enviar proposta?"):
            return
        r = with_conn(lambda c: G.api_loan_in(c, p["id"], wage_pct, monthly_fee))
        messagebox.showinfo("Empréstimo", r["msg"])
        if r["ok"]:
            self.show_hub()

    def _negotiate_terms(self, p, fee):
        """Etapa 2/3 — depois do clube vendedor topar a taxa, JOGADOR
        (exigência salarial) e AGENTE (comissão) entram na mesa."""
        t = with_conn(lambda c: G.api_player_terms(c, p["id"], fee))
        if not t.get("ok"):
            return
        msg = (f"💰 Taxa de transferência acertada com o clube: {t['fee_fmt']}\n\n"
               f"💬 {p['name']} topa assinar — mas exige {t['wage_demand_fmt']}/ano de salário.\n"
               f"💼 O agente dele cobra {t['agent_fee_fmt']} de comissão pra destravar o negócio.\n\n"
               f"Custo total da operação: {t['total_cost_fmt']}\n"
               f"Seu caixa: {t['money_fmt']}\n\n"
               f"Fechar negócio nesses termos?")
        if messagebox.askyesno("Termos com jogador e agente", msg):
            r = with_conn(lambda c: G.api_finalize_transfer(c, p["id"], fee, t["wage_demand"]))
            messagebox.showinfo("Mercado", r["msg"])
            if r["ok"]:
                self.show_hub()

    def _sell_dialog(self):
        squad = with_conn(G.api_squad)
        own = [p for p in squad if not p["loan"]]
        if not own:
            return
        names = [f"{p['position']} {p['name']} ({p['overall']}) — {p['value_fmt']}" for p in own]
        win = tk.Toplevel(self)
        win.title("Vender jogador")
        win.configure(bg=PANEL)
        tk.Label(win, text="Escolha quem vender:", fg=TXT, bg=PANEL, font=(F, 12, "bold")).pack(padx=16, pady=8)
        lb = tk.Listbox(win, bg=BG2, fg=TXT, font=("Menlo", 12), width=46, height=16,
                        selectbackground=GREEN_D, relief="flat")
        lb.pack(padx=16, pady=4)
        for n in names:
            lb.insert("end", n)

        def do_sell():
            s = lb.curselection()
            if not s:
                return
            p = own[s[0]]
            if messagebox.askyesno("Vender", f"Vender {p['name']}?", parent=win):
                r = with_conn(lambda c: G.api_sell(c, p["id"]))
                messagebox.showinfo("Mercado", r["msg"], parent=win)
                win.destroy()
                self.show_hub()
        self._btn(win, "Vender", do_sell).pack(pady=10)

    # ─── CONTRATOS ───────────────────────────────────────────────────────────
    def _panel_contratos(self):
        self._panel_title("Contratos vencendo")
        data = with_conn(G.api_contracts)
        if not data.get("ok"):
            return
        info = tk.Frame(self.panel, bg=BG)
        info.pack(fill="x", padx=24)
        tk.Label(info, text=f"Caixa: {data['money_fmt']}   ·   Folha salarial: {data['wage_bill_fmt']}",
                 fg=DIM, bg=BG, font=(F, 11)).pack(side="left")
        if not data["players"]:
            tk.Label(self.panel, text="Nenhum contrato vencendo nos próximos 2 anos.",
                     fg=DIM, bg=BG, font=(F, 12)).pack(padx=24, pady=20)
            return
        cols = ("name", "pos", "age", "ovr", "wage", "until", "demand", "form")
        heads = {"name": "Jogador", "pos": "POS", "age": "Idade", "ovr": "OVR",
                 "wage": "Salário atual", "until": "Fim contrato", "demand": "Pretensão",
                 "form": "Forma"}
        widths = (190, 50, 60, 55, 110, 100, 110, 60)
        self._ctr_rows = {str(p["id"]): p for p in data["players"]}
        tv = self._table(cols, [heads[c] for c in cols], widths)
        for p in data["players"]:
            tv.insert("", "end", iid=str(p["id"]), values=(
                p["name"], p["role"], p["age"], p["ovr"], p["wage_fmt"],
                p["contract_until"], p["demand_wage_fmt"] + f" ({p['demand_years']}a)", p["form"]))
        self.tv_contracts = tv
        tv.bind("<Double-1>", lambda e: self._negotiate_renewal())
        act = tk.Frame(self.panel, bg=BG)
        act.pack(fill="x", padx=24, pady=(0, 14))
        tk.Label(act, text="Duplo-clique = negociar renovação. \"Pretensão\" é o salário/anos que o jogador espera.",
                 fg=DIM, bg=BG, font=(F, 11)).pack(side="left")
        self._btn(act, "Deixar sair (não renovar)…", self._let_expire_dialog, bg=PANEL2, fg=TXT).pack(side="right")

    def _negotiate_renewal(self):
        sel = self.tv_contracts.selection()
        if not sel:
            return
        p = self._ctr_rows[sel[0]]
        win = tk.Toplevel(self)
        win.title("Renovar contrato")
        win.configure(bg=PANEL)
        tk.Label(win, text=f"{p['name']} ({p['role']}, {p['age']}a, OVR {p['ovr']})",
                 fg=TXT, bg=PANEL, font=(F, 13, "bold")).pack(padx=18, pady=(14, 2))
        tk.Label(win, text=f"Salário atual: {p['wage_fmt']}   ·   Pretensão: {p['demand_wage_fmt']} "
                           f"por {p['demand_years']} anos",
                 fg=DIM, bg=PANEL, font=(F, 11)).pack(padx=18, pady=(0, 10))

        row1 = tk.Frame(win, bg=PANEL); row1.pack(fill="x", padx=18, pady=4)
        tk.Label(row1, text="Salário oferecido (€/ano):", fg=DIM, bg=PANEL, font=(F, 11), width=20, anchor="w").pack(side="left")
        en_wage = tk.Entry(row1, bg=BG2, fg=TXT, insertbackground=TXT, font=(F, 12), relief="flat", width=12)
        en_wage.insert(0, str(p["demand_wage"]))
        en_wage.pack(side="left", ipady=3)

        row2 = tk.Frame(win, bg=PANEL); row2.pack(fill="x", padx=18, pady=4)
        tk.Label(row2, text="Duração (anos):", fg=DIM, bg=PANEL, font=(F, 11), width=20, anchor="w").pack(side="left")
        sc_years = tk.Scale(row2, from_=1, to=5, orient="horizontal", bg=PANEL, fg=TXT,
                            troughcolor=PANEL2, highlightthickness=0, length=160)
        sc_years.set(p["demand_years"])
        sc_years.pack(side="left")

        def propose():
            try:
                wage = int(en_wage.get().strip())
            except ValueError:
                messagebox.showwarning("Inválido", "Informe um salário em €.", parent=win)
                return
            years = sc_years.get()
            r = with_conn(lambda c: G.api_renewal_offer(c, p["id"], wage, years))
            res = r["result"]
            if res == "accept":
                if messagebox.askyesno("Acordo", f"{p['name']} aceita {r['wage_fmt']}/ano por {r['years']} anos.\nFechar?",
                                       parent=win):
                    rr = with_conn(lambda c: G.api_renew(c, p["id"], r["wage"], r["years"]))
                    messagebox.showinfo("Contratos", rr["msg"], parent=win)
                    if rr["ok"]:
                        win.destroy(); self.show_hub()
            elif res == "counter":
                if messagebox.askyesno("Contraproposta",
                        f"{p['name']} recusa, mas toparia {r['wage_fmt']}/ano por {r['years']} anos.\nFechar nesses termos?",
                        parent=win):
                    rr = with_conn(lambda c: G.api_renew(c, p["id"], r["wage"], r["years"]))
                    messagebox.showinfo("Contratos", rr["msg"], parent=win)
                    if rr["ok"]:
                        win.destroy(); self.show_hub()
            else:
                messagebox.showinfo("Recusado",
                    f"{p['name']} recusa a proposta. Quer ao menos {r['demand_wage_fmt']}/ano por {r['demand_years']} anos.",
                    parent=win)

        self._btn(win, "Propor", propose).pack(pady=(10, 16))

    def _let_expire_dialog(self):
        rows = list(self._ctr_rows.values())
        if not rows:
            return
        names = [f"{p['role']} {p['name']} ({p['ovr']}) — termina {p['contract_until']}" for p in rows]
        win = tk.Toplevel(self)
        win.title("Deixar sair")
        win.configure(bg=PANEL)
        tk.Label(win, text="Quem você NÃO vai renovar (sai como agente livre no fim do contrato):",
                 fg=TXT, bg=PANEL, font=(F, 12, "bold"), wraplength=380, justify="left").pack(padx=16, pady=8)
        lb = tk.Listbox(win, bg=BG2, fg=TXT, font=("Menlo", 12), width=50, height=12,
                        selectbackground=GREEN_D, relief="flat")
        lb.pack(padx=16, pady=4)
        for n in names:
            lb.insert("end", n)

        def confirm():
            s = lb.curselection()
            if not s:
                return
            p = rows[s[0]]
            if messagebox.askyesno("Confirmar", f"Deixar {p['name']} sair como agente livre?", parent=win):
                r = with_conn(lambda c: G.api_let_expire(c, p["id"]))
                messagebox.showinfo("Contratos", r["msg"], parent=win)
                win.destroy()
                self.show_hub()
        self._btn(win, "Confirmar", confirm).pack(pady=10)

    # ─── ESTÁDIO & CT ────────────────────────────────────────────────────────
    def _panel_estadio(self):
        self._panel_title("Estádio & Centro de Treinamento")
        d = with_conn(G.api_stadium)
        if not d.get("ok"):
            return
        box = tk.Frame(self.panel, bg=PANEL, padx=22, pady=18, highlightbackground=LINE, highlightthickness=1)
        box.pack(fill="x", padx=24)

        tk.Label(box, text=f"🏟  Capacidade: {d['capacity']:,} lugares   ·   ingresso de referência €{d['base']}",
                 fg=TXT, bg=PANEL, font=(F, 13)).pack(anchor="w", pady=(0, 10))

        row1 = tk.Frame(box, bg=PANEL)
        row1.pack(fill="x", pady=4)
        tk.Label(row1, text="Preço do ingresso (€):", fg=DIM, bg=PANEL, font=(F, 12), width=22, anchor="w").pack(side="left")
        self.sc_price = tk.Scale(row1, from_=5, to=300, orient="horizontal", bg=PANEL, fg=TXT,
                                 troughcolor=PANEL2, highlightthickness=0, length=320,
                                 command=lambda v: self._proj_update())
        self.sc_price.set(d["price"])
        self.sc_price.pack(side="left")

        row2 = tk.Frame(box, bg=PANEL)
        row2.pack(fill="x", pady=4)
        tk.Label(row2, text="Nível do CT (1-5):", fg=DIM, bg=PANEL, font=(F, 12), width=22, anchor="w").pack(side="left")
        self.sc_ct = tk.Scale(row2, from_=1, to=5, orient="horizontal", bg=PANEL, fg=TXT,
                              troughcolor=PANEL2, highlightthickness=0, length=320,
                              command=lambda v: self._proj_update())
        self.sc_ct.set(d["training"])
        self.sc_ct.pack(side="left")

        row3 = tk.Frame(box, bg=PANEL)
        row3.pack(fill="x", pady=4)
        tk.Label(row3, text="Foco do treino:", fg=DIM, bg=PANEL, font=(F, 12), width=22, anchor="w").pack(side="left")
        focus_lbl = {"geral": "Geral", "fisico": "Físico", "tecnico": "Técnico", "finalizacao": "Finalização"}
        self.cb_focus = ttk.Combobox(row3, values=[focus_lbl[k] for k in d["training_focuses"]],
                                     state="readonly", width=14, font=(F, 12))
        self._focus_keys = d["training_focuses"]
        self._focus_lbl = focus_lbl
        self.cb_focus.set(focus_lbl.get(d["training_focus"], "Geral"))
        self.cb_focus.pack(side="left")

        self.lbl_proj = tk.Label(box, text="", fg=GOLD, bg=PANEL, font=(F, 12), justify="left")
        self.lbl_proj.pack(anchor="w", pady=(10, 4))
        tk.Label(box, text="CT >2 acelera evolução do elenco; <2 economiza. Foco direciona o "
                           "crescimento extra: físico (ritmo/força/fôlego), técnico (técnica/passe/marcação) "
                           "ou finalização (finalização/técnica/mental). Só afeta jovens em desenvolvimento. "
                           "Bilheteria entra nas finanças anuais.",
                 fg=DIM, bg=PANEL, font=(F, 10), wraplength=560, justify="left").pack(anchor="w")

        self._btn(box, "💾 Salvar", self._save_stadium).pack(anchor="w", pady=(12, 0))
        self._stad = d
        self._proj_update()

    def _proj_update(self):
        from engine.finance import attendance_fill, stadium_revenue
        d = self._stad
        price = self.sc_price.get()
        ct = self.sc_ct.get()
        # projeção rápida reusando engine (prestige da posição média 10/20)
        st = self.state_cache
        prest = st["club"]["prestige"]
        fill = attendance_fill(prest, 10, 20, price)
        rev = stadium_revenue(d["capacity"], prest, 10, 20, price)
        public = int(d["capacity"] * fill)
        self.lbl_proj.config(text=(
            f"Projeção: ocupação {fill*100:.0f}%  ({public:,}/jogo)  ·  bilheteria {G.fmt_money(rev)}/ano\n"
            f"Custo do CT nível {ct}: {G.fmt_money(ct*2_500_000)}/ano"))

    def _save_stadium(self):
        lbl_to_key = {v: k for k, v in self._focus_lbl.items()}
        focus = lbl_to_key.get(self.cb_focus.get(), "geral")
        with_conn(lambda c: G.save_stadium(c, self.sc_price.get(), self.sc_ct.get(), focus))
        messagebox.showinfo("Salvo", "Estádio e CT atualizados.")

    # ─── tabela genérica (ttk.Treeview) ─────────────────────────────────────────
    def _table(self, cols, headers, widths):
        frame = tk.Frame(self.panel, bg=BG)
        frame.pack(fill="both", expand=True, padx=24, pady=8)
        tv = ttk.Treeview(frame, columns=cols, show="headings", style="Dark.Treeview")
        for c, h, w in zip(cols, headers, widths):
            tv.heading(c, text=h)
            anchor = "w" if w >= 150 else "center"
            tv.column(c, width=w, anchor=anchor, stretch=False)
        sb = ttk.Scrollbar(frame, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        tv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        return tv

    def _sortable_table(self, cols, widths, heads, on_sort):
        """Treeview com cabeçalhos clicáveis (chama on_sort(col))."""
        frame = tk.Frame(self.panel, bg=BG)
        frame.pack(fill="both", expand=True, padx=24, pady=8)
        tv = ttk.Treeview(frame, columns=cols, show="headings", style="Dark.Treeview")
        for c, w in zip(cols, widths):
            tv.heading(c, text=heads[c], command=lambda cc=c: on_sort(cc))
            tv.column(c, width=w, anchor=("w" if w >= 140 else "center"), stretch=False)
        sb = ttk.Scrollbar(frame, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        tv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        return tv


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
