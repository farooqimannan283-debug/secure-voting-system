from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3
import os
import time

app = Flask(
    __name__,
    template_folder="public",
    static_folder="public/static"
)

app.secret_key = "secret123"

UPLOAD_FOLDER = "public/static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =========================================
# DATABASE
# =========================================

def init_db():

    conn = sqlite3.connect("database.db", timeout=10)
    c = conn.cursor()

    # Elections
    c.execute("""
    CREATE TABLE IF NOT EXISTS elections(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        mode TEXT,
        status TEXT
    )
    """)

    # Candidates
    c.execute("""
    CREATE TABLE IF NOT EXISTS candidates(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        election_id INTEGER,
        name TEXT,
        image TEXT
    )
    """)

    # Votes
    c.execute("""
    CREATE TABLE IF NOT EXISTS votes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        election_id INTEGER,
        candidate TEXT,
        phone TEXT
    )
    """)

    # Prevent duplicate online voting
    c.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS unique_vote
    ON votes(election_id, phone)
    """)

    conn.commit()
    conn.close()

init_db()

# =========================================
# HOME
# =========================================

@app.route("/")
def home():

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # ONLINE ELECTION
    c.execute("""
    SELECT *
    FROM elections
    WHERE mode='online'
    AND status='live'
    LIMIT 1
    """)

    online = c.fetchone()

    # EVM ELECTION
    c.execute("""
    SELECT *
    FROM elections
    WHERE mode='evm'
    AND status='live'
    LIMIT 1
    """)

    evm = c.fetchone()

    conn.close()

    return render_template(
        "landing.html",
        online_live=True if online else False,
        evm_live=True if evm else False
    )

# =========================================
# ADMIN LOGIN
# =========================================

@app.route("/admin", methods=["GET", "POST"])
def admin():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "admin123":

            session["admin"] = True

            return redirect("/admin/dashboard")

    return render_template("admin.html")

# =========================================
# ADMIN DASHBOARD
# =========================================

@app.route("/admin/dashboard")
def dashboard():

    if "admin" not in session:
        return redirect("/admin")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
    SELECT *
    FROM elections
    WHERE status='live'
    LIMIT 1
    """)

    election = c.fetchone()

    candidates = []
    chart_labels = []
    chart_votes = []
    total_votes = 0
    leader = None

    if election:

        eid = election[0]

        c.execute("""

        SELECT c.name,
               c.image,
               COUNT(v.id)

        FROM candidates c

        LEFT JOIN votes v
        ON c.name = v.candidate
        AND c.election_id = v.election_id

        WHERE c.election_id=?

        GROUP BY c.name

        ORDER BY COUNT(v.id) DESC

        """, (eid,))

        rows = c.fetchall()

        for r in rows:
            total_votes += r[2]

        for r in rows:

            percent = 0

            if total_votes > 0:
                percent = round((r[2] / total_votes) * 100, 2)

            data = {
                "name": r[0],
                "image": r[1],
                "votes": r[2],
                "percent": percent
            }

            candidates.append(data)

            chart_labels.append(r[0])
            chart_votes.append(r[2])

        if candidates:
            leader = candidates[0]

    conn.close()

    election_status = "closed"

    if election:
        election_status = "live"

    return render_template(
        "admin_dashboard.html",
        election=election,
        candidates=candidates,
        total_votes=total_votes,
        leader=leader,
        chart_labels=chart_labels,
        chart_votes=chart_votes,
        election_status=election_status
    )

# =========================================
# CREATE NEW ELECTION
# =========================================

@app.route("/admin/new", methods=["GET", "POST"])
def new_election():

    if "admin" not in session:
        return redirect("/admin")

    if request.method == "POST":

        name = request.form["name"]
        mode = request.form["mode"]

        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        # CLOSE OLD ELECTIONS
        c.execute("""
        UPDATE elections
        SET status='closed'
        """)

        # CREATE NEW ELECTION
        c.execute("""
        INSERT INTO elections
        VALUES(NULL,?,?,?)
        """, (name, mode, "live"))

        eid = c.lastrowid

        names = request.form.getlist("candidate_name")
        files = request.files.getlist("candidate_image")

        for i, n in enumerate(names):

            filename = ""

            if i < len(files) and files[i].filename:

                filename = files[i].filename

                files[i].save(
                    os.path.join(UPLOAD_FOLDER, filename)
                )

            c.execute("""
            INSERT INTO candidates
            VALUES(NULL,?,?,?)
            """, (eid, n, filename))

        conn.commit()
        conn.close()

        return redirect("/admin/dashboard")

    return render_template("new_election.html")

# =========================================
# CLOSE ELECTION
# =========================================

