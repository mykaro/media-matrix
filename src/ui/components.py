"""
Shared UI components for MediaMatrix — reusable widgets matching HTML prototypes.
Migrated to Flet 1.0 declarative style (@ft.component).
"""
from typing import Callable, Optional
import flet as ft

from ui.theme import (
    ACCENT_GREEN, ACCENT_WHITE, BG_COLOR, CARD_BORDER_RADIUS,
    CARD_PADDING_H, CARD_PADDING_V, DANGER, FONT_BTN, FONT_CODE,
    FONT_LOGO, FONT_MAIN, IDLE_TEXT, LIGHT_GRAY, PRIMARY, PRIMARY_HOVER,
    WARNING, accent_green_dim, accent_green_glow, border_bright_color,
    border_color, primary_glow, surface_color, surface_hover_color,
)
from ui.i18n import i18n


@ft.component
def StatChip(value: str, label: str, green: bool = False, width: int = 110):
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(
                    value,
                    font_family=FONT_CODE,
                    size=16,
                    weight=ft.FontWeight.W_500,
                    color=ACCENT_GREEN if green else ACCENT_WHITE,
                ),
                ft.Text(
                    label,
                    size=11,
                    color=IDLE_TEXT,
                    font_family=FONT_MAIN,
                    text_align=ft.TextAlign.RIGHT,
                    no_wrap=True,
                ),
            ],
            spacing=2,
            horizontal_alignment=ft.CrossAxisAlignment.END,
        ),
        padding=ft.Padding.symmetric(vertical=6, horizontal=12),
        bgcolor=surface_color(),
        border=ft.Border.all(1, border_color()),
        border_radius=10,
        width=width,
    )


@ft.component
def PageHeader(
    title_white: str,
    title_green: str,
    description: str,
    stat_chips: list[ft.Control],
):
    title = ft.Text(
        spans=[
            ft.TextSpan(title_white, ft.TextStyle(color=ACCENT_WHITE)),
            ft.TextSpan(title_green, ft.TextStyle(color=ACCENT_GREEN)),
        ],
        font_family=FONT_LOGO,
        size=24,
        weight=ft.FontWeight.W_700,
    )
    desc = ft.Text(
        description,
        size=13,
        color=IDLE_TEXT,
        font_family=FONT_MAIN,
    )

    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Column(
                    controls=[title, desc],
                    spacing=4,
                    expand=True,
                ),
                ft.Row(controls=stat_chips, spacing=10),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.START,
        ),
        padding=ft.Padding.only(bottom=4)
    )


@ft.component
def Card(
    icon: ft.Control,
    title: str,
    badge_text: Optional[str] = None,
    children: Optional[list[ft.Control]] = None,
):
    is_hovered, set_hovered = ft.use_state(False)

    icon_box = ft.Container(
        content=icon,
        width=28,
        height=28,
        alignment=ft.Alignment.CENTER,
        border_radius=8,
        bgcolor=surface_hover_color(),
    )

    title_text = ft.Text(
        title,
        font_family=FONT_BTN,
        size=15,
        weight=ft.FontWeight.W_500,
        color=ACCENT_WHITE,
    )

    header_controls: list[ft.Control] = [icon_box, title_text]

    if badge_text:
        badge = ft.Container(
            content=ft.Text(
                badge_text,
                size=11,
                font_family=FONT_CODE,
                color=ACCENT_GREEN,
            ),
            bgcolor=accent_green_dim(),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.2, ACCENT_GREEN)),
            border_radius=20,
            padding=ft.Padding.symmetric(vertical=2, horizontal=8),
        )
        header_controls.append(ft.Container(expand=True))
        header_controls.append(badge)

    header = ft.Row(controls=header_controls, spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    all_controls: list[ft.Control] = [header]
    if children:
        all_controls.extend(children)

    return ft.Container(
        content=ft.Column(controls=all_controls, spacing=12),
        bgcolor=surface_color(),
        border=ft.Border.all(1, border_bright_color() if is_hovered else border_color()),
        border_radius=CARD_BORDER_RADIUS,
        padding=ft.Padding.symmetric(vertical=CARD_PADDING_V, horizontal=CARD_PADDING_H),
        on_hover=lambda e: set_hovered(e.data == "true"),
        animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT)
    )


