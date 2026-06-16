"""
FUTMANAGER — GUI compacta (Tkinter).
Modo offline/leve para quem prefere janela nativa sobre navegador.
Reusa gameapi diretamente. Não replica todas as views da web.
Uso:  python3 -m gui.compact   ou   python3 main.py --gui
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tkinter as tk
from tkinter import ttk, messagebox
import gameapi as G

BG = "#0d1411"
BG2 = "#14201a"
PANEL = "#1a2a22"
PANEL2 = "#213328"
LINE = "#2c4537"
GREEN = "#2ea043"
GREEN_D = "#1f6f30"
GOLD = "#e3b341"
TXT = "#d8e6dd"
DIM = "#8aa698"
RED = "#d9544d"
F = "Helvetica"


def with_conn(fn):
    c = G.conn()
    try:
        return fn(c)
    finally:
        c.close()


class CompactApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FUTMANAGER — Modo Compacto")
        self.geometry("720x520")
        self.minsize(640, 440)
        self.configure(bg=BG)
        self._style()
        self.frame = tk.Frame(self, bg=BG)
        self.frame.pack(fill="both", expand=True, padx=18, pady=18)
        self.show_saves()

    def _style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("Dark.Treeview", background=PANEL, fieldbackground=PANEL,
                    foreground=TXT, rowheight=24, borderwidth=0, font=(F, 12))
        s.configure("Dark.Treeview.Heading", background=PANEL2, foreground=DIM,
                    font=(F, 10, "bold"), borderwidth=0, relief="flat")
        s.map("Dark.Treeview", background=[("selected", GREEN_D)],
              foreground=[("selected", "#ffffff")])

    def _clear(self):
        for w in self.frame.winfo_children():
            w.destroy()

    def _btn(self, parent, text, cmd, bg=GREEN, fg="#fff", fill=False):
        b = tk.Label(parent, text=text, bg=bg, fg=fg, font=(F, 12, "bold"),
                     padx=14, pady=8, cursor="hand2")
        b.bind("<Enter>", lambda e: b.configure(bg=GREEN_D))
        b.bind("<Leave>", lambda e: b.configure(bg=bg))
        b.bind("<Button-1>", lambda e: cmd())
        if fill:
            b.pack(fill="x", pady=4)
        else:
            b.pack(pady=4)
        return b

    # ─── SAVES ───
    def show_saves(self):
        self._clear()
        tk.Label(self.frame, text="⚽ FUTMANAGER", fg=GREEN, bg=BG,
                 font=(F, 26, "bold")).pack(pady=(0, 2))
        tk.Label(self.frame, text="modo compacto", fg=DIM, bg=BG,
                 font=(F, 12)).pack(pady=(0, 16))

        box = tk.Frame(self.frame, bg=PANEL, padx=20, pady=18,
                       highlightbackground=LINE, highlightthickness=1)
        box.pack(fill="x")
        tk.Label(box, text="CARREGAR JOGO", fg=DIM, bg=PANEL,
                 font=(F, 10, "bold")).pack(anchor="w")

        saves = G.api_saves()
        if not saves:
            tk.Label(box, text="Nenhum jogo salvo.", fg=DIM, bg=PANEL,
                     font=(F, 12), pady=12).pack()
        else:
            for sv in saves:
                self._save_row(box, sv)

        self._btn(box, "＋ Novo jogo", self.show_new_career).pack(fill="x", pady=(12, 0))

    def _save_row(self, parent, sv):
        row = tk.Frame(parent, bg=BG2, padx=12, pady=10,
                       highlightbackground=LINE, highlightthickness=1)
        row.pack(fill="x", pady=4)
        meta = (f"{sv.get('coach','?')} · temp. {sv.get('season','?')} · "
                f"{sv.get('titles',0)} títulos"
                + (" · DEMITIDO" if sv.get("status") == "sacked" else ""))
        tk.Label(row, text=sv.get("club", "?"), fg=TXT, bg=BG2,
                 font=(F, 13, "bold")).pack(anchor="w")
        tk.Label(row, text=meta, fg=DIM, bg=BG2, font=(F, 10)).pack(anchor="w")
        row.bind("<Button-1>", lambda e, slug=sv["slug"]: self._load(slug))
        for w in row.winfo_children():
            w.bind("<Button-1>", lambda e, slug=sv["slug"]: self._load(slug))

    def _load(self, slug):
        res = G.save_load(slug)
        if not res.get("ok"):
            messagebox.showerror("Erro", "Não foi possível carregar o jogo.")
            return
        self.show_hub()

    def show_new_career(self):
        self._clear()
        tk.Label(self.frame, text="Novo Jogo", fg=TXT, bg=BG,
                 font=(F, 18, "bold")).pack(pady=(0, 12))
        box = tk.Frame(self.frame, bg=PANEL, padx=20, pady=18,
                       highlightbackground=LINE, highlightthickness=1)
        box.pack(fill="x")

        tk.Label(box, text="Liga", fg=DIM, bg=PANEL, font=(F, 10, "bold")).pack(anchor="w")
        leagues = [l["name"] for l in with_conn(G.api_leagues)]
        cb_league = ttk.Combobox(box, values=leagues, state="readonly", font=(F, 12))
        cb_league.pack(fill="x", pady=(0, 10))
        if leagues:
            cb_league.current(0)

        tk.Label(box, text="Clube", fg=DIM, bg=PANEL, font=(F, 10, "bold")).pack(anchor="w")
        cb_club = ttk.Combobox(box, state="readonly", font=(F, 12))
        cb_club.pack(fill="x", pady=(0, 10))

        def update_clubs(*_):
            idx = cb_league.current()
            if idx < 0:
                return
            lid = with_conn(G.api_leagues)[idx]["id"]
            self._clubs = with_conn(lambda c: G.api_clubs(c, lid))
            cb_club["values"] = [c["name"] for c in self._clubs]
            if self._clubs:
                cb_club.current(0)
        cb_league.bind("<<ComboboxSelected>>", update_clubs)
        self._clubs = []
        update_clubs()

        tk.Label(box, text="Técnico", fg=DIM, bg=PANEL, font=(F, 10, "bold")).pack(anchor="w")
        ent_name = tk.Entry(box, bg=BG2, fg=TXT, insertbackground=TXT,
                            font=(F, 12), highlightbackground=LINE, highlightthickness=1)
        ent_name.insert(0, "Técnico")
        ent_name.pack(fill="x", pady=(0, 14))

        def start():
            idx = cb_club.current()
            if idx < 0 or idx >= len(self._clubs):
                messagebox.showwarning("Aviso", "Escolha um clube.")
                return
            name = ent_name.get().strip() or "Técnico"
            res = G.create_career(self._clubs[idx]["id"], name)
            if not res.get("ok"):
                messagebox.showerror("Erro", res.get("msg", "Erro ao criar carreira."))
                return
            self.show_hub()

        self._btn(box, "Iniciar Carreira ▶", start).pack(fill="x")
        self._btn(box, "← Voltar", self.show_saves, bg=PANEL2).pack(fill="x")

    # ─── HUB ───
    def show_hub(self):
        self._clear()
        st = with_conn(G.api_state)
        tk.Label(self.frame, text=f"⚽ {st.get('club','?')}", fg=TXT, bg=BG,
                 font=(F, 20, "bold")).pack(anchor="w")
        tk.Label(self.frame, text=f"{st.get('coach','?')} · Temp. {st.get('season','?')} · "
                 f"Prestígio {st.get('prestige','?')}", fg=DIM, bg=BG,
                 font=(F, 12)).pack(anchor="w", pady=(0, 10))

        box = tk.Frame(self.frame, bg=PANEL, padx=16, pady=14,
                       highlightbackground=LINE, highlightthickness=1)
        box.pack(fill="x", pady=(0, 14))
        grid = tk.Frame(box, bg=PANEL)
        grid.pack(fill="x")
        for i, (label, val, color) in enumerate([
            ("Caixa", st.get("cash", "?"), TXT),
            ("Títulos", st.get("titles", "?"), GOLD),
            ("Reputação", f"{st.get('reputation','?')}/100", TXT),
            ("Posição", st.get("position", "?"), GREEN),
        ]):
            tk.Label(grid, text=label, fg=DIM, bg=PANEL, font=(F, 10, "bold")).grid(row=0, column=i, padx=14)
            tk.Label(grid, text=str(val), fg=color, bg=PANEL, font=(F, 15, "bold")).grid(row=1, column=i, padx=14)

        actions = tk.Frame(self.frame, bg=BG)
        actions.pack(fill="x")
        self._btn(actions, "▶ Jogar próxima rodada", self._play_next).pack(fill="x", pady=4)
        self._btn(actions, "👥 Ver elenco", self.show_squad, bg=PANEL2).pack(fill="x", pady=4)
        self._btn(actions, "📂 Trocar jogo", self.show_saves, bg=PANEL2).pack(fill="x", pady=4)
        self._btn(actions, "🌐 Abrir versão web", self._open_web, bg=PANEL2).pack(fill="x", pady=4)

    def _play_next(self):
        res = with_conn(G.api_play)
        lines = []
        if "matches" in res:
            for m in res["matches"]:
                lines.append(f"{m.get('home','?')} {m.get('home_goals','?')} x "
                             f"{m.get('away_goals','?')} {m.get('away','?')}")
        msg = "\n".join(lines) if lines else str(res)
        messagebox.showinfo("Resultado da rodada", msg)
        self.show_hub()

    def _open_web(self):
        import subprocess
        subprocess.Popen([sys.executable, str(ROOT / "launch_web.py")],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # ─── ELENCO ───
    def show_squad(self):
        self._clear()
        squad = with_conn(G.api_squad)
        tk.Label(self.frame, text="Elenco", fg=TXT, bg=BG,
                 font=(F, 18, "bold")).pack(anchor="w", pady=(0, 10))

        cols = ("Pos", "Nome", "Idade", "OVR", "Pot", "Cond")
        tree = ttk.Treeview(self.frame, columns=cols, show="headings",
                            height=14, style="Dark.Treeview")
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=50 if c in ("Pos", "Idade", "OVR", "Pot", "Cond") else 220)
        tree.pack(fill="both", expand=True, pady=(0, 10))

        for p in squad:
            tree.insert("", "end", values=(
                p.get("pos", "?"), p.get("name", "?"), p.get("age", "?"),
                p.get("ovr", "?"), p.get("pot", "?"), p.get("fitness", "?")
            ))

        self._btn(self.frame, "← Voltar", self.show_hub, bg=PANEL2).pack(fill="x")


def main():
    app = CompactApp()
    app.mainloop()


if __name__ == "__main__":
    main()
