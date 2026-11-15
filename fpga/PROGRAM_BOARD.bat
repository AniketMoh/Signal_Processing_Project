@echo off
rem Double-click to load the design onto the Boolean Board (needed after every power-on), then check the link.
rem Optional argument: another bitstream file name from vivado\bitstreams (default: the SW12 build used for the live demo).
rem Vivado location: set VIVADO_BIN if Vivado is not in D:\2025.2\Vivado\bin.
setlocal
set BIT=%~1
if "%BIT%"=="" set BIT=top_boolean_m12_a16_r1_sw12.bit
if "%VIVADO_BIN%"=="" set VIVADO_BIN=D:\2025.2\Vivado\bin
cd /d "%~dp0vivado"
echo Programming the FPGA with %BIT%, please wait (about 1 minute)...
call "%VIVADO_BIN%\vivado.bat" -mode batch -nojournal -nolog -source program_board.tcl -tclargs bitstreams/%BIT%
cd /d "%~dp0host"
echo.
echo Checking the board (expect version: 2) ...
python run_board.py ident
echo.
pause
