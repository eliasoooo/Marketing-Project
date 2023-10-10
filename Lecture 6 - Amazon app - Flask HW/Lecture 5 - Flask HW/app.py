from flask import (
    Flask,
    render_template,
    request,
    flash,
    redirect,
    url_for,
    make_response,
    session,
)
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
import sqlite3
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField
from wtforms.validators import DataRequired
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
from flask_login import current_user
from flask_caching import Cache
import time

app = Flask(__name__)
app.secret_key = "123"

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Initialize Flask-Caching
cache = Cache(app, config={"CACHE_TYPE": "simple"})  # Adjust configuration as needed

# MongoDB connection
url = "mongodb+srv://eliasghanem:123@cluster0.0nlzsxs.mongodb.net/?retryWrites=true&w=majority&appName=AtlasApp"
client = MongoClient(url, tls=True, tlsAllowInvalidCertificates=True)
db = client["shopping_database"]
product_collection = db["products"]
order_collection = db["orders"]


# SQLite setup
def setup_sqlite():
    with sqlite3.connect("database.db") as con:
        con.execute(
            "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, password TEXT, email TEXT)"
        )


# User model
class User(UserMixin):
    def __init__(self, id):
        self.id = id


# Load user from SQLite
@login_manager.user_loader
def load_user(user_id):
    return User(user_id)


# Registration form
class RegistrationForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = StringField("Password", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired()])


# Login form
class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = StringField("Password", validators=[DataRequired()])


# Cart form
class CartForm(FlaskForm):
    quantity = IntegerField("Quantity", validators=[DataRequired()])


# Checkout form
class CheckoutForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    address = StringField("Address", validators=[DataRequired()])
    payment_info = StringField("Payment Information", validators=[DataRequired()])
    submit_order = SubmitField("Submit Order")


# Example products
example_products = [
    {
        "name": "HTC Vive Focus 3 Eye Tracker",
        "description": "We've been able to leverage VIVE Focus 3's facial and eye-tracking technology for an unprecedented portable and expressive experience for live actors.",
        "price": "249$",
        "image_url": "static/HTC Vive Focus 3 Eye Tracker.png",
    },
    {
        "name": "Tobbi Pro Glasses",
        "description": "Tobii Pro Glasses 3 are versatile. They gather first-hand attention data without skipping a beat in a vehicle or classroom.",
        "price": "10,000$",
        "image_url": "static/Tobii-Pro-Glasses3-winning-award-logos.png",
    },
    {
        "name": "Tobii-Pro-Spectrum-with-gaze",
        "description": "For exhaustive research into human behavior and the mechanics of quick eye movements, Tobii Pro Spectrum is our most sophisticated eye-tracking tool./n Data is captured at several sampling rates up to 1200 Hz while permitting head movement.",
        "price": "600$",
        "image_url": "static/Tobii-Pro-Spectrum-with-gaze.png",
    },
    {
        "name": "Tobii Pro Nano",
        "description": "Tobii Pro Nano is a portable research solution for tiny displays. For real study data collecting, use a Windows or Mac laptop with your stimulus./n Bring your portable lab to participants.",
        "price": "349$",
        "image_url": "static/TobiiPro-Nano-front-view.png",
    },
]

for product in example_products:
    existing_product = product_collection.find_one({"name": product["name"]})
    if existing_product is None:
        product_collection.insert_one(product)
    else:
        product_collection.update_one(
            {"_id": existing_product["_id"]},
            {
                "$set": {
                    "description": product["description"],
                    "price": product["price"],
                }
            },
        )


@app.before_request
def log_request_info():
    app.logger.info(
        f"Request from {request.remote_addr} - {request.method} {request.url}"
    )
    request._start_time = time.time()


@app.after_request
def log_response_info(response):
    response_time = time.time() - request._start_time
    app.logger.info(f"Response time: {response_time:.6f} seconds")
    return response


@app.errorhandler(Exception)
def log_exception(error):
    app.logger.error(f"Error: {error}")
    return render_template("error.html"), 500


# Welcome page
@app.route("/")
def welcome():
    return render_template("welcome.html")


# Home page
@cache.cached(timeout=600)
@app.route("/home")
def home():
    products = product_collection.find()
    form = CartForm()
    return render_template("home.html", products=products, form=form)


@app.route("/add_to_cart/<product_id>", methods=["POST"])
def add_to_cart(product_id):
    form = CartForm(request.form)
    if request.method == "POST" and form.validate_on_submit():
        quantity = form.quantity.data
        product = product_collection.find_one({"_id": ObjectId(product_id)})

        if "cart" not in session:
            session["cart"] = []

        session["cart"].append(
            {
                "product_id": str(product["_id"]),
                "name": product["name"],
                "price": product["price"],
                "quantity": quantity,
            }
        )
        flash("Product added to cart successfully!", "success")

    return redirect(url_for("home"))


@app.route("/remove_from_cart/<product_id>")
def remove_from_cart(product_id):
    if "cart" in session:
        for item in session["cart"]:
            if item["product_id"] == product_id:
                session["cart"].remove(item)
                flash("Product removed from cart!", "info")
                break
    return redirect(url_for("cart"))


# View cart
@app.route("/cart")
def cart():
    cart_items = session.get("cart", [])
    total_cost = sum(item["price"] * item["quantity"] for item in cart_items)
    return render_template("cart.html", cart_items=cart_items, total_cost=total_cost)


# Checkout
@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    form = CheckoutForm(request.form)
    if request.method == "POST" and form.validate_on_submit():
        name = form.name.data
        address = form.address.data
        payment_info = form.payment_info.data
        cart_items = session.get("cart", [])
        total_cost = sum(item["price"] * item["quantity"] for item in cart_items)

        order = {
            "name": name,
            "address": address,
            "payment_info": payment_info,
            "items": cart_items,
            "total_cost": total_cost,
            "order_time": datetime.now(),
        }
        order_collection.insert_one(order)

        session.pop("cart", None)

        flash("Order placed successfully!", "success")
        return redirect(url_for("home"))

    return render_template("checkout.html", form=form)


@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegistrationForm()
    if request.method == "POST" and form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        email = form.email.data

        with sqlite3.connect("database.db") as con:
            cur = con.cursor()
            try:
                cur.execute(
                    "INSERT INTO users (username, password, email) VALUES (?, ?, ?)",
                    (username, password, email),
                )
                con.commit()
                flash("User created successfully. Please login.", "success")
                return redirect(url_for("login"))
            except sqlite3.Error as e:
                flash(f"Error in user creation: {str(e)}", "danger")

    response = make_response(render_template("register.html", form=form))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response


# Login page
@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if request.method == "POST" and form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        with sqlite3.connect("database.db") as con:
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            cur.execute("SELECT * FROM users WHERE username=?", (username,))
            user = cur.fetchone()

        if user:
            if user["password"] == password:
                user_obj = User(user["id"])
                login_user(user_obj)
                session["user_id"] = user["id"]
                flash("Login successful!", "success")
                return redirect(url_for("home"))
            else:
                flash("Incorrect password. Please try again.", "danger")
        else:
            flash("Username not found. Please try again.", "danger")

    response = make_response(render_template("login.html", form=form))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response


# Logout
@app.route("/logout")
@login_required
def logout():
    logout_user()
    session.pop("user_id", None)
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))


if __name__ == "__main__":
    setup_sqlite()
    app.run(debug=True)
