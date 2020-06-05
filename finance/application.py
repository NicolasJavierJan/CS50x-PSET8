import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")

# TODO

@app.route("/")
@login_required
def index():
    userid = session["user_id"]
    rows = db.execute("SELECT symbol, name, shares, current, sum FROM total WHERE id = :userid", userid=userid)
    cash = db.execute("SELECT cash FROM users WHERE id = :userid", userid=userid)
    holdings = 0
    for row in rows:
        price = lookup(row['symbol'])
        price2 = price['price']
        shares = row['shares']
        total = price2 * shares
        symbol = row['symbol']
        holdings = round(holdings + total, 2)
        db.execute("UPDATE total SET current = :price, sum = :total WHERE id = :userid AND symbol = :symbol", price=price2, total=total, userid=userid, symbol=symbol)
    return render_template("index.html", rows=rows, cash=cash[0]['cash'], holdings=holdings)


# TODO

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "GET":
        return render_template("buy.html")
    else:
        if lookup(request.form.get("symbol")) == None:
            return apology("Field empty or Symbol does not exist")
        else:
            if int(request.form.get("shares")) < 1:
                return apology("Shares must be a positive number")
            else:
                userid = session["user_id"]
                quote = lookup(request.form.get("symbol"))
                symbol = quote['symbol']
                name = quote['name']
                price = quote['price']
                shares = int(request.form.get("shares"))
                money = db.execute("SELECT cash FROM users WHERE id = :userid", userid=userid)
                buy = int(money[0]['cash']) - (price * shares)
                holdings = (price * shares)
                if (price * shares) > int(money[0]['cash']):
                    return apology("Not enough money")
                else:
                    total = db.execute("SELECT symbol FROM total WHERE id =:userid AND symbol =:symbol", userid=userid, symbol=symbol)
                    db.execute("INSERT INTO purchases (id, symbol, name, price, shares, time) VALUES (:userid, :symbol, :name, :price, :shares, datetime('now'))", userid=userid, symbol=symbol, name=name, price=price, shares=shares)
                    db.execute("UPDATE users SET cash = :buy WHERE id = :userid", buy=buy, userid=userid)
                    if not total:
                        db.execute("INSERT INTO total (id, symbol, name, shares, current, sum) VALUES (:userid, :symbol, :name, :shares, :current, :holdings)", userid=userid, symbol=symbol, name=name, shares=shares, current=price, holdings=holdings)
                    else:
                        db.execute("UPDATE total SET shares = shares + :shares, current = :current, sum = sum + :holdings WHERE id = :userid AND symbol = :symbol AND name = :name", shares=shares, current=price, holdings=holdings, userid=userid, symbol=symbol, name=name)
                    return redirect("/")

# TODO

@app.route("/history")
@login_required
def history():
        userid = session["user_id"]
        rows = db.execute("SELECT * FROM purchases WHERE id = :userid", userid=userid)
        print(rows)
        return render_template("history.html", rows=rows)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

# TODO

@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "GET":
        return render_template("quote.html")
    else:
        quote = lookup(request.form.get("symbol"))
        return render_template("quoted.html", name=quote['name'], price=usd(quote['price']), symbol=quote['symbol'])

# TODO

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    else:
        username = str.lower(request.form.get("username"))
        username2 = db.execute("SELECT username FROM users WHERE username = :username", username=username)
        if len(username2) > 0:
            return apology("Username taken")
        elif not username:
            return apology("You must type a Username!")
        else:
            password = request.form.get("password")
            if not password:
                return apology("You must choose a password")
            else:
                confirmation = request.form.get("confirmation")
                if not confirmation:
                    return apology("You must confirm your password")
                else:
                    if confirmation != password:
                        return apology("Password and confirmation must be the same!")
                    else:
                        encryptedpassword = generate_password_hash(password)
                        db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)", username=username, hash=encryptedpassword)
                        return redirect("/")

# TODO

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "GET":
        userid = session["user_id"]
        rows = db.execute("SELECT symbol FROM total WHERE id = :userid", userid=userid)
        return render_template("sell.html", rows=rows)
    else:
        if request.form.get("symbol") == "Symbol":
            return apology("You must select a stock")
        else:
            if request.form.get("shares") == '':
                return apology("Insert a number of stocks")
            elif int(request.form.get("shares")) < 1:
                return apology("Insert a positive number")
            else:
                userid = session["user_id"]
                symbol = request.form.get("symbol")
                shares = db.execute("SELECT shares FROM total WHERE id = :userid AND symbol = :symbol" , userid=userid, symbol=symbol)
                if int(request.form.get("shares")) > shares[0]['shares']:
                    print(shares[0]['shares'])
                    return apology("You don't have enough stocks")
                else:
                    symbol = request.form.get("symbol")
                    quote = lookup(request.form.get("symbol"))
                    names = quote['name']
                    shares = int(request.form.get("shares"))
                    price = quote['price']
                    holdings = (price * shares)
                    db.execute("INSERT INTO purchases (id, symbol, name, shares, price, time) VALUES (:userid, :symbol, :name, :shares * -1, :price, datetime('now'))", userid=userid, symbol=symbol, name=names, shares=shares, price=price)
                    db.execute("UPDATE total SET shares = shares - :shares, current = :price, sum = sum - :holdings WHERE id = :userid AND symbol = :symbol", shares=shares, price=price, holdings=holdings, userid=userid, symbol=symbol)
                    db.execute("UPDATE users SET cash = cash + :holdings WHERE id = :userid", holdings=holdings, userid=userid)
                    delete = db.execute("SELECT shares FROM total WHERE id = :userid AND symbol = :symbol", userid=userid, symbol=symbol)
                    if delete[0]['shares'] == 0:
                        db.execute("DELETE FROM total WHERE id = :userid AND symbol = :symbol", userid=userid, symbol=symbol)
                    return redirect("/")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

# PERSONAL TOUCH (ADD CASH)

@app.route("/cash", methods=["GET", "POST"])
@login_required
def cash():
    if request.method == "GET":
        return render_template("cash.html")
    else:
        if request.form.get("cash") == '':
            return apology("You must enter a number")
        elif int(request.form.get("cash")) < 1:
            return apology("You must enter a positive number")
        else:
            userid = session["user_id"]
            money = db.execute("SELECT cash FROM users WHERE id = :userid", userid=userid)
            db.execute("UPDATE users SET cash = cash + :money WHERE id = :userid", money=int(request.form.get("cash")), userid=userid)
            db.execute("INSERT INTO purchases (id, symbol, name, shares, price, time) VALUES (:userid, :cash, :name, :shares, :money, datetime('now'))", userid=userid, cash="CASH", name='', shares='', money=int(request.form.get("cash")))
            return redirect("/")
