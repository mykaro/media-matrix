import os
import shutil
import time
import logging
import threading
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Callable, Any, Final, Optional, Dict, List, Set, Tuple
from dataclasses import dataclass
from pathlib import Path
from collections import defaultdict
import hashlib

logger = logging.getLogger(__name__)

from ui.i18n import i18n

# Constants
IMAGE_EXTENSIONS: Final[set[str]] = {
    '.heic', '.jpg', '.jpeg', '.png', '.webp', '.tiff', '.tif', '.bmp', '.gif',
    '.cr2', '.nef', '.arw', '.dng', '.orf', '.rw2', '.pef', '.srw', '.raf'
}
VIDEO_EXTENSIONS: Final[set[str]] = {'.mp4', '.mov', '.m4v', '.avi', '.mkv', '.wmv', '.webm'}
SUPPORTED_EXTENSIONS: Final[set[str]] = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS

class ExactHash:
    """Class for storing exact MD5 hash of a file. Supports subtraction syntax
    for compatibility with imagehash comparison logic."""
    def __init__(self, hexdigest: str):
        self.hexdigest = hexdigest
        
    def __sub__(self, other) -> int:
        if not isinstance(other, ExactHash):
            return 9999
        return 0 if self.hexdigest == other.hexdigest else 9999

    def __str__(self):
        return f"MD5:{self.hexdigest}"
    
    def __repr__(self):
        return self.__str__()
    
    def __hash__(self):
        return hash(self.hexdigest)
    
    def __eq__(self, other):
        return isinstance(other, ExactHash) and self.hexdigest == other.hexdigest

def _set_thread_low_priority():
    """Sets the current thread to below normal priority on Windows."""
    import sys
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.kernel32.SetThreadPriority(ctypes.windll.kernel32.GetCurrentThread(), -1)
        except Exception:
            pass
    try:
        from pillow_heif import register_heif_opener
        register_heif_opener()
    except ImportError:
        pass

def get_file_md5(file_path: str) -> str:
    """Calculates exact MD5 hash of a file, reading it in chunks to save memory."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        # Read in chunks of 4 MB
        for chunk in iter(lambda: f.read(4096 * 1024), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

@dataclass
class FileInfo:
    """Class for storing information about an analyzed image."""
    name: str
    path: str
    hash_val: Optional[Any] = None
    size: int = 0
    resolution: int = 0
    error: Optional[str] = None

def process_single_file(file_info: dict[str, Any]) -> dict[str, Any]:
    """
    Processes a single media file: calculates hash, size, and resolution.
    """
    import imagehash
    from PIL import Image
    
    file_path = file_info['path']
    file_name = file_info['name']
    skip_hashing = file_info.get('skip_hashing', False)
    
    try:
        file_suffix = Path(file_path).suffix.lower()
        file_size = os.path.getsize(file_path)
        
        if file_suffix in VIDEO_EXTENSIONS:
            if skip_hashing:
                # Unique video, do not read it completely
                # Use path as unique identifier so it does not match anything
                v_hash = ExactHash(hashlib.md5(file_path.encode()).hexdigest() + "_unique")
            else:
                v_hash = ExactHash(get_file_md5(file_path))
                
            return {
                'name': file_name, 
                'path': file_path, 
                'hash': v_hash, 
                'size': file_size, 
                'resolution': 0,
                'error': None
            }
        else:
            with Image.open(file_path) as img:
                # Save original dimensions before applying draft
                width, height = img.size
                
                # Optimization for JPEG: decode only thumbnail (phash needs 32x32)
                if file_suffix in {'.jpg', '.jpeg'}:
                    # draft allows decoder to skip redundant data
                    img.draft('L', (32, 32))
                
                # imagehash converts to 'L' anyway, so convert('RGB') is not needed
                v_hash = imagehash.phash(img)
                
                return {
                    'name': file_name, 
                    'path': file_path, 
                    'hash': v_hash, 
                    'size': file_size, 
                    'resolution': width * height,
                    'error': None
                }
    except Exception as e:
        logger.error(f"Error processing file {file_path}: {str(e)}")
        return {'name': file_name, 'error': str(e), 'path': file_path}

def format_size(bytes_val: float) -> str:
    """Formats byte size into readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.2f} PB"

def get_unique_path(directory: str, filename: str) -> str:
    """
    Generates a unique file path in a directory, appending (N) suffix if needed.
    This allows preserving original file names without overwriting them.
    """
    base, extension = os.path.splitext(filename)
    target_path = os.path.join(directory, filename)
    counter = 1
    
    while os.path.exists(target_path):
        target_path = os.path.join(directory, f"{base} ({counter}){extension}")
        counter += 1
        
    return target_path

class DisjointSetUnion:
    """Union-Find structure for correct transitive clustering of duplicates."""
    def __init__(self, n: int):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        a, b = self.find(a), self.find(b)
        if a == b:
            return
        if self.rank[a] < self.rank[b]:
            a, b = b, a
        self.parent[b] = a
        if self.rank[a] == self.rank[b]:
            self.rank[a] += 1

