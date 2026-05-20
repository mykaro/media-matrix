"""
PhotoCleaner View — Media cleaning interface matching the cleaner.html prototype.
Migrated to Flet 1.0 declarative style (@ft.component).
"""
import asyncio
import os
from typing import Any, Optional

import flet as ft

from core.worker_photocleaner import PhotoCleanerWorker
from ui.theme import (
    ACCENT_GREEN, ACCENT_WHITE, FONT_CODE, FONT_MAIN, IDLE_TEXT,
    LIGHT_GRAY, PURPLE_ACCENT, YELLOW_ACCENT,
    accent_green_dim, border_color,
)
from ui.components import (
    Card, FilterRow, InfoHint, LogSection, NumInput,
    PageHeader, PathSelector, RunButton, StatChip,
    StyledDropdown,
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

class CleanerWorkerRef:
    worker: Optional[PhotoCleanerWorker] = None

@ft.component
def PhotoCleanerView(page: ft.Page):
    # Subscribe to i18n observable so the component re-renders on language change
    _lang_ver, _set_lang_ver = ft.use_state(0)

    def _subscribe_i18n():
        def _on_change(sender, field):
            _set_lang_ver(lambda v: v + 1)
        return i18n.subscribe(_on_change)

    ft.use_effect(_subscribe_i18n, [])
    folder_path, set_folder_path = ft.use_state("")
    
    # Blur
    blur_enabled, set_blur_enabled = ft.use_state(True)
    blur_val, set_blur_val = ft.use_state("100")
    
    # Exposure
    exp_enabled, set_exp_enabled = ft.use_state(True)
    exp_dark_val, set_exp_dark_val = ft.use_state("30")
    exp_bright_val, set_exp_bright_val = ft.use_state("235")
    
    # Photo Resolution
    res_enabled, set_res_enabled = ft.use_state(True)
    res_val, set_res_val = ft.use_state("800x600")
    
    # Corrupted (Photo & Video)
    corr_enabled, set_corr_enabled = ft.use_state(True)
    
    # Duration (Video)
    dur_enabled, set_dur_enabled = ft.use_state(True)
    dur_val, set_dur_val = ft.use_state("3")
    
    # Video Resolution
    vres_enabled, set_vres_enabled = ft.use_state(True)
    vres_val, set_vres_val = ft.use_state("480")
    
    # Dark Video
    vdark_enabled, set_vdark_enabled = ft.use_state(False)
    
    # No sound Video
    vsound_enabled, set_vsound_enabled = ft.use_state(False)
    
    # Execution State
    is_running, set_is_running = ft.use_state(False)
    
    stat_files_count, set_stat_files_count = ft.use_state("0")
    stat_bad_count, set_stat_bad_count = ft.use_state("0")
    
    logs, set_logs = ft.use_state([])
    progress_current, set_progress_current = ft.use_state(0)
    progress_total, set_progress_total = ft.use_state(0)
    eta_text, set_eta_text = ft.use_state("")
    
    worker_ref = ft.use_ref()
    if not worker_ref.current:
        worker_ref.current = CleanerWorkerRef()
    assert isinstance(worker_ref.current, CleanerWorkerRef)

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

    async def on_progress_cb(current: int, total: int, eta: float, bad_count: int = 0) -> None:
        set_progress_current(current)
        set_progress_total(total)
        set_eta_text(_format_time(eta) if eta > 0 else i18n.t("time.done"))
        set_stat_files_count(f"{total:,}".replace(",", " "))
        
        set_stat_bad_count(f"{bad_count:,}".replace(",", " "))

    async def on_finished_cb() -> None:
        set_is_running(False)

    async def _on_browse_click():
        picker = getattr(page, "_clean_picker", None)
        if picker:
            path = await picker.get_directory_path()
            if path:
                set_folder_path(path)

    def toggle_clean():
        if not is_running:
            if not folder_path:
                page.run_task(add_log, "error", i18n.t("common.error_select_folder"))
                return
            
            set_is_running(True)
            set_logs([])
            set_stat_bad_count("0")
            set_progress_current(0)
            set_progress_total(0)
            set_eta_text("")
            
            # Prepare parameters in flat format for the worker
            worker_params = {
                "check_blur": blur_enabled,
                "blur_threshold": int(blur_val),
                "check_exposure": exp_enabled,
                "dark_threshold": int(exp_dark_val),
                "bright_threshold": int(exp_bright_val),
                "check_res": res_enabled,
                "img_w": int(res_val.split("x")[0]),
                "img_h": int(res_val.split("x")[1]),
                "check_corrupted": corr_enabled,
                "vid_min_duration": int(dur_val) if dur_enabled else 0,
                "vid_resolution_h": int(vres_val) if vres_enabled else 0,
                "vid_check_dark": vdark_enabled,
                "vid_check_sound": vsound_enabled,
            }

            # Determine the trash folder path
            source_name = os.path.basename(os.path.normpath(folder_path))
            parent_dir = os.path.dirname(os.path.normpath(folder_path))
            trash_base = os.path.join(parent_dir, f"{i18n.t('folders.clean_prefix')}{source_name}")

            def _prog_cb(current: int, total: int, eta: float, bad_count: int = 0) -> None:
                page.run_task(on_progress_cb, current, total, eta, bad_count)
                
            def _log_cb(msg: str, color: str = "#888888") -> None:
                page.run_task(log_msg, msg, color)
                
            def _fin_cb(*args: Any) -> None:
                page.run_task(on_finished_cb)

            worker = PhotoCleanerWorker(
                progress_callback=_prog_cb,
                log_callback=_log_cb,
                finished_callback=_fin_cb,
            )
            assert worker_ref.current is not None
            worker_ref.current.worker = worker

            async def _run_worker():
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, worker.clean, folder_path, trash_base, worker_params)

            page.run_task(_run_worker)
        else:
            page.run_task(log_msg, i18n.t("clean.stop_msg"), "#ef4444")
            assert worker_ref.current is not None
            if worker_ref.current.worker:
                worker_ref.current.worker.stop()

    # ── UI Construction ──

    stat_chips: list[ft.Control] = [
        StatChip(value=stat_files_count, label=i18n.t("common.stat_files")),
        StatChip(value=stat_bad_count, label=i18n.t("clean.stat_bad"), green=True)
    ]

    header = PageHeader(
        title_white=i18n.t("clean.title_white"),
        title_green=i18n.t("clean.title_green"),
        description=i18n.t("clean.description"),
        stat_chips=stat_chips,
    )

    card_directory = Card(
        icon=ft.Icon(ft.Icons.FOLDER_OUTLINED, size=14, color=ACCENT_GREEN),
        title=i18n.t("clean.dir_title"),
        badge_text=f"{i18n.t('common.step')} 1",
        children=[
            PathSelector(
                value=folder_path,
                hint_text=i18n.t("clean.path_hint"),
                on_browse=lambda _: page.run_task(_on_browse_click),
                has_error=not folder_path and is_running
            ),
            InfoHint(text=i18n.t("clean.dir_hint").format(prefix=i18n.t("folders.clean_prefix")))
        ],
    )

    # Photo Filters Card
    filter_blur = FilterRow(
        title=i18n.t("clean.blur_title"),
        toggle_value=blur_enabled,
        on_toggle=set_blur_enabled,
        tooltip_text=i18n.t("clean.blur_tooltip"),
        controls_right=[
            NumInput(value=blur_val, label=i18n.t("clean.blur_label"), width=55, on_change=lambda e: set_blur_val(e.control.value), disabled=not blur_enabled or is_running)
        ],
    )

    filter_exposure = FilterRow(
        title=i18n.t("clean.exp_title"),
        toggle_value=exp_enabled,
        on_toggle=set_exp_enabled,
        tooltip_text=i18n.t("clean.exp_tooltip"),
        controls_right=[
            NumInput(value=exp_dark_val, label=i18n.t("clean.exp_dark_label"), width=55, on_change=lambda e: set_exp_dark_val(e.control.value), disabled=not exp_enabled or is_running),
            NumInput(value=exp_bright_val, label=i18n.t("clean.exp_bright_label"), width=55, on_change=lambda e: set_exp_bright_val(e.control.value), disabled=not exp_enabled or is_running)
        ],
    )

    filter_resolution = FilterRow(
        title=i18n.t("clean.res_title"),
        toggle_value=res_enabled,
        on_toggle=set_res_enabled,
        tooltip_text=i18n.t("clean.res_tooltip"),
        controls_right=[
            StyledDropdown(
                options=[
                    ft.dropdown.Option("320x240", "320x240 (QVGA)"),
                    ft.dropdown.Option("640x480", "640x480 (VGA)"),
                    ft.dropdown.Option("800x600", "800x600"),
                    ft.dropdown.Option("1024x768", "1024x768"),
                ],
                value=res_val,
                width=140,
                on_change=lambda e: set_res_val(e.control.value),
                disabled=not res_enabled or is_running
            )
        ],
    )

    filter_corrupted = FilterRow(
        title=i18n.t("clean.corrupted_title"),
        toggle_value=corr_enabled,
        on_toggle=set_corr_enabled,
        tooltip_text=i18n.t("clean.corrupted_tooltip"),
    )

    card_photo_filters = Card(
        icon=ft.Icon(ft.Icons.IMAGE_OUTLINED, size=14, color=PURPLE_ACCENT),
        title=i18n.t("clean.photo_title"),
        badge_text=f"{i18n.t('common.step')} 2",
        children=[
            filter_blur,
            filter_exposure,
            filter_resolution,
            filter_corrupted,
        ],
    )

    # Video Filters Card
    filter_duration = FilterRow(
        title=i18n.t("clean.dur_title"),
        toggle_value=dur_enabled,
        on_toggle=set_dur_enabled,
        tooltip_text=i18n.t("clean.dur_tooltip"),
        controls_right=[
            NumInput(value=dur_val, width=45, on_change=lambda e: set_dur_val(e.control.value), disabled=not dur_enabled or is_running)
        ],
    )

    filter_vid_res = FilterRow(
        title=i18n.t("clean.vid_res_title"),
        toggle_value=vres_enabled,
        on_toggle=set_vres_enabled,
        tooltip_text=i18n.t("clean.vid_res_tooltip"),
        controls_right=[
            StyledDropdown(
                options=[
                    ft.dropdown.Option("360", "360p"),
                    ft.dropdown.Option("480", "480p"),
                    ft.dropdown.Option("720", "720p (HD)"),
                ],
                value=vres_val,
                width=140,
                on_change=lambda e: set_vres_val(e.control.value),
                disabled=not vres_enabled or is_running
            )
        ],
    )

    filter_vid_dark = FilterRow(
        title=i18n.t("clean.vid_dark_title"),
        toggle_value=vdark_enabled,
        on_toggle=set_vdark_enabled,
        tooltip_text=i18n.t("clean.vid_dark_tooltip"),
    )

    filter_vid_sound = FilterRow(
        title=i18n.t("clean.vid_sound_title"),
        toggle_value=vsound_enabled,
        on_toggle=set_vsound_enabled,
        tooltip_text=i18n.t("clean.vid_sound_tooltip"),
    )

    card_video_filters = Card(
        icon=ft.Icon(ft.Icons.VIDEOCAM_OUTLINED, size=14, color=YELLOW_ACCENT),
        title=i18n.t("clean.video_title"),
        children=[
            filter_duration,
            filter_vid_res,
            filter_vid_dark,
            filter_vid_sound,
        ],
    )

    filters_grid = ft.Row(
        controls=[
            ft.Container(content=card_photo_filters, expand=True),
            ft.Container(content=card_video_filters, expand=True),
        ],
        spacing=14,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )

    launch_area = ft.Row(
        controls=[
            RunButton(
                text=i18n.t("common.stop") if is_running else i18n.t("clean.btn_run"),
                on_click=toggle_clean,
                icon_name=ft.Icons.PAUSE if is_running else ft.Icons.PLAY_ARROW,
            ),
            ft.Text(
                spans=[
                    ft.TextSpan(i18n.t("clean.launch_safe"), ft.TextStyle(color=IDLE_TEXT, size=11)),
                    ft.TextSpan(i18n.t("clean.launch_hint"), ft.TextStyle(color=IDLE_TEXT, size=11)),
                    ft.TextSpan(f"{i18n.t('folders.clean_prefix')}<name>", ft.TextStyle(color=LIGHT_GRAY, size=11, weight=ft.FontWeight.W_500)),
                    ft.TextSpan(i18n.t("clean.launch_hint_end"), ft.TextStyle(color=IDLE_TEXT, size=11)),
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
                        filters_grid,
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
