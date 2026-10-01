from dataclasses import dataclass, field
import itertools


# -----------------------------------------------------------
# VarSpec container
# -----------------------------------------------------------
@dataclass
class VarSpec:
    """
    A simple container:
        name : the attribute name the paradigm code will use
        data : the list of values to iterate over
    """
    name: str = ""
    data: list = field(default_factory=list) # https://stackoverflow.com/questions/53632152/why-cant-dataclasses-have-mutable-defaults-in-their-class-attributes-declaratio

    def print_all(self):
        for k,v in self.__dict__.items():
            print(f"{str(k)} = {str(v)}")


# -----------------------------------------------------------
# example of a parameter parser wrapped in a class
# -----------------------------------------------------------
class ParamParserEG:   
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

        self.unwrapped_params = []
        names = [v.name for v in self.outer_vars]
        data = [v.data for v in self.outer_vars]
        for combo in itertools.product(*data):
            self.unwrapped_params.append(dict(zip(names, combo)))
        
        self.total_num_configs = len(self.unwrapped_params)
    
    def set_current_config(self, ind):
        for key, val in self.unwrapped_params[ind].items():
            setattr(self, key, val)

    def make_new_data(self, data):
        setattr(self,"new_data",data)

    def print_all(self):
        for k,v in self.__dict__.items():
            print(f"{str(k)} = {str(v)}")








# params = { # this must be a dictionary whose keys are strings and whose values are VarSpec objects
#     "inner": VarSpec(
#         name="gap_ms",
#         data=dict(
#             start=30,
#             initial_step_down=10,
#             small_step_down=3,
#             small_step_up=3,
#             min_level=1,
#             max_level=200,
#             extra_trials_after_reversal=8,
#         ),
#     ),
#     "outer_1": VarSpec(name="frequency", data=[500, 1500]),
#     "outer_2": VarSpec(name="noise_level", data=[20, 40]),
#     "outer_3": VarSpec(name="something_else", data=[1, 2, 3]),
# }

# test = ParamParserEG(params)
# test.make_new_data('this is a test')
# test.print_all() # it works!

# for x in range(test.total_num_configs):
#     test.set_current_config(x)
#     print(f"freq = {test.frequency}, noise_level = {test.noise_level}, something_else = {test.something_else}")