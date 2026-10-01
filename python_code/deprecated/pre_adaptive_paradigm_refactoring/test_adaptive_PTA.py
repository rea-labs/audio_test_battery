from paradigm_adaptive_PTA import ParadigmPTA_adaptive
# from dataclasses import dataclass, field
from utils.varspec import VarSpec
# import itertools

# # # eventually the pta class will instantiate an instance of the general AdaptiveParadigm class 
# # # and assign the params (maybe could/should eventually be moved to an external config file), 
# # # as well as override any necessary methods, e.g. prepare_trial(), log_data(), etc.

params = { # this must be a dictionary whose keys are strings and whose values are VarSpec objects
    "inner": VarSpec(
        name="gap_ms",
        data=dict( # TODO: fix these names, they're all wrong!
            start=30,
            initial_step_down=10,
            small_step_down=3,
            small_step_up=3,
            min_level=1,
            max_level=200,
            extra_trials_after_reversal=8,
        ),
    ),
    "outer_1": VarSpec(name="fc", data=[220, 440]),
    "outer_2": VarSpec(name="trial_dur", data=[0.5, 1.0]),
    # "outer_1": VarSpec(name="fc", data=[500, 1000, 1500]),
    # "outer_2": VarSpec(name="trial_dur", data=[0.5, 1.0]),
    # "outer_3": VarSpec(name="something_else", data=[1, 2, 3]),
}

pta = ParadigmPTA_adaptive(params)

pta.main() # this can (kina) be run from an interactive window (tkinter crashes at the end...)
# (otherwise uncomment the line above to run from here)

# pta.unwrapped_params
# pta.set_current_config(2)
# print(f"fc = {pta.fc}, trial_dur = {pta.trial_dur}")