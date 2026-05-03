from flask import Flask, render_template, request, redirect, session, send_file
from datetime import datetime
import pandas as pd
import os

# IBM Cloudant
from ibmcloudant.cloudant_v1 import CloudantV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

app = Flask(__name__)
app.secret_key = "secret123"

# ================= CLOUDANT =================
CLOUDANT_API_KEY = "TPV9dtT1mtumtrKs8hOM1H9RwPudvW6BmM3RBYHz5t4c"
CLOUDANT_URL = "https://apikey-v2-1qhw2ui0huvo472ubgqr79z2i18w4ppru1atzfrzwjje:4382de4e176fb28b3cc64c9692e798b5@e87c672b-b47f-4644-a61b-da4be44ff14f-bluemix.cloudantnosqldb.appdomain.cloud"

auth = IAMAuthenticator(CLOUDANT_API_KEY)
client = CloudantV1(authenticator=auth)
client.set_service_url(CLOUDANT_URL)

DB_NAME = "attendance"

def init_db():
    try:
        client.get_database_information(db=DB_NAME).get_result()
        print("✅ Cloudant Connected")
    except:
        client.put_database(db=DB_NAME).get_result()
        print("📦 DB Created")

init_db()

# ================= LOGIN =================
@app.route("/login", methods=["GET","POST"])
def login():
    msg=""
    if request.method=="POST":
        if request.form["user"]=="admin" and request.form["pwd"]=="123":
            session["user"]="admin"
            return redirect("/")
        else:
            msg="❌ Invalid login"
    return render_template("login.html",msg=msg)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ================= HOME =================
@app.route("/", methods=["GET","POST"])
def index():
    if "user" not in session:
        return redirect("/login")

    msg=""
    data=[]

    docs = client.post_all_docs(db=DB_NAME, include_docs=True).get_result()

    students=[]
    attendance=[]

    for row in docs["rows"]:
        doc=row["doc"]
        if doc.get("type")=="student":
            students.append(doc)
        elif doc.get("type")=="attendance":
            attendance.append(doc)

    # 🔥 AUTO QR + FORM
    if request.method=="POST":
        sid=request.form.get("qr","").strip()

        if sid=="":
            msg="❌ Enter ID"
        else:
            student = next((s for s in students if s["id"]==sid), None)

            if not student:
                msg="❌ Student not found"
            else:
                today=datetime.now().strftime("%Y-%m-%d")

                already = any(a["id"]==sid and a["date"]==today for a in attendance)

                if already:
                    msg="⚠️ Already marked"
                else:
                    now=datetime.now()

                    client.post_document(
                        db=DB_NAME,
                        document={
                            "type":"attendance",
                            "id":sid,
                            "name":student["name"],
                            "date":now.strftime("%Y-%m-%d"),
                            "time":now.strftime("%H:%M:%S")
                        }
                    ).get_result()

                    msg="✅ Attendance marked"

    data=attendance
    return render_template("index.html",data=data,msg=msg)

# ================= ADMIN =================
@app.route("/admin", methods=["GET","POST"])
def admin():
    if "user" not in session:
        return redirect("/login")

    msg=""
    docs = client.post_all_docs(db=DB_NAME, include_docs=True).get_result()

    if request.method=="POST":
        sid=request.form.get("id")
        name=request.form.get("name")

        exists = any(row["doc"].get("id")==sid for row in docs["rows"])

        if exists:
            msg="❌ Already exists"
        else:
            client.post_document(
                db=DB_NAME,
                document={"type":"student","id":sid,"name":name}
            ).get_result()
            msg="✅ Student added"

    return render_template("admin.html",msg=msg)

# ================= DASHBOARD =================
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    docs = client.post_all_docs(db=DB_NAME, include_docs=True).get_result()

    total=0
    chart={}

    for row in docs["rows"]:
        doc=row["doc"]
        if doc.get("type")=="attendance":
            total+=1
            d=doc["date"]
            chart[d]=chart.get(d,0)+1

    return render_template("dashboard.html",total=total,chart=chart)

# ================= EXCEL EXPORT =================
@app.route("/export")
def export():
    docs = client.post_all_docs(db=DB_NAME, include_docs=True).get_result()

    data=[]
    for row in docs["rows"]:
        doc=row["doc"]
        if doc.get("type")=="attendance":
            data.append(doc)

    df=pd.DataFrame(data)
    file="attendance.xlsx"
    df.to_excel(file,index=False)

    return send_file(file,as_attachment=True)

# ================= FACE RECOGNITION =================
@app.route("/face")
def face():
    try:
        import cv2
        return "📷 Face recognition module ready (camera logic add later)"
    except:
        return "⚠️ OpenCV not installed"

# ================= RUN =================
if __name__=="__main__":
    app.run(debug=True,host="0.0.0.0")