@app.route("/admin/close")
def close_election():

    if "admin" not in session:
        return redirect("/admin")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
    UPDATE elections
    SET status='closed'
    WHERE status='live'
    """)

    conn.commit()
    conn.close()

    return redirect("/admin/dashboard")

# =========================================
# HISTORY
# =========================================

@app.route("/admin/history")
def history():

    if "admin" not in session:
        return redirect("/admin")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""

    SELECT
    id,
    name,
    mode,
    status

    FROM elections

    WHERE status='closed'

    ORDER BY id DESC

    """)

    elections = c.fetchall()

    conn.close()

    return render_template(
        "history.html",
        elections=elections
    )


# =========================================
# REGISTER PAGE
# =========================================

@app.route("/register", methods=["GET", "POST"])
def register():

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # GET LIVE ONLINE ELECTION
    c.execute("""
    SELECT *
    FROM elections
    WHERE mode='online'
    AND status='live'
    LIMIT 1
    """)

    election = c.fetchone()

    # NO LIVE ELECTION
    if not election:

        conn.close()

        return render_template(
            "index.html",
            election_live=False
        )

    eid = election[0]

    # FORM SUBMIT
    if request.method == "POST":

        fullname = request.form["fullname"]
        phone = request.form["phone"]
        dob = request.form["dob"]

        # CHECK DUPLICATE
        c.execute("""
        SELECT *
        FROM votes
        WHERE election_id=?
        AND phone=?
        """, (eid, phone))

        existing_vote = c.fetchone()

        # ALREADY VOTED
        if existing_vote:

            conn.close()

            return render_template(
                "index.html",
                election_live=True,
                error="This phone number has already voted."
            )

        # SAVE SESSION
        session["fullname"] = fullname
        session["phone"] = phone
        session["dob"] = dob

        conn.close()

        return redirect("/vote")

    conn.close()

    return render_template(
        "index.html",
        election_live=True
    )

# =========================================
# ONLINE VOTE
# =========================================

@app.route("/vote", methods=["GET", "POST"])
def vote():

    # MUST REGISTER FIRST
    if "phone" not in session:
        return redirect("/register")

    phone = session["phone"]

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # GET LIVE ONLINE ELECTION
    c.execute("""
    SELECT *
    FROM elections
    WHERE mode='online'
    AND status='live'
    LIMIT 1
    """)

    election = c.fetchone()

    if not election:

        conn.close()

        return redirect("/register")

    eid = election[0]

    # GET CANDIDATES
    c.execute("""
    SELECT name,image
    FROM candidates
    WHERE election_id=?
    """, (eid,))

    candidates = c.fetchall()

    error = None

    # VOTE SUBMIT
    if request.method == "POST":

        candidate = request.form["candidate"]

        try:

            c.execute("""
            INSERT INTO votes
            VALUES(NULL,?,?,?)
            """, (eid, candidate, phone))

            conn.commit()

            session.clear()

            conn.close()

            return redirect("/success")

        except Exception:

            conn.rollback()

            error = "You have already voted in this election."

    conn.close()

    return render_template(
        "vote.html",
        candidates=candidates,
        error=error
    )

# =========================================
# SUCCESS
# =========================================

@app.route("/success")
def success():
    return render_template("success.html")

# =========================================
# EVM
# =========================================

@app.route("/evm", methods=["GET", "POST"])
def evm():

    conn = sqlite3.connect("database.db", timeout=10)
    c = conn.cursor()

    c.execute("""
    SELECT *
    FROM elections
    WHERE mode='evm'
    AND status='live'
    LIMIT 1
    """)

    election = c.fetchone()

    if not election:

        conn.close()

        return render_template(
            "evm.html",
            election_live=False,
            candidates=[]
        )

    eid = election[0]

    c.execute("""
    SELECT name,image
    FROM candidates
    WHERE election_id=?
    """, (eid,))

    candidates = c.fetchall()

    # SUBMIT EVM VOTE
    if request.method == "POST":

        candidate = request.form["candidate"]

        try:

            unique_voter = "evm_" + str(time.time())

            c.execute("""
            INSERT INTO votes
            VALUES(NULL,?,?,?)
            """, (eid, candidate, unique_voter))

            conn.commit()

        except Exception as e:

            conn.rollback()
            conn.close()

            return str(e)

        conn.close()

        return redirect("/evm_success")

    conn.close()

    return render_template(
        "evm.html",
        election_live=True,
        candidates=candidates
    )

# =========================================
# EVM SUCCESS
# =========================================

@app.route("/evm_success")
def evm_success():
    return render_template("evm_success.html")

# =========================================
# RUN
# =========================================

if __name__ == "__main__":
    app.run(debug=True)