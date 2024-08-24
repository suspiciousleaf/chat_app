from client.gui import Chattr

if __name__ == "__main__":
    chattr = Chattr()
    chattr.run()

#! Client
# TODO Make buttons remain still between screens during login
# TODO channel tab width changes with longer channel names, 10 letters eg wwwwwwwwww
# TODO add full channel name banner to top of client
# TODO Remove channel name truncation and tab select logic

#! Auth
# TODO Verify token expiry is working as expected

#! Server
# TODO Check ws login event loop thread logic and behaviour
# TODO check disconnect logic

#! Database

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
# TODO Server is hosted, health check returns good, log in auth works but notebook doesn't load. Read database file to check channel subscriptions etc, and also check logs in container to see what the error is.
