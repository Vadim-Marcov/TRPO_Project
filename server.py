from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3, os

app = Flask(__name__)
app.secret_key = "paymaster_secret"

DB_PATH = os.path.join(os.path.dirname(__file__), "paymaster.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ---------------- Авторизация ----------------
@app.route("/")
def login_page():
    return render_template("Registred.html")

@app.route("/login", methods=["POST"])
def login():    
    name = request.form["name"]
    password = request.form["password"]

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE Name=? AND Password=?", (name, password))
    user = cur.fetchone()
    conn.close()

    if user:
        # если админ
        if user["Name"] == "admin":
            session["role"] = "admin"
            return redirect(url_for("admin_home"))
        else:
            session["role"] = "buh"
            session["user_id"] = user["id"]
            return redirect(url_for("buh_home"))
    else:
        return render_template("Registred.html", error="Неверный логин или пароль")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))

# ---------------- Админ ----------------
@app.route("/admin")
def admin_home():
    return render_template("Admin.html")

@app.route("/edit_employees")
def edit_employees():
    conn = get_db()
    employees = conn.execute("""
        SELECT e.id, e.FIO, pt.name as payment_type
        FROM Employee e
        LEFT JOIN PaymentType pt ON e.PaymentType_id = pt.id
    """).fetchall()
    conn.close()
    return render_template("Redact.html", employees=employees)

@app.route("/add_employee", methods=["GET","POST"])
def add_employee():
    if request.method == "POST":
        fio = request.form["fio"]
        payment_type_id = request.form["payment_type_id"]
        conn = get_db()
        conn.execute("INSERT INTO Employee(FIO, PaymentType_id) VALUES (?,?)", (fio, payment_type_id))
        conn.commit()
        conn.close()
        return redirect(url_for("edit_employees"))
    conn = get_db()
    payment_types = conn.execute("SELECT * FROM PaymentType").fetchall()
    conn.close()
    return render_template("AddEmployee.html", payment_types=payment_types)

@app.route("/delete_employee", methods=["POST"])
def delete_employee():
    emp_id = request.form["employee_id"]
    conn = get_db()
    conn.execute("DELETE FROM Employee WHERE id=?", (emp_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("edit_employees"))

# ---------------- Бухгалтер ----------------
@app.route("/buh_home")
def buh_home():
    conn = get_db()
    employees = conn.execute("SELECT * FROM Employee").fetchall()
    conn.close()
    return render_template("BuhCalculate.html", employees=employees)

@app.route("/salary_details")
def salary_details():
    conn = get_db()
    payrolls = conn.execute("""
        SELECT e.FIO, p.period, p.hoursWorked, p.overtimeHours, p.Rate, p.overtimeRate,
               p.bonus, p.oneTimePayment, p.taxAmount, p.totalEarnings
        FROM Payroll p
        JOIN Employee e ON p.Employee_id = e.id
    """).fetchall()
    conn.close()
    return render_template("Details.html", payrolls=payrolls)

@app.route("/salary_threshold", methods=["GET","POST"])
def salary_threshold():
    employees = []
    if request.method == "POST":
        threshold = float(request.form["salary"])
        conn = get_db()
        employees = conn.execute("""
            SELECT e.FIO, p.totalEarnings
            FROM Payroll p
            JOIN Employee e ON p.Employee_id = e.id
            WHERE p.totalEarnings >= ?
        """, (threshold,)).fetchall()
        conn.close()
    return render_template("PorogSalary.html", employees=employees)

if __name__ == "__main__":
    app.run(debug=True)
