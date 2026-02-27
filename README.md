This is a CLI-based photo/video organizer written in Python. 
It scans a source folder for media files, extracts date metadata, 
renames them into a standardized format, 
and moves them to a destination folder — with duplicate detection and a simple JSON-based tracking database.

CLI Arguments
--src, -s	Source folder to scan
--dst, -d	Destination folder for organized files
--compare, -c	Duplicate detection: name, binary, size
--ignore, -i	Regex patterns for filenames to skip
--accept, -a	Regex patterns for filenames to include (presets: default, mobile, camera)
--not-recursive	Disable recursive scanning (default is recursive)
--dry-run	Preview without moving files
--sync-folder-and-db	Reconcile the DB with folder contents


Date Extraction Strategy
EXIF — For image files, opens with PIL and reads DateTimeOriginal (tag 36867)
Filename regex — Falls back to parsing date/time from the filename via the "mobile" regex pattern
File system timestamps — Uses the minimum of atime, mtime, ctime
The earliest date found is used to generate the standardized filename.