@ft.component
def PathSelector(
    value: str = "",
    on_browse: Optional[Callable] = None,
    hint_text: str = "",
    has_error: bool = False,
):
    # Subscribe to i18n observable so the component re-renders on language change
    _lang_ver, _set_lang_ver = ft.use_state(0)

    def _subscribe_i18n():
        def _on_change(sender, field):
            _set_lang_ver(lambda v: v + 1)
        return i18n.subscribe(_on_change)

    ft.use_effect(_subscribe_i18n, [])
    path_field = ft.TextField(
        value=value,
        read_only=True,
        text_style=ft.TextStyle(
            font_family=FONT_CODE,
            size=12,
            color=LIGHT_GRAY,
        ),
        bgcolor=ft.Colors.with_opacity(0.25, "#000000"),
        border_color=DANGER if has_error else border_color(),
        border_radius=8,
        content_padding=ft.Padding.only(left=34, top=8, bottom=8, right=14),
        expand=True,
        hint_text=hint_text,
        hint_style=ft.TextStyle(color=IDLE_TEXT, size=13),
        focused_border_color=ft.Colors.with_opacity(0.6, PRIMARY),
    )

    folder_icon = ft.Icon(
        ft.Icons.FOLDER_OUTLINED,
        size=14,
        color=IDLE_TEXT,
    )
    path_wrap = ft.Stack(
        controls=[
            path_field,
            ft.Container(
                content=folder_icon,
                left=12,
                top=0,
                bottom=0,
                alignment=ft.Alignment.CENTER_LEFT,
            ),
        ],
        expand=True,
    )

    return ft.Row(
        controls=[path_wrap, GhostButton(i18n.t("comp.browse"), on_click=on_browse, icon=ft.Icons.SEARCH, small=True)],
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


@ft.component
def InfoHint(
    text: str = "",
    border_left_color: str = ACCENT_GREEN,
    content_control: Optional[ft.Control] = None,
):
    inner = content_control or ft.Text(
        text,
        size=13,
        color=IDLE_TEXT,
        font_family=FONT_MAIN,
    )

    return ft.Container(
        content=inner,
        bgcolor=ft.Colors.with_opacity(0.2, "#000000"),
        border=ft.Border.only(left=ft.BorderSide(2, border_left_color)),
        border_radius=ft.BorderRadius.only(top_right=6, bottom_right=6),
        padding=ft.Padding.symmetric(vertical=4, horizontal=10)
    )


@ft.component
def GhostButton(
    text: str,
    on_click: Optional[Callable] = None,
    icon: Optional[ft.IconData] = None,
    small: bool = False,
    disabled: bool = False,
):
    is_hovered, set_hovered = ft.use_state(False)

    controls: list[ft.Control] = []
    if icon:
        controls.append(ft.Icon(
            icon, 
            size=13, 
            color=ACCENT_WHITE if (is_hovered and not disabled) else IDLE_TEXT
        ))
        
    controls.append(ft.Text(
        text,
        font_family=FONT_BTN,
        size=12,
        weight=ft.FontWeight.W_500,
        color=ACCENT_WHITE if (is_hovered and not disabled) else IDLE_TEXT,
    ))

    pad = 8 if small else 10
    
    bgcolor = ft.Colors.with_opacity(0.02 if disabled else (0.09 if is_hovered else 0.05), ACCENT_WHITE)
    bdr_color = border_bright_color() if (is_hovered and not disabled) else border_color()

    return ft.Container(
        content=ft.Row(
            controls=controls,
            spacing=6,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        padding=ft.Padding.symmetric(vertical=pad, horizontal=16 if not small else 12),
        border_radius=8,
        bgcolor=bgcolor,
        border=ft.Border.all(1, bdr_color),
        on_click=on_click if not disabled else None,
        on_hover=lambda e: set_hovered(e.data == "true"),
        animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
        opacity=0.5 if disabled else 1.0
    )


@ft.component
def RunButton(
    text: str = "Run Analysis",
    on_click: Optional[Callable] = None,
    icon_name: Optional[ft.IconData] = None,
    disabled: bool = False,
):
    is_hovered, set_hovered = ft.use_state(False)

    btn_icon = ft.Icon(
        icon_name or ft.Icons.PLAY_ARROW,
        size=15,
        color=IDLE_TEXT if disabled else "#0a1a14",
    )
    btn_text = ft.Text(
        text,
        font_family=FONT_BTN,
        size=13,
        weight=ft.FontWeight.W_500,
        color=IDLE_TEXT if disabled else "#0a1a14",
    )

    if disabled:
        gradient = None
        bgcolor = ft.Colors.with_opacity(0.05, ACCENT_WHITE)
        border = ft.Border.all(1, border_color())
    else:
        gradient = ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT,
            end=ft.Alignment.BOTTOM_RIGHT,
            colors=[ACCENT_GREEN, "#00a87e"],
        )
        bgcolor = None
        border = None

    return ft.Container(
        content=ft.Row(
            controls=[btn_icon, btn_text],
            spacing=6,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        padding=ft.Padding.symmetric(vertical=10, horizontal=24),
        border_radius=8,
        gradient=gradient,
        bgcolor=bgcolor,
        border=border,
        on_click=on_click if not disabled else None,
        on_hover=lambda e: set_hovered(e.data == "true"),
        animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
        opacity=0.6 if disabled else 1.0,
        offset=ft.Offset(0, -0.01) if (is_hovered and not disabled) else ft.Offset(0, 0)
    )


@ft.component
def PrimaryButton(
    text: str,
    on_click: Optional[Callable] = None,
    icon_name: Optional[ft.IconData] = None,
    disabled: bool = False,
):
    is_hovered, set_hovered = ft.use_state(False)

    controls: list[ft.Control] = []
    if icon_name:
        controls.append(ft.Icon(icon_name, size=15, color=ACCENT_WHITE))
        
    controls.append(ft.Text(
        text,
        font_family=FONT_BTN,
        size=13,
        weight=ft.FontWeight.W_500,
        color=ACCENT_WHITE,
    ))

    return ft.Container(
        content=ft.Row(
            controls=controls,
            spacing=8,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        padding=ft.Padding.symmetric(vertical=10, horizontal=24),
        border_radius=8,
        bgcolor=PRIMARY_HOVER if (is_hovered and not disabled) else PRIMARY,
        on_click=on_click if not disabled else None,
        on_hover=lambda e: set_hovered(e.data == "true"),
        animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
        opacity=0.5 if disabled else 1.0,
        offset=ft.Offset(0, -0.01) if (is_hovered and not disabled) else ft.Offset(0, 0)
    )


@ft.component
def CustomToggle(
    value: bool = False,
    on_change: Optional[Callable[[bool], None]] = None,
):
    knob = ft.Container(
        width=12,
        height=12,
        border_radius=6,
        bgcolor=ACCENT_GREEN if value else "#888888",
        animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
    )

    track = ft.Container(
        content=ft.Row(
            controls=[knob],
            alignment=ft.MainAxisAlignment.END if value else ft.MainAxisAlignment.START,
        ),
        width=32,
        height=18,
        border_radius=20,
        bgcolor=accent_green_dim() if value else ft.Colors.with_opacity(0.1, ACCENT_WHITE),
        border=ft.Border.all(
            1,
            ft.Colors.with_opacity(0.3, ACCENT_GREEN) if value else border_color(),
        ),
        padding=ft.Padding.symmetric(horizontal=2),
        alignment=ft.Alignment.CENTER_LEFT if not value else ft.Alignment.CENTER_RIGHT,
        animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
        on_click=lambda _: on_change(not value) if on_change else None,
    )

    return ft.Container(content=track, width=32, height=18)


@ft.component
def OptItem(
    title: str,
    description: str = "",
    control: Optional[ft.Control] = None,
):
    is_hovered, set_hovered = ft.use_state(False)

    text_col = ft.Column(
        controls=[
            ft.Text(title, size=14, color=ACCENT_WHITE, font_family=FONT_MAIN),
            *(
                [ft.Text(description, size=12, color=IDLE_TEXT, font_family=FONT_MAIN)]
                if description else []
            ),
        ],
        spacing=2,
        expand=True,
    )

    row_controls: list[ft.Control] = [text_col]
    if control:
        row_controls.append(control)

    return ft.Container(
        content=ft.Row(
            controls=row_controls,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
        ),
        padding=ft.Padding.symmetric(vertical=10, horizontal=12),
        bgcolor=ft.Colors.with_opacity(0.2, "#000000"),
        border=ft.Border.all(1, border_bright_color() if is_hovered else border_color()),
        border_radius=8,
        height=64,
        on_hover=lambda e: set_hovered(e.data == "true"),
        animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT)
    )


@ft.component
def FilterRow(
    title: str,
    toggle_value: bool = True,
    on_toggle: Optional[Callable[[bool], None]] = None,
    tooltip_text: Optional[str] = None,
    controls_right: Optional[list[ft.Control]] = None,
    height: int = 56,
):
    is_hovered, set_hovered = ft.use_state(False)

    title_controls: list[ft.Control] = [
        ft.Text(title, size=14, color=ACCENT_WHITE, font_family=FONT_MAIN),
    ]
    if tooltip_text:
        title_controls.append(
            ft.Icon(
                ft.Icons.INFO_OUTLINE,
                size=16,
                color=LIGHT_GRAY,
                tooltip=ft.Tooltip(message=tooltip_text, wait_duration=0),
            )
        )

    row_controls: list[ft.Control] = [
        CustomToggle(value=toggle_value, on_change=on_toggle),
        ft.Row(controls=title_controls, spacing=6, expand=True)
    ]
    
    if controls_right:
        row_controls.append(
            ft.Row(controls=controls_right, spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        )

    return ft.Container(
        content=ft.Row(
            controls=row_controls,
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding.symmetric(vertical=4, horizontal=12),
        bgcolor=ft.Colors.with_opacity(0.2, "#000000"),
        border=ft.Border.all(1, border_bright_color() if is_hovered else border_color()),
        border_radius=8,
        height=height,
        on_hover=lambda e: set_hovered(e.data == "true"),
        animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
        opacity=1.0 if toggle_value else 0.6
    )


def NumInput(
    value: str = "",
    label: str = "",
    width: int = 50,
    disabled: bool = False,
    on_change: Optional[Callable] = None,
) -> ft.TextField:
    return ft.TextField(
        value=value,
        width=width,
        height=32,
        text_style=ft.TextStyle(font_family=FONT_CODE, size=11, color=LIGHT_GRAY),
        text_align=ft.TextAlign.CENTER,
        bgcolor=ft.Colors.with_opacity(0.3, "#000000"),
        border_color=border_color(),
        border_radius=6,
        content_padding=ft.Padding.all(4),
        focused_border_color=ACCENT_GREEN,
        label=label,
        label_style=ft.TextStyle(size=11, color=LIGHT_GRAY),
        input_filter=ft.NumbersOnlyInputFilter(),
        disabled=disabled,
        on_change=on_change,
    )


def StyledDropdown(
    options: list[ft.dropdown.Option],
    value: str = "",
    width: int = 100,
    disabled: bool = False,
    on_change: Optional[Callable] = None,
) -> ft.Dropdown:
    dropdown = ft.Dropdown(
        options=options,
        value=value,
        width=width,
        dense=True,
        text_style=ft.TextStyle(font_family=FONT_CODE, size=11, color=LIGHT_GRAY),
        bgcolor=ft.Colors.with_opacity(0.3, "#000000"),
        border_color=border_color(),
        border_radius=6,
        content_padding=ft.Padding.only(left=8, right=8, top=10, bottom=10),
        focused_border_color=border_bright_color(),
        disabled=disabled,
        on_select=on_change,
    )
    dropdown.height = 52
    dropdown.text_size = 12
    dropdown.menu_height = 200
    return dropdown


@ft.component
def LogSection(
    is_running: bool,
    logs: list[dict], # list of dicts: {"type": "info", "time": "12:00:00", "message": "msg"}
    progress_current: int,
    progress_total: int,
    eta_text: str = "",
    progress_label_prefix: str = "",
):
    # Subscribe to i18n observable so the component re-renders on language change
    _lang_ver, _set_lang_ver = ft.use_state(0)

    def _subscribe_i18n():
        def _on_change(sender, field):
            _set_lang_ver(lambda v: v + 1)
        return i18n.subscribe(_on_change)

    ft.use_effect(_subscribe_i18n, [])
    is_expanded, set_expanded = ft.use_state(False)
    
    EXPANDED_HEIGHT = 230
    COLLAPSED_HEIGHT = 32

    # Embed progress
    pct = (progress_current / progress_total) if progress_total > 0 else 0
    lbl_progress_val = f"{progress_label_prefix or i18n.t('comp.progress_processed')}: {progress_current:,} / {progress_total:,}".replace(",", " ")
    lbl_eta_val = eta_text or i18n.t("comp.progress_calc")

    progress_area = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text(lbl_progress_val, size=11, color=IDLE_TEXT, font_family=FONT_MAIN),
                        ft.Text(lbl_eta_val, size=10, color=IDLE_TEXT, font_family=FONT_CODE),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Container(
                    content=ft.Stack(controls=[
                        ft.Container(
                            height=3, width=max(0, pct * 800), border_radius=3,
                            gradient=ft.LinearGradient(colors=[ACCENT_GREEN, "#00e8b0"]),
                            animate=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
                        )
                    ]),
                    height=3,
                    bgcolor=ft.Colors.with_opacity(0.07, ACCENT_WHITE),
                    border_radius=3,
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                ),
            ],
            spacing=6,
        ),
        padding=ft.Padding.only(left=16, right=16, top=8, bottom=10),
        bgcolor=ft.Colors.with_opacity(0.03, ACCENT_WHITE),
        visible=is_running,
    )

    # Log list
    LOG_ICONS = {"info": "›", "success": "✓", "warning": "!", "error": "✕"}
    LOG_COLORS = {"info": IDLE_TEXT, "success": ACCENT_GREEN, "warning": WARNING, "error": DANGER}
    
    log_controls: list[ft.Control] = []
    for log in logs:
        msg_color = LOG_COLORS.get(log["type"], IDLE_TEXT)
        log_controls.append(
            ft.Row(
                controls=[
                    ft.Text(log["time"], size=10, color="#555555", font_family=FONT_CODE, width=60),
                    ft.Text(LOG_ICONS.get(log["type"], "·"), size=10, color=msg_color, font_family=FONT_CODE, width=14, text_align=ft.TextAlign.CENTER),
                    ft.Text(log["message"], size=11, color=msg_color, font_family=FONT_CODE),
                ],
                spacing=10,
            )
        )

    list_ref = ft.use_ref()  # type: ignore

    log_body = ft.Container(
        content=ft.Column(ref=list_ref,  # type: ignore
 controls=log_controls, spacing=3, scroll=ft.ScrollMode.AUTO, auto_scroll=is_running),
        expand=True,
        padding=ft.Padding.symmetric(horizontal=16, vertical=6),
    )

    # Header
    header = ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(width=6, height=6, border_radius=3, bgcolor=ACCENT_GREEN),
                ft.Text(i18n.t("comp.log_header"), size=11, color=IDLE_TEXT, font_family=FONT_BTN, weight=ft.FontWeight.W_500),
                ft.Container(expand=True),
                ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN if is_expanded else ft.Icons.KEYBOARD_ARROW_UP, size=16, color=IDLE_TEXT),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        height=32,
        padding=ft.Padding.symmetric(horizontal=16, vertical=0),
        on_click=lambda _: set_expanded(not is_expanded),
        ink=True,
    )

    def auto_expand():
        if is_running and not is_expanded:
            set_expanded(True)
        elif not is_running and list_ref.current:
            async def delayed_scroll():
                import asyncio
                await asyncio.sleep(0.1)
                try:
                    if list_ref.current and list_ref.current.page:
                        await list_ref.current.scroll_to(offset=-1, duration=300)
                except Exception:
                    pass
            if list_ref.current.page:
                list_ref.current.page.run_task(delayed_scroll)

    ft.use_effect(auto_expand, [is_running])

    return ft.Container(
        content=ft.Column(
            controls=[header, progress_area, log_body],
            expand=True,
            spacing=0,
        ),
        height=EXPANDED_HEIGHT if is_expanded else COLLAPSED_HEIGHT,
        animate=ft.Animation(250, ft.AnimationCurve.EASE_OUT),
        bgcolor="#1e1e1e",
        border=ft.Border.only(top=ft.BorderSide(1, ft.Colors.with_opacity(0.10, ACCENT_WHITE))),
    )


