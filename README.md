# IS211_FinalProject - Blog

## Giulia Michieli

This final APP project is a simple blog. 
Allows users to register so they can create blog posts.
The application uses two Python files: db.py and app.py.
    db.py abstracts database connections and querying to simplify the code.
    app.py contains all of the application route logic and uses db.py for communicating with the database.
    The database used is sqlite for portability. It is initialized and filled with dummy data when the index route is visited if the schema doesn't already exist and the tables are empty.

Published posts are visible by all users, authenticated or not.
Unpublished posts are only visible to the users that created them.
Posts can be unpublished, edited, and deleted only by the users that created them.

Categories can be created by authenticated users and can be used by other authenticated users.

There are three data models:
- Users
    - Holds user/author information
    - Used to authenticate users and to attach posts to
- Categories
    - Used to hold information about post categories
- Posts
    - Used to store blog posts

### Run
python3 app.py

### Users
Emails = john@example.com, paul@example.com, george@example.com, ringo@example.com
Password = password
