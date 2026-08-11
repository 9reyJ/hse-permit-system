import os

from auth import login_required, role_required
from flask import Flask, flash, abort, url_for, redirect, render_template, request, session
from flask_session import Session as FlaskSession
from database import engine
from models import Employee, Permit, PermitAction
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload
from dotenv import load_dotenv
load_dotenv()

# Configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
FlaskSession(app)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")

""" Without these headers, hitting back could show a cached "approve permit" 
page with sensitive workflow data still visible, even after logout. 
For a compliance/safety-adjacent tool where you'll likely want to say "only authorized approvers 
ever saw this data," that's a real property you want, not just tidiness.
"""
@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = "0"
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        phone_number = request.form["phone_number"]
        email = request.form["email"]
        password = request.form["password"]
        password_confirmation = request.form["password_confirmation"]


        if not username or not first_name or not last_name or not phone_number or not email or not password or not password_confirmation:
            flash("Missing required fields!")
            return render_template("register.html")

        if password != password_confirmation:
            flash("Passwords don't match!")
            return render_template("register.html")

        try:
            with Session(engine) as session:
                new_user = Employee(
                    username=username,
                    hash=generate_password_hash(password),
                    first_name=first_name,
                    last_name=last_name,
                    phone_number=phone_number,
                    email=email,
                    role="requester",
                )

                session.add(new_user)
                session.commit()
                flash("Registered successfully!")
                return redirect(url_for("login"))

        except IntegrityError:
            flash("That username, email, or phone is already registered.")
            return render_template("register.html")
    else:
        return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if not username or not password:
            flash("Missing username/password!")
            return render_template("login.html")

        with Session(engine) as db_session:
            user = db_session.query(Employee).filter_by(username=username).first()
            
        if user is not None and check_password_hash(user.hash, password):
            session["user_id"] = user.id
            session["role"] = user.role
            flash("Login Successful!")
            return redirect(url_for("index"))
        else:
            flash("Invalid username and/or password!")
            return render_template("login.html")
            
    session.clear()
    return render_template("login.html")

@app.route("/")
@role_required("requester", "ehs")
@login_required
def index():
    if session["role"] == "requester":
        with Session(engine) as db_session:
            permits = (
                db_session.query(Permit)
                .options(joinedload(Permit.requester), selectinload(Permit.actions))
                .filter_by(requester_id=session["user_id"])
                .all()
            )
        return render_template("index.html", permits=permits)

    if session["role"] == "ehs":
        with Session(engine) as db_session:
            permits = (
                db_session.query(Permit)
                .options(joinedload(Permit.requester), selectinload(Permit.actions))
                .all()
            )
        return render_template("index.html", permits=permits)

    return render_template("index.html")

@app.route("admin/users/<int:employee_id>")
@role_required("admin")
@login_required
def admin_users(employee_id):
    return redirect(url_for("index"))

@app.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("login"))