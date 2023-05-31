from datetime import date
from flask import Flask, redirect, render_template, session, request, flash
from flaskwebgui import FlaskUI
from tempfile import mkdtemp
from flask_session import Session
from cs50 import SQL
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image

from chatbot import send_attachment as send_ticket
from barcode_generator import generate_barcode
from ticket_generator import generate_ticket

import string
import random
import os
import fitz

app = Flask(__name__)
ui = FlaskUI(app, width=500, height=500)
app.config["TEMPLATES_AUTO_RELOAD"] = True

UPLOAD_FOLDER = "designs/"
ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

db = SQL("sqlite:///tickets.db")
year = date.today().year

def apology(message, error_code):
    return render_template("apology.html", message=message, error_code=error_code)

def generate_ticket_hash(size=10, chars=string.ascii_uppercase + string.digits):
    return "".join(random.SystemRandom().choice(chars) for _ in range(size))

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def pdf_to_png(filename):
    filepath = "designs/%s"%filename
    doc = fitz.open(filepath)
    page = doc.loadPage(0)
    pix = page.get_pixmap()
    output = filename.rsplit(".", 1)[0].lower() + ".png"
    pix.save("designs/%s"%output)

def jpg_to_png(filename, id):
    im = Image.open("designs/%s"%filename)
    im.save("designs/%s.png"%id)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") == None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        if not request.form.get("event"):
            return apology("Oops! Something went wrong.", 503)
        global event_id
        event_id = request.form.get("event")
        return redirect("/event/%s"%event_id)
    events = db.execute("SELECT * FROM events WHERE user_id = ?", session["user_id"])
    return render_template("index.html", year=year, title="Home", events=events)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if not request.form.get("username"):
            return apology("Must provide username", 403)
        if not request.form.get("password"):
            return apology("Must provide password", 403)
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
        if len(rows) != 1 or not check_password_hash(rows[0]["password"], request.form.get("password")):
            return apology("Invalid username and/or password", 409)
        session["user_id"] = rows[0]["id"]
        return redirect("/")
    return render_template("login.html", year=year, title="Login")

@app.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        if not request.form.get("username"):
            return apology("Must provide username", 403)
        if not request.form.get("password") or not request.form.get("confirmation"):
            return apology("Must provide password and/or confirmation", 403)
        if request.form.get("password") != request.form.get("confirmation"):
            return apology("Password and confirmation do not match", 403)
        usernames = db.execute("SELECT username FROM users")
        for username in usernames:
            if request.form.get("username") == username:
                return apology("Username already taken", 409)
        db.execute("INSERT INTO users (username, password) VALUES (?, ?)", request.form.get("username"), generate_password_hash(request.form.get("password")))
        return redirect("/")
    return render_template("register.html", year=year, title="Register")

@app.route("/changepass", methods=["GET", "POST"])
@login_required
def changepass():
    if request.method == "POST":
        if not request.form.get("password") or not request.form.get("confirmation"):
            return apology("Missing password and/or confirmation", 403)
        if request.form.get("password") != request.form.get("confirmation"):
            return apology("Password and confirmation do not match", 409)
        db.execute("UPDATE users SET password = ? WHERE id = ?", generate_password_hash(request.form.get("password"), session["user_id"]))
        return redirect("/")
    return render_template("changepass.html", year=year, title="Change Password")

@app.route("/event/<id>", methods=["GET", "POST"])
@login_required
def event(id):
    tickets = db.execute("SELECT * FROM tickets WHERE event_id = ?", id)
    if request.method == "POST":
        if not request.form.get("name") or not request.form.get("email"):
            return apology("Missing name and/or email", 403)
        if len(tickets) != 0:
            last_number = int(tickets[-1]["number"])
            number = last_number + 1
        else:
            number = 2022001
        hash = generate_ticket_hash()
        ticket_number = str(id) + "_" + str(number)
        code = ticket_number + " " + hash + " "
        generate_barcode(code)
        design = db.execute("SELECT design FROM events WHERE event_id = ?", id)[0]["design"]
        if str(design) == "1":
            generate_ticket(ticket_number, "designs/%s.png"%id)
        db.execute("INSERT INTO tickets (number, event_id, name, email, ticket_hash) VALUES (?, ?, ?, ?, ?)", number, id, request.form.get("name"), request.form.get("email"), hash)
        return redirect("/event/%s"%id)
    name = db.execute("SELECT name FROM events WHERE event_id = ?", id)[0]["name"]
    return render_template("event.html", year=year, title=name, name=name, tickets=tickets, id=id)

