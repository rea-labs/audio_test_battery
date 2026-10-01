# NEW VERSION where the inner value defines the start size and step sizes that are 
# used to make the configuration more or less difficult on successive trials.  
# Use this as a guide for modifying the existing version, it's missing a lot of 
# complexity (e.g. catch trials, TP/FN/FP/TN, etc.) --> need to modify recursive 
# loop so it advances when the trial coundown finishes

from dataclasses import dataclass


# ===========================================================
# VarSpec container
# ===========================================================
@dataclass
class VarSpec:
    name: str
    data: any   # list OR dict for staircase config


# ===========================================================
# Staircase implementing your new rules 
# --> this logic is already (more or less) implemented
# ===========================================================
class Staircase:
    """
    NEW RULES:
      1. Begin with large initial_step_down
      2. Continue stepping DOWN until first reversal
      3. After first reversal → use small symmetric steps
      4. After reversal → run N more trials then stop
    """

    def __init__(self, start, initial_step_down,
                 small_step_down, small_step_up,
                 min_level, max_level,
                 extra_trials_after_reversal):

        self.level = start

        self.initial_step_down = initial_step_down
        self.small_step_down = small_step_down
        self.small_step_up = small_step_up # just use one small_step_up/down size??

        self.min_level = min_level
        self.max_level = max_level

        self.extra_trials_after_reversal = extra_trials_after_reversal
        self.remaining_post_reversal = None

        self.last_direction = None
        self.reversal_detected = False
        self.finished = False

    def next(self, heard):
        """Advance staircase given user response."""

        if self.finished:
            return None

        # Direction of movement
        direction = "down" if heard else "up"

        # Detect first reversal
        if self.last_direction and direction != self.last_direction:
            if not self.reversal_detected:
                self.reversal_detected = True
                self.remaining_post_reversal = self.extra_trials_after_reversal

        self.last_direction = direction

        # Step magnitude depends on pre/post reversal status
        if not self.reversal_detected:
            step = -self.initial_step_down
        else:
            step = -self.small_step_down if direction == "down" else self.small_step_up

        # Apply update
        new_level = self.level + step
        self.level = max(self.min_level, min(self.max_level, new_level))

        # Count down post-reversal trials
        if self.reversal_detected:
            self.remaining_post_reversal -= 1
            if self.remaining_post_reversal <= 0:
                self.finished = True

        return self.level


# ===========================================================
# Base paradigm class
# ===========================================================
class ParadigmBase:
    """
    Automatically identifies:
      - self.inner_var  from key "inner"
      - self.outer_vars from keys starting with "outer_"
    """

    def __init__(self, params: dict[str, VarSpec]):
        self.params = params

        # Make attributes using their key names --> self.inner, self.outer_1, ...
        for key, spec in params.items(): # .items() returns the name and associated data as a "dict_items" object
            # key is the variable name (e.g. var_1, var_2, ...)
            # spec is the associated VarSpec object 
            # e.g. VarSpec(name='frequency', data=[100, 200])
            setattr(self, key, spec)

        # Make attributes like self.frequency, self.amplitude, ...
        for spec in params.values(): # .values() only returns the data as a "dict_values" object
            setattr(self, spec.name, spec.data)

        # Loop role extraction
        self.inner_var = params["inner"] # gets the dict_value that has a loop_role of "inner"
        self.outer_vars = [ # gets the dict_values that has a loop_role of "outer_*"
            params[k] for k in params 
            if k.startswith("outer_")
        ]

    def run(self):
        results = []
        self._recursive_loop(0, {}, results)
        return results

    def _recursive_loop(self, idx, chosen, results):
        """Generic outer-loop recursion."""

        if idx < len(self.outer_vars):
            outer = self.outer_vars[idx]
            for value in outer.data:
                chosen[outer.name] = value
                self._recursive_loop(idx + 1, chosen, results)
            return

        # Now run the staircase for this outer-condition combination
        self._run_staircase(chosen, results)

    # -------------------------------------------------------
    # Staircase runner
    # -------------------------------------------------------
    def _run_staircase(self, chosen, results):

        cfg = self.inner_var.data

        staircase = Staircase(
            start=cfg["start"],
            initial_step_down=cfg["initial_step_down"],
            small_step_down=cfg["small_step_down"],
            small_step_up=cfg["small_step_up"],
            min_level=cfg["min_level"],
            max_level=cfg["max_level"],
            extra_trials_after_reversal=cfg["extra_trials_after_reversal"],
        )

        # Temporary simulation of user's hearing for demo purposes
        def fake_user_heard(level):
            return level > 25

        # Generate staircase trials
        while not staircase.finished:
            level = staircase.level
            chosen[self.inner_var.name] = level
            trial = self.generate_trial(**chosen)
            results.append(trial)

            heard = fake_user_heard(level)
            staircase.next(heard)


