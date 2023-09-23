"""Get sequencer based on a elementary cellular automaton.
https://en.wikipedia.org/wiki/Elementary_cellular_automaton

The state of the automaton is updated on every trigger on the digital input.
The updates are made according to the rules as described here 

The rules are numbered accoding to the Wolfram code scheme.
There are 256 elementary cellular automata, all with a slightly different
behavior. Some automata doesn't do anything, while some exhibit looping behavior,
and some generate very complex patterns.
"""
# pylint:disable=import-error,invalid-name
from random import choice
from math import factorial

# Device import path
from europi import OLED_WIDTH, ain, b1, b2, cvs, din, k1, k2, oled
from europi_script import EuroPiScript

STATE_SIZE = 16
SQUARE_WIDTH = OLED_WIDTH // STATE_SIZE


def get_rule_set(rule):
    """Generate automaton rule-set.

    The rule-set is a list of outputs
    represented by "0" and "1".s
    """
    rule_bin = bin(rule)[2:]
    n_symbols = len(rule_bin)
    rule_bin = (8 - n_symbols)*"0" + rule_bin
    rule_set = [rule_bin[i] for i in range(7, -1, -1)]
    return rule_set


def choose(n, k):
    """n choose k
    Compute the total number of unique k-combinations in a set of n elements.
    """
    if n < k:
        return 0
    return factorial(n) / (factorial(k) * factorial(n - k))


def combination(n, k, m):
    """Get the n:th combination.
    Compute the mth combination in lexicographical order from a set of n
    elements chosen k at a time.
    Algorithm from http://msdn.microsoft.com/en-us/library/aa289166(v=vs.71).aspx
    From https://gist.github.com/jonesinator/eed9614d2599921d5a4caffd7f2055bb
    """
    # TODO: Update this function to return only 
    result = []
    a      = n
    b      = k
    x      = (choose(n, k) - 1) - m
    for _ in range(0, k):
        a = a - 1
        while choose(a, b) > x:
            a = a - 1
        result.append(n - 1 - a)
        x = x - choose(a, b)
        b = b - 1
    return result

class ElementaryCellularAutomata:
    """Elementary cellular automaton.
    """
    def __init__(self, length=STATE_SIZE, rule=110, randomize=False):
        self.length = length
        self.rule = rule
        self.state = ["0" for _ in range(self.length)]
        self.rule_set = get_rule_set(self.rule)
        if randomize:
            self.randomize_state()

    def set_state(self, s: int):
        """Set the state based on the integer representation."""
        state = bin(s)[2:]
        self.state = list("0"*(STATE_SIZE - len(state)) + state)

    def randomize_state(self):
        """Randomize the state."""
        self.state = [choice("01") for _ in range(self.length)]

    def reset_state(self):
        """Set state to zero."""
        self.state = ["0" for _ in range(self.length)]

    def _apply_rule(self, n):
        """Get output based on rule-set."""
        return self.rule_set[n]

    def update_ruleset(self, rule):
        """Update the rule-set."""
        self.rule = rule
        self.rule_set = get_rule_set(rule)

    def update_state(self):
        """Update the state according to the rules."""
        new_state = list(self.state)
        for i in range(self.length):
            s = self.state[i - 1] + self.state[i] + self.state[(i + 1) % self.length]
            n = int(s, 2)
            new_state[i] = str(self._apply_rule(n))
            self.state = new_state
        return self.state


class EuroPiCellularAutomata(EuroPiScript):
    """Interface to the EuroPi module."""
    def __init__(self):
        super().__init__()
        self._ca = ElementaryCellularAutomata()
        self.outputs = [0, 1, 2, 3, 4, 5]
        self._save_state()

        @b1.handler
        def reset():
            """Set automaton state to zero."""
            self._ca.reset_state()
            self._save_state()

        @b2.handler
        def randomize():
            """Randomize automaton state."""
            self._ca.randomize_state()
            self._save_state()

        @din.handler
        def gate_on():
            load_state_input = ain.percent()
            if load_state_input > 0.3:
                self._ca.state = self.saved_state
            k = k2.read_position(steps=100)
            self.outputs = combination(STATE_SIZE, 6, 8*k)
            for i in range(6):
                if self._ca.state[self.outputs[i]] == "1":
                    cvs[i].value(1.0)
            self._ca.update_state()

        @din.handler_falling
        def gate_off():
            # Turn off all triggers on falling clock trigger to match clock.
            for cv in cvs:
                cv.off()

    def _save_state(self):
        """Save the current state of the automaton."""
        self.saved_state = list(self._ca.state)

    def update_screen(self):
        """Update the screen.

        The screen shows:
        - The currently selected rule
        - A representation of the state
        - Indicators for which state cells determine the output gates.
        """
        oled.fill(0)
        # Show the rule.
        oled.text(f"R: {self._ca.rule}", 0, 0, 1)
        # Add state representation.
        for i in range(self._ca.length):
            if self._ca.state[i] == "1":
                oled.fill_rect(i*8, 16, 8, 8, 1)
            else:
                oled.rect(i*8, 16, 8, 8, 1)
        # Add output indicators
        for k in self.outputs:
            oled.text("v", 8*k, 8, 1)
        oled.show()

    def main(self):
        """Main loop of the program."""
        # Start the main loop.
        while True:
            self.update_screen()
            rule = k1.read_position(steps=256)
            self._ca.update_ruleset(rule=rule)


if __name__ == "__main__":
    # Reset module display state.
    cellular_automata = EuroPiCellularAutomata()
    cellular_automata.main()