@ft.component
def ResultBox(title: str, subtitle: str, value: str = "—", active: bool = False):
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(
                    value,
                    font_family=FONT_CODE,
                    size=18,
                    weight=ft.FontWeight.W_500,
                    color=ACCENT_GREEN if active else ACCENT_WHITE,
                ),
                ft.Text(title, size=10, color=LIGHT_GRAY, font_family=FONT_MAIN, text_align=ft.TextAlign.CENTER),
                ft.Text(subtitle, size=9, color=IDLE_TEXT, font_family=FONT_MAIN, text_align=ft.TextAlign.CENTER),
            ],
            spacing=2,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=ft.Colors.with_opacity(0.05, ACCENT_GREEN) if active else ft.Colors.with_opacity(0.25, "#000000"),
        border=ft.Border.all(1, ft.Colors.with_opacity(0.3, ACCENT_GREEN) if active else border_color()),
        border_radius=8,
        padding=ft.Padding.symmetric(vertical=12, horizontal=8),
        alignment=ft.Alignment.CENTER,
        expand=True,
        animate=ft.Animation(300, ft.AnimationCurve.EASE_OUT)
    )


@ft.component
def CustomRadioItem(
    text: str,
    value: str,
    selected: bool = False,
    on_select: Optional[Callable[[str], None]] = None,
    height: Optional[int] = None,
):
    is_hovered, set_hovered = ft.use_state(False)

    inner_dot = ft.Container(
        width=8, height=8, border_radius=4,
        bgcolor=ACCENT_GREEN if selected else ft.Colors.TRANSPARENT,
        animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
    )
    outer_ring = ft.Container(
        content=inner_dot,
        width=16, height=16, border_radius=8,
        border=ft.Border.all(2, ACCENT_GREEN if selected else IDLE_TEXT),
        alignment=ft.Alignment.CENTER,
        animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
    )

    return ft.Container(
        content=ft.Row(
            controls=[
                outer_ring,
                ft.Text(text, size=12, color=LIGHT_GRAY, font_family=FONT_MAIN),
            ],
            spacing=12,
        ),
        padding=ft.Padding.symmetric(vertical=10, horizontal=14),
        bgcolor=ft.Colors.with_opacity(0.02, ACCENT_WHITE) if (is_hovered and not selected) else ft.Colors.with_opacity(0.2, "#000000"),
        border=ft.Border.all(1, border_bright_color() if is_hovered else border_color()),
        border_radius=8,
        height=height,
        on_click=lambda _: on_select(value) if on_select else None,
        on_hover=lambda e: set_hovered(e.data == "true"),
        animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT)
    )


