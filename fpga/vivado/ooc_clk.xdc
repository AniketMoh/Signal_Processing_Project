# ooc_clk.xdc -- clock for out-of-context runs of single modules: 100 MHz (the Boolean Board oscillator frequency).
create_clock -period 10.000 -name clk [get_ports clk]
