import os
import datetime as dt

from auth import login_required, role_required
from flask import Flask, flash, abort, url_for, redirect, render_template, request, session
from flask_session import Session as FlaskSession
from database import engine
from models import Employee, Permit, PermitAction
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import select, desc
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

@app.route("/", methods=["GET", "POST"])
@login_required
@role_required("requester", "ehs", "admin")
def index():
    if session["role"] == "requester":
        with Session(engine) as db_session:
            permits = (
                db_session.query(Permit)
                .options(joinedload(Permit.requester), selectinload(Permit.actions))
                .filter_by(requester_id=session["user_id"])
                .order_by(Permit.created_at.desc())
                .all()
            )
        return render_template("index.html", permits=permits)

    if session["role"] == "ehs":
        with Session(engine) as db_session:
            permits = (
                db_session.query(Permit)
                .options(joinedload(Permit.requester), selectinload(Permit.actions))
                .order_by(Permit.created_at.desc())
                .all()
            )
        return render_template("index.html", permits=permits)

    if session["role"] == "admin":
        return redirect(url_for('admin_users'))

    return render_template("index.html")


@app.route("/permits/<int:id>/action", methods=["POST", "GET"])
@role_required("ehs", "requester")
@login_required
def permit_action(id):

    if session["role"] == "ehs":
        action = request.form["action"]
        if not action:
            flash("Error! Could not understand request!")
            return redirect("/")

        comment = request.form.get("comment")
        
        with Session(engine) as db_session:
            permit = db_session.query(Permit).filter_by(id=id).first()
            if permit is None:
                flash("Permit not found")
                return redirect(url_for("index"))
            if action == "approve":
                permit.status = "approved"
                permit_action = PermitAction (
                    permit_id = id,
                    actor_id = session["user_id"],
                    action = "approved",
                    comment = comment
                )

                flash("Permit Approved!")
                db_session.add(permit_action)
                db_session.commit()
                return redirect(url_for("index"))

            if action == "reject":
                permit.status = "rejected"
                permit_action = PermitAction (
                    permit_id = id,
                    actor_id = session["user_id"],
                    action = "rejected",
                    comment = comment
                )
                flash("Permit Rejected!")
                db_session.add(permit_action)
                db_session.commit()
                return redirect(url_for("index"))
    close = request.form["close"]
    if not close:
        flash("Error! Could not understand request!")
        return redirect("/")
    if session["role"] == "requester":
        with Session(engine) as db_session:
            permit = db_session.query(Permit).filter_by(id=id).first()
            if permit is None:
                flash("Permit not found")
                return redirect(url_for("index"))
            permit.status = "closed"
            permit_action = PermitAction (
                permit_id = id,
                actor_id = session["user_id"],
                action = "closed",
            )
            flash("Permit Closed!")
            db_session.add(permit_action)
            db_session.commit()
            return redirect(url_for("index"))
    return redirect(url_for("index"))


@app.route("/create_permit", methods=["GET", "POST"])
@role_required("requester")
@login_required
def create_permit():

    if request.method == "POST":
        p_type = request.form["type"]
        location = request.form["location"]
        valid_from = request.form["valid_from"]
        valid_until = request.form["valid_until"]
        description = request.form["description"]

        if not p_type or not location or not valid_from or not valid_until or not description:
            flash("Missing one or many required fields!")
            return redirect(url_for("create_permit"))

        with Session(engine) as db_session:
            permit = Permit(
                requester_id = session["user_id"],
                type = p_type,
                location = location,
                valid_from = dt.datetime.fromisoformat(valid_from),
                valid_until = dt.datetime.fromisoformat(valid_until),
                status = "submitted",
                description = description
            )
            db_session.add(permit)
            db_session.commit()

            permit_action = PermitAction(
                permit_id = permit.id,
                actor_id = session["user_id"],
                action = "submitted",
                comment = "Initial Submission"
            )
            db_session.add(permit_action)
            db_session.commit()

            flash("Permit Created Successfully!")
            return redirect(url_for("create_permit"))

    return render_template("create_permit.html")

@app.route("/admin/users")
@role_required("admin")
@login_required
def admin_users():
    with Session(engine) as db_session:
        employees = db_session.query(Employee).all()
    return render_template("admin_users.html", employees=employees)

@app.route("/admin/users/<int:employee_id>/role", methods=["POST"])
@role_required("admin")
@login_required
def update_role(employee_id):
    new_role = request.form["role"]

    if new_role not in ("requester", "ehs", "admin"):
        flash("Invalid role")
        return redirect(url_for("admin_users"))

    with Session(engine) as db_session:
        employee = db_session.query(Employee).filter_by(id=employee_id).first()
        if employee is None:
            flash("Employee not found")
            return redirect(url_for("admin_users"))

        employee.role = new_role
        flash(f"Updated {employee.username}'s role to {new_role}")
        db_session.commit()

    return redirect(url_for("admin_users"))

@app.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("login"))