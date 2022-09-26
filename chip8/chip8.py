import pygame

from pygame import key
from random import randint

from chip8.config import (
    MAX_MEMORY, STACK_POINTER_START, KEY_MAPPINGS, PROGRAM_COUNTER_START
)

# C O N S T A N T S ###########################################################

# The total number of registers in the Chip 8 CPU
NUM_REGISTERS = 0x10

# The various modes of operation
MODE_NORMAL = 'normal'
MODE_EXTENDED = 'extended'

class UnknownOpCodeException(Exception):
    """
    A class to raise unknown op code exceptions.
    """
    def __init__(self, op_code):
        Exception.__init__(self, "Unknown op-code: {:X}".format(op_code))

class Chip8CPU(object):

    def __init__(self, screen):
        """
        Initialize the Chip8 CPU. The only required parameter is a screen
        object that supports the draw_pixel function. For testing purposes,
        this can be set to None.
        :param screen: the screen object to draw pixels on
        """
        # There are two timer registers, one for sound and one that is general
        # purpose known as the delay timer. The timers are loaded with a value
        # and then decremented 60 times per second.
        self.timers = {
            'delay': 0,
            'sound': 0,
        }

        self.registers = {
            'v': [],
            'index': 0,
            'sp': 0,
            'pc': 0,
            'rpl': []
        }

        self.operation_lookup = {
            0x0: self.clear_return,  # 0nnn - SYS  nnn
            0x1: self.jump_to_address,  # 1nnn - JUMP nnn
            0x2: self.jump_to_subroutine,  # 2nnn - CALL nnn
            0x3: self.skip_if_reg_equal_val,  # 3snn - SKE  Vs, nn
            0x4: self.skip_if_reg_not_equal_val,  # 4snn - SKNE Vs, nn
            0x5: self.skip_if_reg_equal_reg,  # 5st0 - SKE  Vs, Vt
            0x6: self.move_value_to_reg,  # 6snn - LOAD Vs, nn
            0x7: self.add_value_to_reg,  # 7snn - ADD  Vs, nn
            0x8: self.execute_logical_instruction,  # see subfunctions below
            0x9: self.skip_if_reg_not_equal_reg,  # 9st0 - SKNE Vs, Vt
            0xA: self.load_index_reg_with_value,  # Annn - LOAD I, nnn
            0xB: self.jump_to_index_plus_value,  # Bnnn - JUMP [I] + nnn
            0xC: self.generate_random_number,  # Ctnn - RAND Vt, nn
            0xD: self.draw_sprite,  # Dstn - DRAW Vs, Vy, n
            0xE: self.keyboard_routines,  # see subfunctions below
            0xF: self.misc_routines,  # see subfunctions below
        }

        self.logical_operation_lookup = {
            0x0: self.move_reg_into_reg,  # 8st0 - LOAD Vs, Vt
            0x1: self.logical_or,  # 8st1 - OR   Vs, Vt
            0x2: self.logical_and,  # 8st2 - AND  Vs, Vt
            0x3: self.exclusive_or,  # 8st3 - XOR  Vs, Vt
            0x4: self.add_reg_to_reg,  # 8st4 - ADD  Vs, Vt
            0x5: self.subtract_reg_from_reg,  # 8st5 - SUB  Vs, Vt
            0x6: self.right_shift_reg,  # 8st6 - SHR  Vs
            0x7: self.subtract_reg_from_reg1,  # 8st7 - SUBN Vs, Vt
            0xE: self.left_shift_reg,  # 8stE - SHL  Vs
        }

        self.misc_routine_lookup = {
            0x07: self.move_delay_timer_into_reg,  # Ft07 - LOAD Vt, DELAY
            0x0A: self.wait_for_keypress,  # Ft0A - KEYD Vt
            0x15: self.move_reg_into_delay_timer,  # Fs15 - LOAD DELAY, Vs
            0x18: self.move_reg_into_sound_timer,  # Fs18 - LOAD SOUND, Vs
            0x1E: self.add_reg_into_index,  # Fs1E - ADD  I, Vs
            0x29: self.load_index_with_reg_sprite,  # Fs29 - LOAD I, Vs
            0x30: self.load_index_with_extended_reg_sprite,  # Fs30 - LOAD I, Vs
            0x33: self.store_bcd_in_memory,  # Fs33 - BCD
            0x55: self.store_regs_in_memory,  # Fs55 - STOR [I], Vs
            0x65: self.read_regs_from_memory,  # Fs65 - LOAD Vs, [I]
            0x75: self.store_regs_in_rpl,  # Fs75 - SRPL Vs
            0x85: self.read_regs_from_rpl,  # Fs85 - LRPL Vs
        }

        self.operand = 0
        self.mode = MODE_NORMAL
        self.screen = screen
        self.memory = bytearray(MAX_MEMORY)
        self.reset()
        self.running = True

    def execute_instruction(self, operand=None):
        """
        :param operand: the operand to execute
        :return: returns the operand executed
        """
        if operand:
            self.operand = operand
        else:
            self.operand = int(self.memory[self.registers['pc']])
            self.operand = self.operand << 8
            self.operand += int(self.memory[self.registers['pc'] + 1])
            self.registers['pc'] += 2
        operation = (self.operand & 0xF000) >> 12
        self.operation_lookup[operation]()
        return self.operand

    def execute_logical_instruction(self):
        operation = self.operand & 0x000F
        try:
            self.logical_operation_lookup[operation]()
        except KeyError:
            raise UnknownOpCodeException(self.operand)

    def clear_return(self):
        """
        Opcodes starting with a 0 are one of the following instructions:

            0nnn - Jump to machine code function (ignored)
            00Cn - Scroll n pixels down
            00E0 - Clear the display
            00EE - Return from subroutine
            00FB - Scroll 4 pixels right
            00FC - Scroll 4 pixels left
            00FD - Exit
            00FE - Disable extended mode
            00FF - Enable extended mode
        """
        operation = self.operand & 0x00FF
        sub_operation = operation & 0x00F0
        if sub_operation == 0x00C0:
            num_lines = self.operand & 0x000F
            self.screen.scroll_down(num_lines)

        if operation == 0x00E0:
            self.screen.clear_screen()

        if operation == 0x00EE:
            self.return_from_subroutine()

        if operation == 0x00FB:
            self.screen.scroll_right()

        if operation == 0x00FC:
            self.screen.scroll_left()

        if operation == 0x00FD:
            self.running = False

        if operation == 0x00FE:
            self.disable_extended_mode()

        if operation == 0x00FF:
            self.enable_extended_mode()

    def return_from_subroutine(self):
        """
        00EE - RTS

        Return from subroutine. Pop the current value in the stack pointer
        off of the stack, and set the program counter to the value popped.
        """
        self.registers['sp'] -= 1
        self.registers['pc'] = self.memory[self.registers['sp']] << 8
        self.registers['sp'] -= 1
        self.registers['pc'] += self.memory[self.registers['sp']]

    def jump_to_address(self):
        """
        1nnn - JUMP nnn

        Jump to address. The address to jump to is calculated using the bits
        taken from the operand as follows:

           Bits:  15-12    11-8      7-4      3-0
                  unused  address  address  address
        """
        self.registers['pc'] = self.operand & 0x0FFF

    def jump_to_subroutine(self):
        """
        2nnn - CALL nnn

        Jump to subroutine. Save the current program counter on the stack. The
        subroutine to jump to is taken from the operand as follows:

           Bits:  15-12    11-8      7-4      3-0
                  unused  address  address  address
        """
        self.memory[self.registers['sp']] = self.registers['pc'] & 0x00FF
        self.registers['sp'] += 1
        self.memory[self.registers['sp']] = (self.registers['pc'] & 0xFF00) >> 8
        self.registers['sp'] += 1
        self.registers['pc'] = self.operand & 0x0FFF

    def skip_if_reg_equal_val(self):
        """
        3snn - SKE Vs, nn

        Skip if register contents equal to constant value. The calculation for
        the register and constant is performed on the operand:

           Bits:  15-12     11-8      7-4       3-0
                  unused   source  constant  constant

        The program counter is updated to skip the next instruction by
        advancing it by 2 bytes.
        """
        source = (self.operand & 0x0F00) >> 8
        if self.registers['v'][source] == (self.operand & 0x00FF):
            self.registers['pc'] += 2

    def skip_if_reg_not_equal_val(self):
        """
        4snn - SKNE Vs, nn

        Skip if register contents not equal to constant value. The calculation
        for the register and constant is performed on the operand:

           Bits:  15-12     11-8      7-4       3-0
                  unused   source  constant  constant

        The program counter is updated to skip the next instruction by
        advancing it by 2 bytes.
        """
        source = (self.operand & 0x0F00) >> 8
        if self.registers['v'][source] != (self.operand & 0x00FF):
            self.registers['pc'] += 2

    def skip_if_reg_equal_reg(self):
        """
        5st0 - SKE Vs, Vt

        Skip if source register is equal to target register. The calculation
        for the registers to use is performed on the operand:

           Bits:  15-12     11-8      7-4       3-0
                  unused   source    target      0

        The program counter is updated to skip the next instruction by
        advancing it by 2 bytes.
        """
        source = (self.operand & 0x0F00) >> 8
        target = (self.operand & 0x00F0) >> 4
        if self.registers['v'][source] == self.registers['v'][target]:
            self.registers['pc'] += 2

    def move_value_to_reg(self):
        """
        6snn - LOAD Vs, nn

        Move the constant value into the specified register. The calculation
        for the registers is performed on the operand:

           Bits:  15-12     11-8      7-4       3-0
                  unused   target    value     value
        """
        target = (self.operand & 0x0F00) >> 8
        self.registers['v'][target] = self.operand & 0x00FF

    def add_value_to_reg(self):
        """
        7snn - ADD Vs, nn

        Add the constant value to the specified register. The calculation
        for the registers is performed on the operand:

           Bits:  15-12     11-8      7-4       3-0
                  unused   target    value     value
        """
        target = (self.operand & 0x0F00) >> 8
        temp = self.registers['v'][target] + (self.operand & 0x00FF)
        self.registers['v'][target] = temp if temp < 256 else temp - 256

    def move_reg_into_reg(self):
        """
        8st0 - LOAD Vs, Vt

        Move the value of the source register into the value of the target
        register. The calculation for the registers is performed on the
        operand:

           Bits:  15-12     11-8      7-4       3-0
                  unused   target    source      0
        """
        target = (self.operand & 0x0F00) >> 8
        source = (self.operand & 0x00F0) >> 4
        self.registers['v'][target] = self.registers['v'][source]

    def logical_or(self):
        """
        8ts1 - OR   Vs, Vt

        Perform a logical OR operation between the source and the target
        register, and store the result in the target register. The register
        calculations are as follows:

           Bits:  15-12     11-8      7-4       3-0
                  unused   target    source      1
        """
        target = (self.operand & 0x0F00) >> 8
        source = (self.operand & 0x00F0) >> 4
        self.registers['v'][target] |= self.registers['v'][source]

    def logical_and(self):
        """
        8ts2 - AND  Vs, Vt

        Perform a logical AND operation between the source and the target
        register, and store the result in the target register. The register
        calculations are as follows:

           Bits:  15-12     11-8      7-4       3-0
                  unused   target    source      2
        """
        target = (self.operand & 0x0F00) >> 8
        source = (self.operand & 0x00F0) >> 4
        self.registers['v'][target] &= self.registers['v'][source]

    def exclusive_or(self):
        """
        8ts3 - XOR  Vs, Vt

        Perform a logical XOR operation between the source and the target
        register, and store the result in the target register. The register
        calculations are as follows:

           Bits:  15-12     11-8      7-4       3-0
                  unused   target    source      3
        """
        target = (self.operand & 0x0F00) >> 8
        source = (self.operand & 0x00F0) >> 4
        self.registers['v'][target] ^= self.registers['v'][source]

    def add_reg_to_reg(self):
        """
        8ts4 - ADD  Vt, Vs

        Add the value in the source register to the value in the target
        register, and store the result in the target register. The register
        calculations are as follows:

           Bits:  15-12     11-8      7-4       3-0
                  unused   target    source      4

        If a carry is generated, set a carry flag in register VF.
        """
        target = (self.operand & 0x0F00) >> 8
        source = (self.operand & 0x00F0) >> 4
        temp = self.registers['v'][target] + self.registers['v'][source]
        if temp > 255:
            self.registers['v'][target] = temp - 256
            self.registers['v'][0xF] = 1
        else:
            self.registers['v'][target] = temp
            self.registers['v'][0xF] = 0

    def subtract_reg_from_reg(self):
        """
        8ts5 - SUB  Vt, Vs

        Subtract the value in the target register from the value in the source
        register, and store the result in the target register. The register
        calculations are as follows:

           Bits:  15-12     11-8      7-4       3-0
                  unused   target    source      5

        If a borrow is NOT generated, set a carry flag in register VF.
        """
        target = (self.operand & 0x0F00) >> 8
        source = (self.operand & 0x00F0) >> 4
        source_reg = self.registers['v'][source]
        target_reg = self.registers['v'][target]
        if target_reg > source_reg:
            target_reg -= source_reg
            self.registers['v'][0xF] = 1
        else:
            target_reg = 256 + target_reg - source_reg
            self.registers['v'][0xF] = 0
        self.registers['v'][target] = target_reg

    def right_shift_reg(self):
        """
        8st6 - SHR  Vs, Vt

        Shift the bits in the source register 1 bit to the right and
        stores the result in the target register, leaving source
        with its original value. Bit 0 will be shifted into register
        vf. The register calculation is as follows:

           Bits:  15-12     11-8      7-4       3-0
                  unused   source    target      6
        """
        source = (self.operand & 0x0F00) >> 8
        target = (self.operand & 0x00F0) >> 4
        bit_zero = self.registers['v'][source] & 0x1
        self.registers['v'][target] = self.registers['v'][source] >> 1
        self.registers['v'][0xF] = bit_zero

    def subtract_reg_from_reg1(self):
        """
        8ts7 - SUBN Vt, Vs

        Subtract the value in the source register from the value in the target
        register, and store the result in the target register. The register
        calculations are as follows:

           Bits:  15-12     11-8      7-4       3-0
                  unused   target    source      7

        If a borrow is NOT generated, set a carry flag in register VF.
        """
        target = (self.operand & 0x0F00) >> 8
        source = (self.operand & 0x00F0) >> 4
        source_reg = self.registers['v'][source]
        target_reg = self.registers['v'][target]
        if source_reg > target_reg:
            target_reg = source_reg - target_reg
            self.registers['v'][0xF] = 1
        else:
            target_reg = 256 + source_reg - target_reg
            self.registers['v'][0xF] = 0
        self.registers['v'][target] = target_reg

    def left_shift_reg(self):
        """
        8stE - SHL  Vs, Vt

        Shift the bits in the source register 1 bit to the left and
        stores the result in the target register, leaving the source
        register with its original value. Bit 7 will be shifted into
        register vf. The register calculation is as follows:

           Bits:  15-12     11-8      7-4       3-0
                  unused   source    target      E
        """
        source = (self.operand & 0x0F00) >> 8
        target = (self.operand & 0x00F0) >> 4
        bit_seven = (self.registers['v'][source] & 0x80) >> 8
        self.registers['v'][target] = self.registers['v'][source] << 1
        self.registers['v'][0xF] = bit_seven

    def skip_if_reg_not_equal_reg(self):
        """
        9st0 - SKNE Vs, Vt

        Skip if source register is equal to target register. The calculation
        for the registers to use is performed on the operand:

           Bits:  15-12     11-8      7-4       3-0
                  unused   source    target    unused

        The program counter is updated to skip the next instruction by
        advancing it by 2 bytes.
        """
        source = (self.operand & 0x0F00) >> 8
        target = (self.operand & 0x00F0) >> 4
        if self.registers['v'][source] != self.registers['v'][target]:
            self.registers['pc'] += 2

    def load_index_reg_with_value(self):
        """
        Annn - LOAD I, nnn

        Load index register with constant value. The calculation for the
        constant value is performed on the operand:

           Bits:  15-12     11-8      7-4       3-0
                  unused   constant  constant  constant
        """
        self.registers['index'] = self.operand & 0x0FFF

    def jump_to_index_plus_value(self):
        """
        Bnnn - JUMP [I] + nnn

        Load the program counter with the memory value located at the specified
        operand plus the value of the index register. The address calculation
        is based on the operand, masked as follows:

           Bits:  15-12     11-8      7-4       3-0
                  unused   address  address  address
        """
        self.registers['pc'] = self.registers['index'] + (self.operand & 0x0FFF)

    def generate_random_number(self):
        """
        Ctnn - RAND Vt, nn

        A random number between 0 and 255 is generated. The contents of it are
        then ANDed with the constant value passed in the operand. The result is
        stored in the target register. The register and constant values are
        calculated as follows:

           Bits:  15-12     11-8      7-4       3-0
                  unused    target    value    value
        """
        value = self.operand & 0x00FF
        target = (self.operand & 0x0F00) >> 8
        self.registers['v'][target] = value & randint(0, 255)

    def draw_sprite(self):
        """
        Dxyn - DRAW x, y, num_bytes

        Draws the sprite pointed to in the index register at the specified
        x and y coordinates. Drawing is done via an XOR routine, meaning that
        if the target pixel is already turned on, and a pixel is set to be
        turned on at that same location via the draw, then the pixel is turned
        off. The routine will wrap the pixels if they are drawn off the edge
        of the screen. Each sprite is 8 bits (1 byte) wide. The num_bytes
        parameter sets how tall the sprite is. Consecutive bytes in the memory
        pointed to by the index register make up the bytes of the sprite. Each
        bit in the sprite byte determines whether a pixel is turned on (1) or
        turned off (0). For example, assume that the index register pointed
        to the following 7 bytes:

                       bit 0 1 2 3 4 5 6 7

           byte 0          0 1 1 1 1 1 0 0
           byte 1          0 1 0 0 0 0 0 0
           byte 2          0 1 0 0 0 0 0 0
           byte 3          0 1 1 1 1 1 0 0
           byte 4          0 1 0 0 0 0 0 0
           byte 5          0 1 0 0 0 0 0 0
           byte 6          0 1 1 1 1 1 0 0

        This would draw a character on the screen that looks like an 'E'. The
        x_source and y_source tell which registers contain the x and y
        coordinates for the sprite. If writing a pixel to a location causes
        that pixel to be turned off, then VF will be set to 1.

           Bits:  15-12     11-8      7-4       3-0
                  unused    x_source  y_source  num_bytes
        """
        x_source = (self.operand & 0x0F00) >> 8
        y_source = (self.operand & 0x00F0) >> 4
        x_pos = self.registers['v'][x_source]
        y_pos = self.registers['v'][y_source]
        num_bytes = self.operand & 0x000F
        self.registers['v'][0xF] = 0

        if self.mode == MODE_EXTENDED and num_bytes == 0:
            self.draw_extended(x_pos, y_pos, 16)
        else:
            self.draw_normal(x_pos, y_pos, num_bytes)

