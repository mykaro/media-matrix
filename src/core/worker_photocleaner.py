import os
import shutil
import logging
import time
import multiprocessing
import threading
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Callable, Any, Generator, Optional, Final, TYPE_CHECKING

from ui.i18n import i18n

if TYPE_CHECKING:
    import numpy as np

logger = logging.getLogger(__name__)

# File extension constants
EXTENSIONS: Final[tuple[str, ...]] = (
    '.jpg', '.jpeg', '.png', '.heic', '.webp', '.tiff', '.tif', '.bmp', '.gif',
    '.mp4', '.mov', '.avi', '.mkv', '.3gp', '.m4v'
)

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

def format_size(bytes_size: float) -> str:
    """Formats size in bytes into readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.2f} PB"

def load_grayscale_image(file_path: str) -> Optional['np.ndarray']:
    """Loads image in grayscale with size optimization."""
    import cv2
    import numpy as np
    from PIL import Image

    ext = Path(file_path).suffix.lower()
    MAX_SIZE: Final = 800.0
    
    # Try fast loading via OpenCV for non-HEIC files
    if ext != '.heic':
        try:
            img_array = np.fromfile(file_path, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_GRAYSCALE)
            
            if img is not None:
                h, w = img.shape
                if max(h, w) > 1000:
                    scale = MAX_SIZE / max(h, w)
                    img = cv2.resize(img, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
                return img
        except Exception:
            pass

    # Fallback to PIL (especially for HEIC)
    try:
        with Image.open(file_path) as pil_img:
            pil_img.draft('L', (int(MAX_SIZE), int(MAX_SIZE)))
            pil_img = pil_img.convert('L')
            pil_img.thumbnail((int(MAX_SIZE), int(MAX_SIZE)), Image.Resampling.NEAREST)
            return np.array(pil_img)
    except Exception:
        return None

def is_corrupted_fast(file_path: str, file_size: int) -> bool:
    """Fast integrity check for an image file."""
    if file_size == 0:
        return True
        
    ext = Path(file_path).suffix.lower()
    from PIL import Image
    
    try:
        with Image.open(file_path) as img:
            img.verify()
    except Exception:
        return True

    return False

def check_video(file_path: str, params: dict[str, Any]) -> Optional[str]:
    """Analyzes video properties and returns filter status code."""
    import cv2
    import numpy as np
    try:
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            return "corrupted"

        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        duration = frame_count / fps if fps > 0 else 0.0

        # Resolution check
        if (width > 0 and width < params.get('vid_resolution_w', 0)) or \
           (height > 0 and height < params.get('vid_resolution_h', 0)):
            cap.release()
            return "low_res_video"

        # Duration check
        if duration > 0 and duration < params.get('vid_min_duration', 0):
            cap.release()
            return "short_video"

        # Optimized dark check (3 sample points: 20%, 50%, 80%)
        if params.get('vid_check_dark', False):
            total_brightness = 0.0
            samples = 0
            
            # Avoid edges (fades), take 3 representative sample points
            for factor in [0.2, 0.5, 0.8]:
                pos = int(frame_count * factor)
                cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
                ret, frame = cap.read()
                if ret:
                    # Calculate mean across all channels (faster than cvtColor)
                    total_brightness += np.mean(frame)
                    samples += 1
                    
            if samples > 0 and (total_brightness / samples) < params.get('dark_threshold', 30):
                cap.release()
                return "dark_video"
                
        cap.release()
    except Exception:
        return "corrupted"
        
    return None

def worker_task(data: tuple[str, int, dict[str, Any], dict[str, str]]) -> dict[str, Any]:
    """Atomic task for a single file (used in ProcessPoolExecutor)."""
    file_path, file_size, params, target_dirs = data
    file_name = os.path.basename(file_path)
    result = {"status": "ok", "size": file_size, "path": file_path, "target": None}
    
    ext = Path(file_path).suffix.lower()
    is_video = ext in {'.mp4', '.mov', '.avi', '.mkv', '.3gp', '.m4v'}

    try:
        if is_video:
            # For video, corruption check is integrated into check_video
            vid_status = check_video(file_path, params)
            if vid_status:
                # If status is corrupted, or another filter (low_res, etc.)
                # we move the file only if the corresponding option is enabled.
                # But for "corrupted", the check is usually always enabled when check_corrupted=True.
                if vid_status == "corrupted":
                    if params.get('check_corrupted', False):
                        result.update({"status": "corrupted", "target": os.path.join(target_dirs['corrupted'], file_name)})
                else:
                    # Other filters (blurry, low_res_video, etc. are handled below)
                    result.update({"status": vid_status, "target": os.path.join(target_dirs.get(vid_status, target_dirs['corrupted']), file_name)})
            
            if result["status"] != "ok":
                _perform_move(result)
                return result
        else:
            # Corruption check for photos
            if params.get('check_corrupted', False):
                if is_corrupted_fast(file_path, file_size):
                    result.update({"status": "corrupted", "target": os.path.join(target_dirs['corrupted'], file_name)})
                    _perform_move(result)
                    return result

            # Further analysis of valid images (blur, exposure, res)
            if params.get('check_blur', False) or params.get('check_exposure', False):
                img = load_grayscale_image(file_path)
                if img is not None:
                    # Blur
                    if params.get('check_blur', False):
                        import cv2
                        score = cv2.Laplacian(img, cv2.CV_64F).var()
                        if score < params.get('blur_threshold', 100):
                            result.update({"status": "blurry", "target": os.path.join(target_dirs['blurry'], file_name)})
                    
                    # Exposure
                    if result["status"] == "ok" and params.get('check_exposure', False):
                        import numpy as np
                        brightness = np.mean(img)
                        if brightness < params.get('dark_threshold', 30):
                            result.update({"status": "dark", "target": os.path.join(target_dirs['dark'], file_name)})
                        elif brightness > params.get('bright_threshold', 235):
                            result.update({"status": "bright", "target": os.path.join(target_dirs['bright'], file_name)})
                else:
                    if params.get('check_corrupted', False):
                        result.update({"status": "corrupted", "target": os.path.join(target_dirs['corrupted'], file_name)})
            
            # Photo resolution
            if result["status"] == "ok" and params.get('check_res', False):
                from PIL import Image
                with Image.open(file_path) as img_res:
                    w, h = img_res.size
                    if w < params.get('img_w', 800) or h < params.get('img_h', 600):
                        result.update({"status": "low_res", "target": os.path.join(target_dirs['low_res'], file_name)})
            
    except Exception:
        if params.get('check_corrupted', False):
            result.update({"status": "corrupted", "target": os.path.join(target_dirs['corrupted'], file_name)})
        
    _perform_move(result)
    return result

def _perform_move(result: dict[str, Any]) -> None:
    """Physical file move to the trash folder."""
    if result["status"] != "ok" and result["target"]:
        os.makedirs(os.path.dirname(result["target"]), exist_ok=True)
        try:
            # EAFP pattern
            os.replace(result["path"], result["target"])
        except OSError:
            try:
                shutil.move(result["path"], result["target"])
            except Exception as e:
                logger.error(f"Failed to move file {result['path']} to {result['target']}: {str(e)}")


def fast_scandir_size(dirname: str, extensions: tuple[str, ...]) -> Generator[tuple[str, int], None, None]:
    """Fast directory scan to collect files and their sizes."""
    subfolders = [dirname]
    while subfolders:
        current_folder = subfolders.pop(0)
        try:
            for entry in os.scandir(current_folder):
                if entry.is_dir(follow_symlinks=False):
                    if entry.name.startswith(i18n.t("folders.clean_prefix")):
                        continue
                    subfolders.append(entry.path)
                elif entry.is_file() and entry.name.lower().endswith(extensions):
                    yield entry.path, entry.stat().st_size
        except PermissionError:
            continue

class PhotoCleanerWorker:
    """Worker class for background media file cleaning."""

    def __init__(self,
                 progress_callback: Callable[[int, int, float, int], None],
                 log_callback: Callable[[str, str], None],
                 finished_callback: Callable[[int, int, float], None]) -> None:
        
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        self.finished_callback = finished_callback
        self._stop_event = threading.Event()

    def stop(self) -> None:
        """Sends a stop signal."""
        self._stop_event.set()

    def clean(self, source_dir: str, trash_base: str, params: dict[str, Any]) -> None:
        """Main cleaning method with guaranteed final callback invocation."""
        logger.info(f"Starting photo cleaning in: {source_dir}")
        self._stop_event.clear()
        t_start = time.perf_counter()
        found_count, found_size = 0, 0
        total_old_size = 0
        
        try:
            target_dirs = {
                'blurry': os.path.join(trash_base, i18n.t("folders.blurry")),
                'dark': os.path.join(trash_base, i18n.t("folders.dark")),
                'bright': os.path.join(trash_base, i18n.t("folders.bright")),
                'low_res': os.path.join(trash_base, i18n.t("folders.low_res")),
                'corrupted': os.path.join(trash_base, i18n.t("folders.corrupted")),
                'short_video': os.path.join(trash_base, i18n.t("folders.short_video")),
                'dark_video': os.path.join(trash_base, i18n.t("folders.dark_video")),
                'low_res_video': os.path.join(trash_base, i18n.t("folders.low_res_video"))
            }

            self.log_callback(i18n.t("w.clean.scanning"), "#888888")
            all_files: list[tuple[str, int]] = []
            
            for path, size in fast_scandir_size(source_dir, EXTENSIONS):
                if self._stop_event.is_set():
                    self.log_callback(i18n.t("w.clean.scan_stopped"), "#ef4444")
                    return
                all_files.append((path, size))
                total_old_size += size

            total_count = len(all_files)
            if total_count == 0:
                self.log_callback(i18n.t("w.clean.no_files"), "#f59e0b")
                return

            self.log_callback(i18n.t("w.clean.found").format(n=total_count, size=format_size(total_old_size)), "#38bdf8")
            
            # Optimization: filter out files that don't need analysis
            photo_active = any(params.get(k, False) for k in ['check_blur', 'check_exposure', 'check_res', 'check_corrupted'])
            video_active = any([
                params.get('check_corrupted', False),
                params.get('vid_min_duration', 0) > 0,
                params.get('vid_resolution_h', 0) > 0,
                params.get('vid_check_dark', False),
                params.get('vid_check_sound', False)
            ])

            tasks = []
            skipped_count = 0
            for f_path, f_size in all_files:
                ext = Path(f_path).suffix.lower()
                is_v = ext in {'.mp4', '.mov', '.avi', '.mkv', '.3gp', '.m4v'}
                
                if (is_v and video_active) or (not is_v and photo_active):
                    tasks.append((f_path, f_size, params, target_dirs))
                else:
                    skipped_count += 1

            done = skipped_count
            
            # If nothing to analyze — finish
            if not tasks:
                self.progress_callback(total_count, total_count, 0, 0)
                self.log_callback(i18n.t("w.clean.result").format(n=0, size=format_size(0), pct="0.0"), "#3ecf8e")
                return

            # Use 50% of available cores to prevent CPU frequency maxing out and overheating
            cores = max(1, multiprocessing.cpu_count() or 1)
            executor_start_time = time.perf_counter()

            if skipped_count > 0:
                self.progress_callback(done, total_count, 0, 0)

            from concurrent.futures import ThreadPoolExecutor, as_completed
            with ThreadPoolExecutor(max_workers=cores, initializer=_set_thread_low_priority) as pool:
                futures = {pool.submit(worker_task, task): task for task in tasks}
                for future in as_completed(futures):
                    if self._stop_event.is_set():
                        for f in futures:
                            f.cancel()
                        self.log_callback(i18n.t("w.clean.analysis_stopped"), "#ef4444")
                        return
                    
                    try:
                        res = future.result()
                    except Exception as e:
                        logger.error(f"Error in future result: {e}")
                        continue
                        
                    if res["status"] != "ok":
                        found_count += 1
                        found_size += res["size"]
                        
                    done += 1
                    if done % 10 == 0 or done == total_count:
                        elapsed_exec = time.perf_counter() - executor_start_time
                        speed = done / elapsed_exec if elapsed_exec > 0 else 1
                        eta = (total_count - done) / speed
                        self.progress_callback(done, total_count, eta, found_count)

            percentage = (found_size / total_old_size * 100) if total_old_size > 0 else 0
            self.log_callback(i18n.t("w.clean.result").format(n=found_count, size=format_size(found_size), pct=f"{percentage:.1f}"), "#3ecf8e")
            logger.info(f"Cleaning finished: found {found_count} files, total size: {format_size(found_size)}")
            
        except Exception as e:
            self.log_callback(f"❌ {i18n.t('w.clean.critical').format(err=str(e))}", "#ef4444")
            logger.exception("Critical error during cleaning process")
        finally:
            elapsed = time.perf_counter() - t_start
            self.finished_callback(found_count, found_size, elapsed)
