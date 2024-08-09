from client.gui import Chattr

if __name__ == "__main__":
    chattr = Chattr()
    chattr.run()

#! Client
# TODO On startup, add server status request response to the screen
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


#! Database
# TODO Add password salt to database

#! General
# TODO Add proper logging
# TODO unit testing
# TODO Integration testing
# TODO End-to-end testing
# TODO User flow testing
# TODO Perf testing
