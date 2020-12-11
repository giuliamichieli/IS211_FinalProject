from flask import Flask, render_template, request, session, redirect, abort, url_for
from db import init_db, query, insert, update, delete, close_connection
import datetime, re

app = Flask(__name__)

app.secret_key = "f1e069787ece74531d112559945c6871"

def check_auth():
    if "auth" in session:
        return True
    return False

def get_categories():
    categories = query("select * from categories order by category_display_name asc")
    return categories


def get_slug(slug, title):
    if (slug.strip() == ""):
        slug = title.strip().lower().replace(" ", "-")
    else:
        slug = slug.strip().lower().replace(" ", "-")
    slugs = query("select slug from posts where slug = ? or slug GLOB ?", (slug, slug + "-[0-9]"))
    
    if slugs:
        slug = slug + "-" + str(len(slugs))

    return slug


@app.route('/')
def index():
    init_db()
    breadcrumbs = [{"title": "Home", "url": "/"}]
    
    posts = query("select p.*, c.category_name, c.category_display_name, u.first_name as author_first_name, u.last_name as author_last_name \
            from posts p \
            inner join categories c \
            on c.id = p.category_id \
            inner join users u \
            on u.id = p.author_id \
            where p.is_published = 1 and published_at <= ?\
            order by updated_at desc, published_at desc", (datetime.datetime.now(),))

    return render_template("public/index.html", breadcrumbs=breadcrumbs, posts=posts, categories=get_categories(), page=1, alert=session.pop("alert", None) )

@app.route('/register')
def get_register():
    if not check_auth():
        breadcrumbs = [ {"title": "Home", "url": "/"}, {"title": "Register", "url": "/register"} ]
        return render_template("auth/register.html", breadcrumbs=breadcrumbs, errors=session.pop("errors", None), alert=session.pop("alert", None) )
    else:
        return redirect("/dashboard")



@app.route('/register', methods=['POST'])
def post_register():
    if check_auth():
        return redirect("/dashboard")

    def validate(form):
        validation_errors = {"messages": {}, "input": {}}
        
        if (form["first_name"].strip() == ""): validation_errors["messages"].update( {"first_name": "First name is a required field."})
        if (form["last_name"].strip() == ""): validation_errors["messages"].update( {"last_name": "Last name is a required field."})
        if not re.search(r'^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$', form["email"]):
            validation_errors["messages"].update({"email": "A valid email address is required."})
        if len(form['password']) < 8:
            validation_errors["messages"].update( {"password": "Password must be at least 8 characters long."})
        if (form["password_confirm"].strip() == ""): validation_errors["messages"].update( {"password_confirm": "Password confirmation is a required field."})
        if (form["password_confirm"] != form["password"]): validation_errors["messages"].update( {"password_confirm": "Passwords do not match."})
        if validation_errors["messages"]: validation_errors.update({"input": dict(form)})
        else: validation_errors = {}
        return validation_errors
    
    validation = validate(request.form)
    
    if not validation:
        row_id = insert("Insert into users (first_name, last_name, email, password) values (?, ?, ?, ?)",
                    (request.form["first_name"], request.form["last_name"], request.form["email"], request.form["password"] ))

        session['auth'] = { 'id': row_id, 'first_name': request.form["first_name"], 'last_name': request.form["last_name"], 'email':  request.form["email"]}        
        session["alert"] = { "level": "success", "message": "Success registered!"}
        return redirect("/dashboard")
    else:
        session["errors"] = validation
        return redirect("/register")


@app.route('/login')
def get_login():
    if not check_auth():
        return render_template("auth/login.html",alert=session.pop("alert", None))  
    else:
        return redirect("/dashboard")


@app.route('/login', methods=['POST'])
def post_login():
    def authenticate(email, password):
        auth = query("select id, first_name, last_name, email from users where email = ? and password = ?", (email, password), True)
        return auth

    auth = authenticate(request.form["email"], request.form["password"])
        
    if auth:
        session['auth'] = auth
        session["alert"] = { "level": "success", "message": "Successfully logged in!" }
        return redirect("/dashboard")
    else:
        session["alert"] = { "level": "danger", "message": "Incorrect Login. Please try again!" }
        return redirect("/login")

@app.route('/logout')
def logout():
    if check_auth():
        session.pop("auth", None)    
    return redirect("/")


