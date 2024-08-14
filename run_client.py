from client.gui import Chattr

if __name__ == "__main__":
    chattr = Chattr()
    chattr.run()

#! Client
# TODO Make buttons remain still between screens during login
# TODO Write channel handler
# TODO Store channel message text in a dict so it can persist on channel updates when tabs are destroyed and rebuilt

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
# TODO Make db_manager async

#! General
# TODO Add proper logging
# TODO unit testing
# TODO Integration testing
# TODO End-to-end testing
# TODO User flow testing
# TODO Perf testing
