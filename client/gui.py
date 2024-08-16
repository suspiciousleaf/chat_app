import datetime
import tkinter as tk
from tkinter import ttk, Event
import asyncio
import threading
import json
from json import JSONDecodeError
import requests
import time
from _tkinter import TclError

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

WINDOW_WIDTH = 375
WINDOW_HEIGHT = 300
CHANNEL_WIDTH = 75

# Format for text message as received:
# {
#   "channel": "username_1",
#   "sender": "user123",
#   "content": "Hello, world!",
#   "sent_at": "2023-07-25T12:34:56Z"
# }

# Format for text message as sent:
# {
#   "channel": "welcome",
#   "content": "Hello, world!",
# }

# Format for info message as received:
# {
#   "event": "channel_subscriptions",
#   "data": ["welcome", "hello",...]
# }


class Chattr:
    def __init__(self):
        # Create instance attributes
        self.window: tk.Tk = tk.Tk()
        self.width: int = WINDOW_WIDTH
        self.height: int = WINDOW_HEIGHT
        self.channel_width = CHANNEL_WIDTH
        self.window.geometry(f"{self.width}x{self.height}")
        self.window.minsize(self.channel_width + 300, 300)
        self.window.title("Chattr")
        self.buttons: dict[str, tk.Button] = {}
        self.labels: dict[str, tk.Label] = {}
        self.entries: dict[str, tk.Entry] = {}
        self.fields: dict = {}
        self.frames: dict[str, ttk.Frame] = {}
        self.context_event: Event | None = None

        self.nb: ttk.Notebook | None = None
        self.nb_tabs: dict = {}
        self.active_channel: str | None = None

        style = ttk.Style()
        style.configure("Login.TFrame", background="light red")
        style.configure("Channel.TFrame", background="light blue")
        style.configure("Chat.TFrame", background="light green")

        # Session attributes
        self.username: tk.StringVar = tk.StringVar(value="username")
        self.password: tk.StringVar = tk.StringVar(value="password")
        self.channels: list | None = None
        self.message_text = tk.StringVar(value="")
        self.screen_text = tk.StringVar(value="Messages will appear here")
        self.auth_token: dict[str, str] = {}
        self.client_websocket: MyWebSocket | None = None
        self.server_status: tk.StringVar = tk.StringVar(value="checking...")
        self.is_running = True

        # Create background async event loop to handle IO operations and move to its own thread
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.run_async_loop, daemon=True)
        self.thread.start()

        # Create shutdown protocol that calls the shutdown method on closing
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Create the GUI
        self.create_startup_screen()

        # Disable buttons while checking the server status, will be enabled once health check returns positive
        self.disable_buttons()
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
        self.create_login_frame()
        self.create_login_button()
        self.create_signup_button()
        self.create_server_status_label()
        self.configure_login_responsive()

    def create_login_button(self):
        """Create the "Login" button"""
        self.username.set("username_1")
        self.password.set("password_1")
        login_button = ttk.Button(
            self.frames["login"],
            text="Log in",
            command=lambda: self.create_login_screen(),
        )
        self.buttons["login"] = login_button
        login_button.grid(row=0, column=0)

    def create_signup_button(self):
        """Create the "Sign up" button"""
        signup_button = ttk.Button(
            self.frames["login"],
            text="Create account",
            command=lambda: self.create_signup_screen(),
        )
        self.buttons["signup"] = signup_button
        signup_button.grid(row=1, column=0)

    def create_server_status_label(self):
        """Create a label bottom left that shows the status of the server"""
        status_label = ttk.Label(
            self.window,
            text=f"Server status: {self.server_status.get()}",
            font=VERY_SMALL_FONT_STYLE,
        )
        status_label.grid(row=0, column=0, sticky="sw", padx=5, pady=5)
        self.labels["server_status"] = status_label

    def create_login_screen(self):
        """Clears the screen, then creates the login widgets"""
        self.delete_widgets()
        self.create_username_entry()
        self.create_password_entry()
        self.create_login_submit_button()
        self.create_back_button()

    def create_username_entry(self):
        """Create 'username' entry widget"""
        username_entry = ttk.Entry(
            self.frames["login"],
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
            self.frames["login"],
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
            self.frames["login"],
            text="Log in",
            command=lambda: self.submit_login(),
        )
        self.buttons["login"] = login_button
        login_button.grid(row=2)

    def create_back_button(self):
        """Create 'back' button"""
        back_button = ttk.Button(
            self.frames["login"],
            text="Back",
            command=lambda: self.create_startup_screen(),
        )
        self.buttons["back"] = back_button
        back_button.grid(row=3)

    def submit_login(self):
        self.auth_token = self.get_auth_token()
        # This will create the chat screen if login is successfull
        if self.auth_token:
            self.process_login()
            self.create_chat()

    def process_login(self):
        self.client_websocket = MyWebSocket(self.auth_token)
        asyncio.run_coroutine_threadsafe(self.message_listener_init(), self.loop)

    def process_logout(self):
        # TODO Log in screen shifts left when this is called
        self.create_startup_screen()

    def create_chat(self):
        """Creates the main chat window if login is successfull"""

        self.delete_all()
        self.message_text = tk.StringVar(value="")
        self.screen_text = tk.StringVar(value="Messages will appear here")
        self.create_container_frame()
        self.create_chat_frame()
        self.create_bottom_frame()
        self.create_text_field()
        self.create_text_entry()
        self.create_logout_button()
        self.create_send_button()
        self.configure_chat_responsive()

    def create_logout_button(self):
        logout_button = ttk.Button(
            self.frames["bottom"],
            text="Log out",
            width=10,
            command=self.process_logout,
        )
        logout_button.grid(row=0, column=0, sticky="sw", padx=2, pady=2)
        self.buttons["logout"] = logout_button

    def create_send_button(self):
        send_button = ttk.Button(
            self.frames["bottom"], text="Send", command=self.send_message
        )
        send_button.grid(
            row=0, column=2, sticky="es", padx=2, pady=2
        )  # padx=(0, 5), pady=5)
        self.buttons["send"] = send_button

    # def create_channel_placeholder(self):
    #     channel_label = ttk.Label(
    #         self.frames["channel"], text="Channels", wraplength=self.channel_width - 10
    #     )
    #     channel_label.grid(row=0, column=0, sticky="n")
    #     self.labels["channel_placeholder"] = channel_label

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
        self.delete_widgets()

        # Clear the screen
        self.create_signup_info_label()
        self.create_username_entry()
        self.create_password_entry()
        self.create_signup_submit_button()
        self.create_back_button()

    def create_signup_info_label(self):
        signup_info_label = ttk.Label(
            self.frames["login"],
            text="Enter username and password",
            font=VERY_SMALL_FONT_STYLE,
        )
        signup_info_label.grid(row=4, column=0)
        self.labels["signup_info"] = signup_info_label

    def create_signup_submit_button(self):
        """Create signup 'submit' button"""
        signup_button = ttk.Button(
            self.frames["login"],
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
                self.frames["login"].after(2500, self.submit_login)

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
                    self.frames["login"].after(2500, self.create_startup_screen)

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

    def delete_widgets(self):
        """Delete all elements on the screen, excluding Frame"""
        self.delete_labels()
        self.delete_buttons()
        self.delete_entries()

    def run_async_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    async def message_listener_init(self):
        await self.connect_client_websocket()
        await self.listen_for_messages()

    async def connect_client_websocket(self):
        await self.client_websocket.connect()

    async def listen_for_messages(self):
        while self.is_running:
            try:
                message_str = await asyncio.wait_for(
                    self.client_websocket.websocket.recv(), timeout=1.0
                )
                message: dict = self.decode_received_message(message_str)
                if message is not None:
                    # "messages" can contain event information such as channel subscriptions, or message data. This filters based on keys present.
                    event_type = message.get("event")
                    if event_type == "channel_subscriptions":
                        self.channels = message.get("data")
                        self.build_channel_tabs()
                    elif event_type == "message history":
                        for individual_message in message.get("data", []):
                            self.process_received_message(individual_message)
                    else:
                        self.process_received_message(message)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error receiving message: {e}")
                if not self.is_running:
                    break
                await asyncio.sleep(5)

    def process_received_message(self, message: dict):
        """Format the received message and send it to the method to update the display"""
        # Generate a string showing the message sent timestamp in HH:MM format for the local timezone of the client
        message_timestamp = (
            datetime.datetime.fromisoformat(message["sent_at"])
            .astimezone()
            .strftime("%H:%M")
        )
        display_text = f"{message_timestamp}: {message['content']}\n"
        # Use after() method to safely update GUI from a different thread
        self.window.after(0, self.update_text_field, message["channel"], display_text)

    def update_text_field(self, channel: str, text: str):
        self.nb_tabs[channel].config(state="normal")
        self.nb_tabs[channel].insert(tk.END, text)
        self.nb_tabs[channel].config(state="disabled")
        self.nb_tabs[channel].yview(tk.END)  # Auto-scroll to the bottom

    def decode_received_message(self, message: str) -> dict:
        try:
            return json.loads(message)
        except JSONDecodeError:
            print(f"Could not decode message: {message}")
        except Exception as e:
            print(f"Unknown error occurred when decoding message: {e}")

    def create_text_field(self):
        self.style = ttk.Style()
        self.style.configure(
            "lefttab.TNotebook", tabposition=tk.W + tk.N, tabplacement=tk.N + tk.EW
        )
        current_theme = self.style.theme_use()
        self.style.theme_settings(
            current_theme,
            {
                "TNotebook.Tab": {
                    "configure": {"background": "white", "padding": [4, 4]}
                }
            },
        )
        self.style.configure("TNotebook", tabposition="wn")
        self.nb = ttk.Notebook(self.frames["chat"], style="lefttab.TNotebook")
        self.nb.grid(row=0, column=0, sticky="nsew")
        self.style.configure("TFrame", background="white")
        # Each time the active tab is changed, this virtual event will update self.active_channel
        self.nb.bind("<<NotebookTabChanged>>", self.set_active_channel)
        # self.nb.bind("<Button-3>", self.on_notebook_right_click)
        # Bind right-click event to the notebook tabs
        self.nb.bind("<Button-3>", self.show_context_menu_with_channel_name)

        self.create_nb_context_menu()
        # Bind right-click event to each tab
        # self.nb.bind("<Button-3>", self.show_context_menu)

    def create_nb_context_menu(self):
        """Create context menus to add or add/leave channels"""
        # Create add/leave context menu
        add_leave_context_menu = tk.Menu(self.nb, tearoff=0)
        add_leave_context_menu.add_command(
            label="Add new channel",
            command=lambda: self.add_new_channel(),
        )
        add_leave_context_menu.add_command(
            label="Leave Channel", command=lambda: self.leave_channel()
        )
        self.nb.add_leave_context: tk.Menu = add_leave_context_menu

        # Create add-only context menu
        add_context_menu = tk.Menu(self.nb, tearoff=0)
        add_context_menu.add_command(
            label="Add new channel",
            command=lambda: self.add_new_channel(),
        )
        self.nb.add_context_menu: tk.Menu = add_context_menu

    def on_tab_right_click(self, event, channel_name):
        # # Focus on the right-clicked tab
        # selected_tab = self.nb_tabs[channel_name]
        # self.nb.select(selected_tab)

        # Handle the right-click action for this specific tab
        print(f"{channel_name} tab clicked")

    def on_notebook_right_click(self, event):
        # # Handle the right-click action for the notebook background (outside of tabs)
        print("Right-clicked on the notebook, but not on a tab")

    def show_context_menu(self, event):
        """Show the relevant context menu based on cursor position"""
        try:
            self.context_event = event
            try:
                tab_index = self.nb.index(f"@{event.x},{event.y}")
            except:
                tab_index = -1
            if tab_index != -1:
                self.nb.add_leave_context.post(event.x_root, event.y_root)
            else:
                self.nb.add_context_menu.post(event.x_root, event.y_root)
        except Exception as e:
            print(f"Error showing context menu: {e}")

    def leave_channel(self):
        print("leave_channel()")

        event = self.context_event

        if event:
            tab_index = self.nb.index(f"@{event.x},{event.y}")

            channel_name = self.nb.tab(tab_index, "text")
            print(f"Removing channel: {channel_name}")

            # # Remove the channel from the list and the notebook
            # if channel_name in self.channels:
            #     self.channels.remove(channel_name)
            # if channel_name in self.nb_tabs:
            #     del self.nb_tabs[channel_name]
            # self.nb.forget(tab_index)

            # # If this was the last tab, set active_channel to None
            # if not self.channels:
            #     self.active_channel = None
            # # Otherwise, set it to the new current tab
            # else:
            #     self.set_active_channel()

            # # TODO: Notify the server that we've left this channel

    def add_new_channel(self, event=None):
        print("add_new_channel()")
        if event is None:
            event = self.context_event
        print(event)

    def set_active_channel(self, event=None):
        # self.active_channel = self.channels[self.nb.index(self.nb.select())]

        selected_tab = self.nb.select()
        if selected_tab:
            self.active_channel = self.nb.tab(selected_tab, "text")
        else:
            self.active_channel = None

    # def build_channel_tabs(self):
    #     if self.channels:
    #         for channel_name in self.channels:
    #             text_field = tk.Text(self.nb, wrap="word", state="disabled")
    #             text_field.grid(row=0, column=0, sticky="nsew")
    #             self.nb_tabs[channel_name] = text_field

    #             self.nb.add(
    #                 self.nb_tabs[channel_name],
    #                 text=channel_name,
    #                 sticky="nsew",
    #             )

    # #! Does not work
    # # Set a fixed width for all tabs. This will truncate long names but allow them to be viewed on hover
    # self.nb.configure(width=400)

    def build_channel_tabs(self):
        if self.channels:
            for channel_name in self.channels:
                self.add_channel(channel_name)

    def add_channel(self, channel_name):
        # Create a text field for the new channel
        text_field = tk.Text(self.nb, wrap="word", state="disabled")
        text_field.grid(row=0, column=0, sticky="nsew")

        # Store the text field in the nb_tabs dictionary
        self.nb_tabs[channel_name] = text_field

        # Truncate the channel name if necessary for display
        if len(channel_name) > 10:
            channel_name_displayed = f"{channel_name[:7]}..."
        else:
            channel_name_displayed = channel_name

        # Add the tab to the notebook using the truncated name for display
        self.nb.add(
            text_field,
            text=channel_name_displayed,
            sticky="nsew",
        )

    def show_context_menu_with_channel_name(self, event):
        """Show context menu and identify which tab was right-clicked."""
        try:
            # Try to identify the index of the tab that was right-clicked
            tab_index = self.nb.index(f"@{event.x},{event.y}")
            print(f"{tab_index=}")
            if tab_index != "":
                # Get the full channel name from the nb_tabs dictionary
                for channel_name, text_field in self.nb_tabs.items():
                    if text_field == self.nb.nametowidget(self.nb.tabs()[tab_index]):
                        # Now you have the full channel name
                        print(f"Right-clicked on tab: {channel_name}")
                        self.on_tab_right_click(event, channel_name)
                        break
            # else:
            #     # If no tab is clicked, handle right-click on the notebook background
            #     self.on_notebook_right_click(event)
        except TclError as e:
            if str(e) == 'expected integer but got ""':
                self.on_notebook_right_click(event)
        except:
            print(f"Error determining the right-clicked tab: {e}")

    def configure_login_responsive(self):
        # Configure grid row and column weights for login responsive behaviour
        self.window.grid_rowconfigure(0, weight=1)
        self.window.grid_columnconfigure(0, weight=1)
        self.frames["login"].grid_rowconfigure(0, weight=1)
        self.frames["login"].grid_columnconfigure(0, weight=1)
        self.frames["login"].grid_columnconfigure(1, weight=0)

    def configure_chat_responsive(self):
        """Configure grid row and column weights for chat responsive behaviour"""
        self.window.grid_rowconfigure(0, weight=1)
        self.window.grid_columnconfigure(0, weight=1)

        self.frames["container"].grid_rowconfigure(0, weight=1)
        self.frames["container"].grid_rowconfigure(1, weight=0)
        self.frames["container"].grid_columnconfigure(0, weight=1)

        self.frames["chat"].grid_rowconfigure(0, weight=1)
        self.frames["chat"].grid_columnconfigure(0, weight=1)

        self.frames["bottom"].grid_columnconfigure(1, weight=1)

    def send_message(self, event=None):
        message = self.entries["write_message"].get()
        if message.strip():  # Check if the message is not empty
            self.entries["write_message"].delete(0, tk.END)
            # Message formatted as json to send to server
            formatted_message: dict = {
                # Username is added in the server from the bearer token to ensure accuracy
                "channel": self.active_channel,
                "content": message.strip(),
            }
            asyncio.run_coroutine_threadsafe(
                self.client_websocket.send_message(formatted_message), self.loop
            )

    def create_text_entry(self):
        """Create the text entry widget to write and send messages"""
        message_entry = ttk.Entry(self.frames["bottom"], background=OFF_WHITE)
        message_entry.grid(row=0, column=1, sticky="nsew", padx=1, pady=2)
        message_entry.bind("<Return>", self.send_message)
        self.entries["write_message"] = message_entry

        self.frames["chat"].grid_columnconfigure(0, weight=1)
        self.frames["chat"].grid_columnconfigure(1, weight=0)

    def print_contents(self, event: Event):
        entry_widget = event.widget
        print("Hi. The current entry content is:", entry_widget.get())

    def delete_buttons(self):
        """Delete all buttons"""
        for button in self.buttons:
            self.buttons[button].grid_forget()
        self.buttons.clear()

    def delete_entries(self):
        """Delete all entries"""
        for entry in self.entries:
            self.entries[entry].grid_forget()
        self.entries.clear()

    def delete_labels(self):
        """Delete all labels"""
        for label in self.labels:
            self.labels[label].grid_forget()
        self.labels.clear()

    def delete_frames(self):
        """Delete all frames"""
        for frame in self.frames:
            self.frames[frame].destroy()
        self.frames.clear()

    def delete_widgets(self):
        """Delete all widgets"""
        self.delete_labels()
        self.delete_buttons()
        self.delete_entries()

    def delete_all(self):
        """Delete everything on the GUI"""
        self.delete_widgets()
        self.delete_frames()

    def create_login_frame(self):
        """Create the login Frame element"""
        frame = ttk.Frame(self.window, height=self.height, width=self.width)
        frame.grid(row=0, column=0)
        frame["style"] = "Login.TFrame"
        self.frames["login"] = frame

    def create_container_frame(self):
        container_frame = ttk.Frame(self.window)
        container_frame.grid(row=0, column=0, sticky="nsew")
        self.frames["container"] = container_frame

    def create_chat_frame(self):
        """Create the chat Frame element"""
        frame = ttk.Frame(self.frames["container"])
        # frame.grid(row=0, column=1, sticky="nsew")
        frame.grid(row=0, column=0, sticky="nsew")
        frame["style"] = "Chat.TFrame"
        self.frames["chat"] = frame

    def create_bottom_frame(self):
        """Create the bottom Frame element"""
        frame = ttk.Frame(self.frames["container"], height=30)  # Fixed height
        frame.grid(row=1, column=0, sticky="ew")
        frame.grid_propagate(False)
        frame["style"] = "Bottom.TFrame"
        self.frames["bottom"] = frame

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
        self.server_status.set(await self.check_server_status())
        self.window.after(0, self.update_server_status_label)

    def update_server_status_label(self):
        if hasattr(self, "labels") and "server_status" in self.labels:
            self.labels["server_status"].config(
                text=f"Server status: {self.server_status.get()}"
            )
        if self.server_status.get() == "ready":
            self.enable_buttons()

    def on_closing(self):
        """Handle the closing event of the application."""
        self.is_running = False

        if self.loop.is_running():
            self.loop.call_soon_threadsafe(lambda: asyncio.create_task(self.shutdown()))
        self.window.after(100, self.check_shutdown)

    def check_shutdown(self):
        """Check if background loop has closed, once it has close the main window"""
        if self.thread.is_alive():
            self.window.after(100, self.check_shutdown)
        else:
            self.window.destroy()

    async def shutdown(self):
        """Coroutine to handle the shutdown process."""
        # Close the websocket connection if it exists
        if self.client_websocket:
            await self.client_websocket.close()

        # Gather all tasks in the background event loop (excluding this one), and cancel them
        tasks = [
            t for t in asyncio.all_tasks(self.loop) if t is not asyncio.current_task()
        ]
        for task in tasks:
            task.cancel()

        # Wait for all tasks to be cancelled, then stop the loop
        await asyncio.gather(*tasks, return_exceptions=True)
        self.loop.stop()

    def run(self):
        try:
            self.window.mainloop()
        finally:
            if self.is_running:
                self.on_closing()
            self.thread.join()


if __name__ == "__main__":
    chattr = Chattr()
    chattr.run()
