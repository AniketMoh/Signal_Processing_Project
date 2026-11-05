# build_top.tcl -- synthesis, implementation and bitstream of top_boolean for the Boolean Board (non-project mode).  Level L4.
# Responsible member: Bhavyam Shankar (review, verification, viva)
# Written with AI assistance (Claude, Anthropic), project decision D-06.
#
# Usage (from fpga/vivado):
#   vivado -mode batch -nojournal -log build/top.log -source build_top.tcl -tclargs <B_MUL> <B_ACC> <RND>
# Output: build/top_m<B_MUL>_a<B_ACC>_r<RND>/ (bitstream, checkpoint, reports); one summary line appended to
#         reports/top_summary.txt; copies of the utilisation and timing reports in reports/.
set here  [file dirname [file normalize [info script]]]
set B_MUL [expr {[llength $argv] > 0 ? [lindex $argv 0] : 12}]
set B_ACC [expr {[llength $argv] > 1 ? [lindex $argv 1] : 16}]
set RND   [expr {[llength $argv] > 2 ? [lindex $argv 2] : 1}]
set part  xc7s50csga324-1
set tag   m${B_MUL}_a${B_ACC}_r${RND}
set out   [file join $here build top_$tag]
set rep   [file join $here reports]
file mkdir $out
file mkdir $rep

set rtl [file join $here .. rtl]
set mid [file join $here .. .. midterm_mtr-22 2_code_and_results_by_phase 09_P7-P8_RTL code]
foreach f {top_boolean.v host_if.v uart_rx.v uart_tx.v board_io.v exp_core.v payload_lfsr.v rx_chain_syn.v lms_rx_syn.v
           chan_front_syn.v var_ctrl_syn.v} { read_verilog [file join $rtl $f] }
foreach f {lfsr_noise.v prbs15.v} { read_verilog [file join $mid $f] }
read_xdc [file join $here boolean.xdc]

synth_design -top top_boolean -part $part -generic B_MUL=$B_MUL -generic B_ACC=$B_ACC -generic RND=$RND
report_utilization -file [file join $out util_synth.rpt]
opt_design
place_design
phys_opt_design
route_design
write_checkpoint -force [file join $out top_routed.dcp]
report_utilization             -file [file join $out util_routed.rpt]
report_utilization -hierarchical -hierarchical_depth 3 -file [file join $out util_hier.rpt]
report_timing_summary          -file [file join $out timing_routed.rpt] -max_paths 10
report_drc                     -file [file join $out drc.rpt]
report_power                   -file [file join $out power.rpt]
file copy -force [file join $out util_routed.rpt]   [file join $rep top_${tag}_utilization.rpt]
file copy -force [file join $out timing_routed.rpt] [file join $rep top_${tag}_timing.rpt]
file copy -force [file join $out util_hier.rpt]     [file join $rep top_${tag}_utilization_hier.rpt]

set util [report_utilization -return_string]
regexp {\| Slice LUTs\s+\|\s+(\d+)}      $util -> lut
regexp {\| Slice Registers\s+\|\s+(\d+)} $util -> ff
regexp {\| DSPs\s+\|\s+(\d+)}            $util -> dsp
regexp {\| Block RAM Tile\s+\|\s+(\S+)}  $util -> bram
set wns [get_property SLACK [get_timing_paths -max_paths 1 -nworst 1 -setup]]
set whs [get_property SLACK [get_timing_paths -max_paths 1 -nworst 1 -hold]]
set fmax [expr {1000.0 / (10.0 - $wns)}]
set line [format "%s  top_boolean B_MUL=%s B_ACC=%s RND=%s  DSP48E1=%s/120  LUT=%s/32600  FF=%s/65200  BRAM=%s  WNS=%.3f ns  WHS=%.3f ns  Fmax(est)=%.1f MHz  (routed, full design)" \
          [clock format [clock seconds] -format {%Y-%m-%d %H:%M}] $B_MUL $B_ACC $RND $dsp $lut $ff $bram $wns $whs $fmax]
puts $line
set fh [open [file join $rep top_summary.txt] a]; puts $fh $line; close $fh

if {$wns >= 0} {
    write_bitstream -force [file join $out top_boolean.bit]
    puts "BITSTREAM [file join $out top_boolean.bit]"
} else {
    puts "TIMING FAILED: no bitstream written"
}
