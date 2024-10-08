import tkinter as tk
from tkinter import ttk
import requests

LARGE_FONT_STYLE = ("Arial", 40, "bold")
SMALL_FONT_STYLE = ("Arial", 16)
DIGIT_FONT_STYLE = ("Arial", 24, "bold")
DEFAULT_FONT_STYLE = ("Arial", 20)

OFF_WHITE = "#F8FAFF"
WHITE = "#FFFFFF"
LIGHT_BLUE = "#CCEDFF"
LIGHT_GRAY = "#F5F5F5"
LABEL_COLOUR = "#25265E"

URL = "http://127.0.0.1:8000"
LOGIN_ENDPOINT = "/auth/token"


class Chattr:
    def __init__(self):
        self.window = tk.Tk()
        self.width: int = 375
        self.height: int = 375
        self.window.geometry(f"{self.width}x{self.height}")
        self.window.title("Chattr")
        self.buttons: dict = {}
        self.labels: dict = {}
        self.entries: dict = {}
        self.frame: tk.Frame = self.create_display_frame()
        self.username = tk.StringVar()
        self.password = tk.StringVar()
        self.auth_token: dict = {}
        self.create_login_buttons()
        self.configure_responsive()

    def create_login_buttons(self):
        """Create the initial screen with "Login" and "Sign up" options"""
        self.username.set("username_1")
        self.password.set("password_1")
        self.delete_all()
        self.create_login_button()
        self.create_signup_button()

    def create_login_button(self):
        """Create the "Login" button"""
        login_button = ttk.Button(
            self.frame,
            text="Log in",
            command=lambda: self.create_login_screen(),
        )
        self.buttons["login"] = login_button
        login_button.grid(row=0, column=0)  # , sticky="ew")

    def create_signup_button(self):
        """Create the "Sign up" button"""
        signup_button = ttk.Button(
            self.frame,
            text="Create account",
            command=lambda: self.create_signup_screen(),
        )
        self.buttons["signup"] = signup_button
        signup_button.grid(row=1, column=0)  # , sticky="ew")

    def configure_responsive(self):
        """Configure grid row and column weights for responsive behaviour"""
        self.window.rowconfigure(0, weight=1)
        self.window.columnconfigure(0, weight=1)
        # self.window.columnconfigure(1, weight=0)

        self.frame.rowconfigure(1, weight=1)
        self.frame.rowconfigure(0, weight=1)
        self.frame.columnconfigure(0, weight=1)

    def print_contents(self, event):
        """Temporary function for testing"""
        entry_widget = event.widget
        print("Hi. The current entry content is:", entry_widget.get())

    def create_login_screen(self):
        # Clear the screen
        self.delete_all()

        # Create 'username' entry
        username_entry = ttk.Entry(
            self.frame,
            background=WHITE,
            foreground=LABEL_COLOUR,
            font=SMALL_FONT_STYLE,
            exportselection=0,
        )
        self.entries["username_entry"] = username_entry
        username_entry.grid(row=0, column=0)
        username_entry["textvariable"] = self.username
        username_entry.bind("<Key-Return>", self.print_contents)

        # Create 'password' entry
        password_entry = ttk.Entry(
            self.frame,
            background=WHITE,
            foreground=LABEL_COLOUR,
            font=SMALL_FONT_STYLE,
            exportselection=0,
            show="*",
        )
        self.entries["password_entry"] = password_entry
        password_entry.grid(row=1, column=0)
        password_entry["textvariable"] = self.password
        password_entry.bind("<Key-Return>", self.print_contents)

        login_button = ttk.Button(
            self.frame,
            text="Log in",
            command=lambda: self.get_auth_token(),
        )
        self.buttons["login"] = login_button
        login_button.grid(row=2)

        back_button = ttk.Button(
            self.frame,
            text="Back",
            command=lambda: self.create_login_buttons(),
        )
        self.buttons["back"] = back_button
        back_button.grid(row=3)

    def get_auth_token(self):
        """Submits username and password to get a bearer token from the server"""
        try:
            payload = {"username": self.username.get(), "password": self.password.get()}
            response = requests.post(f"{URL}{LOGIN_ENDPOINT}", data=payload)
            response.raise_for_status()
            self.auth_token = response.json()
            return True

        except:
            print("Auth token request failed")

    def create_signup_screen(self):
        """Create the sign up screen with input elements and buttons, called by clicking the "Sign up" button"""
        print("'Sign up' clicked")
        self.delete_all()

    def delete_buttons(self):
        """Delete all Button elements"""
        for button in self.buttons:
            self.buttons[button].grid_forget()
        self.buttons.clear()

    def delete_entries(self):
        """Delete all Entry elements"""
        for entry in self.entries:
            self.entries[entry].grid_forget()
        self.entries.clear()

    def delete_labels(self):
        """Delete all Label elements"""
        for label in self.labels:
            self.labels[label].grid_forget()
        self.labels.clear()

    def delete_all(self):
        """Delete all elements on the screen, excluding Frame"""
        self.delete_labels()
        self.delete_buttons()
        self.delete_entries()

    def create_display_frame(self) -> tk.Frame:
        """Create the display Frame element"""
        frame = ttk.Frame(
            self.window, height=self.height, width=self.width
        )  # , background="white", foreground="white")

        frame.grid(row=0, column=0)
        return frame

    def run(self):
        self.window.mainloop()


if __name__ == "__main__":
    chattr = Chattr()
    chattr.run()