@ft.component
def CustomRadioGroup(
    options: list[tuple[str, str]],  # [(text, value), ...]
    value: str = "",
    on_change: Optional[Callable[[str], None]] = None,
    height: Optional[int] = None,
):
    items = []
    for text, val in options:
        items.append(CustomRadioItem(
            text=text,
            value=val,
            selected=(val == value),
            on_select=on_change,
            height=height,
        ))

    return ft.Container(
        content=ft.Column(controls=items, spacing=8)
    )


@ft.component
def SupportMenu():
    support_hovered, set_support_hovered = ft.use_state(False)

    async def on_binance_click(e):
        await e.page.clipboard.set("451987508")
        snack = ft.SnackBar(
            content=ft.Text("ID copied", color=ACCENT_WHITE, font_family=FONT_MAIN),
            bgcolor=surface_color(),
            duration=2000,
        )
        e.page.overlay.append(snack)
        snack.open = True
        e.page.update()

    async def on_patreon_click(e):
        await e.page.launch_url("https://patreon.com/Mykaro?utm_medium=unknown&utm_source=join_link&utm_campaign=creatorshare_creator&utm_content=copyLink")

    async def on_kofi_click(e):
        await e.page.launch_url("https://ko-fi.com/bymykaro")

    btn_content = ft.Container(
        content=ft.Icon(
            ft.Icons.FAVORITE,
            size=16,
            color=ft.Colors.RED_400 if support_hovered else "#ff4757",
        ),
        width=32,
        height=32,
        border_radius=5,
        alignment=ft.Alignment.CENTER,
        bgcolor=ft.Colors.with_opacity(0.04, "#FFFFFF"),
        border=ft.Border.all(1, ft.Colors.RED_400 if support_hovered else "#3d3d3d"),
        animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
        on_hover=lambda e: set_support_hovered(e.data == "true"),
    )

    return ft.PopupMenuButton(
        content=btn_content,
        bgcolor=BG_COLOR,
        shadow_color=ft.Colors.with_opacity(0.3, "#000000"),
        elevation=8,
        shape=ft.RoundedRectangleBorder(radius=8),
        items=[
            ft.PopupMenuItem(
                content=ft.Row([
                    ft.Image(src="patreon-logo.png", width=27, height=27),
                    ft.Text("Patreon", font_family=FONT_MAIN, size=13, color=ACCENT_WHITE)
                ]),
                on_click=on_patreon_click
            ),
            ft.PopupMenuItem(
                content=ft.Row([
                    ft.Image(src="ko-fi-logo.png", width=27, height=27),
                    ft.Text("Ko-fi", font_family=FONT_MAIN, size=13, color=ACCENT_WHITE)
                ]),
                on_click=on_kofi_click
            ),
            ft.PopupMenuItem(
                content=ft.Row([
                    ft.Image(src="binance-logo.png", width=27, height=27),
                    ft.Text("Binance", font_family=FONT_MAIN, size=13, color=ACCENT_WHITE)
                ]),
                on_click=on_binance_click
            )
        ]
    )


@ft.component
def ContactButton(email: str = "bymykaro@gmail.com"):
    is_hovered, set_hovered = ft.use_state(False)
    
    async def on_click(e):
        await e.page.launch_url(f"https://mail.google.com/mail/?view=cm&fs=1&to={email}")

    return ft.Container(
        content=ft.Image(src="google-mail-logo.png", width=18, height=18, fit=ft.BoxFit.CONTAIN),
        width=32,
        height=32,
        border_radius=5,
        alignment=ft.Alignment.CENTER,
        bgcolor=ft.Colors.with_opacity(0.04, "#FFFFFF"),
        border=ft.Border.all(1, ft.Colors.with_opacity(0.14, "#FFFFFF") if is_hovered else "#3d3d3d"),
        animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
        on_hover=lambda e: set_hovered(e.data == "true"),
        on_click=on_click,
        tooltip=ft.Tooltip(message="Contact Us", wait_duration=500),
    )
