from trial_player import TrialPlayer
from paradigm_FM import ParadigmFM

tp = TrialPlayer()
fm = ParadigmFM(tp)

fm.main()

# NOTE: the repeat key press behavior is *sort of* fixed in paradigm_FM atm - it still 
# causes the trial to end, but at least it doesn't create false responses, i suppose 
# this is *good enough* for the time being, TODO: revisit this issue in the future...