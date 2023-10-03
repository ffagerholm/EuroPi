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
from random import random
from math import cos, sin, pi
from time import sleep_ms

# Device import path
from europi import OLED_WIDTH, OLED_HEIGHT, ain, b1, b2, cvs, din, k1, k2, oled
from europi_script import EuroPiScript


G = 9.8  # acceleration due to gravity, in m/s^2


class ChaosPendulum:
    """Double pendulum.

    Double pendulum that displays chaotic behavior.
    
    Parameters
    ----------
    length_1 : float
        Length of pendulum 1 in m. Default is 1.0
    length_2 : float
        Length of pendulum 2 in m. Default is 1.0
    mass_1 : float
        Mass of pendulum 1 in kg. Default is 1.0
    mass_2 : float
        Mass of pendulum 2 in kg. Default is 1.0
    """
    def __init__(self, 
                 length_1 : float = 1.0,
                 length_2 : float = 1.0,
                 mass_1 : float = 1.0,
                 mass_2 : float = 1.0,
                 dt : float = 0.01
            ):
        self.l1 = length_1
        self.l2 = length_2
        self.m1 = mass_1
        self.m2 = mass_2
        self.dt = dt
        self.state = None
        # initial state
        self.randomize_state()

    def set_state(self, state):
        self.state = state

    def randomize_state(self):
        """Randomize the state."""
        # The initial angles (radians)
        theta_1 = 2*pi*random()
        theta_2 = 2*pi*random()
        omega_1 = 0.0
        omega_2 = 0.0
        self.set_state([theta_1, omega_1, theta_2, omega_2])
    
    def derivs(self, state):
        dydx = list(state)
        dydx[0] = state[1]
        delta = state[2] - state[0]
        den1 = (self.m1+self.m2) * self.l1 - self.m2 * self.l1 * cos(delta) * cos(delta)
        dydx[1] = (
            (
                  self.m2 * self.l1 * state[1] * state[1] * sin(delta) * cos(delta)
                + self.m2 * G * sin(state[2]) * cos(delta)
                + self.m2 * self.l2 * state[3] * state[3] * sin(delta)
                - (self.m1+self.m2) * G * sin(state[0])
            ) / den1
        )
        dydx[2] = state[3]
        den2 = (self.l2 / self.l1) * den1
        dydx[3] = (
            (
                - self.m2 * self.l2 * state[3] * state[3] * sin(delta) * cos(delta)
                + (self.m1+self.m2) * G * sin(state[0]) * cos(delta)
                - (self.m1+self.m2) * self.l1 * state[1] * state[1] * sin(delta)
                - (self.m1+self.m2) * G * sin(state[2])
            ) / den2
        )
        return dydx

    def update_state(self):
        """Update the state according to the rules."""
        y = self.state
        y_d = self.derivs(y)
        y = [a + b*self.dt for a, b in zip(y, y_d)]
        t1 = (y[0] % (2*pi)) / (2*pi)
        x1 = self.l1*sin(y[0])
        y1 = -self.l1*cos(y[0])
        t2 = (y[2] % (2*pi)) / (2*pi)
        x2 = self.l2*sin(y[2])
        y2 = -self.l2*cos(y[2])
        self.state = y
        return t1, x1, y1, t2, x2, y2


class EuroPiChaosPendulum(EuroPiScript):
    """Interface to the EuroPi module."""
    def __init__(self):
        super().__init__()
        self._pendulum = ChaosPendulum()
        self.saved_state = None
        self._save_state()
        self.update_time = 20
        self.scaling = 5.0

        @b1.handler
        def reset():
            """Set system state to the inital saved state."""
            self._pendulum.set_state(self.saved_state)

        @b2.handler
        def randomize():
            """Randomize automaton state."""
            self._pendulum.randomize_state()
            self._save_state()

        @din.handler
        def gate_reset():
            self._pendulum.set_state(self.saved_state)

    def _save_state(self):
        """Save the current state of the automaton."""
        self.saved_state = list(self._pendulum.state)

    def _update_outputs(self, values : list, scaling : float):
        for i, v in enumerate(values):
            cvs[i].voltage(5 + scaling*v)

    def update_screen(self, values : list):
        """Update the screen."""
        oled.fill(0)
        # 128, 32
        oled.text(f"T: {self.update_time}", 0, 0, 1)
        oled.text(f"S: {self.scaling:.1f}", 0, 16, 1)

        # oled.rect(16, int(16 + 15*values[1]), 24, 32, 1)
        # oled.rect(24, int(16 + 15*values[2]), 32, 32, 1)
        # oled.rect(32, int(16 + 15*values[4]), 40, 32, 1)
        # oled.rect(40, int(16 + 15*values[5]), 48, 32, 1)
        
        x_middle = OLED_WIDTH // 2 + 16
        y_middle = OLED_HEIGHT // 2
        length = OLED_HEIGHT // 4

        join_1_x = int(x_middle + length*values[1])
        join_1_y = int(y_middle + length*values[2])
        join_2_x = int(x_middle + length*values[1] + length*values[4])
        join_2_y = int(y_middle + length*values[2] + length*values[5])
        oled.line(
            x_middle,
            y_middle,
            join_1_x,
            join_1_y,
            1
        )
        oled.line(
            join_1_x,
            join_1_y,
            join_2_x,
            join_2_y,
            1
        )
        oled.show()

    def main(self):
        """Main loop"""
        while True:
            self.update_time = k1.range(steps=500) + 1
            self.scaling = 5*k2.percent()
            values = self._pendulum.update_state()
            self._update_outputs(values, self.scaling)
            self.update_screen(values)
            sleep_ms(self.update_time)


if __name__ == "__main__":
    chaos_pendulum = EuroPiChaosPendulum()
    chaos_pendulum.main()
