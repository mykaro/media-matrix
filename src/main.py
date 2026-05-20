import multiprocessing
import sys

if __name__ == "__main__":
    if sys.platform.startswith("win"):
        multiprocessing.freeze_support()

import logging
import os
from pathlib import Path
import flet as ft
from typing import Final

sys.path.insert(0, str(Path(__file__).parent.resolve()))
from ui.i18n import i18n

# Configuration Constants
WINDOW_WIDTH: Final = 1210
WINDOW_HEIGHT: Final = 810
MIN_WINDOW_WIDTH: Final = 1000
MIN_WINDOW_HEIGHT: Final = 750
APP_VERSION: Final = "1.0.0"
GITHUB_REPO: Final = "mykaro/media-matrix"

from core.logger import setup_logging
from core.updater import check_for_updates

setup_logging()
logger = logging.getLogger(__name__)
logger.info("Application starting up...")

@ft.component
def ContentArea(nav_index: int, page: ft.Page):
    from ui.view_twinfinder import TwinFinderView
    from ui.view_photosorter import PhotoSorterView
    from ui.view_photocleaner import PhotoCleanerView
    # Render all views once and toggle visibility to preserve state
    return ft.Container(
        expand=True,
        bgcolor="#2E2E2E",
        alignment=ft.Alignment.TOP_LEFT,
        content=ft.Stack(
            controls=[
                ft.Container(content=TwinFinderView(page), visible=nav_index == 0, expand=True),
                ft.Container(content=PhotoCleanerView(page), visible=nav_index == 1, expand=True),
                ft.Container(content=PhotoSorterView(page), visible=nav_index == 2, expand=True),
            ],
            expand=True,
        ),
    )

@ft.component
def App(page: ft.Page):
    from ui.sidebar import AppSidebar
    # Subscribe to i18n observable so the component re-renders on language change
    _lang_ver, _set_lang_ver = ft.use_state(0)

    def _subscribe_i18n():
        def _on_change(sender, field):
            _set_lang_ver(lambda v: v + 1)
        return i18n.subscribe(_on_change)

    ft.use_effect(_subscribe_i18n, [])
    nav_index, set_nav_index = ft.use_state(0)
    
    # Creating the sidebar (now a declarative component)
    sidebar = AppSidebar(
        nav_index=nav_index,
        on_nav_change=set_nav_index
    )

    return ft.Row(
        controls=[
            sidebar,
            ft.VerticalDivider(width=1, color="transparent"),
            ContentArea(nav_index=nav_index, page=page)
        ],
        expand=True,
        spacing=0,
    )

@ft.component
def Root(page: ft.Page):
    is_loaded, set_loaded = ft.use_state(False)

    async def load_app():
        # Center window first, while splash is visible
        await page.window.center()

        # Initialize FilePickers.
        # In Flet 1.0 FilePicker is a service — it's added only to page.services (not to overlay).
        picker_twin = ft.FilePicker()
        picker_clean = ft.FilePicker()
        picker_sort_src = ft.FilePicker()
        picker_sort_dst = ft.FilePicker()

        page.services.append(picker_twin)
        page.services.append(picker_clean)
        page.services.append(picker_sort_src)
        page.services.append(picker_sort_dst)
        page.update()

        # Save references for access from components via page
        setattr(page, "_twin_picker", picker_twin)
        setattr(page, "_clean_picker", picker_clean)
        setattr(page, "_sort_src_picker", picker_sort_src)
        setattr(page, "_sort_dst_picker", picker_sort_dst)

        # Pre-import heavy UI modules to cache them
        from ui.sidebar import AppSidebar  # noqa: F401
        from ui.view_twinfinder import TwinFinderView  # noqa: F401
        from ui.view_photosorter import PhotoSorterView  # noqa: F401
        from ui.view_photocleaner import PhotoCleanerView  # noqa: F401

        # Check for updates in the background
        page.run_task(check_for_updates, page, APP_VERSION, GITHUB_REPO)

        set_loaded(True)

    def _on_mount():
        page.run_task(load_app)

    ft.use_effect(_on_mount, [])

    if not is_loaded:
        # Splash screen
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Image(src="logo.png", width=128, height=128),
                    ft.Container(height=20),
                    ft.ProgressRing(width=32, height=32, stroke_width=3, color=ft.Colors.BLUE_400)
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=0
            ),
            alignment=ft.Alignment(0, 0),
            expand=True,
            bgcolor="#2E2E2E"
        )
    return App(page)

def main(page: ft.Page) -> None:
    """
    Main entry point for the MediaMatrix application.
    """
    page.title = "MediaMatrix"
    page.window.width = WINDOW_WIDTH
    page.window.height = WINDOW_HEIGHT
    page.window.min_width = MIN_WINDOW_WIDTH
    page.window.min_height = MIN_WINDOW_HEIGHT

    icon_path = os.path.join(os.path.dirname(__file__), "assets", "logo_256x256.ico")
    page.window.icon = icon_path

    page.fonts = {
        "Montserrat": "fonts/Montserrat.ttf",
        "Inter": "fonts/Inter.ttf",
        "Roboto": "fonts/Roboto.ttf",
        "JetBrains Mono": "fonts/JetBrainsMono.ttf",
    }

    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#2E2E2E"
    page.padding = 0
    page.spacing = 0

    page.theme = ft.Theme(
        color_scheme_seed="#1e3a8a",
        visual_density=ft.VisualDensity.COMFORTABLE,
        font_family="Inter, Segoe UI",
    )

    # Load translations (fast, sync operation)
    lang_dir = os.path.join(os.path.dirname(__file__), "assets", "lang")
    i18n.load(assets_dir=lang_dir)

    # Render immediately — splash appears, then Root.load_app handles the rest
    page.render(Root, page=page)

if __name__ == "__main__":
    assets_path = os.path.join(os.path.dirname(__file__), "assets")
    ft.run(main, assets_dir=assets_path)