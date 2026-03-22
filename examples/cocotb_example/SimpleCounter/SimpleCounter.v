// SimpleCounter - 8 位可控计数器
// 一个简单的计数器模块，用于演示 cocotb 验证流程

module SimpleCounter (
    input wire clk,
    input wire rst_n,
    input wire enable,
    input wire clear,
    output wire [7:0] count,
    output wire overflow
);

reg [7:0] count_reg;
reg overflow_reg;

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        count_reg    <= 8'b0;
        overflow_reg <= 1'b0;
    end else if (clear) begin
        count_reg    <= 8'b0;
        overflow_reg <= 1'b0;
    end else if (enable) begin
        if (count_reg == 8'hFF) begin
            count_reg    <= 8'b0;
            overflow_reg <= 1'b1;
        end else begin
            count_reg    <= count_reg + 1'b1;
            overflow_reg <= 1'b0;
        end
    end else begin
        overflow_reg <= 1'b0;
    end
end

assign count    = count_reg;
assign overflow = overflow_reg;

endmodule