@app.route('/dashboard')
def dashboard():
    if not check_auth():
        return redirect("/login")

    breadcrumbs = [ {"title": "Home", "url": "/"}, {"title": "Dashboard", "url": "/dashboard"} ]
    
    posts = query("select p.*, c.category_name, c.category_display_name, u.first_name, u.last_name \
            from posts p \
            inner join categories c \
            on c.id = p.category_id \
            inner join users u \
            on u.id = p.author_id \
            where u.id = ? order by updated_at desc, published_at desc", (session['auth']['id'], ))

    return render_template("admin/dashboard.html", breadcrumbs=breadcrumbs, posts=posts, categories=get_categories(), alert=session.pop("alert", None) )


@app.route('/post/<id>')
def get_post(id):

    post = query("select p.*, c.category_name, c.category_display_name, u.first_name author_first_name, u.last_name author_last_name\
                    from posts p \
                    inner join categories c \
                    on c.id = p.category_id \
                    inner join users u \
                    on u.id = p.author_id where p.id = ? or p.slug = ?", (id, id), True)

    if not post:
        abort(404)
    
    breadcrumbs = [
        {"title": "Home", "url": "/"},
        {"title": post['category_display_name'], "url": "/category/"+post['category_name']},
        {"title": post['title'], "url": "/post/"+post['slug']}
    ]
        
    return render_template("public/view_post.html", breadcrumbs=breadcrumbs, post=post, alert=session.pop("alert", None) )


@app.route('/post/add')
def get_add_post():
    if not check_auth():
        return redirect("/login")
    
    breadcrumbs = [
        {"title": "Home", "url": "/"},
        {"title": "Dashboard", "url": "/dashboard"},
        {"title": "Add Post", "url": "/post/add"}
    ]
    return render_template("admin/add/add_post.html", breadcrumbs=breadcrumbs, categories=get_categories(), errors=session.pop("errors", None), alert=session.pop("alert", None))


@app.route('/post/add', methods=['POST'])
def post_add_post():
    if not check_auth():
        return redirect("/login")

    def validate(form):
        validation_errors = {"messages": {}, "input": {}}

        if (form["category_id"].strip() == ""):
            validation_errors["messages"].update({"category_id": "Category is required."})
        
        elif (not query("select id from categories where id = ?", (int(form["category_id"]), ),True)):
            validation_errors["messages"].update(
                {"category_id": "Please select a category from the list."})
        
        if (form["title"].strip() == ""):
            validation_errors["messages"].update(
                {"last_name": "Title is a required field."})
        
        if (form["content"].strip() == ""):
            validation_errors["messages"].update(
                {"content": "Post content is required."})
        
        if (form["published_at"].strip() != ""):
            try:
                datetime.datetime.strptime(form["published_at"], '%Y-%m-%d')
            except ValueError:
                validation_errors["messages"].update(
                    {"published_at": "A valid date is required."})
        
        if validation_errors["messages"]:
            validation_errors.update({"input": dict(form)})        
        else:
            validation_errors = {}
        
        return validation_errors
    
    validation = validate(request.form)
    
    if not validation:
        slug = get_slug(request.form["slug"], request.form["title"])
        timestamp = datetime.datetime.now() \
                        if request.form["published_at"].strip() == "" \
                        else datetime.datetime.strptime(
                                request.form["published_at"], '%Y-%m-%d')
        is_published = 1 if not request.form.get('save', None) else 0
        row_id = insert("Insert into posts\
                        (\
                            author_id,\
                            category_id,\
                            title,\
                            slug,\
                            short_content,\
                            content,\
                            is_published,\
                            published_at,\
                            updated_at\
                        )\
                        values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            session["auth"]["id"],
                            request.form["category_id"],
                            request.form["title"],
                            slug,
                            request.form["short_content"],
                            request.form["content"],
                            is_published,
                            timestamp,
                            timestamp
                        )
                    )

        session["alert"] = { "level": "success", "message": "Post added successfully!" }
        return redirect("/post/{}".format(slug))    
    else:
        session["errors"] = validation
        return redirect("/post/add")


@app.route('/post/<id>/edit')
def get_edit_post(id):
    if not check_auth():
        return redirect("/login")
    
    post = query("select * from posts where id = ? or slug = ? and author_id = ?",(id, id, session["auth"]["id"]), True)
    
    if not post:
        abort(404)
    
    breadcrumbs = [
        {"title": "Home", "url": "/"},
        {"title": "Dashboard", "url": "/dashboard"},
        {"title": post['title'], "url": "/post/"+post['slug']},
        {"title": "Edit Post", "url": "/post/{}/edit".format(post['slug'])}
    ]

    return render_template("admin/edit/edit_post.html", breadcrumbs=breadcrumbs, categories=get_categories(), post=post, errors=session.pop("errors", None),
                           alert=session.pop("alert", None)
                           )

