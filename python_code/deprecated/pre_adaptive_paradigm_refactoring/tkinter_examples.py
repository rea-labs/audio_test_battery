import tkinter as tk
from tkinter import ttk

###### REFERENCES ######
# https://www.youtube.com/watch?v=epDKamC-V-8&list=PLzpgwLdhCxXjEVcphaS9ql55LzzgH4iqS&index=31
# https://gist.github.com/CoreyMSchafer/558014ea68297f4fc89f46513260bb00


# tk._test()

root = tk.Tk() # make a window
root.title("Simple App") # add a title


###### HELLO WORLD EXAMPLE ######
# def on_click(): # fcn for button click
#     print("Testing") # print "Testing" to console
#     lbl.config(text="Button Clicked") # update label text o nclick

# lbl = tk.Label(root, text="Label 1") # create label text
# lbl.grid() # IMPORTANT add the label to the layout

# print(lbl.config().keys()) # print out label methods

# btn = tk.Button(root, text="Button 1", command=on_click) # make a button 
### IMPORTANT: don't include ()'s on the function name, so it isn't executed
# btn.grid(row=0, column=1) # IMPORTANT add the button to the layout

def add_to_list(event=None):
    text = entry.get()
    if text:
        text_list.insert(tk.END, text) # tk.END represents the end of current content in a widget
        entry.delete(0, tk.END)

root.columnconfigure(0, weight=1) 
root.columnconfigure(1, weight=3) 
root.rowconfigure(0,weight=1)

frame_1 = ttk.Frame(root) # create a frame
frame_1.grid(row=0, column=0, sticky="nsew", padx=5, pady=5) # add it to the layout

frame_1.columnconfigure(0, weight=1)
frame_1.rowconfigure(1, weight=1)

entry = ttk.Entry(frame_1) # add an (text) entry to the frame
entry.grid(row=0, column=0, sticky="ew") # and place it

entry.bind("<Return>",add_to_list) # make pressing Return call the add_to_list fcn

entry_btn = ttk.Button(frame_1, text="Add", command=add_to_list) # add a new button for text entry
entry_btn.grid(row=0, column=1)

text_list = tk.Listbox(frame_1) # add a text entry field
text_list.grid(row=1, column=0, columnspan=2, sticky="nsew") # add to grid make it "stick"



frame_2 = tk.Frame(root) # create a frame
frame_2.grid(row=0, column=1, sticky="nsew", padx=5, pady=5) # add it to the layout

frame_2.columnconfigure(0, weight=1)
frame_2.rowconfigure(1, weight=1)

entry = tk.Entry(frame_2) # add an (text) entry to the frame
entry.grid(row=0, column=0, sticky="ew") # and place it

entry.bind("<Return>",add_to_list) # make pressing Return call the add_to_list fcn

entry_btn = tk.Button(frame_2, text="Add", command=add_to_list) # add a new button for text entry
entry_btn.grid(row=0, column=1)

text_list = tk.Listbox(frame_2) # add a text entry field
text_list.grid(row=1, column=0, columnspan=2, sticky="nsew") # add to grid make it "stick"



root.mainloop() # start the applications main loop to keep the window open