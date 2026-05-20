import os
import re
import shutil
import logging
import time
import multiprocessing
import threading
from datetime import datetime
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Callable, Any, Final, Optional

from ui.i18n import i18n

logger = logging.getLogger(__name__)

# File extension constants
PHOTO_EXT: Final[set[str]] = {'.jpg', '.jpeg', '.png', '.heic', '.webp', '.tiff', '.tif', '.bmp', '.gif', '.cr2', '.nef', '.arw', '.dng', '.orf', '.rw2', '.pef', '.srw', '.raf'}
VIDEO_EXT: Final[set[str]] = {'.mp4', '.mov', '.avi', '.mkv', '.3gp', '.m4v', '.wmv', '.mts', '.m2ts'}

DATE_PATTERNS: Final[list[re.Pattern]] = [
    re.compile(r'(\d{4})[_\-\.](\d{2})[_\-\.](\d{2})'),
    re.compile(r'(\d{4})(\d{2})(\d{2})'),
    re.compile(r'(\d{2})[_\-\.](\d{2})[_\-\.](\d{4})'),
]

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
        import pillow_heif
        pillow_heif.register_heif_opener()
    except ImportError:
        pass

def extract_date_from_file(filepath: str, use_fallback: bool = False) -> tuple[str, Optional[datetime], Optional[str], bool]:
    """
    Extracts file creation date from EXIF, filename, or system metadata.
    
    Returns:
        tuple[path, date, detection_method, is_screenshot]
    """
    path = Path(filepath)
    ext = path.suffix.lower()
    name = path.stem

    dt: Optional[datetime] = None
    method: Optional[str] = None
    is_screenshot: bool = False

    name_lower = name.lower()
    screenshot_keywords = {'screenshot', 'screen_', 'screen-', 'capture', 'snip'}
    if any(kw in name_lower for kw in screenshot_keywords):
        is_screenshot = True

    # Step 1: EXIF for photos
    if ext in {'.jpg', '.jpeg', '.png', '.heic', '.webp', '.tiff', '.tif'}:
        dt, method, is_screenshot_from_ex = _extract_from_exif(filepath)
        if is_screenshot_from_ex:
            is_screenshot = True
        
        # PNG without EXIF is often a screenshot
        if dt is None and ext == '.png':
            is_screenshot = True

    # Step 2: Video metadata
    if dt is None and ext in VIDEO_EXT:
        dt, method = _extract_from_video(filepath)

    # Step 3: Regex patterns from filename
    if dt is None:
        dt, method = _extract_from_name_patterns(name)

    # Step 4: Timestamp in filename (e.g. WhatsApp, Telegram)
    if dt is None:
        dt, method = _extract_from_timestamp(name)

    # Step 5: OS date fallback
    if dt is None and use_fallback:
        try:
            mtime = os.path.getmtime(filepath)
            parsed_dt = datetime.fromtimestamp(mtime)
            if 1970 <= parsed_dt.year <= 2100:
                dt = parsed_dt
                method = 'os_date'
        except Exception:
            pass

    return (filepath, dt, method, is_screenshot)

def _extract_from_exif(filepath: str) -> tuple[Optional[datetime], Optional[str], bool]:
    """Internal function for EXIF extraction."""
    from PIL import Image
    from PIL.ExifTags import TAGS
    
    dt = None
    method = None
    is_screenshot = False
    has_camera_info = False
    
    try:
        with Image.open(filepath) as img:
            exif_data = img._getexif() if hasattr(img, '_getexif') else img.getexif()  # type: ignore
            if exif_data:
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    
                    if tag in ('Make', 'Model', 'FNumber', 'ExposureTime', 'ISOSpeedRatings', 'FocalLength'):
                        has_camera_info = True
                    
                    if tag in ('Software', 'UserComment') and 'screenshot' in str(value).lower():
                        is_screenshot = True
                            
                    if dt is None and tag in ('DateTimeOriginal', 'DateTime', 'DateTimeDigitized'):
                        try:
                            val_str = str(value).replace('\x00', '').strip()
                            parsed_dt = datetime.strptime(val_str, '%Y:%m:%d %H:%M:%S')
                            if parsed_dt.year > 1970:
                                dt = parsed_dt
                                method = 'exif'
                        except (ValueError, TypeError):
                            pass
    except Exception:
        pass
        
    if not has_camera_info and Path(filepath).suffix.lower() == '.png':
        is_screenshot = True
        
    return dt, method, is_screenshot