# ===========================================================
# Paradigm A
# ===========================================================
class ParadigmA(ParadigmBase):

    def __init__(self):
        params = {
            "inner": VarSpec(
                name="amplitude",
                data=dict(
                    start=60,
                    initial_step_down=15,
                    small_step_down=5,
                    small_step_up=5,
                    min_level=-20,
                    max_level=120,
                    extra_trials_after_reversal=10,
                ),
            ),
            "outer_1": VarSpec(name="frequency", data=[500, 1000]),
            "outer_2": VarSpec(name="mod_index", data=[0.1, 0.2]),
        }
        super().__init__(params)

    def generate_trial(self, amplitude, frequency, mod_index):
        print(f"[A] Trial: amp={amplitude}, f={frequency}, β={mod_index}")
        return dict(amplitude=amplitude, frequency=frequency, mod_index=mod_index)


# ===========================================================
# Paradigm B
# ===========================================================
class ParadigmB(ParadigmBase):

    def __init__(self):
        params = {
            "inner": VarSpec(
                name="gap_ms",
                data=dict(
                    start=30,
                    initial_step_down=10,
                    small_step_down=3,
                    small_step_up=3,
                    min_level=1,
                    max_level=200,
                    extra_trials_after_reversal=8,
                ),
            ),
            "outer_1": VarSpec(name="frequency", data=[500, 1500]),
            "outer_2": VarSpec(name="noise_level", data=[20, 40]),
            "outer_3": VarSpec(name="something_else", data=[1, 2]),
        }
        super().__init__(params)

    def generate_trial(self, gap_ms, frequency, noise_level, something_else):
        print(f"[B] Trial: gap={gap_ms}, f={frequency}, noise={noise_level}, x={something_else}")
        return dict(
            gap_ms=gap_ms, frequency=frequency,
            noise_level=noise_level, something_else=something_else
        )


# ===========================================================
# Paradigm C
# ===========================================================
class ParadigmC(ParadigmBase):

    def __init__(self):
        params = {
            "inner": VarSpec(
                name="weird_param",
                data=dict(
                    start=100,
                    initial_step_down=25,
                    small_step_down=5,
                    small_step_up=5, # steps_down = steps_up
                    min_level=0,
                    max_level=200,
                    extra_trials_after_reversal=5,
                ),
            ),
            "outer_1": VarSpec(name="rate", data=[0.1, 0.5]),
        }
        super().__init__(params)

    def generate_trial(self, weird_param, rate):
        print(f"[C] Trial: weird={weird_param}, rate={rate}")
        return dict(weird_param=weird_param, rate=rate)


# ===========================================================
# Demo
# ===========================================================
if __name__ == "__main__":
    A = ParadigmA()
    print("\nRunning Paradigm A:")
    A.run()

    B = ParadigmB()
    print("\nRunning Paradigm B:")
    B.run()

    C = ParadigmC()
    print("\nRunning Paradigm C:")
    C.run()







# # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# # 
# #           SECOND OLD VERSION (TOO MANY LOOPS)...
# # 
# # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# NOTE: this isn't quite right, the inner variable shouldn't be looped through, but rather define the 
# step sizes that are used to make the configuration more or less difficult on successive trials


# from dataclasses import dataclass


# # -----------------------------------------------------------
# # The VarSpec container
# # -----------------------------------------------------------
# @dataclass
# class VarSpec:
#     """
#     A simple container:
#         name : the attribute name the paradigm code will use
#         data : the list of values to iterate over
#     """
#     name: str
#     data: list


# # -----------------------------------------------------------
# # Base paradigm class
# # -----------------------------------------------------------
# class ParadigmBase:
#     """
#     This class automatically extracts:
#         - inner loop variable
#         - outer loop variables
#     based entirely on the dictionary keys:
#         "inner", "outer_1", "outer_2"
#     """

#     def __init__(self, params: dict[str, VarSpec]):
#         self.params = params

#         # 1. Expose attributes using their key names
#         for key, spec in params.items(): # .items() returns the name and associated data as a "dict_items" object
#             # key is the variable name (e.g. var_1, var_2, ...)
#             # spec is the associated VarSpec object 
#             # e.g. VarSpec(name='frequency', data=[100, 200])
#             setattr(self, key, spec) # this creates self.inner = VarSpec(...), self.outer_1 = VarSpec(...), ...

#         # 2. Expose direct references like:
#         #       self.frequency, self.amplitude, etc.
#         for spec in params.values(): # .values() only returns the data as a "dict_values" object
#             setattr(self, spec.name, spec.data) # --> e.g. self.frequency = [100, 200, 300]

#         # 3. Derived loop roles (no more loop_role stored)
#         self.inner_var = params["inner"] # gets the dict_value that has a loop_role of "inner"
#         self.outer_vars = [ # gets the dict_values that has a loop_role of "outer_*"
#             params[k] for k in params
#             if k.startswith("outer_")
#         ]

#     # ---------------------------------------------
#     # Run all trials following OUTER → INNER nesting
#     # ---------------------------------------------
#     def run(self):
#         results = []
#         self._recursive_loop(0, {}, results)
#         return results

#     def _recursive_loop(self, idx, chosen, results):
#         """Handles arbitrary number of outer loops."""
#         if idx < len(self.outer_vars):
#             outer = self.outer_vars[idx]
#             for value in outer.data:
#                 chosen[outer.name] = value
#                 self._recursive_loop(idx + 1, chosen, results)
#             return

#         # Hit inner loop
#         for inner_value in self.inner_var.data:
#             chosen[self.inner_var.name] = inner_value
#             trial = self.generate_trial(**chosen)
#             results.append(trial)


# # -----------------------------------------------------------
# # Example Paradigm A
# # -----------------------------------------------------------
# class ParadigmA(ParadigmBase):

#     def __init__(self):
#         params = {
#             "inner":   VarSpec(name="frequency", data=[100, 200]),
#             "outer_1": VarSpec(name="amplitude", data=[10, 20]),
#             "outer_2": VarSpec(name="mod_index", data=[0.1, 0.2]),
#         }
#         super().__init__(params)

#     def generate_trial(self, frequency, amplitude, mod_index):
#         print(f"[A] Trial: f={frequency}, amp={amplitude}, β={mod_index}")
#         return dict(frequency=frequency,
#                     amplitude=amplitude,
#                     mod_index=mod_index)


# # -----------------------------------------------------------
# # Example Paradigm B (different loop structure)
# # -----------------------------------------------------------
# class ParadigmB(ParadigmBase):

#     def __init__(self):
#         params = {
#             "inner":   VarSpec(name="amplitude", data=[2, 4, 6]),
#             "outer_1": VarSpec(name="gap_ms",    data=[5, 10]),
#             "outer_2": VarSpec(name="frequency", data=[500, 1000]),
#             "outer_3": VarSpec(name="something_else", data=[1, 2]),
#         }
#         super().__init__(params)