@app.route('/post/<id>/edit', methods=['POST'])
def post_edit_post(id):
    if not check_auth():
        return redirect("/login")
    
    post = query("select * from posts where id = ? or slug = ? and author_id = ?", (id, id, session["auth"]["id"]), True)
    
    if not post:
        abort(404)

    def validate(form):

        validation_errors = {"messages": {}, "input": {}}
        
        if (form["category_id"].strip() == ""):
            validation_errors["messages"].update(
                {"category_id": "Category is required."})
        
        elif (not query("select id \
                        from categories \
                        where id = ?",
                        (int(form["category_id"]), ),
                        True)):
            validation_errors["messages"].update({"category_id": "Please select a category from the list."})
        
        if (form["title"].strip() == ""):
            validation_errors["messages"].update({"last_name": "Title is a required field."})
        
        if (form["content"].strip() == ""):
            validation_errors["messages"].update({"content": "Post content is required."})
        
        if (form["published_at"].strip() != ""):
            try:
                datetime.datetime.strptime(form["published_at"], '%Y-%m-%d')
            except ValueError:
                validation_errors["messages"].update({"published_at": "A valid date is required."})
        
        if validation_errors["messages"]: validation_errors.update({"input": dict(form)})
        
        else:
            validation_errors = {}

        return validation_errors
    
    validation = validate(request.form)
    
    if not validation:
        timestamp = datetime.datetime.now()
        is_published = 1 if request.form.get('publish', None) \
                        else 0 if request.form.get('unpublish', None) \
                                else post["is_published"]
        row_id = update("update posts \
                        set category_id = ?, \
                            title = ?,\
                            short_content = ?,\
                            content = ?,\
                            is_published = ?,\
                            published_at = ?,\
                            updated_at = ? \
                        where id = ? and author_id = ?",
                        (
                            request.form["category_id"],
                            request.form["title"],
                            request.form["short_content"],
                            request.form["content"],
                            is_published,
                            datetime.datetime.strptime(
                                                request.form["published_at"]
                                                , '%Y-%m-%d'),
                            timestamp,
                            post["id"],
                            session["auth"]["id"]
                        )
                    )
        
        session["alert"] = {"level": "success", "message": "Post updated successfully!" }
        return redirect("/post/{}".format(post["slug"]))
    else:
        session["errors"] = validation
        return redirect("/post/{}/edit".format(id))


@app.route('/post/<id>/delete')
def get_delete_post(id):
    if not check_auth():
        return redirect("/login")

    post = query("select * from posts where id = ? and author_id = ?", (id, session["auth"]["id"]), True)
    
    if not post:
        abort(404)
    
    delete("delete from posts where id = ?", (id, ))
    
    session["alert"] = { "level": "success", "message": "Deleted post successfully."}
    return redirect("/dashboard")


@app.route('/category/<id>')
def get_category(id):

    category = query("select * from categories where id = ? or category_name = ?", (id, id), True)
    
    if not category:
        abort(404)
    
    posts = query("select p.*, \
                    u.first_name as author_first_name, \
                    u.last_name as author_last_name \
                from posts p \
                inner join users u \
                on u.id = p.author_id \
                where p.is_published = 1 and p.published_at <= ? \
                    and p.category_id = ?\
                order by p.updated_at desc, p.published_at desc",
                (datetime.datetime.now(), category["id"]))

    
    breadcrumbs = [
        {"title": "Home", "url": "/"}, {"title": category['category_display_name'], "url": "/category/"+category['category_name']}, ]
    
    return render_template("public/view_category.html",
                           breadcrumbs=breadcrumbs,
                           category=category,
                           categories=get_categories(),
                           posts=posts,
                           page=1,
                           alert=session.pop("alert", None)
                           )

@app.route('/category/add')
def get_add_category():
    if not check_auth():
        return redirect("/login")
    
    breadcrumbs = [
        {"title": "Home", "url": "/"},
        {"title": "Dashboard", "url": "/dashboard"},
        {"title": "Add Category", "url": "/category/add"}
    ]
    
    return render_template("admin/add/add_category.html",
                           breadcrumbs=breadcrumbs,
                           errors=session.pop("errors", None),
                           alert=session.pop("alert", None)
                           )

