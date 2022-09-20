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
        pass

    def execute_logical_instruction(self):
        pass
