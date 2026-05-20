# Software Requirements Specification (SRS)

**Product Name:** MediaMatrix

---

## 1. Introduction

**Purpose:**
MediaMatrix is a desktop application for automated sorting, cleaning, and organization of media files (photos and videos). The application helps users identify duplicates, filter out defective files (blurry, dark, corrupted), and structure their media archives chronologically.

**Scope:**

- The application supports local processing of graphic formats (JPG, PNG, HEIC, WEBP, TIFF, BMP, GIF, etc.; RAW formats are additionally supported for the Sorter and TwinFinder modules) and video formats (MP4, MOV, AVI, MKV, 3GP, WMV, etc.).
- Performs content analysis (computer vision), metadata reading (EXIF, Hachoir), and hashing (MD5, pHash).
- Executes file operations (moving, renaming) but does not destructively edit the content of the media files themselves.
- Operates exclusively locally (Local-First), without integration with cloud services (AI, databases) or third-party APIs.

---

## 2. General Description

**Product Functions:**

1. **TwinFinder:** Finds absolute and perceptually similar copies of images and videos.
2. **PhotoCleaner:** Identifies defective photos (blurry, dark, overexposed, low resolution, corrupted) and videos (too short, dark, corrupted).
3. **PhotoSorter:** Extracts dates from file metadata or names and organizes media into structured folders.

**User Classes and Characteristics:**
Regular Windows OS users who have large, unorganized archives of media files (from mobile devices, cameras) and are looking for a tool to automate organization and free up disk space without requiring special technical skills.

**Operating Environment:**

- **OS:** Windows.
- **Platform:** Python 3.10+.
- **Key Dependencies:** Flet (UI), OpenCV, Pillow, pillow-heif, ImageHash, Hachoir, NumPy, PyYAML, SciPy.

**Design and Implementation Constraints:**

- **No Network Calls:** All data processing is performed exclusively on local hardware.
- **Front-end and Back-end Synchronization:** Using Flet creates a dependency between the Python logic and the Flutter engine, meaning UI updates (progress bars, logs) require thread-safe callbacks (`progress_callback`, `log_callback`).
- Multithreading is limited by the number of local CPU cores (`multiprocessing.Pool`).

---

## 3. Functional Requirements

### 3.1 TwinFinder

- **Input:** Source directory, similarity threshold, Look Ahead parameters.
- **Processing:**
  - File traversal is performed via an optimized `os.scandir()`.
  - **Video:** Calculation of exact MD5 hash in chunks. *Optimization:* If the video file size is unique for the directory, the hash is not calculated to save I/O resources.
  - **Photo:** Image decoding (via `Image.draft()` in 32x32px grayscale for maximum speed, applied only to JPEG files) and calculation of a perceptual hash (pHash) using the `imagehash` library.
  - **Clustering:** If Threshold > 0, a Disjoint Set Union (DSU) data structure is used to group similar photos together.
- **Output:** Extracting the best version of the file from the group (by resolution and size), moving the others (duplicates) into the `DUPLICATES_<name>` folder.

### 3.2 PhotoCleaner

- **Input:** Target directory, a set of configurable filters (Blur, Exposure, Resolution, Corruption, Video Duration).
- **Processing:**
  - **Photo:** Conversion to `Grayscale` with downscaling (for images larger than 1000px) to speed up processing.
    - *Blur:* Calculating the variance of the Laplacian (`cv2.Laplacian(img, cv2.CV_64F).var()`).
    - *Exposure:* Calculating the mean brightness of the pixel array (`np.mean()`).
    - *Resolution:* Reading the original dimensions via Pillow.
  - **Video:** Analysis via `cv2.VideoCapture`.
    - Checking FPS, total number of frames (to calculate duration), and resolution.
    - Analyzing exposure (darkness) by sampling 3 representative frames (at 20%, 50%, and 80% of the timeline).
- **Output:** Automatically moving files that fail the filtering into appropriate trash subcategories (`Blurry`, `Dark`, `Bright`, `LowRes`, `Corrupted`, `ShortVideo`, `DarkVideo`, `LowResVideo`, etc.).

