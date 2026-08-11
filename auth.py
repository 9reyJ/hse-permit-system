# auth.py
from functools import wraps
from flask import session, redirect

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return wrapper

def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if session.get("role") not in allowed_roles:
                return redirect("/")  # or abort(403)
            return f(*args, **kwargs)
        return wrapper
    return decorator