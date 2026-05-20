"""
PhotoSorter View — File sorting interface matching the sorter.html prototype.
Migrated to Flet 1.0 declarative style (@ft.component).
"""
import asyncio
from pathlib import Path
from typing import Optional, Final

import flet as ft

from core.worker_photosorter import PhotoSorterWorker, PHOTO_EXT, VIDEO_EXT
from ui.theme import (
    ACCENT_GREEN, ACCENT_WHITE, FONT_BTN, FONT_CODE, FONT_MAIN,
    IDLE_TEXT, LIGHT_GRAY, YELLOW_ACCENT, DANGER, WARNING,
    accent_green_dim, border_color,
)
from ui.components import (
    Card, CustomRadioGroup, CustomToggle, FilterRow, InfoHint,
    LogSection, PageHeader, PathSelector,
    ResultBox, RunButton, StatChip,
)
from ui.i18n import i18n


def _format_time(seconds: float) -> str:
    if seconds <= 0:
        return ""
    if seconds < 60:
        return f"~{int(seconds)} {i18n.t('time.sec')} {i18n.t('time.remaining')}"
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"~{mins} {i18n.t('time.min')} {secs} {i18n.t('time.sec')} {i18n.t('time.remaining')}"


class SorterWorkerRef:
    worker: Optional[PhotoSorterWorker] = None