@app.route("/newevent", methods=["GET", "POST"])
@login_required
def newevent():
    if request.method == "POST":
        if not request.form.get("name") or not request.form.get("date"):
            return apology("Missing name and/or date", 403)
        if not request.form.get("design"):
            return apology("Please specify whether you intend to use a ticket design", 403)
        file = request.files["design_file"]
        print(file)
        print(file.filename)
        if request.form.get("design") == "1" and file.filename == "":
            return apology("No selected file", 403)
        if file and allowed_file(file.filename):
            db.execute("INSERT INTO events (name, date, user_id, design) VALUES (?, ?, ?, ?)", request.form.get("name"), request.form.get("date"), session["user_id"], 1)
            id = db.execute("SELECT event_id FROM events WHERE name = ?", request.form.get("name"))[0]["event_id"]
            id = str(id)
            extension = file.filename.rsplit(".", 1)[1].lower()
            filename = secure_filename("%s.%s"%(id, extension))
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            if extension == "pdf":
                pdf_to_png(filename)
                os.remove("designs/%s"%filename)
            elif extension == "jpg" or extension == "jpeg":
                jpg_to_png(filename, id)
                os.remove("designs/%s"%filename)
            return redirect("/")
        db.execute("INSERT INTO events (name, date, user_id, design) VALUES (?, ?, ?, ?)", request.form.get("name"), request.form.get("date"), session["user_id"], 0)
        return redirect("/")
    return render_template("newevent.html", year=year, title="New Event")

@app.route("/deletevent", methods=["GET", "POST"])
@login_required
def deleteEvent():
    if request.method == "POST":
        if not request.form.get("id"):
            return apology("Event missing", 403)
        for extension in ALLOWED_EXTENSIONS:
            if os.path.exists("designs/%s.%s"%(str(request.form.get("id")), extension)):
                os.remove("designs/%s.%s"%(str(request.form.get("id")), extension))
        db.execute("DELETE FROM tickets WHERE event_id = ?", request.form.get("id"))
        db.execute("DELETE FROM events WHERE event_id = ?", request.form.get("id"))
        return redirect("/")
    events = db.execute("SELECT * FROM events WHERE user_id = ?", session["user_id"])
    return render_template("deletevent.html", year=year, title="Delete Event", events=events)

@app.route("/deleteticket/<id>", methods=["GET", "POST"])
@login_required
def deleteTicket(id):
    print(id)
    if request.method == "POST":
        if not request.form.get("number"):
            return apology("Missing ticket", 403)
        db.execute("DELETE FROM tickets WHERE number = ? AND event_id = ?", request.form.get("number"), id)
        return redirect("/event/%s"%id)
    tickets = db.execute("SELECT * FROM tickets WHERE event_id = ?", id)
    return render_template("deleteticket.html", year=year, title="Delete Ticket", tickets=tickets, id=id)

@app.route("/sendticket", methods=["POST"])
def sendticket():
    if not request.form.get("id"):
        return apology("Oops! Something went wrong.", 503)
    ticket = db.execute("SELECT * FROM tickets WHERE ticket_id = ?", request.form.get("id"))
    email = ticket[0]["email"]
    number = ticket[0]["number"]
    event_id = ticket[0]["event_id"]
    design = db.execute("SELECT design FROM events WHERE event_id = ?", event_id)[0]["design"]
    if str(design) == "1":
        filepath = "D:/Jana's project/Jana_s_project/tickets/%s_%s.pdf"%(event_id, number)
    else:
        filepath = "D:/Jana's project/Jana_s_project/barcodes/%s_%s.png"%(event_id, number)
    send_ticket(filepath, email)
    return redirect("/event/%s"%event_id)

if __name__ == "__main__":
    ui.run()
