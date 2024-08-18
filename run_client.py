from client.gui import Chattr

if __name__ == "__main__":
    chattr = Chattr()
    chattr.run()

#! Client
# TODO Make buttons remain still between screens during login
# TODO Store channel message text in a dict so it can persist on channel updates when tabs are destroyed and rebuilt
# TODO channel tab width changes with longer channel names, 10 letters eg wwwwwwwwww

#! Auth
# TODO Verify token expiry is working as expected
# TODO Add password salting logic

#! Server
# TODO Check ws login event loop thread logic and behaviour
# TODO Auth is using its own instance of db_manager, refactor to pass through the main instance
# TODO check disconnect logic

#! Database
# TODO Add password salt to database
# TODO Make db_manager async

#! General
# TODO Add proper logging
# TODO unit testing
# TODO Integration testing
# TODO End-to-end testing
# TODO User flow testing
# TODO Perf testing

#! Other
# TODO Maybe open a PR to fix the issue of .index returning "" and causing TclError? Should return -1 if clicking outside of a tab, not through an exception
