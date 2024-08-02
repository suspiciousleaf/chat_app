import tkinter as tk
from tkinter import ttk


root = tk.Tk()
root.title("App")

# This allows the column and row to expand as the window size increases
root.columnconfigure(0, weight=1)
root.columnconfigure(1, weight=1)
root.rowconfigure(0, weight=1)


def add_to_list():
    text = entry.get()
    if text:
        text_list.insert(tk.END, text)
        entry.delete(0, tk.END)


def add_to_list_2():
    text = entry_2.get()
    if text:
        text_list_2.insert(tk.END, text)
        entry_2.delete(0, tk.END)


# "Sticky" causes the edges of the object to stick to the border, north south east west
frame = ttk.Frame(root)
frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

frame.columnconfigure(0, weight=1)
frame.rowconfigure(1, weight=1)

entry = ttk.Entry(frame)
entry.grid(row=0, column=0, sticky="ew")

# Binding events automatically passes an event argument to the function it calls, so either set "event=None" in the function definition, or call with a lambda function as below
entry.bind("<Return>", lambda event: add_to_list())

entry_btn = ttk.Button(frame, text="Add", command=add_to_list)
entry_btn.grid(row=0, column=1)

text_list = tk.Listbox(frame)
text_list.grid(row=1, column=0, columnspan=2, sticky="nsew")

####################################################################

frame_2 = ttk.Frame(root)
frame_2.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

frame_2.columnconfigure(0, weight=1)
frame_2.rowconfigure(1, weight=1)

entry_2 = ttk.Entry(frame_2)
entry_2.grid(row=0, column=0, sticky="ew")

# Binding events automatically passes an event argument to the function it calls, so either set "event=None" in the function definition, or call with a lambda function as below
entry_2.bind("<Return>", lambda event: add_to_list_2())

entry_btn_2 = ttk.Button(frame_2, text="Add", command=add_to_list_2)
entry_btn_2.grid(row=0, column=1)

text_list_2 = tk.Listbox(frame_2)
text_list_2.grid(row=1, column=0, columnspan=2, sticky="nsew")


root.mainloop()
