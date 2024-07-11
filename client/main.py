import tkinter as tk

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
        self.create_login_buttons()
        self.username = tk.StringVar(value="username")
        self.password = tk.StringVar(value="password")

    def create_login_buttons(self):
        self.create_login_button()
        self.create_signup_button()

    def create_login_button(self):
        login_button = tk.Button(
            self.frame,
            text="Log in",
            bg=OFF_WHITE,
            fg=LABEL_COLOUR,
            font=DEFAULT_FONT_STYLE,
            borderwidth=0,
            command=lambda: self.create_login_screen(),
        )
        self.buttons["login"] = login_button
        login_button.grid(row=0)

    def create_signup_button(self):
        signup_button = tk.Button(
            self.frame,
            text="Create account",
            bg=OFF_WHITE,
            fg=LABEL_COLOUR,
            font=DEFAULT_FONT_STYLE,
            borderwidth=0,
            command=lambda: self.create_signup_screen(),
        )
        self.buttons["signup"] = signup_button
        signup_button.grid(row=1)

    def print_contents(self, event):
        entry_widget = event.widget
        print("Hi. The current entry content is:", entry_widget.get())

    def create_login_screen(self):

        print("'Log in' clicked")
        self.delete_buttons()

        username_entry = tk.Entry(
            self.frame,
            bg=WHITE,
            fg=LABEL_COLOUR,
            font=SMALL_FONT_STYLE,
            exportselection=0,
        )
        self.entries["username_entry"] = username_entry
        username_entry.grid(row=0, column=0)
        username_entry["textvariable"] = self.username
        username_entry.bind("<Key-Return>", self.print_contents)

        # Create 'password' entry
        password_entry = tk.Entry(
            self.frame,
            bg=WHITE,
            fg=LABEL_COLOUR,
            font=SMALL_FONT_STYLE,
            exportselection=0,
            show="*",
        )
        self.entries["password_entry"] = password_entry
        password_entry.grid(row=1, column=0)
        password_entry["textvariable"] = self.password
        password_entry.bind("<Key-Return>", self.print_contents)

    def create_signup_screen(self):
        print("'Sign up' clicked")
        self.delete_buttons()

    def delete_buttons(self):
        for button in self.buttons:
            self.buttons[button].grid_forget()
        self.buttons.clear()

    # def create_buttons_frame(self):
    #     frame = tk.Frame(self.window)
    #     # frame.pack(expand=True, fill="both")
    #     frame.place(relx=0.5, rely=0.5, anchor="center")
    #     return frame

    def create_display_frame(self):
        frame = tk.Frame(self.window, height=221, bg=LIGHT_GRAY)
        frame.pack(expand=True, fill="both")
        return frame

    def run(self):
        self.window.mainloop()


if __name__ == "__main__":
    chattr = Chattr()
    chattr.run()
