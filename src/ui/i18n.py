"""
Internationalization module for MediaMatrix.

Auto-detects OS language at startup:
  - Ukrainian / Russian → 'uk'
  - Everything else     → 'en'

Usage:
    from ui.i18n import i18n
    label = i18n.t("sidebar.twin_finder")   # returns localized string and auto-updates
"""
import locale
import os
from dataclasses import dataclass, field
from typing import Callable
import yaml
import flet as ft


def _detect_system_lang() -> str:
    """Detect OS language. Returns 'uk' for Ukrainian/Russian, 'en' otherwise."""
    try:
        lang_code, _ = locale.getdefaultlocale()
        if lang_code and lang_code[:2] in ("uk", "ru"):
            return "uk"
    except Exception:
        pass
    return "en"


@dataclass
class I18nState(ft.Observable):
    lang: str = "uk"
    _data: dict = field(default_factory=dict, repr=False)
    _assets_dir: str = field(default="src/assets/lang", repr=False)
    _strong_listeners: list = field(default_factory=list, repr=False)

    def subscribe(self, fn: Callable) -> Callable[[], None]:
        """Override subscribe to keep a strong reference to the listener."""
        if fn not in self._strong_listeners:
            self._strong_listeners.append(fn)
        dispose = super().subscribe(fn)
        
        def robust_dispose():
            if fn in self._strong_listeners:
                self._strong_listeners.remove(fn)
            dispose()
            
        return robust_dispose

    def load(self, assets_dir: str = "") -> None:
        """Load YAML translations for the current language."""
        if assets_dir:
            self._assets_dir = assets_dir
        path = os.path.join(self._assets_dir, f"{self.lang}.yaml")
        if not os.path.exists(path):
            path = os.path.join(self._assets_dir, "en.yaml")  # fallback
            
        try:
            with open(path, "r", encoding="utf-8") as f:
                self._data = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Error loading translation from {path}: {e}")
            self._data = {}
        self.notify()

    def set_lang(self, lang: str) -> None:
        """Set current language and auto-update listeners."""
        if lang in ("uk", "en") and lang != self.lang:
            self.lang = lang
            self.load()

    def t(self, key: str) -> str:
        """Return translated string for *key* in the current language."""
        keys = key.split(".")
        val = self._data
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
            else:
                return key
        return str(val) if val is not None else key

    def get_months(self) -> dict[int, str]:
        """Return month-name dict for the current language."""
        months = self._data.get("months", {})
        return {int(k): str(v) for k, v in months.items()}


# Global singleton
i18n = I18nState(lang=_detect_system_lang())
