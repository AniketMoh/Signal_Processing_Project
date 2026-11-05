// tb_lfsr_noise.v -- testbench for lfsr_noise: loads the seeds from seeds.hex, writes NS noise samples to noise_rtl.txt
`timescale 1ns/1ps
module tb_lfsr_noise;
    parameter NS = 20000;
    reg clk = 0, rst = 1, load = 0, en = 0;
    reg  [12*36-1:0] seeds;
    wire signed [19:0] noise;
    wire valid;
    reg [35:0] seed_mem [0:11];
    integer i, fd, count;

    lfsr_noise dut (.clk(clk), .rst(rst), .load(load), .seeds(seeds), .en(en), .noise(noise), .valid(valid));
    always #5 clk = ~clk;

    initial begin
        $readmemh("seeds.hex", seed_mem);
        for (i = 0; i < 12; i = i + 1) seeds[36*i +: 36] = seed_mem[i];
        fd = $fopen("noise_rtl.txt", "w");
        count = 0;
        repeat (3) @(posedge clk);
        rst <= 0;
        @(posedge clk); load <= 1;
        @(posedge clk); load <= 0; en <= 1;
        while (count < NS) begin
            @(posedge clk);
            #1;
            if (valid) begin
                $fdisplay(fd, "%0d", noise);
                count = count + 1;
            end
        end
        $fclose(fd);
        $display("tb_lfsr_noise: wrote %0d samples", count);
        $finish;
    end
endmodule
