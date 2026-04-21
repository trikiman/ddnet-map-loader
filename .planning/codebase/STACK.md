# Stack

## Overview

This repository is a Windows-first DDNet tooling project with two primary runtimes:

- A native Win32 GUI executable in `ddnet_control.cpp`
- An optional Python web control surface in `web/server.py`

The codebase also includes local helper tooling under `tools/` for scraping, screenshots, and LLM access, but those are support utilities rather than the main shipped product.

## Languages and runtimes

- C++20 compiled with MSVC via `compile.bat`
- Windows APIs and Winsock used directly in `ddnet_control.cpp`
- Python 3.x for the optional web server in `web/server.py`
- Vanilla HTML/CSS/JavaScript for the browser UI in `web/index.html`, `web/styles.css`, and `web/script.js`
- PowerShell for file watching and upload automation in `auto_uploader.ps1` and `web/auto_uploader.ps1`
- Batch scripts for local setup and launch tasks such as `compile.bat`, `fix_file_association.bat`, `web/run_server.bat`, and `web/create_shortcut.bat`

## Native application stack

Primary native files:

- `ddnet_control.cpp` - main executable logic, RCON communication, backup handling, file association setup
- `ddnet_control.rc` - Windows resource metadata and icon binding
- `compile.bat` - MSVC environment setup and build entry point
- `myServerconfig.cfg` - DDNet server config sample with econ/RCON settings

Key native platform dependencies:

- C++ standard library: filesystem, streams, chrono, threading, string utilities
- Win32 APIs: `windows.h`, `shellapi.h`, `shlobj.h`, `objbase.h`
- Winsock: `winsock2.h`, `ws2tcpip.h`
- Linked libraries from `compile.bat`: `ws2_32.lib`, `ole32.lib`, `shell32.lib`

## Web stack

Primary web files:

- `web/server.py` - HTTP server, upload/download endpoints, tray icon, file picker, watcher launcher
- `web/index.html` - static UI shell
- `web/script.js` - upload flow, map listing, search, logs, auto-update wiring
- `web/styles.css` - theme variables and layout styling
- `web/run_server.bat` - local launch helper
- `web/requirements.txt` - Python packages for the web server

Web Python dependencies from `web/requirements.txt`:

- `pystray`
- `Pillow`

Frontend characteristics:

- No framework bundler or package manager
- Static assets served directly from `web/`
- State lives in the browser and in filesystem-backed DDNet map folders

## Helper tooling stack

Repository helper tools live under `tools/`:

- `tools/llm_api.py` - wrappers for OpenAI, Azure OpenAI, Anthropic, Gemini, DeepSeek, SiliconFlow, and local OpenAI-compatible endpoints
- `tools/search_engine.py` - DuckDuckGo search CLI
- `tools/web_scraper.py` - Playwright-based scraping CLI
- `tools/screenshot_utils.py` - screenshot helper
- `tools/convert_ico.py` - icon conversion utility
- `tools/create_unstable_icon.ps1` - icon generation helper

Root Python dependencies from `requirements.txt` support those utilities:

- `playwright`
- `html5lib`
- `duckduckgo-search`
- `openai`
- `anthropic`
- `python-dotenv`
- `pytest`
- `pytest-asyncio`
- `unittest2`
- `google-generativeai`
- `grpcio`

## Configuration and environment

Configuration is split across code and local files:

- `myServerconfig.cfg` defines DDNet econ/RCON settings
- `.env` provides API keys for helper tools
- `.devcontainer/devcontainer.json` defines an Ubuntu + Python devcontainer
- `vcvars64.bat` is a local helper for MSVC environment setup

Important hardcoded runtime defaults observed in code:

- DDNet server host `127.0.0.1`
- DDNet econ/RCON port `8303`
- Web server port `8299`
- DDNet maps folder under `%APPDATA%\\DDNet\\maps`

## Shipped and tracked artifacts

The repository currently tracks several binary or generated assets:

- `ddnet_control.exe`
- `test.map`
- `Image/ddnet.ico`
- `Image/ddnet_loader.ico`
- `Image/ddnet-unstable.ico`
- `web/map.ico`
- `web/server.log`

That mix suggests the repo is used both as source control and as a local distribution workspace.
