import flet as ft
from typing import Callable, Final, Optional

from ui.theme import (
    ACCENT_GREEN, ACCENT_WHITE, IDLE_TEXT, PRIMARY,
    SIDEBAR_WIDTH as SIDEBAR_W, SIDEBAR_BG, border_color,
)
from ui.i18n import i18n
from ui.components import SupportMenu, ContactButton, ContactButton

# UI Constants
SIDEBAR_WIDTH: Final = SIDEBAR_W
BG_COLOR: Final = SIDEBAR_BG
ACCENT_COLOR: Final = ACCENT_GREEN
PRIMARY_COLOR: Final = PRIMARY
HOVER_TEXT_COLOR: Final = ACCENT_WHITE
IDLE_TEXT_COLOR: Final = IDLE_TEXT

@ft.component
def SidebarItem(text: str, index: int, selected: bool, on_click: Callable[[int], None]):
    is_hovering, set_hovering = ft.use_state(False)
    
    indicator = ft.Container(
        width=4,
        height=24 if selected else (12 if is_hovering else 0),
        bgcolor=ACCENT_COLOR,
        border_radius=ft.BorderRadius.only(top_right=4, bottom_right=4),
        animate_size=ft.Animation(300, ft.AnimationCurve.EASE_OUT)
    )
    
    item_text = ft.Text(
        text, 
        size=14, 
        color=HOVER_TEXT_COLOR if (selected or is_hovering) else IDLE_TEXT_COLOR,
        weight=ft.FontWeight.W_500,
        font_family="Roboto",
    )
    
    text_container = ft.Container(
        content=item_text,
        padding=ft.Padding.only(left=10 if selected else (5 if is_hovering else 0)),
        animate=ft.Animation(300, ft.AnimationCurve.EASE_OUT)
    )
    
    if selected:
        gradient = ft.LinearGradient(
            begin=ft.Alignment.CENTER_LEFT,
            end=ft.Alignment.CENTER_RIGHT,
            colors=[ft.Colors.with_opacity(0.3, PRIMARY_COLOR), ft.Colors.TRANSPARENT]
        )
        bgcolor = None
    else:
        gradient = None
        bgcolor = ft.Colors.TRANSPARENT

    return ft.Container(
        content=ft.Row(
            controls=[indicator, text_container],
            spacing=16,
            alignment=ft.MainAxisAlignment.START,
        ),
        padding=ft.Padding.only(top=10, bottom=10, left=0, right=20),
        border_radius=8,
        gradient=gradient,
        bgcolor=bgcolor,
        on_click=lambda _: on_click(index),
        on_hover=lambda e: set_hovering(e.data == "true"),
    )

@ft.component
def AppSidebar(nav_index: int, on_nav_change: Callable[[int], None]):
    # Subscribe to i18n observable so the component re-renders on language change
    _lang_ver, _set_lang_ver = ft.use_state(0)

    def _subscribe_i18n():
        def _on_change(sender, field):
            _set_lang_ver(lambda v: v + 1)
        return i18n.subscribe(_on_change)

    ft.use_effect(_subscribe_i18n, [])
    support_btn = SupportMenu()
    contact_btn = ContactButton()
    
    action_buttons = ft.Row(
        controls=[support_btn, contact_btn],
        spacing=8,
    )
    
    # ─── Language Switcher ───
    is_uk = i18n.lang == "uk"
    
    lang_uk = ft.Container(
        content=ft.Text("UK", size=11, font_family="Roboto", weight=ft.FontWeight.W_500, color="#111111" if is_uk else IDLE_TEXT_COLOR),
        padding=ft.Padding.symmetric(vertical=3, horizontal=8),
        border_radius=3,
        bgcolor=ACCENT_COLOR if is_uk else ft.Colors.TRANSPARENT,
        on_click=lambda _: i18n.set_lang("uk"),
    )
    
    lang_en = ft.Container(
        content=ft.Text("EN", size=11, font_family="Roboto", weight=ft.FontWeight.W_500, color="#111111" if not is_uk else IDLE_TEXT_COLOR),
        padding=ft.Padding.symmetric(vertical=3, horizontal=8),
        border_radius=3,
        bgcolor=ACCENT_COLOR if not is_uk else ft.Colors.TRANSPARENT,
        on_click=lambda _: i18n.set_lang("en"),
    )
    
    lang_toggle = ft.Container(
        content=ft.Row(controls=[lang_uk, lang_en], spacing=2),
        bgcolor=ft.Colors.with_opacity(0.04, "#FFFFFF"),
        border=ft.Border.all(1, "#3d3d3d"),
        border_radius=5,
        padding=2,
    )
    
    lang_container = ft.Column(
        controls=[
            ft.Text("Language", size=10, color="#4a4a4a", font_family="Inter"),
            lang_toggle,
        ],
        spacing=4,
        horizontal_alignment=ft.CrossAxisAlignment.END,
    )
    
    controls_row = ft.Container(
        content=ft.Row(
            controls=[action_buttons, lang_container],
            spacing=16,
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.END,
        ),
        padding=ft.Padding.only(left=16, right=16, top=8, bottom=12),
    )
    
    footer_credit = ft.Container(
        content=ft.Text(
            "Developed by Mykaro",
            size=10,
            color="#8c8c8c",
            font_family="Inter",
            text_align=ft.TextAlign.CENTER,
        ),
        alignment=ft.Alignment.CENTER,
        padding=ft.Padding.only(top=12),
        margin=ft.Margin.symmetric(horizontal=16),
        border=ft.Border.only(top=ft.BorderSide(1, ft.Colors.with_opacity(0.04, "#FFFFFF"))),
    )
    
    bottom_controls = ft.Container(
        content=ft.Column(controls=[controls_row, footer_credit], spacing=0),
        margin=ft.Margin.only(bottom=8),
    )

    logo = ft.Container(
        content=ft.Image(
            src="logo.png",
            width=SIDEBAR_WIDTH,
            height=240,
            fit=ft.BoxFit.CONTAIN,
        ),
        alignment=ft.Alignment.CENTER,
        bgcolor=ft.Colors.with_opacity(0.1, PRIMARY_COLOR),
        border=ft.Border.only(bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.06, ACCENT_WHITE))),
        margin=ft.Margin.only(bottom=20)
    )

    items = [
        i18n.t("sidebar.twin_finder"),
        i18n.t("sidebar.photo_cleaner"),
        i18n.t("sidebar.photo_sorter"),
    ]

    menu_items: list[ft.Control] = [
        SidebarItem(text=label, index=i, selected=(i == nav_index), on_click=on_nav_change)
        for i, label in enumerate(items)
    ]
    
    menu_items_container = ft.Container(
        content=ft.Column(
            controls=menu_items,
            spacing=5,
            alignment=ft.MainAxisAlignment.START,
            horizontal_alignment=ft.CrossAxisAlignment.START
        ),
        padding=ft.Padding.symmetric(horizontal=10)
    )

    return ft.Container(
        width=SIDEBAR_WIDTH,
        bgcolor=BG_COLOR,
        border=ft.Border.only(right=ft.BorderSide(1, ft.Colors.with_opacity(0.06, ACCENT_WHITE))),
        padding=ft.Padding.only(left=0, top=0, right=0, bottom=20),
        content=ft.Column(
            controls=[
                logo,
                menu_items_container,
                ft.Container(expand=True),
                bottom_controls
            ],
            expand=True,
            alignment=ft.MainAxisAlignment.START,
            horizontal_alignment=ft.CrossAxisAlignment.START,
            spacing=0
        )
    )