@app.route('/category/add', methods=['POST'])
def post_add_category():
    if not check_auth():
        return redirect("/login")

    def validate(form):
        
        validation_errors = {"messages": {}, "input": {}}
        
        if (form["category_name"].strip() == ""):
            validation_errors["messages"].update({"category_name": "Category name is required."})
        
        elif (query("select category_name from categories where category_name = ?", (form["category_name"], ), True)):
            validation_errors["messages"].update({"category_name": "Category name already exists."})

        if (form["category_display_name"].strip() == ""):
            validation_errors["messages"].update(
                {"last_name": "Category display name is a required field."})
        
        if validation_errors["messages"]:
            validation_errors.update({"input": dict(form)})        
        else:
            validation_errors = {}
        
        return validation_errors

    validation = validate(request.form)
    
    if not validation:
        insert("Insert into categories\
                        (\
                            category_name,\
                            category_display_name,\
                            category_description\
                        )\
                        values (?, ?, ?)",
                        (
                            request.form["category_name"].lower(),
                            request.form["category_display_name"],
                            request.form["category_description"]
                        )
                    )
        
        session["alert"] = { "level": "success", "message": "Category added successfully!" }
        return redirect("/category/{}".format(request.form["category_name"].lower()))
    else:        
        session["errors"] = validation        
        return redirect("/category/add")


@app.route('/category/<id>/edit')
def get_edit_category(id):
    if not check_auth():
        return redirect("/login")
    
    category = query("select * from categories where id = ? or category_name = ?", (id, id), True)

    if not category:
        abort(404)
    
    breadcrumbs = [
        {"title": "Home", "url": "/"},
        {"title": "Dashboard", "url": "/dashboard"},
        {"title": category["category_display_name"], "url": "/category/"+category['category_name']},
        {"title": "Edit Category", "url": "/category/{}/edit".format(category['category_name'])}
    ]

    return render_template("admin/edit/edit_category.html",
                           breadcrumbs=breadcrumbs,
                           category=category,
                           errors=session.pop("errors", None),
                           alert=session.pop("alert", None)
                           )

@app.route('/category/<id>/edit', methods=['POST'])
def post_edit_category(id):
    if not check_auth():
        return redirect("/login")
    
    category = query("select * from categories where id = ? or category_name = ?", (id, id), True)
    
    if not category:
        abort(404)

    def validate(form):

        validation_errors = {"messages": {}, "input": {}}

        if (form["category_name"].strip() == ""):
            validation_errors["messages"].update({"category_name": "Category name is required."})
        
        elif (query("select category_name \
                        from categories \
                        where category_name = ? and id != ?",
                        (form["category_name"], category["id"]),
                        True)):
            validation_errors["messages"].update({"category_name": "Category name already exists."})

        if (form["category_display_name"].strip() == ""):
            validation_errors["messages"].update({"last_name": "Category display name is a required field."})

        if validation_errors["messages"]:
            validation_errors.update({"input": dict(form)})        
        else:
            validation_errors = {}
        return validation_errors
    validation = validate(request.form)
    
    if not validation:
        update("update categories \
                set category_name = ?, \
                    category_display_name = ?,\
                    category_description = ?\
                where id = ?",
                (
                    request.form["category_name"],
                    request.form["category_display_name"],
                    request.form["category_description"],
                    category["id"]
                )
            )
        
        session["alert"] = {"level": "success","message": "Category updated successfully!"}    
        return redirect("/category/{}".format(request.form["category_name"].lower()))
    else:
        session["errors"] = validation
        return redirect("/category/{}/edit".format(id))


@app.route('/category/<id>/delete')
def get_delete_category(id):
    if not check_auth():
        return redirect("/login")

    category = query("select * from categories where id = ?", (id, ), True)
    
    if not category:
        abort(404)

    posts = query("select id from postswhere category_id = ?", (id, ))
    
    if posts:
        
        session["alert"] = {
            "level": "danger",
            "message": "Category could not be deleted, \
                        there are {} posts in the category. \
                        Update the post(s) categories first."\
                            .format(len(posts))
        }
        
        return redirect("/dashboard")

    delete("delete from categories where id = ?", (id, ))
    
    session["alert"] = { "level": "success", "message": "Deleted category successfully." }
    return redirect("/dashboard")

@app.teardown_appcontext
def teardown(exception):
    close_connection(exception)

if __name__ == '__main__':
    app.run()
