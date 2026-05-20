"""
TwinFinder View — Duplicate finder interface matching the HTML prototype.
Migrated to Flet 1.0 declarative style (@ft.component).
"""
import asyncio
import os
from typing import Optional

import flet as ft

from core.worker_twinfinder import TwinFinderWorker
from ui.theme import (
    ACCENT_GREEN, ACCENT_WHITE, FONT_CODE, FONT_MAIN, IDLE_TEXT,
    LIGHT_GRAY, PURPLE_ACCENT, YELLOW_ACCENT, accent_green_dim,
    border_color,
)
from ui.components import (
    Card, CustomToggle, GhostButton, InfoHint, LogSection, OptItem,
    PageHeader, PathSelector, RunButton, StatChip,
    StyledDropdown,
)
from ui.i18n import i18n


def format_time(seconds: float) -> str:
    """Format seconds into localized time remaining string."""
    mins, secs = divmod(int(seconds), 60)
    if mins > 0:
        return f"~{mins} {i18n.t('time.min')} {secs} {i18n.t('time.sec')} {i18n.t('time.remaining')}"
    return f"~{secs} {i18n.t('time.sec')} {i18n.t('time.remaining')}"

SIMILARITY_HINT_KEYS: list[tuple[int, int, str]] = [
    (0, 5, "twin.sim_hint_strict"),
    (6, 15, "twin.sim_hint_optimal"),
    (16, 25, "twin.sim_hint_aggressive"),
    (26, 50, "twin.sim_hint_rough"),
]

class WorkerRef:
    worker: Optional[TwinFinderWorker] = None

