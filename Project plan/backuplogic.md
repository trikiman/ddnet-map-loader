Here's how it works in practice:

First time you run with run_guy1.map:
Code
CopyInsert
currentMapPath = "run_guy0.map"          // Current map on server
backupPath = "run_guy0_backup.map"       // Where backup will go
hasBackup = false                        // No backup exists yet
-> Creates backup of run_guy0.map
-> Replaces with run_guy1.map
Second time you run with run_guy2.map:
Code
CopyInsert
currentMapPath = "run_guy0.map"          // Current map on server
backupPath = "run_guy0_backup.map"       // Where backup would go
hasBackup = true                         // Backup already exists from step 1
-> Uses existing backup (skips creating new one)
-> Replaces with run_guy2.map
When you restore:
Code
CopyInsert
-> Restores from run_guy0_backup.map (which contains original run_guy0.map)
The retry logic (the for loop) is there because sometimes filesystem operations can be slow or have temporary issues. By checking multiple times with small delays, we make sure we don't miss an existing backup file.

This ensures that:

We only ever create one backup of the original map
We keep that original backup even when replacing the map multiple times
When restoring, we always go back to the original map