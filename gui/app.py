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
        kw.setdefault("padx", 14)
        kw.setdefault("pady", 8)
        b = tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg, font=(F, 12, "bold"),
                      relief="flat", activebackground=GREEN_D, activeforeground="#fff",
                      bd=0, cursor="hand2", **kw)
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
        nav = [("jogar", "▶  Jogar"), ("elenco", "👥  Elenco"), ("tabela", "📊  Classificação"),
               ("escalacao", "📋  Escalação"), ("mercado", "💰  Mercado"), ("estadio", "🏟  Estádio & CT")]
        for key, lbl in nav:
            active = key == self.view
            b = tk.Button(side, text=lbl, command=lambda k=key: self._nav(k),
                          bg=GREEN_D if active else BG2, fg="#fff" if active else TXT,
                          font=(F, 12, "bold" if active else "normal"), relief="flat",
                          anchor="w", padx=18, pady=11, bd=0, cursor="hand2",
                          activebackground=PANEL2, activeforeground=TXT)
            b.pack(fill="x", padx=6, pady=2)

        self.panel = tk.Frame(body, bg=BG)
        self.panel.pack(side="left", fill="both", expand=True)
        self._render_panel()

    def _stat(self, parent, label, val, color):
        f = tk.Frame(parent, bg=parent["bg"])
        f.pack(side="left", padx=12)
        tk.Label(f, text=label, fg="#cfe3d8", bg=parent["bg"], font=(F, 9, "bold")).pack(anchor="e")
        tk.Label(f, text=val, fg=color, bg=parent["bg"], font=(F, 16, "bold")).pack(anchor="e")

    def _nav(self, key):
        self.view = key
        self.show_hub()

    def _panel_title(self, text):
        tk.Label(self.panel, text=text, fg=TXT, bg=BG, font=(F, 17, "bold")).pack(anchor="w", padx=24, pady=(18, 10))

    def _render_panel(self):
        v = self.view
        if v == "jogar":
            self._panel_jogar()
        elif v == "elenco":
            self._panel_elenco()
        elif v == "tabela":
            self._panel_tabela()
        elif v == "escalacao":
            self._panel_escalacao()
        elif v == "mercado":
            self._panel_mercado()
        elif v == "estadio":
            self._panel_estadio()

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
        res = with_conn(G.api_play)
        # atualiza banner/caixa e re-renderiza hub, depois mostra resultado
        self.show_hub()
        if self.view != "jogar":
            return
        self._show_result(res)

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

    # ─── ELENCO ──────────────────────────────────────────────────────────────
    def _panel_elenco(self):
        self._panel_title("Elenco")
        squad = with_conn(G.api_squad)
        cols = ("pos", "name", "age", "ovr", "pot", "value", "wage", "contract")
        tv = self._table(cols, ("POS", "Jogador", "Idade", "OVR", "POT", "Valor", "Salário", "Contrato"),
                         widths=(50, 220, 60, 55, 55, 90, 90, 90))
        for p in squad:
            tag = "loan" if p["loan"] else ""
            tv.insert("", "end", tags=(tag,), values=(
                p["position"], p["name"], p["age"], p["overall"], p["potential"] or "—",
                p["value_fmt"], p["wage_fmt"], p["contract"] or "—"))
        tv.tag_configure("loan", foreground=DIM)

    # ─── TABELA ──────────────────────────────────────────────────────────────
    def _panel_tabela(self):
        data = with_conn(G.api_table)
        self._panel_title(f"Classificação {data.get('season') or ''}")
        if not data["rows"]:
            tk.Label(self.panel, text="Tabela ainda não iniciada (jogue a 1ª rodada).",
                     fg=DIM, bg=BG, font=(F, 12)).pack(padx=24)
            return
        cols = ("pos", "name", "j", "v", "e", "d", "gp", "gc", "sg", "pts")
        tv = self._table(cols, ("#", "Clube", "J", "V", "E", "D", "GP", "GC", "SG", "Pts"),
                         widths=(40, 200, 40, 40, 40, 40, 45, 45, 45, 50))
        for r in data["rows"]:
            tags = []
            if r["is_player"]:
                tags.append("me")
            elif r["zone"] == "cl":
                tags.append("cl")
            elif r["zone"] == "rel":
                tags.append("rel")
            tv.insert("", "end", tags=tuple(tags), values=(
                r["pos"], r["name"], r["played"], r["wins"], r["draws"], r["losses"],
                r["gf"], r["ga"], r["gd"], r["points"]))
        tv.tag_configure("me", background=GREEN_D, foreground="#fff")
        tv.tag_configure("cl", foreground=GREEN)
        tv.tag_configure("rel", foreground=RED)

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

        body = tk.Frame(self.panel, bg=BG)
        body.pack(fill="both", expand=True, padx=24, pady=10)
        # XI
        lf = tk.Frame(body, bg=BG)
        lf.pack(side="left", fill="both", expand=True, padx=(0, 8))
        tk.Label(lf, text="TITULARES (11)", fg=GREEN, bg=BG, font=(F, 11, "bold")).pack(anchor="w")
        self.lb_xi = tk.Listbox(lf, bg=PANEL, fg=TXT, font=("Menlo", 12), relief="flat",
                                selectbackground=GREEN_D, height=14, activestyle="none",
                                highlightthickness=1, highlightbackground=LINE)
        self.lb_xi.pack(fill="both", expand=True, pady=4)
        # Banco
        rf = tk.Frame(body, bg=BG)
        rf.pack(side="left", fill="both", expand=True, padx=(8, 0))
        tk.Label(rf, text="RESERVAS", fg=DIM, bg=BG, font=(F, 11, "bold")).pack(anchor="w")
        self.lb_bench = tk.Listbox(rf, bg=PANEL, fg=TXT, font=("Menlo", 12), relief="flat",
                                   selectbackground=GREEN_D, height=14, activestyle="none",
                                   highlightthickness=1, highlightbackground=LINE)
        self.lb_bench.pack(fill="both", expand=True, pady=4)

        actions = tk.Frame(self.panel, bg=BG)
        actions.pack(fill="x", padx=24, pady=(0, 14))
        self._btn(actions, "⇄ Trocar (titular ↔ reserva)", self._swap_players, bg=PANEL2, fg=TXT).pack(side="left")
        self._btn(actions, "💾 Salvar escalação", self._save_lineup).pack(side="right")
        self._refresh_lineup_lists()

    def _refresh_lineup_lists(self):
        by_id = {p["id"]: p for p in self._lineup["xi"] + self._lineup["bench"]}
        self.lb_xi.delete(0, "end")
        self._xi_order = list(self._xi_ids)
        for pid in self._xi_order:
            p = by_id.get(pid)
            if p:
                self.lb_xi.insert("end", f"{p['pos']:<3} {p['name'][:20]:<20} {p['ovr']}")
        bench_ids = [p["id"] for p in self._lineup["xi"] + self._lineup["bench"] if p["id"] not in self._xi_ids]
        self.lb_bench.delete(0, "end")
        self._bench_order = bench_ids
        for pid in bench_ids:
            p = by_id.get(pid)
            if p:
                self.lb_bench.insert("end", f"{p['pos']:<3} {p['name'][:20]:<20} {p['ovr']}")
        avg = round(sum(by_id[i]["ovr"] for i in self._xi_ids) / 11, 1) if len(self._xi_ids) == 11 else 0
        self.lbl_avg.config(text=f"Média do XI: {avg}")

    def _swap_players(self):
        xs = self.lb_xi.curselection()
        bs = self.lb_bench.curselection()
        if not xs or not bs:
            messagebox.showinfo("Trocar", "Selecione 1 titular E 1 reserva pra trocar.")
            return
        out_id = self._xi_order[xs[0]]
        in_id = self._bench_order[bs[0]]
        self._xi_ids = [in_id if i == out_id else i for i in self._xi_ids]
        self._refresh_lineup_lists()

    def _change_formation(self):
        f = self.cb_form.get()
        self._xi_ids = with_conn(lambda c: G.auto_lineup_ids(c, f))
        self._refresh_lineup_lists()

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
        flt = tk.Frame(self.panel, bg=BG)
        flt.pack(fill="x", padx=24)
        tk.Label(flt, text="Posição:", fg=DIM, bg=BG, font=(F, 11)).pack(side="left")
        self.cb_mpos = ttk.Combobox(flt, values=["Todas", "GK", "DF", "MF", "FW"],
                                    state="readonly", width=7, font=(F, 12))
        self.cb_mpos.set("Todas")
        self.cb_mpos.pack(side="left", padx=(4, 14))
        self._btn(flt, "🔍 Filtrar", self._load_market, bg=PANEL2, fg=TXT, pady=4).pack(side="left")
        self.lbl_money = tk.Label(flt, text="", fg=GREEN, bg=BG, font=(F, 13, "bold"))
        self.lbl_money.pack(side="right")

        cols = ("name", "pos", "age", "ovr", "pot", "club", "asking", "clause")
        self.tv_market = self._table(cols,
            ("Jogador", "POS", "Id", "OVR", "POT", "Clube", "Pede", "Cláusula"),
            widths=(180, 50, 45, 50, 50, 150, 90, 90))
        self.tv_market.bind("<Double-1>", lambda e: self._negotiate())
        act = tk.Frame(self.panel, bg=BG)
        act.pack(fill="x", padx=24, pady=(0, 14))
        tk.Label(act, text="Duplo-clique pra negociar a compra.", fg=DIM, bg=BG, font=(F, 11)).pack(side="left")
        self._btn(act, "Vender selecionado do elenco…", self._sell_dialog, bg=PANEL2, fg=TXT).pack(side="right")
        self._load_market()

    def _load_market(self):
        pos = self.cb_mpos.get()
        pos = None if pos == "Todas" else pos
        data = with_conn(lambda c: G.api_market(c, position=pos))
        self._market = {str(p["id"]): p for p in data["players"]}
        self.lbl_money.config(text=f"Caixa: {data['money_fmt']}")
        for i in self.tv_market.get_children():
            self.tv_market.delete(i)
        for p in data["players"]:
            self.tv_market.insert("", "end", iid=str(p["id"]), values=(
                p["name"], p["pos"], p["age"], p["ovr"], p["pot"] or "—", p["club"],
                p["asking_fmt"], p["clause_fmt"]))

    def _negotiate(self):
        sel = self.tv_market.selection()
        if not sel:
            return
        p = self._market[sel[0]]
        offer = simpledialog.askinteger(
            "Negociar", f"{p['name']} ({p['ovr']}) — {p['club']}\n\n"
            f"Valor: {p['value_fmt']}\nPede: {p['asking_fmt']}\nCláusula: {p['clause_fmt']}\n\n"
            "Sua oferta (€):", parent=self, minvalue=0, initialvalue=p["asking"])
        if offer is None:
            return
        r = with_conn(lambda c: G.api_offer(c, p["id"], offer))
        res = r["result"]
        if res in ("accept", "clause"):
            price = r["value"]
            tag = "cláusula atingida" if res == "clause" else "oferta aceita"
            if messagebox.askyesno("Acordo", f"{tag.capitalize()}! Comprar {p['name']} por {r['value_fmt']}?"):
                self._do_buy(p["id"], price)
        elif res == "counter":
            if messagebox.askyesno("Contraproposta",
                    f"{p['club']} recusou, mas aceita por {r['value_fmt']}.\nFechar negócio?"):
                self._do_buy(p["id"], r["value"])
        else:
            messagebox.showinfo("Recusado", f"{p['club']} recusou a oferta. Pede ao menos {r and G.fmt_money(r['asking'])}.")

    def _do_buy(self, pid, price):
        r = with_conn(lambda c: G.api_buy(c, pid, price))
        messagebox.showinfo("Mercado", r["msg"])
        if r["ok"]:
            self.show_hub()  # atualiza caixa

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

        self.lbl_proj = tk.Label(box, text="", fg=GOLD, bg=PANEL, font=(F, 12), justify="left")
        self.lbl_proj.pack(anchor="w", pady=(10, 4))
        tk.Label(box, text="CT >2 acelera evolução do elenco; <2 economiza. Bilheteria entra nas finanças anuais.",
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
        with_conn(lambda c: G.save_stadium(c, self.sc_price.get(), self.sc_ct.get()))
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


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
