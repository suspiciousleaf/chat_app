import datetime
import tkinter as tk
from tkinter import ttk
import asyncio
import threading
import json
from json import JSONDecodeError

from networking.connect_websocket import MyWebSocket

# import customtkinter as ctk

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
        self.width = 375
        self.height = 375
        self.window.geometry(f"{self.width}x{self.height}")
        # self.window.resizable(0, 0)
        self.window.title("Chattr")
        self.buttons = {}
        self.labels = {}
        self.entries = {}
        self.username = "username_1"
        self.auth_token = {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VybmFtZV8xIiwiZXhwIjoxNzIyODMzODc5fQ.EIU9JYh1nk_2d-RZvzhaOjDQw7mfIR5LB5BxyCgwJcc",
            "token_type": "bearer",
        }
        self.client_websocket = MyWebSocket(self.auth_token)

        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self.connect_client_websocket())

        # self.frame = self.create_display_frame()
        self.username = tk.StringVar(value="username")
        self.password = tk.StringVar(value="password")
        self.message_text = tk.StringVar(value="")
        self.screen_text = tk.StringVar(value="Messages will appear here")
        self.create_text_field()
        self.create_text_entry()
        self.configure_responsive()

        # Start the asyncio loop in a separate thread
        self.thread = threading.Thread(target=self.run_async_loop, daemon=True)
        self.thread.start()

    def run_async_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.async_init())

    async def async_init(self):
        await self.connect_client_websocket()
        await self.listen_for_messages()

    async def connect_client_websocket(self):
        await self.client_websocket.connect()

    async def listen_for_messages(self):
        while True:
            try:
                message = await self.client_websocket.websocket.recv()
                self.display_message(message)
            except Exception as e:
                print(f"Error receiving message: {e}")
                # Implement reconnection logic here if needed
                await asyncio.sleep(5)  # Wait before trying to reconnect

    def display_message(self, message):
        message = self.decode_received_message(message)
        current_time = datetime.datetime.now().strftime("%H:%M")
        display_text = f"{current_time} Channel: {message['channel']}, Message: {message['content']}\n"
        # Use after() method to safely update GUI from a different thread
        self.window.after(0, self.update_text_field, display_text)

    def update_text_field(self, text):
        self.text_field.config(state="normal")
        self.text_field.insert(tk.END, text)
        self.text_field.config(state="disabled")
        self.text_field.yview(tk.END)  # Auto-scroll to the bottom

    def decode_received_message(self, message):
        try:
            return json.loads(message)
        except JSONDecodeError:
            print(f"Could not decode message: {message}")
        except Exception as e:
            print(f"Unknown error occurred when decoding message: {e}")

    def create_text_field(self):
        self.text_field = tk.Text(
            self.window,
            width=self.width,
            # height=200,  # Set height to a smaller number of lines
            background=OFF_WHITE,
            state="disabled",
            wrap="word",
        )
        self.text_field.grid(row=0, column=0, columnspan=2, sticky="nsew")

    def configure_responsive(self):
        # Configure grid row and column weights for responsive behaviour
        self.window.rowconfigure(0, weight=1)
        self.window.columnconfigure(0, weight=1)
        self.window.columnconfigure(1, weight=0)

    def send_message(self, event=None):
        message = self.entries["write_message"].get()
        if message.strip():  # Check if the message is not empty
            self.text_field.config(state="normal")
            current_time = datetime.datetime.now().strftime("%H:%M")
            self.text_field.insert(tk.END, f"{current_time} You: {message}\n")
            self.text_field.config(state="disabled")
            self.text_field.yview(tk.END)  # Auto-scroll to the bottom
            self.entries["write_message"].delete(0, tk.END)

    #! Add code to send messages in the correct format, write function below and trigger here
    #         # Send message through WebSocket
    #         asyncio.run_coroutine_threadsafe(self.send_websocket_message(message), self.loop)

    # async def send_websocket_message(self, message):
    #     try:
    #         await self.client_websocket.send_message(message)
    #     except Exception as e:
    #         print(f"Failed to send message: {e}")
    #         # Handle the sending failure (e.g., show an error message in the UI)

    def create_text_entry(self):
        message_entry = ttk.Entry(
            self.window, width=self.width - 70, background=OFF_WHITE
        )
        message_entry.grid(row=1, column=0, sticky="ew")
        message_entry.bind("<Return>", self.send_message)
        self.entries["write_message"] = message_entry

        send_button = ttk.Button(
            self.window, text="Send", command=self.send_message
        )  # width=50, height=20,
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
        frame = ttk.Frame(
            self.window, height=221, background="white", foreground="white"
        )
        frame.pack(expand=True, fill="both")
        return frame

    def run(self):
        self.window.mainloop()


if __name__ == "__main__":
    chattr = Chattr()
    chattr.run()
