# Agent Workflow Changelog & Fixes

## Critical Fixes
- **live_poster.py Syntax Error Fixed:** Addressed a critical syntax error (`ig_user_id = os.environ.get("META_INSTAGRAM_ACCOUNT_ID", "YOUR_INSTAGRAM_USER_ID`) introduced during the previous public repo sanitization. 

## High Priority Additions
- **Manual Review/Approval Gate:** Added a safety check in `live_poster.py`. If `REQUIRE_APPROVAL` is set in `.env` (defaults to True), the system will halt and write the post details to `output/PENDING_APPROVAL.md`. It will not publish until a flag file (`output/APPROVED_POST.txt`) is created by a human.
- **Missed Days Backfill (Catch-up):** The script now tracks previously published posts using an internal ledger (`output/posted_days.json`). If the machine was asleep and a cron job was missed, the poster will intelligently find the *earliest unposted day* up to the current day of the week, ensuring you never miss a post in the queue.
- **Robust Error Handling:** Wrapped the entire upload and posting pipeline in a `try/except` block. Critical failures (such as Meta API rejections or Drive auth failures) now cleanly exit and log clear alerts to a prominent `output/ERROR_ALERTS.md` file rather than silently crashing in the background.

## Medium Priority Enhancements
- **GCS Cleanup (Storage Optimization):** Added explicit cleanup logic to `live_poster.py`. Once Meta successfully ingests the image via the temporary public URL, the script immediately deletes the public blob from Google Cloud Storage to prevent unbounded storage costs and permanent public exposure.
- **Exact-Match Drive Filenames:** Updated the Google Drive query from a fuzzy `contains '{base_name}'` to a strict exact match across valid extensions (`.HEIC`, `.jpg`, `.JPG`) to prevent downloading the wrong file if two assets share a similar naming prefix.
- **JSON Filename Validation:** Augmented `content_planner.py` to cross-reference the filenames chosen by Gemini against the actual list of available unposted files. If Gemini hallucinates an extension, it fuzzy-matches and corrects the extension, ensuring `live_poster` always receives valid filenames.
- **Silent Exception Swallowing Fixed:** Removed bare `except: pass` in `content_planner.py` cleanup code, replacing it with explicit logging to expose silent failures during temp file removal.
- **Verified Gemini Model Fallbacks:** Updated the fallback chain in `content_planner.py` to strictly use verified models available in Vertex AI (`gemini-2.5-pro` and `gemini-2.5-flash`), removing the hallucinated `gemini-3.8-flash` variants.
- **Agent Dependency Safety (Freshness):** Updated `main.py` to increase the historical data pull from 5 to 50 posts. Added strict `set -e` flags to `run_weekly_planner.sh` so Agent #3 (Planner) will not execute if Agent #2 (Performance Tagging) fails upstream. Removed mock fallback data in Agent #2 to fail loudly instead of poisoning the dataset.
