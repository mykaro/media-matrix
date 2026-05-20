import pytest
import os
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src to sys.path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.worker_photosorter import extract_date_from_file, build_dest_folder, PhotoSorterWorker, move_file

def test_build_dest_folder_nested():
    dt = datetime(2025, 1, 15)
    # Mock i18n to return a fixed month name
    with patch('core.worker_photosorter.i18n.get_months', return_value={1: "January"}):
        path = build_dest_folder(dt, 'nested', 'C:/output')
        expected = os.path.join('C:/output', '2025', 'January')
        assert path == expected

def test_build_dest_folder_flat():
    dt = datetime(2025, 5, 20)
    with patch('core.worker_photosorter.i18n.get_months', return_value={5: "May"}):
        path = build_dest_folder(dt, 'flat', 'C:/output')
        expected = os.path.join('C:/output', '2025_May')
        assert path == expected

@patch('os.path.getmtime')
def test_extract_date_from_file_name_pattern(mock_mtime):
    # Test file with date in name: 2023-12-25_image.jpg
    filepath = "C:/photos/2023-12-25_image.jpg"
    
    # We mock exif to return None
    with patch('core.worker_photosorter._extract_from_exif', return_value=(None, None, False)):
        with patch('core.worker_photosorter._extract_from_video', return_value=(None, None)):
            path, dt, method, is_screenshot = extract_date_from_file(filepath)
            
            assert dt is not None
            assert dt.year == 2023
            assert dt.month == 12
            assert dt.day == 25
            assert method == 'name'

def test_generate_new_name_no_rename():
    worker = PhotoSorterWorker(MagicMock(), MagicMock(), MagicMock(), MagicMock())
    path = Path("image.jpg")
    dt = datetime(2025, 1, 1)
    
    new_name = worker._generate_new_name(path, dt, rename=False)
    assert new_name == "image.jpg"

def test_generate_new_name_with_rename():
    worker = PhotoSorterWorker(MagicMock(), MagicMock(), MagicMock(), MagicMock())
    path = Path("my_photo.PNG")
    dt = datetime(2024, 10, 5, 14, 30, 5)
    
    new_name = worker._generate_new_name(path, dt, rename=True)
    assert new_name == "2024_10_05_143005.png"

@patch('core.worker_photosorter.shutil.move')
@patch('core.worker_photosorter.os.makedirs')
@patch('core.worker_photosorter.Path.exists')
def test_move_file(mock_exists, mock_makedirs, mock_move):
    mock_exists.return_value = False
    
    src = "src.jpg"
    dest_folder = "out_dir"
    new_name = "dst.jpg"
    
    res_src, res_dest, err = move_file((src, dest_folder, new_name))
    
    assert res_src == src
    assert res_dest == os.path.join(dest_folder, new_name)
    assert err is None
    mock_makedirs.assert_called_once_with(dest_folder, exist_ok=True)
    mock_move.assert_called_once()

@patch('core.worker_photosorter.multiprocessing.Pool')
@patch('core.worker_photosorter.Path.rglob')
def test_photosorter_worker_analyze(mock_rglob, mock_pool_class):
    # Mock file discovery
    mock_file1 = MagicMock()
    mock_file1.is_file.return_value = True
    mock_file1.suffix.lower.return_value = '.jpg'
    mock_file1.__str__.return_value = "file1.jpg"  # type: ignore
    
    mock_rglob.return_value = [mock_file1]
    
    # Mock pool
    mock_pool = MagicMock()
    mock_pool_class.return_value = mock_pool
    # returns tuple: (filepath, dt, method, is_screenshot)
    mock_pool.imap_unordered.return_value = [
        ("file1.jpg", datetime(2025, 1, 1), "exif", False)
    ]
    
    analysis_cb = MagicMock()
    worker = PhotoSorterWorker(MagicMock(), MagicMock(), analysis_cb, MagicMock())
    
    worker.analyze("src", {'.jpg'}, False)
    
    analysis_cb.assert_called_once()
    results, elapsed = analysis_cb.call_args[0]
    assert len(results) == 1
    assert results[0][0] == "file1.jpg"

@patch('core.worker_photosorter.multiprocessing.Pool')
def test_photosorter_worker_sort(mock_pool_class):
    mock_pool = MagicMock()
    mock_pool_class.return_value = mock_pool
    # returns tuple: src, dest, err
    mock_pool.imap_unordered.return_value = [
        ("file1.jpg", "out/file1.jpg", None),
        ("file2.jpg", None, "error")
    ]
    
    sort_cb = MagicMock()
    worker = PhotoSorterWorker(MagicMock(), MagicMock(), MagicMock(), sort_cb)
    
    results = [
        ("file1.jpg", datetime(2025, 1, 1), "exif", False),
        ("file2.jpg", None, None, False)
    ]
    
    worker.sort(results, "flat", "out", False, False)
    
    sort_cb.assert_called_once()
    moved, undated, errors, elapsed = sort_cb.call_args[0]
    assert moved == 1
    assert undated == 1 # file2 had None date
    assert len(errors) == 1