@ft.component
def TwinFinderView(page: ft.Page):
    # Subscribe to i18n observable so the component re-renders on language change
    _lang_ver, _set_lang_ver = ft.use_state(0)

    def _subscribe_i18n():
        def _on_change(sender, field):
            _set_lang_ver(lambda v: v + 1)
        return i18n.subscribe(_on_change)

    ft.use_effect(_subscribe_i18n, [])
    folder_path, set_folder_path = ft.use_state("")
    threshold, set_threshold = ft.use_state(15)
    use_look_ahead, set_use_look_ahead = ft.use_state(True)
    look_ahead_val, set_look_ahead_val = ft.use_state("50")
    
    is_running, set_is_running = ft.use_state(False)
    
    stat_files_count, set_stat_files_count = ft.use_state("0")
    stat_duplicates_count, set_stat_duplicates_count = ft.use_state("0")
    
    logs, set_logs = ft.use_state([])
    progress_current, set_progress_current = ft.use_state(0)
    progress_total, set_progress_total = ft.use_state(0)
    eta_text, set_eta_text = ft.use_state("")
    
    worker_ref = ft.use_ref()
    if not worker_ref.current:
        worker_ref.current = WorkerRef()
    assert isinstance(worker_ref.current, WorkerRef)
        
    async def add_log(log_type: str, message: str):
        import datetime
        time_str = datetime.datetime.now().strftime("%H:%M:%S")
        new_log = {"type": log_type, "time": time_str, "message": message}
        # Keep only the last 500 logs
        set_logs(lambda prev: (prev + [new_log])[-500:])

    async def log_msg(msg: str) -> None:
        log_type = "info"
        if "✅" in msg or "📊" in msg:
            log_type = "success"
        elif "⚠️" in msg:
            log_type = "warning"
        elif "❌" in msg or "🛑" in msg:
            log_type = "error"
        await add_log(log_type, msg)

    async def update_progress_cb(current: int, total: int, eta: float, filename: str, status_text: str, duplicates_count: int = 0) -> None:
        set_progress_current(current)
        set_progress_total(total)
        set_eta_text(format_time(eta) if eta > 0 else i18n.t("time.done"))
        set_stat_files_count(f"{total:,}".replace(",", " "))
        set_stat_duplicates_count(f"{duplicates_count:,}".replace(",", " "))
        
    async def on_finished_cb() -> None:
        set_is_running(False)

    async def _on_browse_click():
        picker = getattr(page, "_twin_picker", None)
        if picker:
            path = await picker.get_directory_path()
            if path:
                set_folder_path(path)

    def toggle_analysis():
        if not is_running:
            if not folder_path:
                page.run_task(add_log, "error", i18n.t("common.error_select_folder"))
                return
            
            set_is_running(True)
            set_logs([])
            set_stat_duplicates_count("0")
            set_progress_current(0)
            set_progress_total(0)
            set_eta_text("")
            
            def _prog_cb(current: int, total: int, eta: float, filename: str, status_text: str, duplicates_count: int = 0) -> None:
                page.run_task(update_progress_cb, current, total, eta, filename, status_text, duplicates_count)
            
            def _log_cb(msg: str) -> None:
                page.run_task(log_msg, msg)
                
            def _fin_cb() -> None:
                page.run_task(on_finished_cb)

            worker = TwinFinderWorker(
                source_folder=folder_path,
                threshold=threshold,
                use_look_ahead=use_look_ahead,
                look_ahead_val=int(look_ahead_val),
                progress_callback=_prog_cb,
                log_callback=_log_cb,
                finished_callback=_fin_cb,
            )
            assert worker_ref.current is not None
            worker_ref.current.worker = worker

            async def _run_worker():
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, worker.run)

            page.run_task(_run_worker)
        else:
            page.run_task(log_msg, i18n.t("twin.stop_msg"))
            assert worker_ref.current is not None
            if worker_ref.current.worker:
                worker_ref.current.worker.stop()

    # ── UI Construction ──

    stat_chips: list[ft.Control] = [
        StatChip(value=stat_files_count, label=i18n.t("common.stat_files")),
        StatChip(value=stat_duplicates_count, label=i18n.t("twin.stat_duplicates"), green=True)
    ]

    header = PageHeader(
        title_white=i18n.t("twin.title_white"),
        title_green=i18n.t("twin.title_green"),
        description=i18n.t("twin.description"),
        stat_chips=stat_chips,
    )

    card_directory = Card(
        icon=ft.Icon(ft.Icons.FOLDER_OUTLINED, size=14, color=ACCENT_GREEN),
        title=i18n.t("twin.dir_title"),
        badge_text=f"{i18n.t('common.step')} 1",
        children=[
            PathSelector(
                value=folder_path,
                hint_text=i18n.t("twin.path_hint"),
                on_browse=lambda _: page.run_task(_on_browse_click),
                has_error=not folder_path and is_running
            ),
            InfoHint(text=i18n.t("twin.dir_hint").format(prefix=i18n.t("folders.duplicates_prefix")))
        ],
    )

    sim_hint_text = ""
    for lo, hi, key in SIMILARITY_HINT_KEYS:
        if lo <= threshold <= hi:
            sim_hint_text = i18n.t(key)
            break

    card_similarity = Card(
        icon=ft.Icon(ft.Icons.BAR_CHART, size=14, color=PURPLE_ACCENT),
        title=i18n.t("twin.sim_title"),
        badge_text=f"{i18n.t('common.step')} 2",
        children=[
            ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(i18n.t("twin.slider_left"), size=12, color="#666666", font_family=FONT_MAIN),
                            ft.Text(i18n.t("twin.slider_right"), size=12, color="#666666", font_family=FONT_MAIN),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Row(
                        controls=[
                            ft.Slider(
                                min=0, max=50, divisions=50, value=threshold,
                                active_color=ACCENT_GREEN,
                                inactive_color=ft.Colors.with_opacity(0.1, ACCENT_WHITE),
                                thumb_color=ACCENT_WHITE,
                                on_change=lambda e: set_threshold(int(e.control.value or 0)),
                                expand=True,
                                disabled=is_running,
                            ),
                            ft.Container(
                                content=ft.Text(str(threshold), font_family=FONT_CODE, size=12, color=ACCENT_GREEN),
                                bgcolor=accent_green_dim(),
                                border=ft.Border.all(1, ft.Colors.with_opacity(0.2, ACCENT_GREEN)),
                                border_radius=6,
                                padding=ft.Padding.symmetric(vertical=1, horizontal=6),
                                width=36,
                                alignment=ft.Alignment.CENTER,
                            )
                        ],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    )
                ],
                spacing=0,
            ),
            InfoHint(text=sim_hint_text)
        ],
    )

    card_params = Card(
        icon=ft.Icon(ft.Icons.RADAR, size=14, color=YELLOW_ACCENT),
        title=i18n.t("twin.params_title"),
        badge_text=f"{i18n.t('common.step')} 3",
        children=[
            ft.Row(
                controls=[
                    ft.Container(
                        content=OptItem(
                            title=i18n.t("twin.opt_fast_title"),
                            description=i18n.t("twin.opt_fast_desc"),
                            control=CustomToggle(
                                value=use_look_ahead,
                                on_change=lambda val: set_use_look_ahead(val) if not is_running else None
                            )
                        ),
                        expand=True,
                    ),
                    ft.Container(
                        content=OptItem(
                            title=i18n.t("twin.opt_window_title"),
                            description=i18n.t("twin.opt_window_desc"),
                            control=StyledDropdown(
                                options=[
                                    ft.dropdown.Option("25"),
                                    ft.dropdown.Option("50"),
                                    ft.dropdown.Option("75"),
                                ],
                                value=look_ahead_val,
                                on_change=lambda e: set_look_ahead_val(e.control.value),
                                width=80,
                                disabled=not use_look_ahead or is_running,
                            )
                        ),
                        expand=True,
                    ),
                ],
                spacing=10,
            ),
            ft.Container(
                content=InfoHint(
                    text=i18n.t("twin.opt_hint_fast") if use_look_ahead else i18n.t("twin.opt_hint_deep"),
                    border_left_color=ACCENT_GREEN if use_look_ahead else PURPLE_ACCENT,
                ),
                height=48,
            )
        ],
    )

    launch_area = ft.Row(
        controls=[
            RunButton(
                text=i18n.t("common.stop") if is_running else i18n.t("twin.btn_run"),
                on_click=toggle_analysis,
                icon_name=ft.Icons.PAUSE if is_running else ft.Icons.PLAY_ARROW,
                disabled=False, # It handles stop internally
            ),
            ft.Text(
                spans=[
                    ft.TextSpan(i18n.t("twin.launch_safe"), ft.TextStyle(color=IDLE_TEXT, size=12)),
                    ft.TextSpan(i18n.t("twin.launch_hint"), ft.TextStyle(color=IDLE_TEXT, size=12)),
                    ft.TextSpan(f"{i18n.t('folders.duplicates_prefix')}<folder>", ft.TextStyle(color=LIGHT_GRAY, size=12, weight=ft.FontWeight.W_500)),
                    ft.TextSpan(i18n.t("twin.launch_hint_end"), ft.TextStyle(color=IDLE_TEXT, size=12)),
                ],
                font_family=FONT_MAIN,
            )
        ],
        spacing=14,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.ListView(
                    controls=[
                        header,
                        card_directory,
                        card_similarity,
                        card_params,
                        launch_area,
                    ],
                    expand=True,
                    spacing=14,
                    padding=ft.Padding.only(top=24, bottom=14, left=32, right=32),
                ),
                ft.Container(
                    content=LogSection(
                        is_running=is_running,
                        logs=logs,
                        progress_current=progress_current,
                        progress_total=progress_total,
                        eta_text=eta_text,
                    ),
                    padding=ft.Padding.only(bottom=0, left=32, right=32)
                )
            ],
            expand=True,
            spacing=0,
        ),
        expand=True,
    )
