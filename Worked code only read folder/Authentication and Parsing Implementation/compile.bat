@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
cl /EHsc /std:c++20 ddnet_control.cpp ws2_32.lib ole32.lib shell32.lib
