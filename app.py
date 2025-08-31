import os
import hashlib
import requests
import subprocess
from flask import Flask, render_template, request

# =============================
# Flask Setup
# =============================
app = Flask(__name__, template_folder=".")
  # 👈 look for HTML in root

# =============================
# John the Ripper Setup
# =============================
JOHN_HOME = os.environ.get("JOHN_HOME", r"C:\JohnTheRipper\run")
JOHN_BIN = os.path.join(JOHN_HOME, "john")
JOHN_CONF = os.path.join(JOHN_HOME, "john.conf")
JOHN_POT = "jtr-demo.pot"

# =============================
# HIBP Password Check
# =============================
def check_password(password: str):
    sha1pwd = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
    prefix, suffix = sha1pwd[:5], sha1pwd[5:]

    url = f"https://api.pwnedpasswords.com/range/{prefix}"
    res = requests.get(url)

    if res.status_code != 200:
        return "⚠️ Error: Could not check password."

    hashes = (line.split(":") for line in res.text.splitlines())
    for h, count in hashes:
        if h == suffix:
            return f"❌ This password has been found {count} times in breaches!"
    return "✅ Good news — this password was NOT found in known breaches."

# =============================
# XposedOrNot Email Breach Check
# =============================
def check_email(email: str):
    url = f"https://api.xposedornot.com/v1/breach-analytics?email={email}"
    res = requests.get(url)

    if res.status_code == 404:
        return f"✅ Good news — {email} was NOT found in any breaches."
    elif res.status_code == 200:
        # A 200 status code indicates the email was found in the database.
        # Regardless of the breach count in the JSON, we return a positive breach message.
        return f"❌ {email} was found in at least one known breach."
    else:
        return f"⚠️ Error: Could not check email (status {res.status_code})."


# =============================
# Routes
# =============================
@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    if request.method == "POST":
        password = request.form["password"]
        result = check_password(password)
    return render_template("index.html", result=result)

@app.route("/email-check", methods=["GET", "POST"])
def email_check():
    result = None
    if request.method == "POST":
        email = request.form["email"]
        result = check_email(email)
    return render_template("email_check.html", result=result)

@app.route("/jtr-demo")
def jtr_demo():
    try:
        # Reset pot file
        if os.path.exists(JOHN_POT):
            os.remove(JOHN_POT)

        # Run cracking attempt
        subprocess.run(
            [JOHN_BIN, f"--config={JOHN_CONF}", f"--pot={JOHN_POT}",
             "--format=raw-sha1", "--wordlist=wordlist.txt", "sample_hashes.txt"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Collect cracked results
        show = subprocess.run(
            [JOHN_BIN, f"--config={JOHN_CONF}", f"--pot={JOHN_POT}",
             "--show", "--format=raw-sha1", "sample_hashes.txt"],
            stdout=subprocess.PIPE,
            text=True
        )

        results = show.stdout.strip() or "No passwords cracked."

        with open("sample_hashes.txt", "r") as f:
            sample_hashes = f.read()

        return render_template("jtr_demo.html",
                               hashes=sample_hashes.splitlines(),
                               results=results.splitlines())

    except Exception as e:
        return f"⚠️ JtR error: {e}"

# =============================
# Run Flask App
# =============================
if __name__ == "__main__":
    app.run(debug=True)