### 3.3 PhotoSorter

- **Input:** Source directory, destination directory, folder structure format (Nested/Flat), renaming policies.
- **Processing:**
  - Multi-level date identification algorithm (Fallback Mechanism):
    1. **EXIF / Video Metadata:** Via `Pillow.getexif()` or `Pillow._getexif()` for photos and `Hachoir` for videos.
    2. **Filename Patterns:** Regular expression (Regex) search like `YYYY_MM_DD` or `YYYYMMDD`.
    3. **Unix Timestamp:** Identifying 10, 13, or 16-character timestamps in the filename (typical for messengers).
    4. **OS Date:** Reading `os.path.getmtime()` (if fallback is enabled).
  - The algorithm detects screenshots by keywords in the name or special tags in EXIF (`Software`, `UserComment`).
- **Output:** Creating a directory hierarchy. Moving media with potential file renaming to the standard format `YYYY_MM_DD_HHMMSS`.
  - *Screenshots:* Can be optionally isolated into a separate `Screenshots` folder to prevent cluttering the chronological archive.
  - *Undated Files:* Files where no date could be determined are safely moved to a dedicated `Undated` folder.

---

## 4. External Interface Requirements

**User Interface:**

- The front-end interface is built on the cross-platform `Flet` framework in a declarative style (however, the application is supported and tested only on Windows).
- The architecture consists of a navigation sidebar (`AppSidebar`) and a content area (`ContentArea`), which houses the three main modules (`TwinFinderView`, `PhotoCleanerView`, `PhotoSorterView`).
- The sidebar also integrates a "Support & Contact" section, providing users with direct communication channels (e.g., Gmail integration via URL schemes) and support links (Patreon, Ko-fi, Crypto) without requiring heavy third-party SDKs.
- Interaction with the OS file system (folder selection dialogs) is implemented via `ft.FilePicker`. In Flet 1.0+, dialogs are initialized as services during page load (`page.services.append`).
- Instant internationalization (i18n) is supported, based on subscriptions (observable pattern) — the interface updates reactively without reloading.

**Software Interfaces:**

- **Local File System:** Tight integration with Windows FS (`os`, `shutil`, `pathlib`) for reading/moving files.
- **Multimedia Drivers:** Usage of `OpenCV` (cv2) as the computer vision engine, and `Pillow` (with the `pillow_heif` extension) for decoding and interacting with RAW/HEIC images.

---

## 5. Non-functional Requirements

**Performance:**

- **Throughput & Latency:** The architecture is built on active multiprocessing (`multiprocessing.Pool`), allowing parallel file processing across all CPU cores. I/O operations are optimized by traversing the tree with `os.scandir()` (with `follow_symlinks=False` to prevent infinite loops in OS junction points like Windows `Application Data`) instead of the classic `os.walk()`.
- **Memory Optimization:** MD5 hashing of large video files is split into 4 MB chunks (`4096 * 1024`). Visual analysis of images is performed on their thumbnails (downscaling / draft mode).

**Security & Privacy:**

- **No Telemetry:** The product operates isolated and entirely locally. No file is sent to third-party servers. There is no analytic data or telemetry collection at the code level.

**Reliability:**

- **Fault Tolerance:** Implemented `try-except` wrappers when opening files to skip "broken" or incorrect formats (to prevent stopping the entire processing flow).
- **Collision Management:** Automatic handling of name conflicts during moving (adding counters formatted as `(1)` or `_1`).
- **Concurrency:** Implemented handling of `PermissionError` (if the file is locked by another program) with a series of retries in the PhotoSorter module. There is a clear mechanism for terminating threads via `threading.Event` (`_stop_event`) across all modules.
- **Maintainability & Logging:** The application maintains structured local logs (`core.logger`) for debugging and auditing file operations. Since there is no telemetry, these local logs are the primary mechanism to investigate edge cases or file system permissions errors.

**Constraints:**

- Maximum throughput is limited by the type of the user's file system and storage drive (HDD vs SSD).
- CV algorithms (specifically OpenCV) run on the CPU. Therefore, latency is directly proportional to the client's processor power.