def _extract_from_video(filepath: str) -> tuple[Optional[datetime], Optional[str]]:
    """Internal function for extracting video metadata."""
    try:
        from hachoir.parser import createParser
        from hachoir.metadata import extractMetadata
        parser = createParser(filepath)
        if parser:
            with parser:
                metadata = extractMetadata(parser)
                if metadata:
                    for attr in ('creation_date', 'last_modification'):
                        val = metadata.get(attr)
                        if val and hasattr(val, 'year') and val.year > 1970:
                            return datetime(val.year, val.month, val.day, 
                                            getattr(val, 'hour', 0), 
                                            getattr(val, 'minute', 0), 
                                            getattr(val, 'second', 0)), 'exif'
    except Exception:
        pass
    return None, None

def _extract_from_name_patterns(name: str) -> tuple[Optional[datetime], Optional[str]]:
    """Search for date in filename by regex patterns."""
    for pattern in DATE_PATTERNS:
        m = pattern.search(name)
        if m:
            groups = m.groups()
            try:
                # Determine format: YYYY MM DD or DD MM YYYY
                if len(groups[0]) == 4:
                    y, mo, d = int(groups[0]), int(groups[1]), int(groups[2])
                else:
                    d, mo, y = int(groups[0]), int(groups[1]), int(groups[2])
                
                if 1970 <= y <= 2100 and 1 <= mo <= 12 and 1 <= d <= 31:
                    return datetime(y, mo, d), 'name'
            except (ValueError, IndexError):
                continue
    return None, None

def _extract_from_timestamp(name: str) -> tuple[Optional[datetime], Optional[str]]:
    """Search for Unix Timestamp in filename."""
    ts_match = re.search(r'(?:^|[^0-9])(1[4-8]\d{8,14})(?:[^0-9]|$)', name)
    if ts_match:
        ts_str = ts_match.group(1)
        try:
            ts_val = int(ts_str)
            parsed_dt = None
            if len(ts_str) == 10:
                parsed_dt = datetime.fromtimestamp(ts_val)
            elif len(ts_str) == 13:
                parsed_dt = datetime.fromtimestamp(ts_val / 1000.0)
            elif len(ts_str) == 16:
                parsed_dt = datetime.fromtimestamp(ts_val / 1000000.0)
            
            if parsed_dt and 1970 <= parsed_dt.year <= 2100:
                return parsed_dt, 'name'
        except (ValueError, OSError):
            pass
    return None, None

def build_dest_folder(dt: datetime, structure: str, base_out: str) -> str:
    """Builds path to the destination folder according to settings."""
    y, m = dt.year, dt.month
    months = i18n.get_months()
    month_name = months.get(m, str(m))
    if structure == 'nested':
        # e.g. 2025/January/
        return os.path.join(base_out, str(y), month_name)
    else:  # 'flat'
        # e.g. 2025_January/
        return os.path.join(base_out, f'{y}_{month_name}')

def move_file(args: tuple[str, str, str]) -> tuple[str, Optional[str], Optional[str]]:
    """Moves a file (used in process pool)."""
    src, dest_folder, new_name = args
    os.makedirs(dest_folder, exist_ok=True)
    
    dest_path = Path(dest_folder) / new_name
    
    # Resolve filename conflicts
    if dest_path.exists():
        stem = dest_path.stem
        suffix = dest_path.suffix
        counter = 1
        while (Path(dest_folder) / f'{stem}_{counter}{suffix}').exists():
            counter += 1
        dest_path = Path(dest_folder) / f'{stem}_{counter}{suffix}'
        
    for attempt in range(4):
        try:
            shutil.move(src, str(dest_path))
            return src, str(dest_path), None
        except PermissionError:
            if attempt < 3:
                time.sleep(0.5)
            else:
                return src, None, i18n.t("w.sort.file_busy")
        except Exception as e:
            logger.error(f"Failed to move file {src} to {dest_path}: {str(e)}")
            return src, None, str(e)
            
    return src, None, i18n.t("w.sort.unknown_error")

