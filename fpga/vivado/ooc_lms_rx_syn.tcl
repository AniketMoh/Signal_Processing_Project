# ooc_lms_rx_syn.tcl -- out-of-context synthesis + place + route of lms_rx_syn alone on the XC7S50, 100 MHz clock.
# Gives DSP/LUT/FF use and timing of the LMS core by itself (no I/O buffers, no board).  Level L4 (core only, not the full design).
# Responsible member: Pradeep Kumar (review, verification, viva)
# Written with AI assistance (Claude, Anthropic), project decision D-06.
#
# Usage (from fpga/vivado):
#   vivado -mode batch -nojournal -log build/ooc.log -source ooc_lms_rx_syn.tcl -tclargs <B_MUL> <B_ACC> <RND>
# Reports go to build/ooc_m<B_MUL>_a<B_ACC>_r<RND>/ ; a one-line summary is appended to reports/ooc_lms_rx_syn_summary.txt
set here  [file dirname [file normalize [info script]]]
set B_MUL [expr {[llength $argv] > 0 ? [lindex $argv 0] : 12}]
set B_ACC [expr {[llength $argv] > 1 ? [lindex $argv 1] : 16}]
set RND   [expr {[llength $argv] > 2 ? [lindex $argv 2] : 1}]
set part  xc7s50csga324-1
set tag   m${B_MUL}_a${B_ACC}_r${RND}
set out   [file join $here build ooc_$tag]
file mkdir $out
file mkdir [file join $here reports]

read_verilog [file join $here .. rtl lms_rx_syn.v]
read_xdc -mode out_of_context [file join $here ooc_clk.xdc]
synth_design -top lms_rx_syn -part $part -mode out_of_context -generic B_MUL=$B_MUL -generic B_ACC=$B_ACC -generic RND=$RND
report_utilization -file [file join $out util_synth.rpt]
opt_design
place_design
route_design
report_utilization     -file [file join $out util_routed.rpt]
report_timing_summary  -file [file join $out timing_routed.rpt] -max_paths 10
report_timing          -file [file join $out worst_path.rpt] -max_paths 1 -nworst 1

set wns  [get_property SLACK [get_timing_paths -max_paths 1 -nworst 1 -setup]]
# numbers as in the utilisation report (counting LUT cells would count both halves of packed LUT6_2 pairs)
set util [report_utilization -return_string]
regexp {\| Slice LUTs\s+\|\s+(\d+)}      $util -> lut
regexp {\| Slice Registers\s+\|\s+(\d+)} $util -> ff
regexp {\| DSPs\s+\|\s+(\d+)}            $util -> dsp
set line [format "%s  B_MUL=%s B_ACC=%s RND=%s  DSP48E1=%d  LUT=%d  FF=%d  WNS@100MHz=%.3f ns  (routed, out-of-context, core only)" \
          [clock format [clock seconds] -format {%Y-%m-%d %H:%M}] $B_MUL $B_ACC $RND $dsp $lut $ff $wns]
puts $line
set fh [open [file join $here reports ooc_lms_rx_syn_summary.txt] a]
puts $fh $line
close $fh
