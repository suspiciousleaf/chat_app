from client.gui import Chattr

if __name__ == "__main__":
    chattr = Chattr()
    chattr.run()

#! Client
# TODO Make channel selection list
# TODO Filter messages by channel
# TODO Store channel messages in a dict
# TODO Make buttons remain still between screens during login
# TODO Log in screen shifts left when log out button is pressed

#! Auth
# TODO Verify token expiry is working as expected
# TODO Add password salting logic

#! Server
# TODO Accounts logging in will need to receive messages from the server, and also any messages stored in connection_man.message_cache
# TODO Check ws login event loop thread logic and behaviour
# TODO Add ability for people to update their channel subscriptions via endpoint
# TODO Auth is using its own instance of db_manager, refactor to pass through the main instance
# TODO check disconnect logic

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
