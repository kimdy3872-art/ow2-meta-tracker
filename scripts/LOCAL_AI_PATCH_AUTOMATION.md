# Local AI Patch Automation

This Mac runs the local Ollama patch analysis through launchd.

## Schedule

- LaunchAgent label: `com.da.overwatch.ai-patch`
- Main trigger: every day at 09:00
- Catch-up trigger: every 900 seconds
- Guard rule: the script exits before 09:00 and exits after one successful run per day.

## Files

- Script: `scripts/run_local_ai_patch_update.sh`
- LaunchAgent template: `scripts/com.da.overwatch.ai-patch.plist`
- Installed LaunchAgent: `~/Library/LaunchAgents/com.da.overwatch.ai-patch.plist`
- Success marker: `data/local_run_state/patch_ai_last_success.txt`
- Logs:
  - `logs/local_ai_patch_update.log`
  - `logs/launchd_ai_patch.out.log`
  - `logs/launchd_ai_patch.err.log`

## Manual Run

```bash
scripts/run_local_ai_patch_update.sh
```

To force another run on the same day:

```bash
rm -f data/local_run_state/patch_ai_last_success.txt
scripts/run_local_ai_patch_update.sh
```

## Status

```bash
launchctl print gui/$(id -u)/com.da.overwatch.ai-patch
tail -50 logs/local_ai_patch_update.log
```

## Reload

```bash
cp scripts/com.da.overwatch.ai-patch.plist ~/Library/LaunchAgents/com.da.overwatch.ai-patch.plist
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.da.overwatch.ai-patch.plist 2>/dev/null || true
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.da.overwatch.ai-patch.plist
launchctl enable gui/$(id -u)/com.da.overwatch.ai-patch
```

## Disable

```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.da.overwatch.ai-patch.plist
```
