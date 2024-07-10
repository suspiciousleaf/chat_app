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
        # self.window.resizable(0, 0)
        self.window.title("Chattr")
        self.buttons = {}
        self.labels = {}
        self.frame = self.create_buttons_frame()
        self.create_login_buttons()
        self.username = "username"
        self.password = "password"

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
        login_button.pack(expand=True, fill="both")

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
        signup_button.pack(expand=True, fill="both")

    def create_login_screen(self):
        print("'Log in' clicked")
        self.delete_buttons()
        self.create_login_labels()

    def create_login_labels(self):
        username_label = tk.Label(
            self.frame,
            text=self.username,
            anchor=tk.E,
            bg=LIGHT_GRAY,
            fg=LABEL_COLOUR,
            padx=24,
            font=SMALL_FONT_STYLE,
        )

        self.labels["username_label"] = username_label
        username_label.pack(expand=True, fill="both")

        password_label = tk.Label(
            self.frame,
            text="".join(["*" for char in self.password]),
            anchor=tk.E,
            bg=LIGHT_GRAY,
            fg=LABEL_COLOUR,
            padx=24,
            font=LARGE_FONT_STYLE,
        )
        self.labels["password_label"] = password_label
        password_label.pack(expand=True, fill="both")

    def create_signup_screen(self):
        print("'Sign up' clicked")
        self.delete_buttons()

    def delete_buttons(self):
        for button in self.buttons:
            self.buttons[button].pack_forget()

    def create_buttons_frame(self):
        frame = tk.Frame(self.window)
        # frame.pack(expand=True, fill="both")
        frame.place(relx=0.5, rely=0.5, anchor="center")
        return frame

    # def create_display_frame(self):
    #     frame = tk.Frame(self.window, height=221, bg=LIGHT_GRAY)
    #     frame.pack(expand=True, fill="both")
    #     return frame

    def run(self):
        self.window.mainloop()


if __name__ == "__main__":
    chattr = Chattr()
    chattr.run()
