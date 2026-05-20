import pytest
import os
from pathlib import Path
import hashlib
from unittest.mock import patch, MagicMock

# Add src to sys.path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.worker_twinfinder import ExactHash, get_file_md5, process_single_file, get_unique_path, DisjointSetUnion, TwinFinderWorker

def test_exact_hash_equality():
    h1 = ExactHash("abc123")
    h2 = ExactHash("abc123")
    h3 = ExactHash("def456")
    
    assert h1 == h2
    assert h1 != h3
    assert (h1 - h2) == 0
    assert (h1 - h3) == 9999

def test_exact_hash_string():
    h = ExactHash("test_hash")
    assert str(h) == "MD5:test_hash"

@patch("builtins.open")
def test_get_file_md5(mock_open):
    # Mock file content
    mock_file = MagicMock()
    # We want to simulate two blocks of data, then an empty block
    mock_file.read.side_effect = [b"hello", b"world", b""]
    
    # iter(lambda: f.read(4096 * 1024), b"")
    # Actually, my mock should return b"" when it's done.
    # The code uses: for chunk in iter(lambda: f.read(4096 * 1024), b""):
    
    mock_open.return_value.__enter__.return_value = mock_file
    
    with patch("hashlib.md5") as mock_md5:
        m = MagicMock()
        mock_md5.return_value = m
        
        result = get_file_md5("dummy.path")
        
        # Verify update was called with chunks
        assert m.update.call_count == 2
        m.hexdigest.assert_called_once()

@patch("PIL.Image.open")
@patch("imagehash.phash")
@patch("os.path.getsize")
def test_process_single_file_image(mock_getsize, mock_phash, mock_image_open):
    mock_getsize.return_value = 1024
    mock_phash.return_value = "dummy_hash"
    
    file_info = {'path': 'test.jpg', 'name': 'test.jpg'}
    
    # Mock image size
    mock_image = MagicMock()
    mock_image.size = (800, 600)
    mock_image_open.return_value.__enter__.return_value = mock_image
    
    result = process_single_file(file_info)
    
    assert result['name'] == 'test.jpg'
    assert result['hash'] == 'dummy_hash'
    assert result['size'] == 1024
    assert result['resolution'] == 800 * 600
    assert result['error'] is None

@patch('core.worker_twinfinder.os.path.exists')
def test_get_unique_path(mock_exists):
    mock_exists.side_effect = [True, True, False]
    
    res = get_unique_path("/dir", "file.jpg")
    assert res == os.path.join("/dir", "file (2).jpg")

def test_disjoint_set_union():
    dsu = DisjointSetUnion(5)
    dsu.union(0, 1)
    dsu.union(1, 2)
    dsu.union(3, 4)
    
    assert dsu.find(0) == dsu.find(2)
    assert dsu.find(3) == dsu.find(4)
    assert dsu.find(0) != dsu.find(3)

def test_twinfinder_worker_init():
    worker = TwinFinderWorker("/src", 0, False, 0, MagicMock(), MagicMock(), MagicMock())
    assert not worker._stop_event.is_set()
    worker.stop()
    assert worker._stop_event.is_set()

@patch('core.worker_twinfinder.os.scandir')
@patch('multiprocessing.Pool')
@patch('core.worker_twinfinder.os.makedirs')
def test_twinfinder_worker_analyze(mock_makedirs, mock_pool_class, mock_scandir):
    # Mock scandir
    mock_entry1 = MagicMock()
    mock_entry1.is_dir.return_value = False
    mock_entry1.is_file.return_value = True
    mock_entry1.name = "file1.jpg"
    mock_entry1.path = "/src/file1.jpg"
    mock_entry1.stat.return_value.st_size = 1000
    
    mock_scandir.return_value.__enter__.return_value = [mock_entry1]
    
    # Mock Pool
    mock_pool = MagicMock()
    mock_pool_class.return_value = mock_pool
    mock_pool.imap_unordered.return_value = [
        {
            'name': 'file1.jpg',
            'path': '/src/file1.jpg',
            'hash': ExactHash('123'),
            'size': 1000,
            'resolution': 100,
            'error': None
        }
    ]
    
    progress_cb = MagicMock()
    log_cb = MagicMock()
    finished_cb = MagicMock()
    
    worker = TwinFinderWorker("/src", 0, False, 0, progress_cb, log_cb, finished_cb)
    worker._analyze()
    
    assert log_cb.call_count > 0
    assert progress_cb.call_count > 0