#     def generate_trial(self, amplitude, gap_ms, frequency, something_else):
#         print(f"[B] Trial: amp={amplitude}, gap={gap_ms}, f={frequency}, something_else={something_else}")
#         return dict(amplitude=amplitude,
#                     gap_ms=gap_ms,
#                     frequency=frequency,
#                     something_else=something_else)


# # -----------------------------------------------------------
# # Example Paradigm C (different loop structure)
# # -----------------------------------------------------------
# class ParadigmC(ParadigmBase):

#     def __init__(self):
#         params = {
#             "inner":   VarSpec(name="i_dunno", data=[1, 10, 100]),
#             "outer_1": VarSpec(name="i_am_data",    data=[0.1, 0.01]),
#         }
#         super().__init__(params)

#     def generate_trial(self, i_dunno, i_am_data):
#         print(f"[C] Trial: huh?={i_dunno}, i_am_data={i_am_data}")
#         return dict(i_dunno=i_dunno,
#                     i_am_data=i_am_data)


# # -----------------------------------------------------------
# # Demo
# # -----------------------------------------------------------
# if __name__ == "__main__":
#     A = ParadigmA()
#     print("\nRunning Paradigm A:")
#     A.run()

#     B = ParadigmB()
#     print("\nRunning Paradigm B:")
#     B.run()

#     C = ParadigmC()
#     print("\nRunning Paradigm C:")
#     C.run()





# # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# # 
# #              FIRST OLD CLUNKIER VERSION...
# # 
# # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# from dataclasses import dataclass

# # -----------------------------------------------------------
# # VarSpec: defines a variable, its data, and its loop role
# # -----------------------------------------------------------

# @dataclass # the dataclass module is a shortcut for def __init__(self, ...)
# class VarSpec:
#     name: str
#     data: list
#     loop_role: str    # "inner", "outer1", "outer2"


# # -----------------------------------------------------------
# # Base class: contains all the reusable logic
# # -----------------------------------------------------------

# class ParadigmBase:

#     def __init__(self, params):
#         """
#         params is a dict:
#         {
#             "var_1": VarSpec(..., "inner"),
#             "var_2": VarSpec(..., "outer1"),
#             "var_3": VarSpec(..., "outer2")
#         }
#         """

#         self.params = params

#         # Expose var_1, var_2, var_3 directly
#         for slot, spec in params.items(): # .items() returns the name and associated data as a "dict_items" object
#             # slot is the variable name (e.g. var_1, var_2, ...)
#             # spec is the associated VarSpecobject 
#             # e.g. VarSpec(name='frequency', data=[100, 200], loop_role='inner')
#             setattr(self, slot, spec) # this creates var_1 = VarSpec(...), var_2 = VarSpec(...), ...

#         # Also create attributes with their real names: self.frequency, etc.
#         for spec in params.values(): # .values() only returns the data as a "dict_values" object
#             setattr(self, spec.name, spec.data) # --> e.g. self.frequency = [100, 200, 300]

#         # Extract loop roles (these never change across paradigms)
#         self.inner_var = next(v for v in params.values() if v.loop_role == "inner") # gets the dict_value that has a loop_role of "inner"
#         self.outer_vars = [ # gets the dict_values that has a loop_role of "outer1" and "outer2"
#             v for v in params.values()
#             if v.loop_role in ("outer1", "outer2")
#         ]

#         # Loop counters
#         self.inner_idx = 0
#         self.outer1_idx = 0
#         self.outer2_idx = 0

#         # State
#         self.end_paradigm = False
#         self.data = []

#     # ------------------------------------------------------------------

