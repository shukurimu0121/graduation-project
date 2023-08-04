from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from cs50 import SQL

# configure app
app = Flask(__name__)

#configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

db = SQL("sqlite:///test.db")

# login required decorator
def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

# each route 
# index route
@app.route("/")
@login_required
def index():
    # show users goal
    user_id = session["user_id"]

    # get the user's goal
    rows = db.execute("SELECT * FROM goals WHERE user_id = ?", user_id)
    if len(rows) != 0:
        user_goal = rows[0]["goal"]
        return render_template("index.html", goal=user_goal)
    
    else:
        return render_template("index.html")

# login route
@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    # Forget any user_id
    session.clear()

    # When POST
    if request.method == "POST":
        # get the user's input
        username = request.form.get("username")
        password = request.form.get("password")

        # When invalid input
        if not username:
            return render_template("apology.html", msg="must provide username")

        elif not password:
            return render_template("apology.html", msg="must provide password")

        # Get all username from database
        rows = db.execute("SELECT * FROM users WHERE name = ?", username)

        # Check the username and password are correct
        if len(rows) != 1 or not check_password_hash(rows[0]["password_hash"], password):
            return render_template("apology.html", msg="invalid username or password")

        # All OK add user to session
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # When GET
    else:
        return render_template("login.html")
    
# logout route
@app.route("/logout")
def logout():
    """Log user out"""
    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

# register route
@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
     # When POST
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Ensure username was submitted
        if not username:
            return render_template("apology.html", msg="must provide username")

        # Ensure password was submitted
        elif not password:
            return render_template("apology.html", msg="must provide password")

        # Ensure password was submitted again
        elif not confirmation:
            return render_template("apology.html", msg="must provide password again")

        # password matches confirmation
        elif password != confirmation:
            return render_template("apology.html", msg="must provide the same passwords")

        # Check the username already exists
        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE name = ?", username)
        if  len(rows) != 0:
            return render_template("apology.html", msg="the username is already used")

        else:
            # Insert username and password hash to table
            password_hash = generate_password_hash(password)
            db.execute("INSERT INTO users (name, password_hash) VALUES(?, ?)", username, password_hash)

            # redirect log in page
            return redirect("/")

    else:
        return render_template("register.html")
    
# room route
@app.route("/make_room", methods=["GET", "POST"])
@login_required
def make_room():
    """Make Room"""
    # get the user's id
    user_id = session["user_id"]

    # When POST
    if request.method == "POST":
        # get the user's input
        room_id = int(request.form.get("room_id"))
        room_password = request.form.get("room_password")

        # When invalid input
        if not room_id or not room_password:
            return render_template("apology.html", msg="must provide room id and password")
        
        # if the room id already exists, return apology
        rows = db.execute("SELECT * FROM rooms WHERE id = ?", room_id)
        if len(rows) != 0:
            return render_template("apology.html", msg="the room id is already used")

        # password to hash
        room_password_hash = generate_password_hash(room_password)

        # Put room info to database
        try:
            db.execute("INSERT INTO rooms (id, room_password_hash, user_id) VALUES(?, ?, ?)", room_id, room_password_hash, user_id)
            return redirect(url_for("enter_room"), room_id=room_id)
        
        except:
            return render_template("apology.html", msg="you already join a room")

    # When GET
    else:
        return render_template("make_room.html")
    
# enter room route
@app.route("/enter_room", methods=["GET", "POST"])
@login_required
def enter_room():
    """enter room"""
    # get the user's id
    user_id = session["user_id"]

    # When POST
    if request.method == "POST":
        # get the user's input
        room_id = request.form.get("room_id")
        room_password = request.form.get("room_password")

        # When invalid input
        if not room_id or not room_password:
            return render_template("apology.html", msg="must provide room id and password")
        
        # check user submit goal
        goal = db.execute("SELECT * FROM goals WHERE user_id = ?", user_id)
        if len(goal[0]["goal"]) == 0:
            return render_template("apology.html", msg="you must submit your goal")
        
        # Get room info from database
        room = db.execute("SELECT * FROM rooms WHERE id = ?", room_id)

        # Check the room id and password are correct
        if len(room) == 0 or not check_password_hash(room[0]["room_password_hash"], room_password):
            return render_template("apology.html", msg="invalid room id or password")
        
        else:
            rows = db.execute("SELECT * FROM rooms WHERE user_id = ?", user_id)
            if len(rows) != 0:
                return redirect(url_for("room", room_id=room_id))
            
            else:
                # ユーザーを部屋に追加
                db.execute("INSERT INTO rooms (id, room_password_hash, user_id) VALUES (?, ?, ?)", room_id, room[0]["room_password_hash"], user_id)
                return redirect(url_for("room", room_id=room_id))
    # When GET
    else:
        return render_template("enter_room.html")
    
# room route
@app.route("/room")
@login_required
def room():
    room_id = request.args.get("room_id")

    # get the participants' id info
    participants_id = db.execute("SELECT user_id FROM rooms WHERE id = ?", room_id)

    # set the list of goals
    goals = []
    # get all menbers' goal info
    for participant in participants_id:
        participant_id = participant["user_id"]
        goal = db.execute("SELECT goal FROM goals WHERE user_id = ?", participant_id)[0]["goal"]
        goals.append(goal)
    
    return render_template("room.html", goals=goals)
    
# goal route
@app.route("/goal", methods=["GET", "POST"])
@login_required
def goal():
    """goal"""
    # Get user's id
    user_id = session["user_id"]

    # When POST
    if request.method == "POST":
        # get the user's goal input
        goal = request.form.get("goal")

        # When invalid input
        if not goal:
            return render_template("apology.html", msg="must provide goal")
        
        # Put goal info to database
        try:
            db.execute("INSERT INTO goals (goal, user_id) VALUES(?, ?)", goal, user_id)

        except:
            return render_template("apology.html", msg="failure")
        
        # Redirect user to room page
        return redirect("/")
    
    # When GET
    else:
        # if user already has a goal, display it
        rows = db.execute("SELECT * FROM goals WHERE user_id = ?", user_id)
        if len(rows) == 1:
            return render_template("goal.html", goal=rows[0]["goal"], id=rows[0]["id"])
        else:
            return render_template("goal.html")
        
# delete goal route
@app.route("/delete_goal", methods=["POST"])
@login_required
def delete_goal():
    """delete goal"""

    # get user goal id
    goal_id = request.form.get("goal_id")

    # delete goal from database
    try:
        db.execute("DELETE FROM goals WHERE id = ?", goal_id)
        return redirect("/goal")
    
    except:
        return render_template("apology.html", msg="failure")

        
if __name__ == "__main__":
    app.run(debug=True, port=5000)  
