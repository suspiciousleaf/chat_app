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
# TODO Read DDIA on message encoding and decoding, protobuff. Could send messages faster over ws
# TODO Button or trigger to load older message history?
# TODO Add a max message character limit
# Errors sending messages to websockets that have disconnected, still present in docker logs


#! Database
#! TODO Add indexes

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
# TODO Add flame graph profiling to server
# ? Create endpoint to delete account, so accounts can be created, used, and deleted dynamically during testing