class TwinFinderWorker:
    """Logic for background duplicate image search."""

    def __init__(self, 
                 source_folder: str, 
                 threshold: int, 
                 use_look_ahead: bool, 
                 look_ahead_val: int,
                 progress_callback: Callable[[int, int, float, str, str, int], None],
                 log_callback: Callable[[str], None],
                 finished_callback: Callable[[], None]) -> None:
        
        self.source_folder = source_folder
        self.threshold = threshold
        self.use_look_ahead = use_look_ahead
        self.look_ahead_val = look_ahead_val
        
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        self.finished_callback = finished_callback
        
        self._stop_event = threading.Event()
    
    def stop(self) -> None:
        """Sends a signal to stop the worker."""
        self._stop_event.set()

    def run(self) -> None:
        """Main execution method running in a separate thread."""
        logger.info(f"Starting TwinFinder analysis in: {self.source_folder}")
        try:
            self._analyze()
        except Exception as e:
            self.log_callback(f"❌ {i18n.t('w.twin.critical').format(err=str(e))}")
            logger.exception("Critical error during TwinFinder process")
        finally:
            self.finished_callback()

    def _analyze(self) -> None:
        """Main process of analyzing and removing duplicates."""
        source_name = os.path.basename(os.path.normpath(self.source_folder))
        parent_dir = os.path.dirname(os.path.normpath(self.source_folder))
        dst_folder: str = os.path.join(parent_dir, f"{i18n.t('folders.duplicates_prefix')}{source_name}")
        
        os.makedirs(dst_folder, exist_ok=True)

        self.log_callback(i18n.t("w.twin.start").format(path=self.source_folder))
        self.log_callback(i18n.t("w.twin.dest").format(path=dst_folder))
        self.log_callback(i18n.t("w.twin.threshold").format(val=self.threshold))

        # FILE SEARCH (Optimized via scandir)
        self.progress_callback(0, 0, 0, i18n.t("w.twin.searching"), "", 0)
        files_to_process: list[dict[str, Any]] = []
        video_sizes = defaultdict(list)
        
        # Recursive traversal via scandir
        def scan_dir(path: str):
            if self._stop_event.is_set():
                return
            try:
                with os.scandir(path) as it:
                    for entry in it:
                        if self._stop_event.is_set():
                            break
                        # follow_symlinks=False is important to prevent infinite loops
                        # in junction points on Windows (e.g. Application Data)
                        if entry.is_dir(follow_symlinks=False):
                            # Ignore results folder
                            if entry.name == f"{i18n.t('folders.duplicates_prefix')}{source_name}":
                                continue
                            scan_dir(entry.path)
                        elif entry.is_file(follow_symlinks=False):
                            ext = Path(entry.name).suffix.lower()
                            if ext in SUPPORTED_EXTENSIONS:
                                f_info = {
                                    'path': entry.path,
                                    'name': entry.name,
                                    'size': entry.stat(follow_symlinks=False).st_size,
                                    'ext': ext
                                }
                                files_to_process.append(f_info)
                                if ext in VIDEO_EXTENSIONS:
                                    video_sizes[f_info['size']].append(f_info)
            except Exception as e:
                self.log_callback(f"⚠️ Access error to {path}: {e}")
                logger.warning(f"Access error to {path}: {e}")

        scan_dir(self.source_folder)

        total_files: int = len(files_to_process)
        if total_files == 0 or self._stop_event.is_set():
            self.log_callback(i18n.t("w.twin.no_files"))
            return

        # Pre-filter for videos: if size is unique, do not calculate MD5
        for size, v_list in video_sizes.items():
            if len(v_list) == 1:
                v_list[0]['skip_hashing'] = True

        total_files: int = len(files_to_process)
        if total_files == 0 or self._stop_event.is_set():
            self.log_callback(i18n.t("w.twin.no_files"))
            return

        self.log_callback(i18n.t("w.twin.found").format(n=total_files))

        # STEP 1: ANALYSIS (Multiprocessing)
        all_photos: list[dict[str, Any]] = []
        total_scanned_size: int = 0
        hashing_errors: int = 0
        start_time: float = time.perf_counter()

        from concurrent.futures import ThreadPoolExecutor, as_completed
        workers = max(1, os.cpu_count() or 1)
        
        with ThreadPoolExecutor(max_workers=workers, initializer=_set_thread_low_priority) as pool:
            futures = {pool.submit(process_single_file, f): f for f in files_to_process}
            for index, future in enumerate(as_completed(futures), 1):
                if self._stop_event.is_set():
                    for f in futures:
                        f.cancel()
                    self.log_callback(i18n.t("w.twin.stopped"))
                    return

                try:
                    result = future.result()
                except Exception as e:
                    result: dict[str, Any] = {'error': str(e), 'name': futures[future].get('name', 'unknown')}

                if result.get('error') is None:
                    all_photos.append(result)
                    total_scanned_size += int(result.get('size', 0))
                else:
                    hashing_errors += 1

                if index % 5 == 0 or index == total_files:
                    elapsed = time.perf_counter() - start_time
                    speed = index / elapsed if elapsed > 0 else 1
                    eta = (total_files - index) / speed
                    self.progress_callback(index, total_files, eta, result.get('name', ''), i18n.t("w.twin.step1"), 0)

        # STEP 2: COMPARISON
        self.log_callback(i18n.t("w.twin.hash_done"))
        
        moved_count: int = 0
        moved_size: int = 0
        moving_errors: int = 0
        compare_start: float = time.perf_counter()
        total_photos: int = len(all_photos)

        # Optimization for exact match (threshold == 0)
        if self.threshold == 0:
            groups = defaultdict(list)
            for photo in all_photos:
                groups[photo['hash']].append(photo)
            
            for index, (h_val, group) in enumerate(groups.items()):
                if self._stop_event.is_set(): break
                if len(group) > 1:
                    group.sort(key=lambda x: (x['resolution'], x['size']), reverse=True)
                    for dup in group[1:]:
                        target_path = "unknown"
                        try:
                            target_path = get_unique_path(dst_folder, dup['name'])
                            shutil.move(dup['path'], target_path)
                            moved_count += 1
                            moved_size += dup['size']
                        except Exception as e:
                            logger.error(f"Failed to move duplicate {dup['path']} to {target_path}: {str(e)}")
                            moving_errors += 1
                
                if index % 20 == 0:
                    self.progress_callback(index, len(groups), 0, group[0]['name'], i18n.t("w.twin.step2"), moved_count)
        else:
            all_photos.sort(key=lambda x: x['name'])
            look_ahead_window: int = self.look_ahead_val if self.use_look_ahead else total_photos
            
            if self.use_look_ahead:
                self.log_callback(i18n.t("w.twin.look_ahead_on").format(n=look_ahead_window))
            else:
                self.log_callback(i18n.t("w.twin.look_ahead_off").format(n=look_ahead_window))

            # Phase 1: Compare all pairs within the window and union via DSU
            dsu = DisjointSetUnion(total_photos)
            for i in range(total_photos):
                if self._stop_event.is_set():
                    break
                hash_i = all_photos[i]['hash']
                for j in range(i + 1, min(i + look_ahead_window, total_photos)):
                    hash_j = all_photos[j]['hash']
                    if isinstance(hash_i, ExactHash) != isinstance(hash_j, ExactHash):
                        continue
                    if (hash_i - hash_j) <= self.threshold:
                        dsu.union(i, j)
                
                if i % 20 == 0 or i == total_photos - 1:
                    elapsed_comp = time.perf_counter() - compare_start
                    speed_comp = (i + 1) / elapsed_comp if elapsed_comp > 0 else 1
                    eta_comp = (total_photos - i) / speed_comp
                    self.progress_callback(i + 1, total_photos, eta_comp, all_photos[i]['name'], i18n.t("w.twin.step2"), moved_count)

            # Phase 2: Extract groups from DSU and move duplicates
            groups: dict[int, list[dict[str, Any]]] = defaultdict(list)
            for i in range(total_photos):
                groups[dsu.find(i)].append(all_photos[i])

            for group in groups.values():
                if self._stop_event.is_set():
                    break
                if len(group) > 1:
                    group.sort(key=lambda x: (x['resolution'], x['size']), reverse=True)
                    for dup in group[1:]:
                        target_path = "unknown"
                        try:
                            target_path = get_unique_path(dst_folder, dup['name'])
                            shutil.move(dup['path'], target_path)
                            moved_count += 1
                            moved_size += dup['size']
                        except Exception as e:
                            logger.error(f"Failed to move duplicate {dup['path']} to {target_path}: {str(e)}")
                            moving_errors += 1

        # FINAL REPORT
        total_time: float = time.perf_counter() - start_time
        pct_saved = (moved_size / total_scanned_size * 100) if total_scanned_size > 0 else 0
        
        self.log_callback("\n" + "═"*45)
        self.log_callback(i18n.t("w.twin.report_header"))
        self.log_callback(i18n.t("w.twin.report_time").format(val=f"{total_time/60:.1f}"))
        self.log_callback(i18n.t("w.twin.report_total").format(size=format_size(total_scanned_size), n=total_files))
        self.log_callback(i18n.t("w.twin.report_moved").format(size=format_size(moved_size), pct=f"{pct_saved:.1f}", n=moved_count))
        
        if hashing_errors > 0 or moving_errors > 0:
            error_msg = i18n.t("w.twin.report_errors")
            parts = []
            if hashing_errors > 0: parts.append(f"{hashing_errors} {i18n.t('w.twin.error_read')}")
            if moving_errors > 0: parts.append(f"{moving_errors} {i18n.t('w.twin.error_move')}")
            self.log_callback(error_msg + " / ".join(parts))
            
        self.log_callback("═"*45)
        self.progress_callback(total_files, total_files, 0, i18n.t("w.twin.done_file"), i18n.t("w.twin.done_status"), moved_count)
        logger.info(f"TwinFinder finished: moved {moved_count} duplicates")
