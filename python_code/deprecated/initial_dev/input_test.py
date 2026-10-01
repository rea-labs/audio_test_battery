from psychopy import core, visual, event
from psychopy.hardware import keyboard


# If you want to obtain key-presses during the wait, be sure to use pyglet 
# and to hogCPU for the entire time, and then call psychopy.event.getKeys() 
# after calling ~.psychopy.core.wait()


# Create a window
win = visual.Window(size=(800, 600))

# Initialize the keyboard
kb = keyboard.Keyboard()

# Display text
text_stim = visual.TextStim(win, text="Press any key when you see 'GO'", height=0.05)
text_stim.draw()
win.flip()

# Wait before displaying the GO signal
core.wait(2.0)

# Show "GO" and start timing
text_stim.text = "GO!"
text_stim.draw()
win.flip()
kb.clock.reset()  # Reset the clock to measure reaction time

# Wait for a key press
keys = kb.waitKeys()

# Record reaction time
if keys:
    key_name = keys[0].name
    reaction_time = keys[0].rt
    print(f"Key pressed: {key_name}, Reaction time: {reaction_time:.3f} seconds")

# Cleanup
event.clearEvents()  # Clear pending events
win.flip()  # Ensure the screen is refreshed
win.close()
core.quit()
