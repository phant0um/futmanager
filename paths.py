"""
FUTMANAGER — Path Resolver
Resolve caminhos tanto em dev quanto dentro do bundle PyInstaller.
"""
from __future__ import annotations
import sys
import os
from pathlib import Path


def _is_frozen() -> bool:
    """True se rodando dentro de bundle PyInstaller."""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def resource_dir() -> Path:
    """
    Diretório de recursos read-only empacotados (DB inicial, etc).
    - dev: raiz do projeto
    - bundle: sys._MEIPASS (pasta temporária do PyInstaller)
    """
    if _is_frozen():
        return Path(sys._MEIPASS)
    return Path(__file__).parent


def user_data_dir() -> Path:
    """
    Diretório gravável para a DB do usuário (saves, progresso).
    - dev: ./data
    - bundle: ~/Library/Application Support/FutManager
    """
    if _is_frozen():
        d = Path.home() / "Library" / "Application Support" / "FutManager"
        d.mkdir(parents=True, exist_ok=True)
        return d
    return Path(__file__).parent / "data"


def template_db() -> Path:
    """
    Mundo pristino (clubes/jogadores) — base para criar novos saves.
    Nunca é jogado diretamente; saves são cópias dele.
    No bundle: copia o template empacotado para área gravável na 1ª execução.
    """
    if _is_frozen():
        target = user_data_dir() / "futmanager.db"
        if not target.exists():
            import shutil
            bundled = resource_dir() / "data" / "futmanager.db"
            if bundled.exists():
                shutil.copy2(bundled, target)
        return target
    return Path(__file__).parent / "data" / "futmanager.db"


def saves_dir() -> Path:
    """Diretório dos saves (1 arquivo .db por jogo salvo)."""
    d = user_data_dir() / "saves"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _active_marker() -> Path:
    return saves_dir() / ".active"


def active_save_name() -> str | None:
    m = _active_marker()
    if m.exists():
        name = m.read_text().strip()
        if name and (saves_dir() / f"{name}.db").exists():
            return name
    return None


def set_active_save(name: str | None):
    if name is None:
        if _active_marker().exists():
            _active_marker().unlink()
    else:
        _active_marker().write_text(name)


def db_path() -> Path:
    """
    DB em uso: o save ativo, se houver; senão o template (somente leitura efetiva
    — o jogo cria um save antes de jogar).
    """
    name = active_save_name()
    if name:
        return saves_dir() / f"{name}.db"
    return template_db()


def is_frozen() -> bool:
    return _is_frozen()
