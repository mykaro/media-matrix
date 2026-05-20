"""
Design System for MediaMatrix — centralized colors, fonts, and style constants.
Matches the HTML prototypes' CSS :root variables.
"""
from typing import Final

import flet as ft

# ═══════════════════════════════════════
#  COLORS
# ═══════════════════════════════════════

BG_COLOR: Final = "#2E2E2E"
SIDEBAR_BG: Final = "#232323"

# Surfaces
SURFACE_OPACITY: Final = 0.04
SURFACE_HOVER_OPACITY: Final = 0.07

# Primary (Deep Blue)
PRIMARY: Final = "#1E3A8A"
PRIMARY_HOVER: Final = "#2B4EAC"
PRIMARY_GLOW_OPACITY: Final = 0.35

# Accent 1 — White
ACCENT_WHITE: Final = "#FFFFFF"

# Accent 2 — Neon Green
ACCENT_GREEN: Final = "#00C896"
ACCENT_GREEN_DIM_OPACITY: Final = 0.12
ACCENT_GREEN_GLOW_OPACITY: Final = 0.3

# Text
LIGHT_GRAY: Final = "#F5F5F5"
IDLE_TEXT: Final = "#8a8a8a"

# Borders
BORDER_OPACITY: Final = 0.08
BORDER_BRIGHT_OPACITY: Final = 0.14

# Status
DANGER: Final = "#ff4757"
WARNING: Final = "#ffa502"

# Misc
PURPLE_ACCENT: Final = "#a78bfa"
YELLOW_ACCENT: Final = "#fbbf24"

# ═══════════════════════════════════════
#  FONTS
# ═══════════════════════════════════════

FONT_LOGO: Final = "Montserrat"
FONT_MAIN: Final = "Inter"
FONT_BTN: Final = "Roboto"
FONT_CODE: Final = "JetBrains Mono"

# ═══════════════════════════════════════
#  SIZING
# ═══════════════════════════════════════

SIDEBAR_WIDTH: Final = 250
CONTENT_PADDING_TOP: Final = 24
CONTENT_PADDING_BOTTOM: Final = 24
CONTENT_PADDING_LEFT: Final = 32
CONTENT_PADDING_RIGHT: Final = 32
CONTENT_GAP: Final = 14

CARD_BORDER_RADIUS: Final = 12
CARD_PADDING_V: Final = 14
CARD_PADDING_H: Final = 18

# ═══════════════════════════════════════
#  HELPER FUNCTIONS
# ═══════════════════════════════════════

def surface_color() -> str:
    """Card/panel background: rgba(255,255,255,0.04)."""
    return ft.Colors.with_opacity(SURFACE_OPACITY, ACCENT_WHITE)


def surface_hover_color() -> str:
    """Hover background: rgba(255,255,255,0.07)."""
    return ft.Colors.with_opacity(SURFACE_HOVER_OPACITY, ACCENT_WHITE)


def border_color() -> str:
    """Default border: rgba(255,255,255,0.08)."""
    return ft.Colors.with_opacity(BORDER_OPACITY, ACCENT_WHITE)


def border_bright_color() -> str:
    """Hover border: rgba(255,255,255,0.14)."""
    return ft.Colors.with_opacity(BORDER_BRIGHT_OPACITY, ACCENT_WHITE)


def accent_green_dim() -> str:
    """Dim green for toggle/badge backgrounds: rgba(0,200,150,0.12)."""
    return ft.Colors.with_opacity(ACCENT_GREEN_DIM_OPACITY, ACCENT_GREEN)


def accent_green_glow() -> str:
    """Green glow/shadow: rgba(0,200,150,0.3)."""
    return ft.Colors.with_opacity(ACCENT_GREEN_GLOW_OPACITY, ACCENT_GREEN)


def primary_glow() -> str:
    """Primary blue glow: rgba(30,58,138,0.35)."""
    return ft.Colors.with_opacity(PRIMARY_GLOW_OPACITY, PRIMARY)
