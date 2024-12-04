@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
rc ddnet_control.rc
cl /EHsc /std:c++17 ddnet_control.cpp ddnet_control.res /link ws2_32.lib ole32.lib shell32.lib /out:ddnet_control.exe
