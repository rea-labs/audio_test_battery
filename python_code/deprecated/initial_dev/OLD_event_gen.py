def event_gen(specs):
    # this seems a bit weird to do, but necessary
    # TODO: add ramp
    import psychtoolbox as ptb
    import psychopy.core as core
    audioLib = 'pygame' # for the moment, it seems that only pygame is working on apple silicon macs...
    from psychopy import prefs
    prefs.hardware['audioLib'] = audioLib
    prefs.hardware
    from psychopy import sound
    
    
    mask_sound = sound.AudioClip.sine(duration=specs["masker"]["dur"]/1000, freqHz=specs["masker"]["freq"], gain=specs["masker"]["gain"])  # generate a tone
    mask_sound = sound.Sound(mask_sound)
    
    target_sound = sound.AudioClip.sine(duration=specs["target"]["dur"]/1000, freqHz=specs["target"]["freq"], gain=specs["target"]["gain"])  # generate a tone
    target_sound = sound.Sound(target_sound)

    # return mask_sound, target_sound
    # return mask_sound

    result = dict(mask=mask_sound, target=target_sound, delay_time=(specs["masker"]["dur"] + specs["gap"])/1000)
    return result

