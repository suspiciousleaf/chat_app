from client.gui import Chattr

if __name__ == "__main__":
    chattr = Chattr()
    chattr.run()

#! Client
# TODO Make buttons remain still between screens during login
# TODO Store channel message text in a dict so it can persist on channel updates when tabs are destroyed and rebuilt
# TODO show_context_menu() needs a try/except block when not clicking on a tab, find out why
# TODO Maybe open a PR to fix the issue of .index returning "" and causing TclError? Should return -1 if clicking outside of a tab, not through an exception
# TODO Change channel sub behaviour so adding or removing a channel sends a formatted ws message, which updates db and then sends a formatted message back that causes the channels to update


#! Auth
# TODO Verify token expiry is working as expected
# TODO Add password salting logic

#! Server
# TODO Check ws login event loop thread logic and behaviour
# TODO Add ability for people to update their channel subscriptions via endpoint
# TODO Auth is using its own instance of db_manager, refactor to pass through the main instance
# TODO check disconnect logic
# TODO Parse received messages for add / leave channel

#! Database
# TODO Add password salt to database
# TODO Add database functions to update channel subscriptions
# TODO Make db_manager async
# TODO DB method to add channel
# TODO DB method to leave channel

#! General
# TODO Add proper logging
# TODO unit testing
# TODO Integration testing
# TODO End-to-end testing
# TODO User flow testing
# TODO Perf testing
