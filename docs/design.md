# MediaMatrix Design System

This document serves as the Single Source of Truth for the visual language of the MediaMatrix application. It outlines the design standards that must be followed to maintain interface consistency.

## 1. Design Philosophy

The design of MediaMatrix combines **modern minimalism** with elements of **retro-terminal** aesthetics. Dark Mode reduces eye strain during prolonged work with media files. The use of neon-green accents on a dark background creates the feel of a high-tech tool, while monospaced fonts in logs and statistics refer back to classic terminal interfaces. The goal of this design is to provide maximum functionality and readability while delivering a professional and technological visual experience (Affordance).

## 2. Color Palette

All colors are based on the Dark Mode theme. HEX values with added opacity are used to create surface effects (Glassmorphism).

| Variable Name | HEX | Purpose |
| --- | --- | --- |
| `BG_COLOR` | `#2E2E2E` | Main application background color |
| `SIDEBAR_BG` | `#232323` | Navigation sidebar background color |
| `PRIMARY` | `#1E3A8A` | Main blue accent color (e.g., PrimaryButton) |
| `PRIMARY_HOVER` | `#2B4EAC` | Hover state for primary blue elements |
| `ACCENT_WHITE` | `#FFFFFF` | White color for text, icons, and translucent surfaces |
| `ACCENT_GREEN` | `#00C896` | Neon green for success statuses and accents |
| `LIGHT_GRAY` | `#F5F5F5` | Light gray for main text and input fields |
| `IDLE_TEXT` | `#8A8A8A` | Dark gray for secondary text, descriptions, and inactive elements |
| `DANGER` | `#FF4757` | Red for errors and destructive actions |
| `WARNING` | `#FFA502` | Orange for warnings |
| `PURPLE_ACCENT` | `#A78BFA` | Additional accent (purple) |
| `YELLOW_ACCENT` | `#FBBF24` | Additional accent (yellow) |

**Surfaces & Borders:**

- `SURFACE_OPACITY` (`0.04` over white): Background for cards and panels.
- `SURFACE_HOVER_OPACITY` (`0.07` over white): Card background on hover.
- `BORDER_OPACITY` (`0.08` over white): Standard element borders.
- `BORDER_BRIGHT_OPACITY` (`0.14` over white): Borders on hover or active state.

## 3. Typography

The typographic hierarchy clearly delineates functional areas of the interface. The application uses 4 main font families:

| Purpose | Font Family | Weight | Size |
| --- | --- | --- | --- |
| **Logo / Main Headers** | Montserrat | Bold (W_700) | 24px |
| **Card title** | Roboto | Medium (W_500) | 15px |
| **Body text / Descriptions** | Inter | Regular (W_400) | 12-14px |
| **Buttons** | Roboto | Medium (W_500) | 12-13px |
| **Statistics / Values** | JetBrains Mono | Medium (W_500) | 16-18px |
| **Logs / Data / Input Value** | JetBrains Mono | Regular / W_500 | 10-12px |
| **Helper text / ETA** | Inter | Regular | 9-11px |

## 4. Component Library

### Buttons

- **PrimaryButton**:
  - **Default**: Background `PRIMARY`, text color `ACCENT_WHITE`, padding `10px 24px`, border-radius `8px`.
  - **Hover**: Background changes to `PRIMARY_HOVER`, a slight upward offset is added (`offset -0.01`).
  - **Disabled**: Reduced opacity (`opacity=0.5`), events disabled.
- **GhostButton**:
  - **Default**: Translucent background (0.05 white), 1px border (0.08 white), text color `IDLE_TEXT`.
  - **Hover**: Background gets brighter (0.09 white), border gets brighter (0.14 white), text `ACCENT_WHITE`.
  - **Disabled**: Background 0.02 white, `opacity=0.5`.
- **RunButton** (Accent trigger button):
  - **Default**: Linear gradient from `ACCENT_GREEN` to `#00A87E`, text dark-green/black (`#0A1A14`).

### Inputs and Cards

