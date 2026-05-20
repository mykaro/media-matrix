import pytest
import flet as ft
from unittest.mock import MagicMock
from flet.components.utils import _CURRENT_RENDERER

# Import all UI views to catch syntax and module-level attribute errors
from ui.sidebar import AppSidebar
from ui.view_twinfinder import TwinFinderView
from ui.view_photosorter import PhotoSorterView
from ui.view_photocleaner import PhotoCleanerView
from ui.components import Card, StatChip, PageHeader, RunButton, PrimaryButton

@pytest.fixture
def mock_page():
    """Returns a mocked Flet Page."""
    page = MagicMock(spec=ft.Page)
    page.session_id = "test_session"
    page.run_task = MagicMock()
    return page

@pytest.fixture(autouse=True)
def mock_renderer_context():
    """
    Mocks Flet's CURRENT_RENDERER context variable.
    Required for declarative components (@ft.component) in Flet 0.26+.
    """
    mock_r = MagicMock()
    # Newer Flet uses ContextVar to store the current renderer
    token = _CURRENT_RENDERER.set(mock_r)
    yield mock_r
    _CURRENT_RENDERER.reset(token)

def test_ui_imports_and_constants():
    """Test successful import of all UI modules."""
    assert True

def test_twinfinder_view_render(mock_page):
    """Smoke test for TwinFinderView."""
    view = TwinFinderView(mock_page)
    assert view is not None

def test_photosorter_view_render(mock_page):
    """Smoke test for PhotoSorterView."""
    view = PhotoSorterView(mock_page)
    assert view is not None

def test_photocleaner_view_render(mock_page):
    """Smoke test for PhotoCleanerView."""
    view = PhotoCleanerView(mock_page)
    assert view is not None

def test_sidebar_render():
    """Smoke test for AppSidebar."""
    sidebar = AppSidebar(nav_index=0, on_nav_change=lambda x: None)
    assert sidebar is not None

def test_common_components():
    """Test instantiation of common components."""
    StatChip(value="0", label="Test")
    PageHeader(title_white="W", title_green="G", description="D", stat_chips=[])
    RunButton(text="Run")
    PrimaryButton(text="Primary")
    Card(icon=ft.Icon(ft.Icons.ABC), title="Title")
