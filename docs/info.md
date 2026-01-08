<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## How it works

This project is an SPI-controlled PWM generator. It receives configuration commands via SPI (Mode 0, write-only) and outputs PWM signals on 8 channels.

The SPI interface uses a 16-bit transaction format: 1 R/W bit + 7-bit address + 8-bit data. (Read values will be ignored.) Five registers control output enables (0x00, 0x01), PWM enables (0x02, 0x03), and duty cycle (0x04). The PWM runs at 3 kHz with 8-bit resolution (0-255).

Each output can be disabled (forced low), enabled as static high, or enabled as PWM based on the enable register settings. All enabled PWM registers share the same duty cycle.

## How to test

Run the cocotb tests in the `test/` directory:

cd test 
make -B

Three tests verify SPI communication, PWM frequency (3 kHz ±1%), and duty cycle accuracy across values in the duty cycle array. All tests should pass.