- **Inputs (PathSelector, NumInput, Dropdown)**:
  - Background: translucent black (`rgba(0,0,0, 0.25)` or `0.3`).
  - Border: standard 1px (`BORDER_OPACITY`), on focus changes to `PRIMARY` or `ACCENT_GREEN`.
  - Border radius: `6px` or `8px`.
  - Text inside input fields uses `JetBrains Mono` for clear readability of paths and numbers.
  - Error state: border changes to `DANGER` (`#FF4757`).
- **Cards (Media file cards / settings containers)**:
  - Background: `surface_color()`.
  - Border radius: `CARD_BORDER_RADIUS` (`12px`).
  - Internal padding: `CARD_PADDING_V` (14px) and `CARD_PADDING_H` (18px).
  - Hover effect: border gets brighter (`border_bright_color()`).

### Form Controls & Settings

- **CustomToggle**: Custom switch implementation. Animated knob changing to `ACCENT_GREEN` when active, with a dimmed green track (`accent_green_dim`).
- **FilterRow / OptItem**: Horizontal setting rows. Title and description on the left, control (toggle/dropdown/radio) on the right. Background brightens and border uses `BORDER_BRIGHT_OPACITY` on hover.
- **CustomRadioGroup / CustomRadioItem**: Custom radio selection. Displays an outer ring and inner green dot when selected. Background adapts on hover and selection state.

### Data & Status Displays

- **StatChip**: Small badges for metrics. Uses `JetBrains Mono` for values. Green text used for highlighted metrics. Border uses standard `BORDER_OPACITY`.
- **ResultBox**: Large presentation containers for final scan results. Values use 18px `JetBrains Mono`. Background changes to `rgba(0,200,150,0.05)` with an `ACCENT_GREEN` border when highlighted as the primary active result.
- **LogSection**: Collapsible processing log area. Includes a gradient progress bar (`ACCENT_GREEN` to `#00e8b0`). Heights toggle between 32px (collapsed) and 230px (expanded). Uses specific color coding for log types (Success: green, Warning: orange, Error: red).
- **InfoHint**: Helper text containers characterized by a 2px solid `ACCENT_GREEN` left border and a translucent dark background.

### Structural & Navigation Components

- **PageHeader**: Main content headers with dual-color typography (White and Green `ACCENT_GREEN`) and an integrated flex-space for `StatChip` blocks.
- **SidebarItem**: Navigation links in the sidebar. Features a sliding animated 4px left-indicator (visible on hover, full height on selection) and a subtle rightward text shift on hover.
- **SupportMenu / ContactButton**: Interactive popover menus in the sidebar. Used for external links (Patreon, Ko-fi) and clipboard actions with `SnackBar` notifications (e.g., copying Binance ID).
- **Language Switcher**: Compact toggle (UK/EN) in the sidebar footer with `ACCENT_GREEN` highlight for the active language.

### Icons

- Standard Material Icons set is used (via `ft.Icons`).
- Sizes vary depending on context:
  - In buttons: `13-15px`.
  - In card headers (in `28x28px` containers): centered.
  - In status bars / logs: `10-16px`.

## 5. Layout & Spacing

The design follows a Responsive approach for desktop applications, using a flexible grid based on `Row` and `Column`.

- **App Window**: Base size `1210x810`, minimum sizes `1000x750`.
- **Grid and Structure**:
  - On the left is a fixed navigation sidebar (`SIDEBAR_WIDTH = 250px`).
  - On the right is the content area (`ContentArea`), which occupies all remaining space (`expand=True`).
- **Spacing & Paddings**:
  - Internal paddings of the content area: Top `24px`, Bottom `24px`, Left `32px`, Right `32px`.
  - Standard gap between components (`CONTENT_GAP`): `14px`.
  - Inside cards, the distance between elements is usually `10px` or `12px`.

## 6. Assets Management

All external resources are stored in the `assets/` folder.

- **Application Logos and Icons**: The file `logo_256x256.ico` is used for the window icon (path: `assets/logo_256x256.ico`).
- **Fonts**: Fonts are loaded locally from the `assets/fonts/` folder. `.ttf` files (variable fonts) are registered in `page.fonts`.
- **Localization**: Translation files (`.json`) are stored in the `assets/lang/` folder and loaded by the `i18n` module.
