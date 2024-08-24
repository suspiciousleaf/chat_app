import datetime
from os import getenv
import tkinter as tk
from tkinter import ttk, Event
import asyncio
import threading
import json
from json import JSONDecodeError
import requests
import time
from _tkinter import TclError

from dotenv import load_dotenv
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

# URL = "http://127.0.0.1:8000"
load_dotenv()
URL = getenv("URL")
LOGIN_ENDPOINT = "/auth/token"
CREATE_ACCOUNT_ENDPOINT = "/create_account"

WINDOW_WIDTH = 375
WINDOW_HEIGHT = 320
CHANNEL_WIDTH = 75
MAX_CHANNELS = 10

# Format for text message as received:
# {
#   "event": "message",
#   "channel": "username_1",
#   "sender": "user123",
#   "content": "Hello, world!",
#   "sent_at": "2023-07-25T12:34:56Z"
# }

# Format for text message as sent:
# {
#   "event": "message",
#   "channel": "welcome",
#   "content": "Hello, world!",
# }

# Format for info message as received:
# {
#   "event": "channel_subscriptions",
#   "data": ["welcome", "hello",...]
# }

# Format for info message as sent:
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
        self.window.minsize(self.channel_width + 300, self.height)
        self.window.title("Chattr")
        self.buttons: dict[str, tk.Button] = {}
        self.labels: dict[str, tk.Label] = {}
        self.entries: dict[str, tk.Entry] = {}
        self.fields: dict = {}
        self.frames: dict[str, ttk.Frame] = {}
        self.popup: dict = {}
        self.context_menu_target_channel: dict = {}
        self.tab_to_channel = {}  # Maps tab widget names to full channel names
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
        self.channels: list = []
        self.message_text = tk.StringVar(value="")
        self.screen_text = tk.StringVar(value="Messages will appear here")
        self.auth_token: dict[str, str] = {}
        self.client_websocket: MyWebSocket | None = None
        self.server_status: tk.StringVar = tk.StringVar(value="checking...")
        self.connection_active: bool = False

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
        username_entry.bind(
            "<Key-Return>", lambda event: self.entries["password_entry"].focus()
        )

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
        password_entry.bind("<Key-Return>", lambda event: self.submit_login())

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
        self.connection_active = True
        self.client_websocket = MyWebSocket(self.auth_token)
        asyncio.run_coroutine_threadsafe(self.message_listener_init(), self.loop)

    def process_logout(self):
        self.connection_active = False
        self.create_startup_screen()
        self.loop.call_soon_threadsafe(
            lambda: asyncio.create_task(self.close_websocket_connection())
        )

    def create_chat(self):
        """Creates the main chat window if login is successfull"""

        self.delete_all()
        self.message_text = tk.StringVar(value="")
        self.screen_text = tk.StringVar(value="Messages will appear here")
        self.create_container_frame()
        self.create_chat_frame()
        self.create_bottom_frame()
        self.create_notebook()
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
        send_button.grid(row=0, column=2, sticky="es", padx=2, pady=2)
        self.buttons["send"] = send_button

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

    def run_async_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    async def message_listener_init(self):
        await self.connect_client_websocket()
        await self.listen_for_messages()

    async def connect_client_websocket(self):
        await self.client_websocket.connect()

    async def listen_for_messages(self):
        while self.connection_active:
            try:
                message_str = await asyncio.wait_for(
                    self.client_websocket.websocket.recv(), timeout=1.0
                )
                message: dict = self.decode_received_message(message_str)
                if message is not None:
                    # "messages" can contain event information such as channel subscriptions, or message data. This filters based on keys present.
                    event_type = message.get("event")
                    if event_type == "channel_subscriptions":
                        new_channels = message.get("data")
                        if isinstance(new_channels, list):
                            self.channels.extend(new_channels)
                            self.build_channel_tabs(new_channels)
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
                if not self.connection_active:
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

    def create_notebook(self):
        self.style = ttk.Style()
        self.style.configure(
            "lefttab.TNotebook", tabposition=tk.W + tk.N, tabplacement=tk.N + tk.EW
        )
        current_theme = self.style.theme_use()
        self.style.theme_settings(
            current_theme,
            {
                "TNotebook.Tab": {
                    "configure": {
                        "background": "white",
                        "padding": [4, 4],
                        "anchor": "center",
                        "width": 10,
                        "font": "TkFixedFont",
                    }
                }
            },
        )

        self.nb = ttk.Notebook(self.frames["chat"], style="lefttab.TNotebook")
        self.nb.grid(row=0, column=0, sticky="nsew")

        # Each time the active tab is changed, this virtual event will update self.active_channel
        self.nb.bind("<<NotebookTabChanged>>", self.set_active_channel)
        # Bind right-click event to the notebook tabs
        self.nb.bind("<Button-3>", self.show_context_menu_with_channel_name)

        self.create_nb_context_menus()

    def create_nb_context_menus(self):
        """Create context menus to add or add/leave channels"""
        add_leave_context_menu = tk.Menu(self.nb, tearoff=0)
        add_leave_context_menu.add_command(
            label="Add new channel",
            command=lambda: self.add_channel_popup(),
        )
        add_leave_context_menu.add_command(
            label="Leave Channel", command=lambda: self.leave_channel()
        )
        self.nb.add_leave_context: tk.Menu = add_leave_context_menu

        # Create add-only context menu
        add_context_menu = tk.Menu(self.nb, tearoff=0)
        add_context_menu.add_command(
            label="Add new channel",
            command=lambda: self.add_channel_popup(),
        )
        self.nb.add_context_menu: tk.Menu = add_context_menu

        # Create leave-only context menu
        leave_context_menu = tk.Menu(self.nb, tearoff=0)
        leave_context_menu.add_command(
            label="Leave Channel", command=lambda: self.leave_channel()
        )
        self.nb.leave_context: tk.Menu = leave_context_menu

    def on_tab_right_click(self, event, channel_name: str, tab_index: int):
        """Handle the right-click action for chosen tab"""
        self.context_menu_target_channel = {
            "channel_name": channel_name,
            "tab_index": tab_index,
        }
        if len(self.channels) < MAX_CHANNELS:
            self.nb.add_leave_context.post(event.x_root, event.y_root)
        else:
            self.nb.leave_context.post(event.x_root, event.y_root)

    def on_notebook_right_click(self, event):
        """Handle the right-click action for the notebook background (outside of tabs)"""
        if len(self.channels) < MAX_CHANNELS:
            self.nb.add_context_menu.post(event.x_root, event.y_root)

    def leave_channel(self):
        channel_name = self.context_menu_target_channel.get("channel_name")
        tab_index = self.context_menu_target_channel.get("tab_index")

        # Remove the channel from the list and the notebook
        if channel_name in self.channels:
            self.channels.remove(channel_name)
        if channel_name in self.nb_tabs:
            tab_widget = self.nb_tabs[channel_name]
            del self.nb_tabs[channel_name]
            # Remove the mapping from tab_to_channel
            if str(tab_widget) in self.tab_to_channel:
                del self.tab_to_channel[str(tab_widget)]

        self.nb.forget(tab_index)

        self.leave_channel_server_notification(channel_name)

        # If this was the last tab, set active_channel to None
        if not self.channels:
            self.active_channel = None
        # Otherwise, set it to the new current tab
        else:
            self.set_active_channel()

    def leave_channel_server_notification(self, channel_name):
        """Create the leave channel message and send to the server"""

        formatted_message = {"event": "leave_channel", "channel": channel_name}

        asyncio.run_coroutine_threadsafe(
            self.client_websocket.send_message(formatted_message), self.loop
        )

    def add_channel_popup(self):
        """Create a popup window to enter new channel name"""
        popup = tk.Toplevel(self.window, background=OFF_WHITE)
        popup.geometry("280x25")
        popup.minsize(280, 25)
        popup.title("Add new channel")
        popup.resizable(True, False)
        popup_entry = ttk.Entry(popup)
        popup_entry.focus()

        popup.grid_columnconfigure(0, weight=1)
        self.popup["window"] = popup
        popup_entry.grid(row=0, column=0, sticky="ew", padx=2, pady=2)
        self.popup["channel_name_entry"]: tk.Entry = popup_entry
        # Bind Return to channel name entry
        self.popup["channel_name_entry"].bind("<Return>", self.add_new_channel)

    def add_new_channel(self, event):
        """Create the add channel message and send to the server"""

        channel_name = self.popup["channel_name_entry"].get()

        if (
            channel_name.strip() and channel_name.strip() not in self.channels
        ):  # Check if the message is not empty, and user isn't already subscribed to that channel

            self.popup["channel_name_entry"].delete(0, tk.END)
            formatted_message = {
                "event": "add_channel",
                "channel": channel_name.strip(),
            }
            # Close the input popup window
            self.popup["window"].destroy()

            # Push the send_message task to async thread
            asyncio.run_coroutine_threadsafe(
                self.client_websocket.send_message(formatted_message), self.loop
            )

    def set_active_channel(self, event=None):
        text_entry = self.entries.get("write_message")
        if text_entry:
            text_entry.focus()
        selected_tab = self.nb.select()
        if selected_tab:
            self.active_channel = self.tab_to_channel.get(str(selected_tab))
        else:
            self.active_channel = None

    def build_channel_tabs(self, channels: list):
        for channel_name in channels:
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

        # Store the mapping of tab widget name to full channel name
        self.tab_to_channel[str(text_field)] = channel_name

    def show_context_menu_with_channel_name(self, event):
        """Show context menu and identify which tab was right-clicked."""
        try:
            # Try to identify the index of the tab that was right-clicked
            tab_index = self.nb.index(f"@{event.x},{event.y}")
            if tab_index is not None:
                tab_widget = self.nb.tabs()[tab_index]
                full_channel_name = self.tab_to_channel.get(str(tab_widget))
                if full_channel_name:
                    self.on_tab_right_click(event, full_channel_name, tab_index)
        except TclError as e:
            # If no tab is clicked, handle right-click on the notebook background
            if str(e) == 'expected integer but got ""':
                self.on_notebook_right_click(event)
            else:
                print(f"Error determining the right-clicked tab: {e}")
        except Exception as e:
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
                "event": "message",
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
        self.connection_active = False

        if self.loop.is_running():
            self.loop.call_soon_threadsafe(lambda: asyncio.create_task(self.shutdown()))
        self.window.after(100, self.check_shutdown)

    def check_shutdown(self):
        """Check if background loop has closed, once it has close the main window"""
        if self.thread.is_alive():
            self.window.after(100, self.check_shutdown)
        else:
            self.window.destroy()

    async def close_websocket_connection(self):
        # Close the websocket connection if it exists
        if self.client_websocket:
            await self.client_websocket.close()

    async def shutdown(self):
        """Coroutine to handle the shutdown process."""

        await self.close_websocket_connection()

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
            if self.connection_active:
                self.on_closing()
            self.thread.join()


if __name__ == "__main__":
    chattr = Chattr()
    chattr.run()
