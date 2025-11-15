from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3, os

app = Flask(__name__)
app.secret_key = "paymaster_secret"

# данные админа
ADMIN_NAME = "admin"
ADMIN_PASSWORD = "123456"

DB_PATH = os.path.join(os.path.dirname(__file__), "paymaster.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Авторизация
@app.route("/")
def login_page():
    return render_template("Registred.html")

@app.route("/login", methods=["POST"])
def login():
    name = request.form["name"]
    password = request.form["password"]

    # проверка на админа
    if name == ADMIN_NAME and password == ADMIN_PASSWORD:
        session["role"] = "admin"
        return redirect(url_for("admin_home"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE Name=? AND Password=?", (name, password))
    user = cur.fetchone()
    conn.close()

    if user:
        session["role"] = "buh"
        session["user_id"] = user["id"]
        return redirect(url_for("buh_home"))
    else:
        return render_template("Registred.html", error="Неверный логин или пароль")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))

# Админ 
@app.route("/admin", methods=["GET", "POST"])
def admin_home():
    if request.method == "POST":
        selected_name = request.form["accountant"]
        session["selected_buh"] = selected_name
        return redirect(url_for("edit_employees"))

    conn = get_db()
    users = conn.execute("SELECT * FROM users").fetchall()
    conn.close()
    return render_template("Admin.html", users=users)

# Редактирование сотрудников
@app.route("/edit_employees", methods=["GET", "POST"])
def edit_employees():
    conn = get_db()

    if request.method == "POST":
        employees_data = request.form.getlist("employee_id")
        for emp_id in employees_data:
            fio = request.form.get(f"fio_{emp_id}")
            period = request.form.get(f"period_{emp_id}")
            hours = request.form.get(f"hours_{emp_id}")
            overtime = request.form.get(f"overtime_{emp_id}")
            rate = request.form.get(f"rate_{emp_id}")
            overtime_rate = request.form.get(f"overtime_rate_{emp_id}")
            bonus = request.form.get(f"bonus_{emp_id}")
            one_time = request.form.get(f"one_time_{emp_id}")
            total = request.form.get(f"total_{emp_id}")

            conn.execute("""
                UPDATE Payroll
                SET period=?, hoursWorked=?, overtimeHours=?, Rate=?, overtimeRate=?, 
                    bonus=?, oneTimePayment=?, totalEarnings=?
                WHERE Employee_id=?
            """, (period, hours, overtime, rate, overtime_rate, bonus, one_time, total, emp_id))

            conn.execute("""
                UPDATE Employee
                SET FIO=?
                WHERE id=?
            """, (fio, emp_id))

        conn.commit()
        conn.close()
        return redirect(url_for("edit_employees"))

    # показываем таблицу сотрудников выбранного бухгалтера
    selected_buh = session.get("selected_buh")
    employees = conn.execute("""
        SELECT e.id, e.FIO, p.period, p.hoursWorked, p.overtimeHours,
               p.Rate, p.overtimeRate, p.bonus, p.oneTimePayment, p.totalEarnings,
               pt.name as payment_type
        FROM Employee e
        LEFT JOIN Payroll p ON e.id = p.Employee_id
        LEFT JOIN PaymentType pt ON e.PaymentType_id = pt.id
        JOIN users u ON e.Users_id = u.id
        WHERE u.Name = ?
    """, (selected_buh,)).fetchall()
    conn.close()

    return render_template("Redact.html", employees=employees)


@app.route("/add_employee", methods=["GET", "POST"])
def add_employee():
    message = None
    if request.method == "POST":
        fio = request.form["fio"]
        payment_type = int(request.form["payment_type"])
 
        users_id = request.form.get("users_id") or session.get("selected_buh_id")

        if not users_id:
            message = "Ошибка: не выбран бухгалтер."
        else:
            conn = get_db()
            conn.execute(
                "INSERT INTO Employee (FIO, PaymentType_id, Users_id) VALUES (?, ?, ?)",
                (fio, payment_type, users_id)
            )
            conn.commit()
            conn.close()
            message = f"Сотрудник {fio} успешно добавлен."

    return render_template("AddEmployee.html", message=message, selected_buh_id=session.get("selected_buh_id"))


# Удаление сотрудника
@app.route("/delete_employee", methods=["GET", "POST"])
def delete_employee():
    conn = get_db()

    if request.method == "POST":
        emp_id = request.form["employee_id"]
        conn.execute("DELETE FROM Employee WHERE id=?", (emp_id,))
        conn.commit()
        conn.close()
        return redirect(url_for("delete_employee")) 

    selected_buh = session.get("selected_buh")
    employees = conn.execute("""
        SELECT e.id, e.FIO
        FROM Employee e
        JOIN users u ON e.Users_id = u.id
        WHERE u.Name = ?
    """, (selected_buh,)).fetchall()
    conn.close()

    return render_template("Delete.html", employees=employees)

    
@app.route("/buh_home")
def buh_home():
    buh_id = session.get("user_id")
    if not buh_id:
        return redirect(url_for("login_page"))

    conn = get_db()
    employees = conn.execute("""
        SELECT e.id, e.FIO, pt.name as payment_type
        FROM Employee e
        JOIN PaymentType pt ON e.PaymentType_id = pt.id
        WHERE e.Users_id = ?
    """, (buh_id,)).fetchall()
    conn.close()

    return render_template("BuhCalculate.html", employees=employees)

#Рассчет ЗП
@app.route("/calc_salary", methods=["POST"])
def calc_salary():
    buh_id = session.get("user_id")
    if not buh_id:
        return redirect(url_for("login_page"))

    emp_id = int(request.form["employee_id"])
    period = request.form["period"]
    hours = int(request.form.get("hours", 0))
    overtime = int(request.form.get("overtime", 0))
    rate = int(request.form.get("rate", 0))
    overtime_rate = int(request.form.get("overtime_rate", 0))
    premium = int(request.form.get("premium", 0))
    bonus = int(request.form.get("bonus", 0))

    gross = hours * rate + overtime * overtime_rate + premium + bonus
    tax = int(gross * 0.12)
    total = gross - tax

    conn = get_db()
    conn.execute("""
        INSERT INTO Payroll (period, hoursWorked, overtimeHours, Rate, overtimeRate,
                             bonus, oneTimePayment, taxAmount, totalEarnings, Employee_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (period, hours, overtime, rate, overtime_rate,
          bonus, premium, tax, total, emp_id))
    conn.commit()
    conn.close()

    message = f"Зарплата для сотрудника успешно рассчитана: {total} ₽ (налог {tax} ₽)"

    return redirect(url_for("buh_home"))

#Детали по ЗП
@app.route("/salary_details")
def salary_details():
    buh_id = session.get("user_id")
    if not buh_id:
        return redirect(url_for("login_page"))

    conn = get_db()
    payrolls = conn.execute("""
        SELECT e.FIO, p.period, p.hoursWorked, p.overtimeHours,
               p.Rate, p.overtimeRate, p.bonus, p.oneTimePayment,
               p.taxAmount, p.totalEarnings
        FROM Payroll p
        JOIN Employee e ON p.Employee_id = e.id
        WHERE e.Users_id = ?
        ORDER BY p.period DESC, e.FIO
    """, (buh_id,)).fetchall()
    conn.close()

    return render_template("Details.html", payrolls=payrolls)


@app.route("/salary_threshold", methods=["GET","POST"])
def salary_threshold():
    buh_id = session.get("user_id")
    if not buh_id:
        return redirect(url_for("login_page"))

    employees = []
    if request.method == "POST":
        try:
            threshold = float(request.form["salary"])
        except (KeyError, ValueError):
            threshold = None

        if threshold is not None:
            conn = get_db()
            employees = conn.execute("""
                SELECT e.FIO, p.totalEarnings, p.period
                FROM Payroll p
                JOIN Employee e ON p.Employee_id = e.id
                WHERE e.Users_id = ? AND p.totalEarnings < ?
                ORDER BY p.totalEarnings ASC
            """, (buh_id, threshold)).fetchall()
            conn.close()

    return render_template("PorogSalary.html", employees=employees)



# Добавление бухгалтера
@app.route("/new_buh", methods=["GET", "POST"])
def new_buh():
    message = None
    if request.method == "POST":
        fio = request.form["fio"]
        password = request.form["password"]

        conn = get_db()
        conn.execute("INSERT INTO users(Name, Password) VALUES (?, ?)", (fio, password))
        conn.commit()
        conn.close()

        message = f"Бухгалтер {fio} успешно добавлен."

    return render_template("NewBuh.html", message=message)



if __name__ == "__main__":
    app.run(debug=True)
