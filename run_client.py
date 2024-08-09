from client.gui import Chattr

if __name__ == "__main__":
    chattr = Chattr()
    chattr.run()

#! Client
# TODO On startup, add server status request response to the screen
# TODO Disable buttons if server status is not ok
# TODO Make logout button
# TODO Filter messages by channel
# TODO Make buttons remain still between screens during login

#! Auth
# TODO Verify token expiry is working as expected
# TODO Add password salting logic

#! Server
# TODO Add timeout for batch message inserts
# TODO Make endpoint to check server health, and make server verify connection to database and redis before responding.
# TODO Check ws login event loop thread logic and behaviour
# TODO Add message timestamp
# TODO Add ability for people to update their channel subscriptions via endpoint
# TODO Auth is using its own instance of db_manager, refactor to pass through the main instance
# TODO Listener isn't listening since reorganising file structure


#! Database
# TODO Add password salt to database
# TODO Add database functions to update channel subscriptions

#! General
# TODO Add proper logging
# TODO unit testing
# TODO Integration testing
# TODO End-to-end testing
# TODO User flow testing
# TODO Perf testing
