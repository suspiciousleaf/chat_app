from client.main_chat import Chattr

if __name__ == "__main__":
    chattr = Chattr()
    chattr.run()

# TODO Verify token expiry is working as expected
# TODO Make chat app ping server on startup to ensure it is available
# TODO Go through server files and reduce to one
# TODO Check ws login event loop thread logic and behaviour
# TODO Add send message functionality
