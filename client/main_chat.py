import tkinter as tk
import customtkinter as ctk

LARGE_FONT_STYLE = ("Arial", 40, "bold")
SMALL_FONT_STYLE = ("Arial", 16)
DIGIT_FONT_STYLE = ("Arial", 24, "bold")
DEFAULT_FONT_STYLE = ("Arial", 20)

OFF_WHITE = "#F8FAFF"
WHITE = "#FFFFFF"
LIGHT_BLUE = "#CCEDFF"
LIGHT_GRAY = "#F5F5F5"
LABEL_COLOUR = "#25265E"


class Chattr:
    def __init__(self):
        self.window = tk.Tk()
        self.window.geometry("375x375")
        self.window.resizable(0, 0)
        self.window.title("Chattr")
        self.buttons = {}
        self.labels = {}
        self.entries = {}
        self.frame = self.create_display_frame()
        self.username = tk.StringVar(value="username")
        self.password = tk.StringVar(value="password")

    def print_contents(self, event):
        entry_widget = event.widget
        print("Hi. The current entry content is:", entry_widget.get())

    def delete_buttons(self):
        for button in self.buttons:
            self.buttons[button].grid_forget()
        self.buttons.clear()

    def delete_entries(self):
        for entry in self.entries:
            self.entries[entry].grid_forget()
        self.entries.clear()

    def delete_labels(self):
        for label in self.labels:
            self.labels[label].grid_forget()
        self.labels.clear()

    def delete_all(self):
        self.delete_labels()
        self.delete_buttons()
        self.delete_entries()

    def create_display_frame(self):
        frame = ctk.CTkFrame(
            self.window, height=221, bg_color="white", fg_color="white"
        )
        frame.pack(expand=True, fill="both")
        return frame

    def run(self):
        self.window.mainloop()


if __name__ == "__main__":
    chattr = Chattr()
    chattr.run()
