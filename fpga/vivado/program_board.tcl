# program_board.tcl -- load a bitstream into the Boolean Board over JTAG (volatile: lost at power-off).
# Usage: vivado -mode batch -nojournal -nolog -source program_board.tcl -tclargs <bitfile>
# Responsible member: Bhavyam Shankar (review, verification, viva)
# Written with AI assistance (Claude, Anthropic), project decision D-06.
set bit [lindex $argv 0]
open_hw_manager
connect_hw_server -allow_non_jtag
open_hw_target
set dev [lindex [get_hw_devices xc7s50*] 0]
current_hw_device $dev
set_property PROGRAM.FILE $bit $dev
program_hw_devices $dev
puts "PROGRAMMED $dev with $bit"
close_hw_target
disconnect_hw_server