@ft.component
def PhotoSorterView(page: ft.Page):
    # Subscribe to i18n observable so the component re-renders on language change
    _lang_ver, _set_lang_ver = ft.use_state(0)

    def _subscribe_i18n():
        def _on_change(sender, field):
            _set_lang_ver(lambda v: v + 1)
        return i18n.subscribe(_on_change)

    ft.use_effect(_subscribe_i18n, [])
    src_path, set_src_path = ft.use_state("")
    dst_path, set_dst_path = ft.use_state("")
    
    struct_val, set_struct_val = ft.use_state("nested")
    
    filter_screens, set_filter_screens = ft.use_state(True)
    filter_fallback, set_filter_fallback = ft.use_state(False)
    filter_rename, set_filter_rename = ft.use_state(False)
    
    is_running, set_is_running = ft.use_state(False)
    running_mode, set_running_mode = ft.use_state(None) # "analysis" | "sort" | None
    
    analysis_results, set_analysis_results = ft.use_state(None)
    
    stat_files_count, set_stat_files_count = ft.use_state("0")
    stat_sorted_count, set_stat_sorted_count = ft.use_state("0")
    
    # Dash
    dash_counters, set_dash_counters = ft.use_state({
        'screen': 0, 'exif': 0, 'name': 0, 'os_date': 0, 'none': 0
    })
    
    logs, set_logs = ft.use_state([])
    progress_current, set_progress_current = ft.use_state(0)
    progress_total, set_progress_total = ft.use_state(0)
    eta_text, set_eta_text = ft.use_state("")
    
    # Rename Dialog State
    rename_dialog_open, set_rename_dialog_open = ft.use_state(False)
    rename_timer, set_rename_timer = ft.use_state(3)
    
    worker_ref = ft.use_ref()
    if not worker_ref.current:
        worker_ref.current = SorterWorkerRef()
    assert isinstance(worker_ref.current, SorterWorkerRef)
        
    async def add_log(log_type: str, message: str):
        import datetime
        time_str = datetime.datetime.now().strftime("%H:%M:%S")
        new_log = {"type": log_type, "time": time_str, "message": message}
        set_logs(lambda prev: (prev + [new_log])[-500:])

    async def log_msg(msg: str, color: str = "#888888") -> None:
        log_type = "info"
        if color == "#ef4444" or "❌" in msg or "🛑" in msg:
            log_type = "error"
        elif color == "#3ecf8e" or "✅" in msg:
            log_type = "success"
        elif color == "#f59e0b" or "⚠️" in msg:
            log_type = "warning"
        await add_log(log_type, msg)

    async def on_progress_cb(current: int, total: int, eta: float = 0.0) -> None:
        set_progress_current(current)
        set_progress_total(total)
        set_eta_text(_format_time(eta) if eta > 0 else i18n.t("time.done"))
        set_stat_files_count(f"{total:,}".replace(",", " "))

    async def on_analysis_done_cb(results: list, elapsed: float) -> None:
        set_analysis_results(results)  # type: ignore
        set_is_running(False)
        set_running_mode(None)  # type: ignore

        counters = {'screen': 0, 'exif': 0, 'name': 0, 'os_date': 0, 'none': 0}
        
        for filepath, _, method, is_screenshot in results:
            key = 'none'
            if filter_screens and is_screenshot:
                key = 'screen'
            elif method in counters:
                key = method
            counters[key] += 1

        set_dash_counters(counters)
        await add_log("success", i18n.t("sort.analysis_done").format(time=f"{elapsed:.1f}", count=f"{len(results):,}"))

    async def on_sort_done_cb(moved: int, undated: int, errors: list, elapsed: float) -> None:
        set_is_running(False)
        set_running_mode(None)  # type: ignore
        set_stat_sorted_count(f"{moved:,}".replace(",", " "))
        await add_log("success", i18n.t("sort.sort_done").format(time=f"{elapsed:.1f}", moved=f"{moved:,}", undated=f"{undated:,}", name=i18n.t("folders.undated")))

        if errors:
            await add_log("error", i18n.t("sort.sort_errors").format(count=len(errors)))
            for src, err in errors[:10]:
                await add_log("error", f"  {Path(src).name} — {err}")

    async def _on_browse_click(is_src: bool):
        picker = getattr(page, "_sort_src_picker" if is_src else "_sort_dst_picker", None)
        if picker:
            path = await picker.get_directory_path()
            if path:
                if is_src: set_src_path(path)
                else: set_dst_path(path)

    # Analysis Action
    def toggle_analysis():
        if not is_running:
            if not src_path:
                page.run_task(add_log, "error", i18n.t("sort.error_src"))
                return
            
            set_is_running(True)
            set_running_mode("analysis")  # type: ignore
            set_analysis_results(None)  # type: ignore
            set_dash_counters({'screen': 0, 'exif': 0, 'name': 0, 'os_date': 0, 'none': 0})
            
            set_logs([])
            set_progress_current(0)
            set_progress_total(0)
            set_eta_text("")
            
            def _prog_cb(current: int, total: int, eta: float = 0.0) -> None:
                page.run_task(on_progress_cb, current, total, eta)
                
            def _log_cb(msg: str, color: str = "#888888") -> None:
                page.run_task(log_msg, msg, color)
                
            def _analysis_fin_cb(results: list, elapsed: float) -> None:
                page.run_task(on_analysis_done_cb, results, elapsed)
                
            def _sort_fin_cb(moved: int, undated: int, errors: list, elapsed: float) -> None:
                page.run_task(on_sort_done_cb, moved, undated, errors, elapsed)

            worker = PhotoSorterWorker(
                progress_callback=_prog_cb,
                log_callback=_log_cb,
                analysis_finished_callback=_analysis_fin_cb,
                sort_finished_callback=_sort_fin_cb,
            )
            assert worker_ref.current is not None
            worker_ref.current.worker = worker

            async def _run_analyze():
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, worker.analyze, src_path, PHOTO_EXT | VIDEO_EXT, filter_fallback)

            page.run_task(_run_analyze)
        elif running_mode == "analysis":
            page.run_task(log_msg, i18n.t("sort.stop_signal"))
            assert worker_ref.current is not None
            if worker_ref.current.worker:
                worker_ref.current.worker.stop()
            set_is_running(False)
            set_running_mode(None)  # type: ignore

    # Sort Action
    def toggle_sort():
        if not is_running:
            if not dst_path:
                page.run_task(add_log, "error", i18n.t("sort.error_dst"))
                return
            if not analysis_results:
                page.run_task(add_log, "error", i18n.t("sort.error_analyse_first"))
                return
                
            set_is_running(True)
            set_running_mode("sort")  # type: ignore
            
            def _prog_cb(current: int, total: int, eta: float = 0.0) -> None:
                page.run_task(on_progress_cb, current, total, eta)
                
            def _log_cb(msg: str, color: str = "#888888") -> None:
                page.run_task(log_msg, msg, color)
                
            def _analysis_fin_cb(results: list, elapsed: float) -> None:
                page.run_task(on_analysis_done_cb, results, elapsed)
                
            def _sort_fin_cb(moved: int, undated: int, errors: list, elapsed: float) -> None:
                page.run_task(on_sort_done_cb, moved, undated, errors, elapsed)

            worker = PhotoSorterWorker(
                progress_callback=_prog_cb,
                log_callback=_log_cb,
                analysis_finished_callback=_analysis_fin_cb,
                sort_finished_callback=_sort_fin_cb,
            )
            assert worker_ref.current is not None
            worker_ref.current.worker = worker

            async def _run_sort():
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None, worker.sort,
                    analysis_results, struct_val, dst_path, filter_rename, filter_screens,
                )

            page.run_task(_run_sort)
        elif running_mode == "sort":
            page.run_task(log_msg, i18n.t("sort.stop_signal"))
            assert worker_ref.current is not None
            if worker_ref.current.worker:
                worker_ref.current.worker.stop()
            set_is_running(False)
            set_running_mode(None)  # type: ignore

    # Rename Dialog Logic
    async def handle_rename_toggle(val: bool):
        if val:
            set_rename_dialog_open(True)
            for i in range(3, 0, -1):
                set_rename_timer(i)
                await asyncio.sleep(1)
            set_rename_timer(0)
        else:
            set_filter_rename(False)

    def cancel_rename():
        set_rename_dialog_open(False)
        set_filter_rename(False)

    def _on_rename_toggle(val: bool) -> None:
        page.run_task(handle_rename_toggle, val)

    def confirm_rename():
        set_rename_dialog_open(False)
        set_filter_rename(True)

    rename_dialog = ft.AlertDialog(
        open=rename_dialog_open,
        title=ft.Row([ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=WARNING), ft.Text(i18n.t("sort.dialog_title"), size=16, weight=ft.FontWeight.W_600)]),
        content=ft.Text(i18n.t("sort.dialog_content"), size=13),
        actions=[
            ft.TextButton(content=ft.Text(i18n.t("sort.dialog_cancel")), on_click=lambda _: cancel_rename()),
            ft.ElevatedButton(
                content=ft.Text(i18n.t("sort.dialog_confirm_timer").replace("{n}", str(rename_timer)) if rename_timer > 0 else i18n.t("sort.dialog_confirm")),
                color=ACCENT_WHITE,
                bgcolor=DANGER,
                disabled=rename_timer > 0,
                on_click=lambda _: confirm_rename(),
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
            )
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        on_dismiss=lambda _: cancel_rename(),
        shape=ft.RoundedRectangleBorder(radius=8),
    )

    # ── UI Construction ──

    stat_chips: list[ft.Control] = [
        StatChip(value=stat_files_count, label=i18n.t("common.stat_files")),
        StatChip(value=stat_sorted_count, label=i18n.t("sort.stat_sorted"), green=True, width=130)
    ]

    header = PageHeader(
        title_white=i18n.t("sort.title_white"),
        title_green=i18n.t("sort.title_green"),
        description=i18n.t("sort.description"),
        stat_chips=stat_chips,
    )

    card_directory = Card(
        icon=ft.Icon(ft.Icons.FOLDER_OUTLINED, size=14, color=ACCENT_GREEN),
        title=i18n.t("sort.dir_title"),
        badge_text=f"{i18n.t('common.step')} 1",
        children=[
            ft.Row(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Text(i18n.t("sort.src_label"), size=11, weight=ft.FontWeight.W_500, color=ACCENT_WHITE, font_family=FONT_MAIN),
                            PathSelector(
                                value=src_path,
                                hint_text=i18n.t("sort.src_hint"),
                                on_browse=lambda _: page.run_task(_on_browse_click, True),
                                has_error=not src_path and is_running and running_mode == "analysis"
                            )
                        ],
                        spacing=6,
                        expand=True,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(i18n.t("sort.dst_label"), size=11, weight=ft.FontWeight.W_500, color=ACCENT_GREEN, font_family=FONT_MAIN),
                            PathSelector(
                                value=dst_path,
                                hint_text=i18n.t("sort.dst_hint"),
                                on_browse=lambda _: page.run_task(_on_browse_click, False),
                                has_error=not dst_path and is_running and running_mode == "sort"
                            )
                        ],
                        spacing=6,
                        expand=True,
                    )
                ],
                spacing=16,
            ),
            InfoHint(text=i18n.t("sort.dir_hint"))
        ],
    )

    # Settings Cards
    card_structure = Card(
        icon=ft.Icon(ft.Icons.LIST_OUTLINED, size=14, color=ACCENT_GREEN),
        title=i18n.t("sort.structure_title"),
        badge_text=f"{i18n.t('common.step')} 2",
        children=[
            CustomRadioGroup(
                options=[
                    (i18n.t("sort.radio_nested"), "nested"),
                    (i18n.t("sort.radio_flat"), "flat"),
                ],
                value=struct_val,
                on_change=set_struct_val,
                height=44,
            )
        ],
    )

    card_options = Card(
        icon=ft.Icon(ft.Icons.SETTINGS_OUTLINED, size=14, color=YELLOW_ACCENT),
        title=i18n.t("sort.options_title"),
        children=[
            ft.Column(
                controls=[
                    FilterRow(
                        title=i18n.t("sort.opt_screenshots"),
                        toggle_value=filter_screens,
                        on_toggle=set_filter_screens,
                        tooltip_text=i18n.t("sort.opt_screenshots_tip"),
                        height=44,
                    ),
                    FilterRow(
                        title=i18n.t("sort.opt_fallback"),
                        toggle_value=filter_fallback,
                        on_toggle=set_filter_fallback,
                        tooltip_text=i18n.t("sort.opt_fallback_tip"),
                        height=44,
                    ),
                    FilterRow(
                        title=i18n.t("sort.opt_rename"),
                        toggle_value=filter_rename,
                        on_toggle=_on_rename_toggle,
                        tooltip_text=i18n.t("sort.opt_rename_tip"),
                        height=44,
                    ),
                ],
                spacing=8,
            )
        ],
    )

    settings_grid = ft.Row(
        controls=[
            ft.Container(content=card_structure, expand=True),
            ft.Container(content=card_options, expand=True),
        ],
        spacing=14,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )

    # Dashboard
    dashboard = ft.Column(
        controls=[
            ft.Text(i18n.t("sort.dashboard_header"), size=10, weight=ft.FontWeight.W_500, color=IDLE_TEXT, font_family=FONT_BTN),
            ft.Row(
                controls=[
                    ResultBox(i18n.t("sort.box_exif_title"), i18n.t("sort.box_exif_sub"), value=f"{dash_counters['exif']:,}".replace(",", " "), active=dash_counters['exif'] > 0),
                    ResultBox(i18n.t("sort.box_name_title"), i18n.t("sort.box_name_sub"), value=f"{dash_counters['name']:,}".replace(",", " "), active=dash_counters['name'] > 0),
                    ResultBox(i18n.t("sort.box_os_title"), i18n.t("sort.box_os_sub"), value=f"{dash_counters['os_date']:,}".replace(",", " "), active=dash_counters['os_date'] > 0),
                    ResultBox(i18n.t("sort.box_screen_title"), i18n.t("sort.box_screen_sub").format(name=i18n.t("folders.screenshots")), value=f"{dash_counters['screen']:,}".replace(",", " "), active=dash_counters['screen'] > 0),
                    ResultBox(i18n.t("sort.box_none_title"), i18n.t("sort.box_none_sub").format(name=i18n.t("folders.undated")), value=f"{dash_counters['none']:,}".replace(",", " "), active=dash_counters['none'] > 0),
                ],
                spacing=10,
            )
        ],
        spacing=8,
    )

    # Actions
    action_row = ft.Row(
        controls=[
            RunButton(
                text=i18n.t("common.stop") if is_running and running_mode == "analysis" else i18n.t("sort.btn_analyse"),
                on_click=toggle_analysis,
                icon_name=ft.Icons.PAUSE if is_running and running_mode == "analysis" else ft.Icons.SEARCH,
                disabled=is_running and running_mode == "sort",
            ),
            RunButton(
                text=i18n.t("common.stop") if is_running and running_mode == "sort" else i18n.t("sort.btn_sort"),
                on_click=toggle_sort,
                icon_name=ft.Icons.PAUSE if is_running and running_mode == "sort" else ft.Icons.DOWNLOAD,
                disabled=not analysis_results or (is_running and running_mode == "analysis"),
            ),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=14,
    )

    return ft.Container(
        content=ft.Stack(
            controls=[
                ft.Column(
                    controls=[
                        ft.ListView(
                            controls=[
                                header,
                                card_directory,
                                settings_grid,
                                dashboard,
                                action_row,
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
                rename_dialog
            ],
            expand=True,
        ),
        expand=True,
    )
