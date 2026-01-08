module spi_peripheral(
    input wire SCLK, nCS, COPI, // SPI Inputs
    input wire clk, rst_n, 

    //regs
    output reg [7:0] EN_REG_OUT_7_0,
    output reg [7:0] EN_REG_OUT_15_8,
    output reg [7:0] EN_REG_PWM_7_0,
    output reg [7:0] EN_REG_PWM_15_8,
    output reg [7:0] PWM_DUTY_CYCLE

);

    reg SCLK_sync1, SCLK_sync2, SCLK_prev;
    reg nCS_sync1, nCS_sync2, nCS_prev;
    reg COPI_sync1, COPI_sync2;

    reg [4:0] bit_counter;
    
    // data[15] -> r/w
    // data[14:8] -> address
    // data[7:0] -> data
    reg [15:0] data;

    wire nCS_negedge;
    wire SCLK_posedge;

    assign nCS_negedge = nCS_prev && !nCS_sync2;
    assign SCLK_posedge = !SCLK_prev && SCLK_sync2;

    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            EN_REG_OUT_7_0 <= 0;
            EN_REG_OUT_15_8 <= 0;
            EN_REG_PWM_7_0 <= 0;
            EN_REG_PWM_15_8 <= 0;
            PWM_DUTY_CYCLE <= 0;

            SCLK_prev <= 0;
            SCLK_sync1 <= 0;
            SCLK_sync2 <= 0;

            nCS_sync1 <= 1;
            nCS_sync2 <= 1;
            nCS_prev <= 1;

            COPI_sync1 <= 0;
            COPI_sync2 <= 0;

            data <= 16'b0;
            bit_counter <= 5'b0;

        end
        else begin

            SCLK_sync1 <= SCLK;
            SCLK_sync2 <= SCLK_sync1;
            SCLK_prev <= SCLK_sync2;

            nCS_sync1 <= nCS;
            nCS_sync2 <= nCS_sync1;
            nCS_prev <= nCS_sync2;

            COPI_sync1 <= COPI;
            COPI_sync2 <= COPI_sync1;
            
            

            if(nCS_negedge)begin
                data <= 16'b0;
                bit_counter <= 5'b0;
            end
            if(!nCS_sync2 && SCLK_posedge && bit_counter != 5'b10000)begin
                data <= {data[14:0],COPI_sync2};
                bit_counter <= bit_counter + 1;
            end

            if(bit_counter == 5'b10000 && data[15] == 1)begin
                case(data[14:8])
                7'h0: EN_REG_OUT_7_0 <= data[7:0];
                7'h1: EN_REG_OUT_15_8 <= data[7:0];
                7'h2: EN_REG_PWM_7_0 <= data[7:0];
                7'h3: EN_REG_PWM_15_8 <= data[7:0];
                7'h4: PWM_DUTY_CYCLE <= data[7:0];
                default: ;
                endcase
            end
        end
    end

endmodule