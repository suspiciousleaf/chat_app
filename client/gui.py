import datetime
import tkinter as tk
from tkinter import ttk
import asyncio
import threading
import json
from json import JSONDecodeError
import requests
import time

from client.services.client_websocket import MyWebSocket

LARGE_FONT_STYLE = ("Arial", 40, "bold")
SMALL_FONT_STYLE = ("Arial", 16)
VERY_SMALL_FONT_STYLE = ("Arial", 12)
DIGIT_FONT_STYLE = ("Arial", 24, "bold")
DEFAULT_FONT_STYLE = ("Arial", 20)

OFF_WHITE = "#F8FAFF"
WHITE = "#FFFFFF"
LIGHT_BLUE = "#CCEDFF"
LIGHT_GRAY = "#F5F5F5"
LABEL_COLOUR = "#25265E"

URL = "http://127.0.0.1:8000"
LOGIN_ENDPOINT = "/auth/token"
CREATE_ACCOUNT_ENDPOINT = "/create_account"


class Chattr:
    def __init__(self):
        self.window: tk.Tk = tk.Tk()
        self.width: int = 375
        self.height: int = 375
        self.window.geometry(f"{self.width}x{self.height}")
        self.window.title("Chattr")
        self.buttons: dict[str, tk.Button] = {}
        self.labels: dict[str, tk.Label] = {}
        self.entries: dict[str, tk.Entry] = {}
        self.fields: dict = {}
        self.frame: tk.Frame = self.create_display_frame()
        self.username: tk.StringVar = tk.StringVar(value="username")
        self.password: tk.StringVar = tk.StringVar(value="password")
        self.auth_token: dict[str, str] = {}
        self.client_websocket: MyWebSocket | None = None
        self.server_status: str = "checking..."
        self.loop = asyncio.get_event_loop()
        asyncio.set_event_loop(self.loop)
        # Daemon threads are stopped abruptly at shutdown. Resources being used may not be released properly
        self.thread = threading.Thread(target=self.run_async_loop, daemon=True)
        self.thread.start()
        self.is_running = True
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.create_startup_screen()
        self.configure_responsive()

        # Buttons are displayed but disabled on startup. Once the server response is received, if everything is working the buttons will be enabled. Otherwise they will remain disabled.
        self.disable_buttons()

        self.message_text = tk.StringVar(value="")
        self.screen_text = tk.StringVar(value="Messages will appear here")

        self.start_server_status_check()

    def disable_buttons(self):
        """Disable all current buttons"""
        for button in self.buttons.values():
            button.config(state="disabled")

    def enable_buttons(self):
        """Enable all current buttons"""
        for button in self.buttons.values():
            button.config(state="normal")

    def create_startup_screen(self):
        """Create the initial screen with "Login" and "Sign up" options"""
        self.delete_all()
        self.create_login_button()
        self.create_signup_button()
        self.create_server_status_label()

    def create_login_button(self):
        """Create the "Login" button"""
        self.username.set("username_1")
        self.password.set("password_1")
        login_button = ttk.Button(
            self.frame,
            text="Log in",
            command=lambda: self.create_login_screen(),
        )
        self.buttons["login"] = login_button
        login_button.grid(row=0, column=0)

    def create_signup_button(self):
        """Create the "Sign up" button"""
        signup_button = ttk.Button(
            self.frame,
            text="Create account",
            command=lambda: self.create_signup_screen(),
        )
        self.buttons["signup"] = signup_button
        signup_button.grid(row=1, column=0)

    def create_server_status_label(self):
        """Create a label bottom left that shows the status of the server"""
        status_label = ttk.Label(
            self.window,
            text=f"Server status: {self.server_status}",
            font=VERY_SMALL_FONT_STYLE,
        )
        status_label.grid(row=2, column=0, sticky="sw", padx=5, pady=5)
        self.labels["server_status"] = status_label

    def create_login_screen(self):
        """Clears the screen, then creates the login widgets"""
        self.delete_all()
        self.create_username_entry()
        self.create_password_entry()
        self.create_login_submit_button()
        self.create_back_button()

    def create_username_entry(self):
        """Create 'username' entry widget"""
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
        # TODO Change or remove this binding
        username_entry.bind("<Key-Return>", self.print_contents)

    def create_password_entry(self):
        """Create 'password' entry widget"""
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

    def create_login_submit_button(self):
        """Create login 'submit' button"""
        login_button = ttk.Button(
            self.frame,
            text="Log in",
            command=lambda: self.submit_login(),
        )
        self.buttons["login"] = login_button
        login_button.grid(row=2)

    def create_back_button(self):
        """Create 'back' button"""
        back_button = ttk.Button(
            self.frame,
            text="Back",
            command=lambda: self.create_startup_screen(),
        )
        self.buttons["back"] = back_button
        back_button.grid(row=3)

    def submit_login(self):
        self.auth_token = self.get_auth_token()
        # This will create the chat screen if login is successfull
        if self.auth_token:
            self.delete_all()
            self.process_login()
            self.create_chat()

    def process_login(self):
        self.client_websocket = MyWebSocket(self.auth_token)
        asyncio.run_coroutine_threadsafe(self.message_listener_init(), self.loop)

    def create_chat(self):
        """Creates the main chat window if login is successfull"""

        self.message_text = tk.StringVar(value="")
        self.screen_text = tk.StringVar(value="Messages will appear here")
        self.create_text_field()
        self.create_text_entry()

    def get_auth_token(self) -> dict | None:
        """Submits username and password to get a bearer token from the server"""
        try:
            payload = {
                "username": self.username.get().strip(),
                "password": self.password.get().strip(),
            }
            response = requests.post(f"{URL}{LOGIN_ENDPOINT}", data=payload)
            response.raise_for_status()
            return response.json()

        except Exception as e:
            print(f"Auth token request failed: {e}")

    def create_signup_screen(self):
        """Create the sign up screen with input elements and buttons, called by clicking the "Sign up" button"""
        self.delete_all()

        # Clear the screen
        self.create_signup_info_label()
        self.create_username_entry()
        self.create_password_entry()
        self.create_signup_submit_button()
        self.create_back_button()

    def create_signup_info_label(self):
        signup_info_label = ttk.Label(
            self.frame,
            text="Enter username and password",
            font=VERY_SMALL_FONT_STYLE,
        )
        signup_info_label.grid(row=4, column=0)
        self.labels["signup_info"] = signup_info_label

    def create_signup_submit_button(self):
        """Create signup 'submit' button"""
        signup_button = ttk.Button(
            self.frame,
            text="Submit",
            command=lambda: self.submit_signup(),
        )
        self.buttons["signup"] = signup_button
        signup_button.grid(row=2)

    def submit_signup(self):
        account_info = {
            "username": self.username.get().strip(),
            "password": self.password.get().strip(),
        }
        try:
            self.entries["username_entry"].config(state="readonly")
            self.entries["password_entry"].config(state="readonly")
            response = requests.post(
                f"{URL}{CREATE_ACCOUNT_ENDPOINT}", json=account_info
            )

            # If account is created successfully, let the user know, wait 2.5s, and then log in with those credentials
            if response.status_code == 201:
                self.labels["signup_info"].config(
                    text="Account created successfully,\nLogging in now..."
                )
                self.frame.after(2500, self.submit_login)

            elif response.status_code == 409:
                self.labels["signup_info"].config(text="Username already exists")
                self.entries["username_entry"].config(state="normal")
                self.entries["password_entry"].config(state="normal")
            else:
                try:
                    issues: list = []
                    for issue in response.json().get("detail"):
                        element_name: str = issue.get("loc")[1].title()
                        issues.append(
                            f"{issue.get('msg').replace('String', element_name)}"
                        )
                    self.labels["signup_info"].config(text="\n".join(issues))
                    self.entries["username_entry"].config(state="normal")
                    self.entries["password_entry"].config(state="normal")

                except:
                    self.labels["signup_info"].config(text="Account creation failed")
                    self.frame.after(2500, self.create_startup_screen)

        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")

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

    def run_async_loop(self):
        # asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_forever()
        finally:
            self.loop.run_until_complete(self.loop.shutdown_asyncgens())
            # self.loop.close()

    async def message_listener_init(self):
        await self.connect_client_websocket()
        await self.listen_for_messages()

    async def connect_client_websocket(self):
        await self.client_websocket.connect()

    async def listen_for_messages(self):
        while self.is_running:
            try:
                message = await asyncio.wait_for(
                    self.client_websocket.websocket.recv(), timeout=1.0
                )
                self.display_message(message)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error receiving message: {e}")
                if not self.is_running:
                    break
                await asyncio.sleep(5)

    def display_message(self, message):
        message = self.decode_received_message(message)
        current_time = datetime.datetime.now().strftime("%H:%M")
        display_text = f"{current_time} Channel: {message['channel']}, Message: {message['content']}\n"
        # Use after() method to safely update GUI from a different thread
        self.window.after(0, self.update_text_field, display_text)

    def update_text_field(self, text):
        self.fields["text"].config(state="normal")
        self.fields["text"].insert(tk.END, text)
        self.fields["text"].config(state="disabled")
        self.fields["text"].yview(tk.END)  # Auto-scroll to the bottom

    def decode_received_message(self, message):
        try:
            return json.loads(message)
        except JSONDecodeError:
            print(f"Could not decode message: {message}")
        except Exception as e:
            print(f"Unknown error occurred when decoding message: {e}")

    def create_text_field(self):
        text_field = tk.Text(
            self.window,
            width=self.width,
            state="disabled",
            wrap="word",
        )
        text_field.grid(row=0, column=0, columnspan=2, sticky="nsew")
        self.fields["text"] = text_field

    def configure_responsive(self):
        # Configure grid row and column weights for responsive behaviour
        self.window.rowconfigure(0, weight=1)
        self.window.columnconfigure(0, weight=1)
        self.window.columnconfigure(1, weight=0)

    # Format for message:
    # {
    #   "channel": "username_1",
    #   "sender": "user123",
    #   "content": "Hello, world!",
    #   "timestamp": "2023-07-25T12:34:56Z"
    # }

    def send_message(self, event=None):
        message = self.entries["write_message"].get()
        if message.strip():  # Check if the message is not empty
            self.fields["text"].config(state="normal")
            current_time = datetime.datetime.now().strftime("%H:%M")
            self.fields["text"].insert(tk.END, f"{current_time} You: {message}\n")
            self.fields["text"].config(state="disabled")
            self.fields["text"].yview(tk.END)  # Auto-scroll to the bottom
            self.entries["write_message"].delete(0, tk.END)
            # Message formatted as json to send to server
            formatted_message: dict = {
                # TODO change channel hardcoding to dynamic once implemented
                # Username is added in the server from the bearer token to ensure accuracy
                "channel": "welcome",
                "content": message.strip(),
                "timestamp": current_time,
            }
            asyncio.run_coroutine_threadsafe(
                self.client_websocket.send_message(formatted_message), self.loop
            )

    def create_text_entry(self):
        message_entry = ttk.Entry(
            self.window, width=self.width - 70, background=OFF_WHITE
        )
        message_entry.grid(row=1, column=0, sticky="ew")
        message_entry.bind("<Return>", self.send_message)
        self.entries["write_message"] = message_entry

        send_button = ttk.Button(self.window, text="Send", command=self.send_message)
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

    def create_display_frame(self) -> tk.Frame:
        """Create the display Frame element"""
        frame = ttk.Frame(self.window, height=self.height, width=self.width)

        frame.grid(row=0, column=0)
        return frame

    async def check_server_status(self):
        try:
            response = await asyncio.to_thread(requests.get, f"{URL}/", timeout=5)
            response.raise_for_status()
            return response.json().get("status")
        except:
            return "unavailable"

    def start_server_status_check(self):
        asyncio.run_coroutine_threadsafe(self.update_server_status(), self.loop)

    async def update_server_status(self):
        self.server_status = await self.check_server_status()
        self.window.after(0, self.update_server_status_label)

    def update_server_status_label(self):
        if hasattr(self, "labels") and "server_status" in self.labels:
            self.labels["server_status"].config(
                text=f"Server status: {self.server_status}"
            )
        if self.server_status == "ready":
            self.enable_buttons()

    def on_closing(self):
        """Handle the closing event of the application."""
        self.is_running = False

        # Schedule the shutdown coroutine
        future = asyncio.run_coroutine_threadsafe(self.shutdown(), self.loop)

        # Wait for the shutdown to complete
        future.result()
        self.window.destroy()

    async def shutdown(self):
        """Coroutine to handle the shutdown process."""
        # Cancel all running tasks
        tasks = [
            t for t in asyncio.all_tasks(self.loop) if t is not asyncio.current_task()
        ]
        for task in tasks:
            task.cancel()

        # Wait for all tasks to be cancelled
        await asyncio.gather(*tasks, return_exceptions=True)

        # Close the websocket connection if it exists
        if self.client_websocket:
            await self.client_websocket.close()

        # Stop the loop
        self.loop.stop()

        # Wait for the loop to actually stop
        while self.loop.is_running():
            await asyncio.sleep(0.1)

        self.loop.close()

        # # Shutdown the executor
        # self.executor.shutdown(wait=True)

    def run(self):
        try:
            self.window.mainloop()
        finally:
            # Ensure shutdown procedure is called even if an exception occurs
            if self.is_running:
                self.on_closing()


if __name__ == "__main__":
    chattr = Chattr()
    chattr.run()