#     def get_active_values(self):
#         """Return the three active variable values."""
#         v1 = self.inner_var.data[self.inner_idx]
#         v2 = self.outer_vars[0].data[self.outer1_idx]
#         v3 = self.outer_vars[1].data[self.outer2_idx]
#         return v1, v2, v3

#     # ------------------------------------------------------------------

#     def update_trial_params(self):
#         """
#         Increment loop counters in a cascading fashion:
#         inner → outer1 → outer2
#         """
#         self.inner_idx += 1

#         if self.inner_idx >= len(self.inner_var.data): # reset when inner_idx is done
#             self.inner_idx = 0
#             self.outer1_idx += 1

#             if self.outer1_idx >= len(self.outer_vars[0].data): # reset when outer1_idx is done
#                 self.outer1_idx = 0
#                 self.outer2_idx += 1

#                 # If outer2 is exhausted, the paradigm ends
#                 if self.outer2_idx >= len(self.outer_vars[1].data):
#                     self.end_paradigm = True

#     # ------------------------------------------------------------------

#     def main(self):
#         """Dummy main loop — executes all combinations of var_1 * var_2 * var_3."""

#         while not self.end_paradigm: # keep going until the end_paradigm flag is set...

#             # Fetch active variable values
#             inner_val, outer1_val, outer2_val = self.get_active_values()

#             # Call the paradigm-specific trial generator
#             trial_info = self.generate_trial(inner_val, outer1_val, outer2_val)

#             # Store trial info (dummy data)
#             self.data.append(trial_info)

#             # Update counters
#             self.update_trial_params()

#         # Done
#         print("Paradigm complete.")
#         print("Collected data:")
#         for d in self.data:
#             print(d)

#     # ------------------------------------------------------------------
#     # Subclasses must override this
#     # ------------------------------------------------------------------
#     def generate_trial(self, inner_val, outer1_val, outer2_val):
#         raise NotImplementedError

# # -----------------------------------------------------------
# # Example concrete paradigm A (audiology-style)
# # -----------------------------------------------------------

# class ParadigmA(ParadigmBase):

#     def __init__(self):
#         params = {
#             "var_1": VarSpec(name="frequency", data=[100, 200, 400], loop_role="inner"),
#             "var_2": VarSpec(name="amplitude", data=[10, 20],        loop_role="outer1"),
#             "var_3": VarSpec(name="mod_ind",   data=[0.1, 0.2, 0.3], loop_role="outer2"),
#         }
#         super().__init__(params)

#     def generate_trial(self, frequency, amplitude, mod_ind):
#         print(
#             f"[A] Trial: frequency={frequency}, amplitude={amplitude}, mod_ind={mod_ind}"
#         )
#         return {
#             "frequency": frequency,
#             "amplitude": amplitude,
#             "mod_ind": mod_ind,
#         }


# # -----------------------------------------------------------
# # Example concrete paradigm B (gap-detection style)
# # -----------------------------------------------------------

# class ParadigmB(ParadigmBase):

#     def __init__(self):
#         params = {
#             "var_1": VarSpec(name="amplitude",  data=[5, 10, 15],   loop_role="inner"),
#             "var_2": VarSpec(name="gap_length", data=[2, 5, 10],    loop_role="outer1"),
#             "var_3": VarSpec(name="frequency",  data=[500, 1000],   loop_role="outer2"),
#         }
#         super().__init__(params)

#     def generate_trial(self, amplitude, gap_length, frequency):
#         print(
#             f"[B] Trial: amplitude={amplitude}, gap_length={gap_length}, frequency={frequency}"
#         )
#         return {
#             "amplitude": amplitude,
#             "gap_length": gap_length,
#             "frequency": frequency,
#         }


# # -----------------------------------------------------------
# # Example of running
# # -----------------------------------------------------------

# if __name__ == "__main__":
#     print("=== Running Paradigm A ===")
#     A = ParadigmA()
#     A.main()

#     print("\n=== Running Paradigm B ===")
#     B = ParadigmB()
#     B.main()
