# Release Checklist (v2)

- [ ] Build `ddnet_control.exe` via `compile.bat` (verify `build.log` OK)
- [ ] Verify EXE icon from `Image/ddnet_loader.ico`
- [ ] Optional: generate `Image/ddnet_loader_fixed.ico` and embed if needed
- [ ] Test CLI:
  - [ ] `ddnet_control.exe "C:\Users\rust-\AppData\Roaming\DDNet\maps\mapsfortest\Tutorial.map"`
  - [ ] See `ddnet_control.log` for hot_reload/status OK
- [ ] File association (user-scope):
  - [ ] `registry\remove_map_association_current_user.bat`
  - [ ] `registry\setup_map_association_current_user.bat`
- [ ] Git: push main and tag
  - [ ] `git push -u origin main`
  - [ ] `git tag v2.0.0 && git push origin v2.0.0`
- [ ] GitHub Release (optional): attach zip with EXE + `registry\` scripts
