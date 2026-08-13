
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import sqlite3, os
from pathlib import Path
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "site.db"

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-change-this-secret")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def current_user():
    uid = session.get("user_id")
    if not uid: return None
    con = get_db()
    user = con.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    con.close()
    return user

def money(cents):
    return f"R$ {cents/100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
app.jinja_env.filters["money"] = money

@app.route("/")
def home():
    con = get_db()
    products = con.execute("SELECT * FROM products WHERE active=1 ORDER BY id DESC").fetchall()
    con.close()
    return render_template("home.html", products=products, user=current_user())

@app.route("/produto/<slug>")
def product(slug):
    con = get_db()
    p = con.execute("SELECT * FROM products WHERE slug=? AND active=1", (slug,)).fetchone()
    con.close()
    if not p: return "Produto não encontrado", 404
    return render_template("product.html", product=p, user=current_user())

@app.route("/cadastro", methods=["GET","POST"])
def register():
    if request.method == "POST":
        con = get_db()
        try:
            cur = con.execute("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)",
                (request.form["name"].strip(), request.form["email"].strip().lower(),
                 generate_password_hash(request.form["password"]), "student"))
            con.commit()
            session["user_id"] = cur.lastrowid
            return redirect(url_for("library"))
        except sqlite3.IntegrityError:
            flash("Este e-mail já está cadastrado.")
        finally:
            con.close()
    return render_template("register.html", user=current_user())

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        con = get_db()
        user = con.execute("SELECT * FROM users WHERE email=?", (request.form["email"].strip().lower(),)).fetchone()
        con.close()
        if user and check_password_hash(user["password_hash"], request.form["password"]):
            session["user_id"] = user["id"]
            return redirect(url_for("admin" if user["role"]=="admin" else "library"))
        flash("E-mail ou senha inválidos.")
    return render_template("login.html", user=current_user())

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/biblioteca")
def library():
    u = current_user()
    if not u: return redirect(url_for("login"))
    con = get_db()
    products = con.execute("SELECT * FROM products WHERE active=1").fetchall()
    con.close()
    return render_template("library.html", products=products, user=u)

@app.route("/ler/<slug>")
def reader(slug):
    u = current_user()
    if not u: return redirect(url_for("login"))
    con = get_db()
    p = con.execute("SELECT * FROM products WHERE slug=?", (slug,)).fetchone()
    con.close()
    if not p: return "Produto não encontrado", 404
    return render_template("reader.html", product=p, user=u)

@app.route("/arquivo/<path:filename>")
def file(filename):
    return send_from_directory(BASE_DIR, filename)

def is_admin():
    u = current_user()
    return bool(u and u["role"]=="admin")

@app.route("/admin")
def admin():
    if not is_admin(): return redirect(url_for("login"))
    con = get_db()
    products = con.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    courses = con.execute("SELECT * FROM courses ORDER BY id DESC").fetchall()
    con.close()
    return render_template("admin.html", products=products, courses=courses, user=current_user())

@app.route("/admin/produto/novo", methods=["GET","POST"])
def admin_new_product():
    if not is_admin(): return redirect(url_for("login"))
    if request.method == "POST":
        cents = int(round(float(request.form["price"].replace(".","").replace(",","."))*100))
        con = get_db()
        con.execute("INSERT INTO products(title,slug,product_type,description,price_cents,active) VALUES(?,?,?,?,?,?)",
            (request.form["title"], request.form["slug"], "ebook", request.form.get("description",""), cents,
             1 if request.form.get("active") else 0))
        con.commit(); con.close()
        return redirect(url_for("admin"))
    return render_template("admin_product_form.html", product=None, user=current_user())

@app.route("/admin/produto/<int:pid>", methods=["GET","POST"])
def admin_edit_product(pid):
    if not is_admin(): return redirect(url_for("login"))
    con = get_db()
    p = con.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
    if request.method == "POST":
        cents = int(round(float(request.form["price"].replace(".","").replace(",","."))*100))
        con.execute("UPDATE products SET title=?,description=?,price_cents=?,active=? WHERE id=?",
            (request.form["title"], request.form.get("description",""), cents,
             1 if request.form.get("active") else 0, pid))
        con.commit(); con.close()
        return redirect(url_for("admin"))
    con.close()
    return render_template("admin_product_form.html", product=p, user=current_user())

if __name__ == "__main__":
    app.run(debug=True)
