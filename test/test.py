# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotb.triggers import ClockCycles
from cocotb.types import Logic
from cocotb.types import LogicArray


async def await_half_sclk(dut):
    """Wait for the SCLK signal to go high or low."""
    start_time = cocotb.utils.get_sim_time(units="ns")
    while True:
        await ClockCycles(dut.clk, 1)
        # Wait for half of the SCLK period (10 us)
        if (start_time + 100*100*0.5) < cocotb.utils.get_sim_time(units="ns"):
            break
    return

def ui_in_logicarray(ncs, bit, sclk):
    """Setup the ui_in value as a LogicArray."""
    return LogicArray(f"00000{ncs}{bit}{sclk}")

async def send_spi_transaction(dut, r_w, address, data):
    """
    Send an SPI transaction with format:
    - 1 bit for Read/Write
    - 7 bits for address
    - 8 bits for data
    
    Parameters:
    - r_w: boolean, True for write, False for read
    - address: int, 7-bit address (0-127)
    - data: LogicArray or int, 8-bit data
    """
    # Convert data to int if it's a LogicArray
    if isinstance(data, LogicArray):
        data_int = int(data)
    else:
        data_int = data
    # Validate inputs
    if address < 0 or address > 127:
        raise ValueError("Address must be 7-bit (0-127)")
    if data_int < 0 or data_int > 255:
        raise ValueError("Data must be 8-bit (0-255)")
    # Combine RW and address into first byte
    first_byte = (int(r_w) << 7) | address
    # Start transaction - pull CS low
    sclk = 0
    ncs = 0
    bit = 0
    # Set initial state with CS low
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 1)
    # Send first byte (RW + Address)
    for i in range(8):
        bit = (first_byte >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # Send second byte (Data)
    for i in range(8):
        bit = (data_int >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # End transaction - return CS high
    sclk = 0
    ncs = 1
    bit = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 600)
    return ui_in_logicarray(ncs, bit, sclk)
    
@cocotb.test()
async def test_spi(dut):
    dut._log.info("Start SPI test")

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    dut._log.info("Test project behavior")
    dut._log.info("Write transaction, address 0x00, data 0xF0")
    ui_in_val = await send_spi_transaction(dut, 1, 0x00, 0xF0)  # Write transaction
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 1000) 

    dut._log.info("Write transaction, address 0x01, data 0xCC")
    ui_in_val = await send_spi_transaction(dut, 1, 0x01, 0xCC)  # Write transaction
    assert dut.uio_out.value == 0xCC, f"Expected 0xCC, got {dut.uio_out.value}"
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x30 (invalid), data 0xAA")
    ui_in_val = await send_spi_transaction(dut, 1, 0x30, 0xAA)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Read transaction (invalid), address 0x00, data 0xBE")
    ui_in_val = await send_spi_transaction(dut, 0, 0x30, 0xBE)
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 100)
    
    dut._log.info("Read transaction (invalid), address 0x41 (invalid), data 0xEF")
    ui_in_val = await send_spi_transaction(dut, 0, 0x41, 0xEF)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x02, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x02, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x04, data 0xCF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xCF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x00")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x00)  # Write transaction
    await ClockCycles(dut.clk, 30000)


    dut._log.info("SPI test completed successfully")