class PhotoSorterWorker:
    """Worker class for background photo and video sorting."""

    def __init__(self,
                 progress_callback: Callable[[int, int, float], None],
                 log_callback: Callable[[str, str], None],
                 analysis_finished_callback: Callable[[list[Any], float], None],
                 sort_finished_callback: Callable[[int, int, list[Any], float], None]) -> None:
        
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        self.analysis_finished_callback = analysis_finished_callback
        self.sort_finished_callback = sort_finished_callback
        self._stop_event = threading.Event()

    def stop(self) -> None:
        """Sends a stop signal."""
        self._stop_event.set()

    def analyze(self, src_folder: str, allowed_ext: set[str], use_fallback: bool) -> None:
        """Scans the folder and determines dates for each file with guaranteed UI updates."""
        logger.info(f"Starting photo analysis in: {src_folder}")
        self._stop_event.clear()
        t_start = time.perf_counter()
        results: list[Any] = []
        
        try:
            files = [
                str(p) for p in Path(src_folder).rglob('*')
                if p.is_file() and p.suffix.lower() in allowed_ext
            ]
            
            total = len(files)
            if total == 0:
                self.log_callback(i18n.t("w.sort.no_files"), "#f59e0b")
                return

            self.log_callback(i18n.t("w.sort.found").format(n=f"{total:,}"), "#555555")
            self.progress_callback(0, total, 0.0)

            cpu_count = max(1, multiprocessing.cpu_count() or 1)
            done = 0
            executor_start_time = time.perf_counter()

            from functools import partial
            from concurrent.futures import ThreadPoolExecutor, as_completed
            func = partial(extract_date_from_file, use_fallback=use_fallback)
            
            with ThreadPoolExecutor(max_workers=cpu_count, initializer=_set_thread_low_priority) as pool:
                futures = {pool.submit(func, f): f for f in files}
                for future in as_completed(futures):
                    if self._stop_event.is_set():
                        for f in futures:
                            f.cancel()
                        self.log_callback(i18n.t("w.sort.analysis_stopped"), "#ef4444")
                        return
                    
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        logger.error(f"Error in future result: {e}")
                        continue
                        
                    done += 1
                    if done % 10 == 0 or done == total:
                        elapsed = time.perf_counter() - executor_start_time
                        speed = done / elapsed if elapsed > 0 else 1
                        eta = (total - done) / speed
                        self.progress_callback(done, total, eta)

        except Exception as e:
            self.log_callback(f"❌ {str(e)}", "#ef4444")
            logger.exception("Critical error during analysis process")
        finally:
            elapsed = time.perf_counter() - t_start
            self.analysis_finished_callback(results, elapsed)

    def sort(self, results: list[Any], structure: str, out_folder: str, rename_files: bool, separate_screens: bool) -> None:
        """Physically moves files with guaranteed UI updates."""
        logger.info(f"Starting photo sorting into: {out_folder}")
        self._stop_event.clear()
        t_start = time.perf_counter()
        moved, errors = 0, []
        undated_count = 0
        
        try:
            tasks = []
            for filepath, dt, _, is_screenshot in results:
                path_obj = Path(filepath)
                
                if separate_screens and is_screenshot:
                    dest_dir = os.path.join(out_folder, i18n.t("folders.screenshots"))
                    new_fn = self._generate_new_name(path_obj, dt, rename_files)
                else:
                    if dt:
                        dest_dir = build_dest_folder(dt, structure, out_folder)
                        new_fn = self._generate_new_name(path_obj, dt, rename_files)
                    else:
                        dest_dir = os.path.join(out_folder, i18n.t("folders.undated"))
                        new_fn = path_obj.name
                        undated_count += 1
                        
                tasks.append((filepath, dest_dir, new_fn))

            total = len(tasks)
            if total == 0:
                return

            cpu_count = max(1, multiprocessing.cpu_count() or 1)
            done = 0
            executor_start_time = time.perf_counter()

            from concurrent.futures import ThreadPoolExecutor, as_completed
            with ThreadPoolExecutor(max_workers=cpu_count, initializer=_set_thread_low_priority) as pool:
                futures = {pool.submit(move_file, task): task for task in tasks}
                for future in as_completed(futures):
                    if self._stop_event.is_set():
                        for f in futures:
                            f.cancel()
                        self.log_callback(i18n.t("w.sort.sort_stopped"), "#ef4444")
                        return

                    try:
                        src, dest, err = future.result()
                    except Exception as e:
                        logger.error(f"Error in future result: {e}")
                        continue

                    if err:
                        errors.append((src, err))
                    else:
                        moved += 1
                        
                    done += 1
                    if done % 5 == 0 or done == total:
                        elapsed = time.perf_counter() - executor_start_time
                        speed = done / elapsed if elapsed > 0 else 1
                        eta = (total - done) / speed
                        self.progress_callback(done, total, eta)
        except Exception as e:
            self.log_callback(f"❌ {str(e)}", "#ef4444")
            logger.exception("Critical error during sorting process")
        finally:
            elapsed = time.perf_counter() - t_start
            self.sort_finished_callback(moved, undated_count, errors, elapsed)
            logger.info(f"Sorting finished: moved {moved} files, {len(errors)} errors")

    def _generate_new_name(self, path: Path, dt: Optional[datetime], rename: bool) -> str:
        """Generates a new filename based on date."""
        if rename and dt:
            return dt.strftime("%Y_%m_%d_%H%M%S") + path.suffix.lower()
        return path.name
