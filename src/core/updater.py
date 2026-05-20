import logging
from typing import Optional, Tuple
import flet as ft
from ui.i18n import i18n

logger = logging.getLogger(__name__)

async def get_latest_release(repo: str) -> Optional[Tuple[str, str]]:
    """
    Fetches the latest release version and its html_url from GitHub.
    repo format: "owner/repo"
    Returns:
        Tuple of (version_string, release_url) or None if failed.
    """
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    import httpx
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, headers={"Accept": "application/vnd.github.v3+json"})
            if response.status_code == 200:
                data = response.json()
                tag_name = data.get("tag_name", "")
                html_url = data.get("html_url", "")
                if tag_name:
                    version = tag_name.lstrip('v')
                    return version, html_url
            else:
                logger.warning(f"Failed to fetch latest release: {response.status_code} {response.text}")
    except Exception as e:
        logger.error(f"Error checking for updates: {e}")
    return None

def is_newer_version(latest_version: str, current_version: str) -> bool:
    """
    Compares two semantic versions. Returns True if latest_version > current_version.
    """
    try:
        latest_parts = [int(x) for x in latest_version.split('.')]
        current_parts = [int(x) for x in current_version.split('.')]
        return latest_parts > current_parts
    except ValueError:
        return latest_version > current_version

async def check_for_updates(page: ft.Page, current_version: str, repo: str):
    latest = await get_latest_release(repo)
    if latest:
        latest_ver, url = latest
        if is_newer_version(latest_ver, current_version):
            
            launcher = ft.UrlLauncher()

            async def open_url(e):
                await launcher.launch_url(url)
                dialog.open = False
                page.update()

            def close_dlg(e):
                dialog.open = False
                page.update()

            title_text = i18n.t("updater.update_available_title")
            content_template = i18n.t("updater.update_available_text")
            content_text = content_template.replace("{version}", latest_ver) if "{version}" in content_template else content_template
            btn_yes = i18n.t("updater.update_yes")
            btn_no = i18n.t("updater.update_no")

            dialog = ft.AlertDialog(
                title=ft.Text(title_text),
                content=ft.Text(content_text),
                actions=[
                    ft.TextButton(btn_yes, on_click=open_url),
                    ft.TextButton(btn_no, on_click=close_dlg),
                ],
            )
            page.services.append(launcher)
            page.overlay.append(dialog)
            dialog.open = True
            page.update()
