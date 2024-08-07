from client.main_chat import Chattr

if __name__ == "__main__":
    chattr = Chattr()
    chattr.run()

# TODO Verify token expiry is working as expected
# TODO Make chat app ping server on startup to ensure it is available
# TODO Go through server files and reduce to one
# TODO Check ws login event loop thread logic and behaviour
# TODO On startup, add server status request response to the screen
# ! chat_app.db is being created in main users directory when accessed from the server, and in project directory when accessed directly
# TODO Go over database mathods and ensure they are returning all data in the expected format - eg retrieve_channels may not be
# TODO Add password salting logic
# TODO Add password salt to database
