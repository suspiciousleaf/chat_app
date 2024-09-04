from client.gui import Chattr

if __name__ == "__main__":
    chattr = Chattr()
    chattr.run()

#! Client
# TODO Make buttons remain still between screens during login
# TODO add full channel name banner to top of client, or show full name on mouse hover
# TODO Print all message history in one block, rather than line by line
# TODO Add a max message character limit

#! Auth
# TODO Verify token expiry is working as expected

#! Server
# TODO Read DDIA on mssage encoding and decoding, protobuff. Could send messages faster over ws
# TODO Check ws login event loop thread logic and behaviour
# TODO check disconnect logic
# TODO Message history can exceed max message size and cause disconnect, only load most recent 50 messages
# TODO Button or trigger to load older message history?
# TODO Add a max message character limit
# Connections are failing due to a TimeOutError, still happens when message history is commented out

#! Database
# TODO Add indexes

#! General
# TODO Add proper logging
# TODO unit testing
# TODO Integration testing
# TODO End-to-end testing
# TODO User flow testing
# TODO Perf testing

#! Other
# TODO Maybe open a PR to fix the issue of .index returning "" and causing TclError? Should return -1 if clicking outside of a tab, not through an exception


#! Hosted

#! Load testing
# TODO Create log out and shut down logic after actions completed
# TODO Run message listener in async loop
# TODO Change channels from hardcoded to dynamic
# TODO Add methods to join and leave groups
# ? Create endpoint to delete account, so accounts can be created, used, and deleted dynamically during testing

#! WIP
# TODO Get Artillery to auth and connect with multiple user accounts, test local and then on VPS"
#! Comment out everything apart from websocket connect and see if timeout issue still occurs
#! Add indexes to database
