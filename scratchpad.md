# Lessons

- For website image paths, always use the correct relative path (e.g., 'images/filename.png') and ensure the images directory exists
- For search results, ensure proper handling of different character encodings (UTF-8) for international queries
- Add debug information to stderr while keeping the main output clean in stdout for better pipeline integration
- When using seaborn styles in matplotlib, use 'seaborn-v0_8' instead of 'seaborn' as the style name due to recent seaborn version changes
- When using Jest, a test suite can fail even if all individual tests pass, typically due to issues in suite-level setup code or lifecycle hooks

## Windsurf learned

- For search results, ensure proper handling of different character encodings (UTF-8) for international queries
- Add debug information to stderr while keeping the main output clean in stdout for better pipeline integration
- When using seaborn styles in matplotlib, use 'seaborn-v0_8' instead of 'seaborn' as the style name due to recent seaborn version changes
- Use 'gpt-4o' as the model name for OpenAI's GPT-4 with vision capabilities 

# DOnt touch text above this line.

# Scratchpad
### Task
Combine two drop zones into one with auto-update checkbox

### Plan
[X] Remove separate auto-update drop zone section
[X] Add checkbox under main drop zone: "Enable auto-update on save"
[X] Show warning when checkbox is checked about PowerShell
[X] Modify uploadFile() to start watcher after upload if checkbox is checked

### Progress
- Single drop zone for uploading maps
- Checkbox to enable auto-update (with PowerShell warning)
- Drop/click → upload → (if checked) auto-start watcher

### References
- Game Server: 127.0.0.1:8303
- Maps Directory: C:/Users/rust-/AppData/Roaming/DDNet/maps

### Lessons (to add later)
- N/A yet.

### Windsurf Learned
- Manual upload via GitHub web interface is most reliable when git push fails
- GitHub topics system effective for tool discoverability
- DDNet community primarily uses Discord for tool sharing
- Release packages should separate source code from end-user binaries