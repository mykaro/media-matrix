import pytest
import os
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.worker_photocleaner import (
    format_size,
    is_corrupted_fast,
    check_video,
    worker_task,
    fast_scandir_size,
    PhotoCleanerWorker
)

def test_format_size():
    assert format_size(500) == "500.00 B"
    assert format_size(1024) == "1.00 KB"
    assert format_size(1024 * 1024 * 1.5) == "1.50 MB"

@patch('core.worker_photocleaner.Image.open')
def test_is_corrupted_fast(mock_image_open):
    # Test file size 0
    assert is_corrupted_fast("test.jpg", 0) is True

    # Test valid image
    mock_img = MagicMock()
    mock_image_open.return_value.__enter__.return_value = mock_img
    assert is_corrupted_fast("test.jpg", 1024) is False
    mock_img.verify.assert_called_once()

    # Test corrupted image (raises exception)
    mock_img.verify.side_effect = Exception("Corrupted")
    assert is_corrupted_fast("bad.jpg", 1024) is True

@patch('core.worker_photocleaner.cv2.VideoCapture')
def test_check_video(mock_video_capture):
    mock_cap = MagicMock()
    mock_video_capture.return_value = mock_cap

    # Test corrupted video
    mock_cap.isOpened.return_value = False
    assert check_video("bad.mp4", {}) == "corrupted"

    # Test low resolution video
    mock_cap.isOpened.return_value = True
    mock_cap.get.side_effect = lambda prop: {
        3: 500, # CAP_PROP_FPS (fake mapping for simplicity)
        7: 100, # CAP_PROP_FRAME_COUNT
        1: 640, # CAP_PROP_FRAME_WIDTH
        4: 480  # CAP_PROP_FRAME_HEIGHT
    }.get(prop, 0)
    assert check_video("lowres.mp4", {'vid_resolution_w': 800, 'vid_resolution_h': 600}) == "low_res_video"

    # Test short video
    mock_cap.get.side_effect = lambda prop: {
        5: 30,  # fps
        7: 60,  # 2 seconds
        3: 1920,
        4: 1080
    }.get(prop, 0)
    assert check_video("short.mp4", {'vid_min_duration': 5.0}) == "short_video"

@patch('core.worker_photocleaner._perform_move')
@patch('core.worker_photocleaner.check_video')
def test_worker_task_video(mock_check_video, mock_perform_move):
    mock_check_video.return_value = "short_video"
    params = {}
    target_dirs = {'short_video': '/trash/short', 'corrupted': '/trash/corrupted'}

    
    result = worker_task(("test.mp4", 1000, params, target_dirs))
    
    assert result["status"] == "short_video"
    assert result["target"] == os.path.join('/trash/short', 'test.mp4')
    mock_perform_move.assert_called_once_with(result)

@patch('core.worker_photocleaner._perform_move')
@patch('core.worker_photocleaner.is_corrupted_fast')
def test_worker_task_photo_corrupted(mock_is_corrupted, mock_perform_move):
    mock_is_corrupted.return_value = True
    params = {'check_corrupted': True}
    target_dirs = {'corrupted': '/trash/corrupted'}
    
    result = worker_task(("test.jpg", 1000, params, target_dirs))
    
    assert result["status"] == "corrupted"
    assert result["target"] == os.path.join('/trash/corrupted', 'test.jpg')
    mock_perform_move.assert_called_once_with(result)

@patch('core.worker_photocleaner._perform_move')
@patch('core.worker_photocleaner.load_grayscale_image')
@patch('core.worker_photocleaner.cv2.Laplacian')
def test_worker_task_photo_blurry(mock_laplacian, mock_load_image, mock_perform_move):
    mock_load_image.return_value = MagicMock()
    mock_laplacian.return_value.var.return_value = 50 # below threshold 100
    
    params = {'check_blur': True, 'blur_threshold': 100}
    target_dirs = {'blurry': '/trash/blurry'}
    
    result = worker_task(("test.jpg", 1000, params, target_dirs))
    
    assert result["status"] == "blurry"
    assert result["target"] == os.path.join('/trash/blurry', 'test.jpg')
    mock_perform_move.assert_called_once_with(result)

def test_photo_cleaner_worker_init():
    worker = PhotoCleanerWorker(lambda *args: None, lambda *args: None, lambda *args: None)
    assert not worker._stop_event.is_set()
    worker.stop()
    assert worker._stop_event.is_set()

@patch('core.worker_photocleaner.fast_scandir_size')
@patch('core.worker_photocleaner.multiprocessing.Pool')
def test_photo_cleaner_worker_clean(mock_pool_class, mock_scandir):
    # Mock scandir
    mock_scandir.return_value = [("file1.jpg", 100), ("file2.mp4", 200)]
    
    # Mock pool and imap_unordered
    mock_pool = MagicMock()
    mock_pool_class.return_value = mock_pool
    mock_pool.imap_unordered.return_value = [
        {"status": "ok", "size": 100, "path": "file1.jpg", "target": None},
        {"status": "corrupted", "size": 200, "path": "file2.mp4", "target": "/trash/corrupted/file2.mp4"}
    ]
    
    progress_cb = MagicMock()
    log_cb = MagicMock()
    finished_cb = MagicMock()
    
    worker = PhotoCleanerWorker(progress_cb, log_cb, finished_cb)
    worker.clean("/source", "/trash", {'check_corrupted': True})
    
    # Check if callbacks were called
    assert log_cb.call_count >= 2
    assert finished_cb.call_count == 1
    # 1 item found as bad out of 2 total
    finished_cb.assert_called_with(1, 200, pytest.approx(0, abs=1))
