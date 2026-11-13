@echo off
rem Double-click to load the design onto the Boolean Board (needed after every power-on), then check the link.
cd /d "%~dp0vivado"
echo Programming the FPGA, please wait (about 1 minute)...
call D:\2025.2\Vivado\bin\vivado.bat -mode batch -nojournal -nolog -source program_board.tcl -tclargs bitstreams/top_boolean_m12_a16_r1.bit
cd /d "%~dp0host"
echo.
echo Checking the board (expect version: 2) ...
python run_board.py ident
echo.
pause
