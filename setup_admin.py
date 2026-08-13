
from app import app, get_db
from werkzeug.security import generate_password_hash
with app.app_context():
    con = get_db()
    email = "admin@daniel.local"
    if not con.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
        con.execute("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)",
                    ("Administrador", email, generate_password_hash("trocar123"), "admin"))
        con.commit()
    con.close()
print("Admin criado: admin@daniel.local / trocar123")
