import datetime
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
        self.window = ctk.CTk()
        self.width = 375
        self.height = 375
        self.window.geometry(f"{self.width}x{self.height}")
        self.window.resizable(0, 0)
        self.window.title("Chattr")
        self.buttons = {}
        self.labels = {}
        self.entries = {}
        # self.frame = self.create_display_frame()
        self.username = tk.StringVar(value="username")
        self.password = tk.StringVar(value="password")
        self.message_text = tk.StringVar(value="")
        self.screen_text = tk.StringVar(value="Messages will appear here")
        self.create_text_field()
        self.create_text_entry()

    def create_text_field(self):
        self.text_field = tk.Text(
            self.window,
            width=self.width,
            # height=200,  # Set height to a smaller number of lines
            bg=OFF_WHITE,
            state="disabled",
            wrap="word",
        )
        self.text_field.grid(row=0, column=0, columnspan=2, sticky="nsew")

        # # Configure grid row and column weights
        self.window.grid_rowconfigure(0, weight=1)
        self.window.grid_columnconfigure(0, weight=1)
        self.window.grid_columnconfigure(1, weight=0)

    def send_message(self, event=None):
        message = self.entries["write_message"].get()
        if message.strip():  # Check if the message is not empty
            self.text_field.config(state="normal")
            current_time = datetime.datetime.now().strftime("%H:%M")
            self.text_field.insert(tk.END, f"{current_time} You: {message}\n")
            self.text_field.config(state="disabled")
            self.text_field.yview(tk.END)  # Auto-scroll to the bottom
            self.entries["write_message"].delete(0, tk.END)

    def create_text_entry(self):
        message_entry = ctk.CTkEntry(
            self.window, width=self.width - 70, bg_color=OFF_WHITE
        )
        message_entry.grid(row=1, column=0, sticky="ew")
        message_entry.bind("<Return>", self.send_message)
        self.entries["write_message"] = message_entry

        send_button = ctk.CTkButton(
            self.window, width=50, height=20, text="Send", command=self.send_message
        )
        send_button.grid(row=1, column=1)
        self.buttons["send"] = send_button

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