@cocotb.test()
async def test_pwm_freq(dut):
    # Write your test here
    expected_freq_hz = 3000  # 3 kHz
    expected_period_ns = 1e9 / expected_freq_hz  # 333,333.33 ns

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    dut._log.info("Write transaction, address 0x00, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x00, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 3000)

    dut._log.info("Write transaction, address 0x01, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x01, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 3000)

    dut._log.info("Write transaction, address 0x02, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x02, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 3000)

    dut._log.info("Write transaction, address 0x03, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x03, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 3000)

    dut._log.info(f"Write transaction, address 0x04, data 0xC1")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xC1)  # Write transaction
    await ClockCycles(dut.clk, 3000)
    
    duty_rising_edge_times = [0,0]
    
    PWM2 = 0
    PWM1 = 0
    
    for a in range(0,2):
        i = 0
        while True: 
            await ClockCycles(dut.clk,1)

            PWM2 = PWM1
            PWM1 = dut.uo_out.value[0]
            i += 1

            if(i > 10**5):
                break

            if(PWM1 == 1 and PWM2 == 0):
                duty_rising_edge_times[a] = cocotb.utils.get_sim_time(units='ns')
            
            if(PWM1 == 0 and PWM2 == 1): 
                break
            
        
    period = duty_rising_edge_times[1] - duty_rising_edge_times[0]
    
    assert (period >= 0.99*expected_period_ns and period <= 1.01*expected_period_ns), \
    f"expected period was {expected_period_ns} ± 1%, got a period of {period}"

    dut._log.info("PWM Frequency test completed successfully")
    


@cocotb.test()
async def test_pwm_duty(dut):
    # Write your test here
    expected_freq_hz = 3000  # 3 kHz
    expected_period_ns = 1e9 / expected_freq_hz  # 333,333.33 ns

    # duty_cycles = [duty for duty in range(0,256)]
    duty_cycles = [0,0x80, 0xFF]

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    

    dut._log.info("Write transaction, address 0x01, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x01, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 3000)
    
    dut._log.info("Write transaction, address 0x02, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x02, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 3000)

    dut._log.info("Write transaction, address 0x00, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x00, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 3000)


    dut._log.info("Write transaction, address 0x03, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x03, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 3000)

    dut._log.info(f"Write transaction, address 0x04, data 0x00")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x00)  # Write transaction
    await ClockCycles(dut.clk, 3000)

    for duty in duty_cycles:
        ui_in_val = await send_spi_transaction(dut, 1, 0x04, duty)  # Write transaction
        expected_pulse_width = duty * expected_period_ns / 256

        PWM2 = 0
        PWM1 = 0
        t_rising_edge = 0
        t_falling_edge = 0
        i = 0
        if duty == 0:
            for i in range(20):
                await ClockCycles(dut.clk, int(expected_period_ns/100))
                assert(dut.uo_out.value[0] == 0), f"expected 0% duty cycle, Duty cycle : {duty}"
            dut._log.info(f"Complete Duty check {duty}")
            continue  
                
        elif duty == 255:
            for i in range(20):
                await ClockCycles(dut.clk, int(expected_period_ns/100))
                assert(dut.uo_out.value[0] == 1), f"expected 100% duty cycle, Duty cycle : {duty}"
            dut._log.info(f"Complete Duty check {duty}")
            continue  
        

        while i < 10**5:
            await ClockCycles(dut.clk, 1)
            PWM2 = PWM1
            PWM1 = dut.uo_out.value[0]
            i += 1
            
            if PWM1 == 0 and PWM2 == 1:  
                break
        assert i < 10**5, f"Timeout waiting for falling edge sync, duty: {duty}"       

        i = 0
        while i < 10**5:
            await ClockCycles(dut.clk,1)

            PWM2 = PWM1
            PWM1 = dut.uo_out.value[0]
            i += 1

            if(PWM1 == 1 and PWM2 == 0):
                t_rising_edge  = cocotb.utils.get_sim_time(units='ns')
            
            if(PWM1 == 0 and PWM2 == 1): 
                t_falling_edge = cocotb.utils.get_sim_time(units='ns')
                break

        assert i < 10**5, f"Timeout waiting for pulse edges, duty: {duty}"
        high_time = t_falling_edge - t_rising_edge

        assert(high_time >= expected_pulse_width *0.99 and high_time <= expected_pulse_width*1.01),\
        f"expected a pulse width of {expected_pulse_width}ns, got {high_time}ns. Duty cycle : {duty}"
        dut._log.info(f"Complete Duty check {duty}")

        


    dut._log.info("PWM Duty Cycle test completed successfully")
    