"""
"""
# pylint:disable=import-error,invalid-name
from random import randint

# Device import path
from europi import OLED_WIDTH, ain, b1, b2, cvs, din, k1, k2, oled
from europi_script import EuroPiScript

N_BITS = 8
SQUARE_WIDTH = OLED_WIDTH // N_BITS


def int_to_rule(k):
    rule = []
    for i in range(8):
        if k & 1:
            rule.append(i + 1)
        k = k >> 1
    return rule


def rule_lfsr(start_state, rule, n_bits=8):
    if any(b < 1 or b > n_bits - 1 for b in rule):
        raise ValueError(f"rule must only contain values in range [1, {n_bits - 1}]")
    lfsr = start_state

    while True:
        yield lfsr
        bit = lfsr
        for b in rule:
            bit ^= (lfsr >> b)
        bit &= 1
        lfsr = (lfsr >> 1) | (bit << (n_bits - 1))


class LFSR:
    """Linear-feedback shift register.
    """
    def __init__(self, state=1, rule_number=110, n_bits=8):
        self._state = state
        self._n_bits = n_bits
        self._init_state = state
        self.set_rule(rule_number)

    def set_state(self, state: int):
        """Set the state based on the integer representation."""
        self._state = state
        self._init_state = state

    def get_state_bits(self):
        return '{:0>{w}}'.format(bin(self._state)[2:], w=self._n_bits)

    def randomize_state(self):
        """Randomize the state."""
        self.set_state(randint(1, 2**self._n_bits))

    def reset_state(self):
        """Set state to zero."""
        self._state = self._init_state

    def set_rule(self, rule_number):
        """Update the rule-set."""
        if rule_number < 1 or rule_number > 2**(self._n_bits - 1):
            raise ValueError(f"Rule number must be greater than 1 and less than {2**(self._n_bits - 1)}") 
        self._rule = int_to_rule(rule_number)

    def update_state(self):
        """Update the state according to the rule."""
        bit = self._state
        for b in self._rule:
            bit ^= (self._state >> b)
        bit &= 1
        self._state = (self._state >> 1) | (bit << (self._n_bits - 1))


class EuroPiLFSR(EuroPiScript):
    """Interface to the EuroPi module."""
    def __init__(self):
        super().__init__()
        self._lfsr = LFSR(n_bits=N_BITS)
        self.outputs = [0, 1, 2, 3, 4, 5]
        self._save_state()
        self._n_steps = 256
        self._step = 0

        @b1.handler
        def reset():
            """Set automaton state to zero."""
            self._lfsr.reset_state()
            self._save_state()

        @b2.handler
        def randomize():
            """Randomize automaton state."""
            self._lfsr.randomize_state()
            self._save_state()

        @din.handler
        def gate_on():
            load_state_input = ain.percent()
            if load_state_input > 0.3:
                self._lfsr._state = self.saved_state
            k = k2.read_position(steps=2**self._lfsr._n_bits)
            bits = self._lfsr.get_state_bits()
            for i in range(6):
                if bits[i] == "1":
                    cvs[i].value(1.0)
            self._lfsr.update_state()
            self._step += 1
            if self._step >= self._n_steps:
                self._lfsr.reset_state()
                self._step = 0

        @din.handler_falling
        def gate_off():
            # Turn off all triggers on falling clock trigger to match clock.
            for cv in cvs:
                cv.off()

    def _save_state(self):
        """Save the current state of the automaton."""
        self.saved_state = self._lfsr._state

    def update_screen(self):
        """Update the screen.

        The screen shows:
        - The currently selected rule
        - A representation of the state
        """
        oled.fill(0)
        # Show a representation of the rule
        oled.text(f"RULE ", 0, 0, 1)
        for i in range(self._lfsr._n_bits):
            if i in self._lfsr._rule:
                oled.fill_rect(48 + i*8, 0, 8, 8, 1)
            else:
                oled.rect(48 + i*8, 0, 8, 8, 1)
        
        # Show a representation of the state
        oled.text(f"{self._n_steps}", 0, 16, 1)
        bits = self._lfsr.get_state_bits()
        for i in range(self._lfsr._n_bits):
            if bits[i] == "1":
                oled.fill_rect(48 + i*8, 16, 8, 8, 1)
            else:
                oled.rect(48 + i*8, 16, 8, 8, 1)
        oled.show()

    def main(self):
        """Main loop of the program."""
        # Start the main loop.
        while True:
            self.update_screen()
            rule_number = k1.read_position(2**(self._lfsr._n_bits - 1) - 1)
            self._lfsr.set_rule(rule_number + 1)
            self._n_steps = 2**(k2.read_position(self._lfsr._n_bits) + 1)


if __name__ == "__main__":
    # Reset module display state.
    lfsr = EuroPiLFSR()
    lfsr.main()
