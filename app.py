# an object of WSGI application
import json
import math
import os
import re
from datetime import datetime
import csv
import io
from io import StringIO
import pyodbc
import requests
import pandas as pd
#import cv2
#from yolo.yolo_inference import run_yolo_inference
#from azure.ai.formrecognizer import DocumentAnalysisClient
#from azure.core.credentials import AzureKeyCredential
from flask import (
    Flask,
    Response,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
    send_file,
    stream_with_context
)

# from flask_session import Session
from fuzzywuzzy import process
#from ultralytics import YOLO
#import pytesseract
import numpy as np
from io import BytesIO
from PIL import Image
# import easyocr
import urllib.parse  # Import URL encoding library
# Initialize EasyOCR reader
# reader = easyocr.Reader(['fr'])  # Specify the language, e.g., 'fr' for French
from flask_mail import Mail, Message
from flask_apscheduler import APScheduler
from ftplib import FTP_TLS
import zipfile
from io import BytesIO
# class Config:
    # SCHEDULER_API_ENABLED = True

# app.config.from_object(Config())
# scheduler = APScheduler()
# scheduler.init_app(app)
# scheduler.start()
# import easyocr

app = Flask(__name__, template_folder="templates")  # Flask constructor
# Load YOLO model
# model = YOLO("yolo/best.pt")  # Replace with your YOLO model path

# Email configuration
app.config['MAIL_SERVER'] = 'smtp.ionos.com'         # or your SMTP server
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'vishwa@aurexus.com'
app.config['MAIL_PASSWORD'] = 'OKPhPPondy&Web4u2'
mail = Mail(app)
# Configure upload folders
UPLOAD_FOLDER = 'static/uploads'
RESULT_FOLDER = 'static/results'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config.from_object("config.Config")
app.secret_key = "aurexus@106"
# app.config["SESSION_PERMANENT"] = False
# app.config["SESSION_TYPE"] = "filesystem"
# Session(app)
conn_str = "Driver={ODBC Driver 17 for SQL Server};Server=tcp:aurexdb.database.windows.net;Database=AUREXDB1;Uid=db_su;Pwd={=!Aurexus21!=};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
cnxn = pyodbc.connect(conn_str)
cursor = cnxn.cursor()
api_key = "a77d51086fb7455dbc9b8284573e7feb"
endpoint = "https://aurexusformprocessocr.cognitiveservices.azure.com/"

# Initialize the scheduler
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()


# FTP INFO for FTP Image Viewer
FTP_HOST = '74.208.220.192'
FTP_USER = 'auxnetimg'
FTP_PASS = 'Keb0~j05ANwfnfhh'

# Initialize the Form Recognizer client
#document_analysis_client = DocumentAnalysisClient(
    #endpoint=endpoint, credential=AzureKeyCredential(api_key)
#)
# Scheduled Job

@scheduler.task('cron', id='daily_report', hour=10, minute=30)  # Every day at 12:15 PM
def send_daily_notification():
    with app.app_context():
        try:
           
            # Database connection
            cnxn = pyodbc.connect(conn_str)
            cursor = cnxn.cursor()

            # Get all users and their associated projects and emails (join query)
            cursor.execute("""
                SELECT b.project, a.proj_type, a.Email 
                FROM User_table a
                INNER JOIN _unimarc_users_attrib b
                ON a.Username = b.usr_name
                WHERE a.proj_type IN ('unimarc', 'intermarc') group by b.project,a.proj_type,a.Email
            """)

            users = cursor.fetchall()  # Fetch all users

            # Loop through each user and send email based on their project type
            for user in users:
                proj = user[0]  # Project (unimarc or intermarc)
                proj_type = user[1]  # Project type (unimarc/intermarc)
                email = user[2]  # User email

                # Get the notification count based on the project type
                if proj_type == "unimarc":
                    cursor.execute("SELECT COUNT(*) FROM _unimarc WHERE proj = ? AND ano_med_send = 1 AND notified = 0 AND ano_anscode is NULL", (proj,))
                elif proj_type == "intermarc":
                    cursor.execute("SELECT COUNT(*) FROM _intermarc WHERE proj = ? AND ano_med_send = 1 AND notified = 0 AND ano_anscode is NULL", (proj,))

                # Fetch the notification count
                count = cursor.fetchone()[0]

                # Only send email if there are new anomalies (count > 0)
                if count > 0:
                    # Prepare email body
                    report_body = f"""
                    <html>
                    <body style="font-family: calibri, sans-serif; margin: 0; padding: 0;">
                        <table role="presentation" style="width: 100%; border: 0; padding: 20px;">
                            <tr>
                                <td style="background-color: #e0e0e0; color: white; padding: 10px;">
                                    <img src="https://www.aurexus.com/wp-content/uploads/2021/10/1_80x50mm_adobe_illustrator.png" alt="Aurexus" style="height: 50px;"/>
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 20px;">
                                    <h2 style="color: #333;">Bonjour,</h2>
                                    <p style="font-size: 16px; color: #555;">
                                            
                                        <strong>{count} nouvelles anomalies</strong> ont été chargées pour le projet "<strong>{proj}</strong>". Merci de les traiter dès que possible.
                                    </p>
                                    <p style="font-size: 16px; color: #555;">
                                        Bien cordialement,<br>
                                        L'équipe Medusa AureXus
                                    </p>
                                </td>
                            </tr>
                            <tr>
                                <td style="background-color: #f4f4f4; padding: 10px; text-align: center; font-size: 14px; color: #777;">
                                    <p>&copy; {datetime.now().year} Aurexus. Tous droits réservés.</p>
                                </td>
                            </tr>
                        </table>
                    </body>
                    </html>
                    """

                    # Create the message object
                    msg = Message(
                        subject="Nouvelles anomalies dans votre projet",
                        sender=app.config['MAIL_USERNAME'],
                        recipients=[email],  # Send the email to the user's email
                        html=report_body
                    )
                    
                    # Send the email
                    mail.send(msg)

                    print(f"[{datetime.now()}] Email sent to {email} for project {proj}. New anomalies: {count}")

                else:
                    print(f"[{datetime.now()}] No new anomalies for project {proj}. No email sent.")

        except Exception as e:
            print(f"Error sending daily notification: {e}")


# Load the Translation files
def load_translations():
    translations_path = os.path.join(app.root_path, "translations.json")
    with open(translations_path, "r", encoding="utf-8") as f:
        return json.load(f)

# Assign Translation JSON
translations = load_translations()


# User Activity Logging Function
def log_user_activity(cursor):
    username = session.get("name", "anonymous")
    proj = session.get("proj")
    path = request.path
    method = request.method
    ip_address = request.remote_addr
    user_agent = request.headers.get("User-Agent")
    action = request.endpoint or "unknown"

    query = """
        INSERT INTO user_history 
        (username, proj, action, path, method, ip_address, user_agent, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """

    params = (
        username,
        proj,
        action,
        path,
        method,
        ip_address,
        user_agent,
        datetime.now()
    )
    cursor.execute(query, params)

# Track User History for Non-Static Requests
@app.before_request
def track_user_history():
    # Skip static files and other system paths
    if request.path.startswith("/static") or request.path in ["/favicon.ico", "/robots.txt"]:
        return

    try:
        with pyodbc.connect(conn_str) as cnxn:
            with cnxn.cursor() as cursor:
                log_user_activity(cursor)
            cnxn.commit()
    except Exception as e:
        # Optionally log error, but do not interrupt the user experience
        print(f"[UserTrackingError] {e}")

# Index Page (Login)
@app.route("/")
def index():

    return render_template("login.html")


#Check login Information and Assign the value in session
@app.route("/home", methods=["POST", "GET"])
def home():
    if request.method == "POST":
        name = request.form.get("user")
        password = request.form.get("pass")
        language = request.form.get("language")
        cnxn = pyodbc.connect(conn_str)
        cursor = cnxn.cursor()
        cursor.execute(
            "select * from dbo.User_table where Username=? and Password=?",
            (name, password),
        )

        row = cursor.fetchall()

        if row:
            session["name"] = name
            cursor.execute(
                """select b.project,a.proj_type,a.Email,c.Client_report from User_table a
                inner join _unimarc_users_attrib b
				on a.Username=b.usr_name
				inner join Report_links c                
				on b.project=c.Proj
                where a.Username=?""",
                (name),
            )
            row = cursor.fetchone()

            if row:
                session["proj"] = row[0]
                session["projtype"] = row[1]
                session["email"] = row[2]
                session["reportLink"]= row[3]
            else:
                # Handle the case where no row is found, if necessary
                session["proj"] = None
                session["projtype"] = None
                session["email"] = None
                session["reportLink"]= None
            session["lang"] = language
            # ✅ Redirect to your homepage view
            return redirect(url_for("hello"))
        else:
            return render_template(
                "login.html", message="Please Check the Credential's"
            )
    #  ADD THIS to handle GET requests
    return render_template("login.html")

#Notification Count
@app.route("/notification_count")
def notification_count():
    proj = session.get("proj")
    proj_type = session.get("projtype")

    try:
        cnxn = pyodbc.connect(conn_str)
        cursor = cnxn.cursor()

        if proj_type == "unimarc":
            cursor.execute("SELECT COUNT(*) FROM _unimarc WHERE proj = ? AND ano_med_send=1 AND notified = 0 AND ano_anscode is NULL", (proj,))
        elif proj_type == "intermarc":
            cursor.execute("SELECT COUNT(*) FROM _intermarc WHERE proj = ? AND ano_med_send=1 AND notified = 0 AND ano_anscode is NULL", (proj,))
        else:
            return Response("0", mimetype="application/json")

        count = cursor.fetchone()[0]
        return Response(str(count), mimetype="application/json")

    except Exception as e:
        print(f"Error in /notification_count: {e}")
        return Response("0", mimetype="application/json")
        
        
# Dashaboard Page
@app.route("/homepage")
def hello():
    language = request.args.get("lang", session["lang"])
    proj_type = session.get("projtype")
    proj = session.get("proj")
    # language = request.args.get("lang", app.config["DEFAULT_LANGUAGE"])
    if language not in app.config["LANGUAGES"]:
        language = app.config["DEFAULT_LANGUAGE"]

    cnxn = pyodbc.connect(conn_str)
    cursor = cnxn.cursor()
    session.pop("sql_query", None)
    session.pop("sql_query2", None)
    session.pop("sort", None)
    session.pop("sortype", None)
    session.pop("params", None)

    # Count of All Traitement in the project
    if proj_type == "unimarc":
        field = "u990_b"
        table = "dbo._unimarc"
    else:
        field = "z990_b"
        table = "dbo._intermarc"
    
    
    # List of Process with progress bar from client report
    title_report = session["proj"] + "_Report"
    cursor.execute(
        f"select * from dbo.[{title_report}]",
    )
    html_process = ""
    for row in cursor.fetchall():
        if row.Quantity:
            if language == "fr":
                title = row.FrenchTitle
            else:
                title = row.EnglishTitle
            percentage = round((row.Done / row.Quantity) * 100)
            html_process += f'<div style="height:45px;"><label class="tx-12 tx-gray-600 mg-b-10" style="font-size:11px">{title} ({percentage}%)</label><div class="progress" style="height: 9px;border-radius:0px;"><div class="progress-bar wd-25p progress-bar-striped active" role="progressbar" style="width:{percentage}%;size:10px;" aria-valuenow="100" aria-valuemin="0" aria-valuemax="100"></div></div></div>'
    
    

    # Generate URLs for flag images
    en_flag_url = url_for('static', filename='assets/images/us_flag.png')
    fr_flag_url = url_for('static', filename='assets/images/fr_flag.png')   

    if language == "fr":
        langButton = f"""<button class="btn btn-primary dropdown-toggle" type="button" id="dropdownMenuButton" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                             <img class="form-control-sm" src="{fr_flag_url}">French
                            </button>
                             <div class="dropdown-menu" aria-labelledby="dropdownMenuButton">
                                <a class="dropdown-item" href="?lang=en"><img class="form-control-sm" src="{en_flag_url}">English</a>
                             </div>"""
    else:
        langButton = f"""<button class="btn btn-primary dropdown-toggle" type="button" id="dropdownMenuButton" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                             <img class="form-control-sm" src="{en_flag_url}">English
                            </button>
                             <div class="dropdown-menu" aria-labelledby="dropdownMenuButton">
                                <a class="dropdown-item" href="?lang=fr"><img class="form-control-sm" src="{fr_flag_url}">French</a>
                             </div>"""
                           
    combined_query = f"""
    -- 1. Anomaly count by folder
    SELECT 'anomaly' AS type, COUNT({field}) AS val1, Folder, Proj, NULL AS val2
    FROM {table}
    WHERE proj = ? AND (chkTest <> 0) AND {field} <> '' AND {field} <> '_'
    GROUP BY Folder, Proj;

    -- 2. Summary: Todo and Done
    SELECT 'summary',
        SUM(CASE WHEN chkTest <> 0 AND {field} <> '' AND {field} <> '_' THEN 1 ELSE 0 END),
        NULL, Proj,
        SUM(CASE WHEN Ano_AnsCode <> '' AND {field} <> '' AND {field} <> '_' THEN 1 ELSE 0 END)
    FROM {table}
    WHERE Proj = ?
    GROUP BY Proj;

    -- 3. Delivery quantity
    SELECT 'delivery', Quantity, NULL, NULL, NULL
    FROM dbo.[{title_report}]
    WHERE EnglishTitle = 'Delivery';

    -- 4. Percentage
    SELECT 'percentage', FrenchTitle, NULL, NULL, NULL
    FROM dbo.[{title_report}]
    WHERE EnglishTitle = 'Percentage';

    -- 5. Scanning count
    SELECT 'scan_count', COUNT(proj), NULL, NULL, NULL
    FROM dbo.[_ImageScan]
    WHERE proj = ?;

    -- 6. Scanning QC
    SELECT 'scan_qc', COUNT(proj), NULL, NULL, NULL
    FROM dbo.[_ImageScan]
    WHERE proj = ? AND Qc_status = 1;

    -- 7. OCR QC
    SELECT 'ocr_qc', COUNT(proj), NULL, NULL, NULL
    FROM dbo.[_Images]
    WHERE proj = ?;

    -- 8. Processed count
    SELECT 'processed', COUNT(traitement), NULL, NULL, NULL
    FROM {table}
    WHERE traitement <> 'import' AND proj = ?;

    -- 9. QC done
    SELECT 'qc_done', COUNT(*), NULL, NULL, NULL
    FROM {table}
    WHERE lot IN (
        SELECT lot FROM {table} WHERE proj = ? AND [check] = 1
    )
    AND traitement <> 'import' AND proj = ?;

    -- 10. All notices
    SELECT 'all_notices', COUNT(*), NULL, NULL, NULL
    FROM {table}
    WHERE proj = ?;

    """

    params = (proj,) * 9
    cursor.execute(combined_query, params)

    results = {}
    while True:
        rows = cursor.fetchall()
        if rows:
            result_type = rows[0][0]  # e.g., 'summary', 'delivery'
            results[result_type] = rows
        if not cursor.nextset():
            break

    return render_template(
        "hometest.html",
        #html_content=html_content,
        #html_ano=html_ano,
        all_count=results.get('delivery', [[None, 0]])[0][1] or 0,
        html_process=html_process,
        todo=results.get('summary', [[None, 0]])[0][1] or 0,
        done=results.get('summary', [[None, 0, None, None, 0]])[0][4] or 0,
        percentage=float(results.get('percentage', [[None, 0]])[0][1]) or 0,
        translations=translations[language],
        lang=language,
        langButton=langButton,
        allcount=results.get('all_notices', [[None, 0]])[0][1] or 0,
        reportallCount=results.get('scan_count', [[None, 0]])[0][1] or 0,
        processedCount=results.get('processed', [[None, 0]])[0][1] or 0,
        ScannQcCount=results.get('scan_qc', [[None, 0]])[0][1] or 0,
        ocrQcCount=results.get('ocr_qc', [[None, 0]])[0][1] or 0,
        QcCountDone=results.get('qc_done', [[None, 0]])[0][1] or 0,
    )

#anoCount per Folder
@app.route('/ajax_anocount', methods=['GET'])
def ajax_anocount():
    proj_type = session.get("projtype")
    proj = session.get("proj")
    cnxn = pyodbc.connect(conn_str)
    cursor = cnxn.cursor()
     # Count of All Traitement in the project
    if proj_type == "unimarc":
        field = "u990_b"
        table = "dbo._unimarc"
    else:
        field = "z990_b"
        table = "dbo._intermarc"

    cursor.execute(f"""SELECT COUNT({field}) AS AnoCount, Folder, Proj
    FROM {table}
    WHERE proj = ? AND ano_med_send = 1
    GROUP BY Folder, Proj
    """, proj)
    rows = cursor.fetchall()
    data = [dict(zip([col[0] for col in cursor.description], row)) for row in rows]
    return jsonify(data)

#Traitement Count
@app.route('/ajax_traitement', methods=['GET'])
def ajax_traitement():
    proj_type = session.get("projtype")
    proj = session.get("proj")
    cnxn = pyodbc.connect(conn_str)
    cursor = cnxn.cursor()
     # Count of All Traitement in the project
    if proj_type == "unimarc":
        field = "u990_b"
        table = "dbo._unimarc"
    else:
        field = "z990_b"
        table = "dbo._intermarc"
    cursor.execute(f"SELECT traitement AS name, COUNT(*) AS count_val FROM {table} WHERE proj = ? GROUP BY traitement", session['proj'])
    rows = cursor.fetchall()
    data = [dict(zip([col[0] for col in cursor.description], row)) for row in rows]
    return jsonify(data)
    
        
# List of notices with pagination and filer form
@app.route("/listdata", methods=["GET", "POST"])
def listdata():

    language = request.args.get("lang", session["lang"])
    chk_test = request.args.get("chkTest", '0')  # Default to '0' if not provided
    
    # Debugging prints to check current and new values
    #print("test")
    #print("Session chk_test:", session.get('chk_test'))
    #print("Current chk_test:", chk_test)

    # Check the page weather current and previous pages are the same
    if chk_test != session.get('chk_test'):
        # Remove the SQL query keys from the session
        session.pop('sql_query', None)
        session.pop('sql_query2', None)
        session.pop('params', None)
        # Remove the 'chk_test' key f
        # rom the session
        session.pop('chk_test', None)
        
        #store session Values
        session.pop("selected_dossier", None)
        session.pop("selected_traitement", None)
        session.pop("selected_type", None)
        session.pop("selected_anscode", None)
        session.pop("keycol", None)
        session.pop("sort", None)
        session.pop("searchword", None)
        session.pop("sortype", None)

    # Optionally update the session with the new value of 'chk_test'
    session['chk_test'] = chk_test
        
    # TEST,ANOMALIE,NOTICE CHECK
    if session['chk_test'] == "1":
        addParam = " AND chkTest='1'"
    elif session['chk_test'] == "2": 
        addParam = " AND Ano_med_send ='1'"  
    elif session['chk_test'] == "3": 
        addParam = " AND Ano_med_send ='1' AND notified=0 AND ano_anscode is NULL"     
    else: 
        addParam = ""
   
    proj_type = session.get("projtype")
    proj = session.get("proj", "")

    if proj_type == "unimarc":
        field = "u990_b"
        field2 = "u990_c"
        table = "dbo._unimarc"
    else:
        field = "z990_b"
        field2 = "z990_c"
        table = "dbo._intermarc"

    # language = request.args.get("lang", app.config["DEFAULT_LANGUAGE"])
    if language not in app.config["LANGUAGES"]:
        language = app.config["DEFAULT_LANGUAGE"]
        session.pop("lang")
        session["lang"] = language
    cnxn = pyodbc.connect(conn_str)
    cursor = cnxn.cursor()
    html_content_fil = ""  # Initialize html_content variable
    process = ""
    anotype = ""
    # Generate URLs for flag images
    en_flag_url = url_for('static', filename='assets/images/us_flag.png')
    fr_flag_url = url_for('static', filename='assets/images/fr_flag.png')
    if language == "fr":
        langButton = f"""<button class="btn btn-primary dropdown-toggle" type="button" id="dropdownMenuButton" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                             <img class="form-control-sm" src="{fr_flag_url}">French
                            </button>
                             <div class="dropdown-menu" aria-labelledby="dropdownMenuButton">
                                <a class="dropdown-item" href="?lang=en"><img class="form-control-sm" src="{en_flag_url}">English</a>
                             </div>"""
    else:
        langButton = f"""<button class="btn btn-primary dropdown-toggle" type="button" id="dropdownMenuButton" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                             <img class="form-control-sm" src="{en_flag_url}">English
                            </button>
                             <div class="dropdown-menu" aria-labelledby="dropdownMenuButton">
                                <a class="dropdown-item" href="?lang=fr"><img class="form-control-sm" src="{fr_flag_url}">French</a>
                             </div>"""

    # Initialize page_no variable
    # page_no = 1
    query1 = f"SELECT lot FROM {table} WHERE proj=? "
    if chk_test == "1":
        query1 += addParam
    query1 += " GROUP BY lot"
    

    html_content = ""
    page_no = int(request.args.get("page_no", 1))  # Get current page number
    session["listpage_no"] = page_no
    if request.method == "POST" and "clear" in request.form:
    # Clear filter-related session keys
        session.pop("sort", None)
        session.pop("sortype", None)
        session.pop("params", None)
        session.pop("sql_query", None)
        session.pop("sql_query2", None)
        session.pop("total_records", None)
          #store session Values
        session.pop("selected_dossier", None)
        session.pop("selected_traitement", None)
        session.pop("selected_type", None)
        session.pop("selected_anscode", None)
        session.pop("keycol", None)
        
        session.pop("searchword", None)
        
        
    if request.method == "POST" and "filters" in request.form:
        session.pop("sort", None)
        session.pop("sortype", None)
        session.pop("params", None)
        session.pop("sql_query", None)
        session.pop("sql_query2", None)
        session.pop("total_records",None)
        # Retrieve form data
        
        #store session Values
        session["selected_dossier"] = request.form["dossier"]
        session["selected_traitement"] = request.form["traitement"]
        session["selected_type"] = request.form["type"]
        session["selected_anscode"] = request.form["anscode"]
        session["keycol"] = request.form["keycol"]
        session["sort"] = request.form["sort"]
        session["searchword"] = request.form["searchword"]
        session["sortype"] = request.form["sortype"]
        
        dossier = request.form["dossier"]
        traitement = request.form["traitement"]
        types = request.form["type"]
        anscode = request.form["anscode"]
        searchword = request.form["searchword"]
        keycol = request.form["keycol"]
        bookmark_filter = request.form.get("bookmark", "ALL")
        session["bookmark_filter"] = bookmark_filter
        sort = request.form.get(
            "sort", "order by z001_x0"
        )  # Default sort column if not provided
        session["sort"] = sort
        sortype = request.form.get("sortype", "ASC")
        session["sortype"] = sortype

        # Build SQL query based on form data
        sql_query = f"""SELECT COUNT(*) FROM {table} WHERE Proj = ?  {addParam}"""
        sql_query2 = f"""
            SELECT a.*, CASE WHEN b.book_id IS NOT NULL THEN 1 ELSE 0 END AS bookmarked,
            Row_Number() Over ({sort} {sortype}) AS Rows 
            FROM {table} a
            LEFT JOIN bookmark_notices b
                ON b.book_id=a.ID and b.[user]='{session.get("name")}' and  b.proj='{session.get("proj")}'
            WHERE a.Proj = ? {addParam}
        """
        params = [proj]

        # if chk_test == '1':
        #     params.append(chk_test)
        
        if dossier != "ALL":
            sql_query += " AND Lot = ?"
            sql_query2 += " AND Lot = ?"
            params.append(dossier)
        if traitement != "ALL":
            sql_query += " AND traitement = ?"
            sql_query2 += " AND traitement = ?"
            params.append(traitement)
        if types != "ALL":
            sql_query += f" AND {field} = ?"
            sql_query2 += f" AND {field} = ?"
            params.append(types)
        if anscode != "ALL":
            if anscode == "Todo":
                sql_query += " AND (Ano_AnsCode IS NULL OR Ano_AnsCode = '')"
                sql_query2 += " AND (Ano_AnsCode IS NULL OR Ano_AnsCode = '')"
            else:
                sql_query += " AND Ano_AnsCode = ?"
                sql_query2 += " AND Ano_AnsCode = ?"
                params.append(anscode)
        if bookmark_filter  != "ALL":
            bookmark_condition = "= 1" if bookmark_filter == "1" else "= 0"
          # For sql_query (no alias 'a')
            sql_query += f""" AND ID IN (
                                SELECT book_id FROM bookmark_notices 
                                WHERE [user]=? AND proj=?
                            )""" if bookmark_filter == "1" else f""" AND ID NOT IN (
                                SELECT book_id FROM bookmark_notices 
                                WHERE [user]=? AND proj=? {addParam} 
                            )"""

            # For sql_query2 (alias 'a' is present)
            sql_query2 += f""" AND a.ID IN (
                                SELECT book_id FROM bookmark_notices 
                                WHERE [user]=? AND proj=?
                            )""" if bookmark_filter == "1" else f""" AND a.ID NOT IN (
                                SELECT book_id FROM bookmark_notices 
                                WHERE [user]=? AND proj=? {addParam}
                            )"""
            
            params.extend([session.get("name"), session.get("proj")])
        if searchword:
            sql_query += f" AND {keycol} COLLATE Latin1_General_CI_AI LIKE ?"
            sql_query2 += f" AND {keycol}  COLLATE Latin1_General_CI_AI LIKE ?"
            params.append(f"%{searchword}%")

        # Save queries and params in session
        session["sql_query"] = sql_query
        session["sql_query2"] = sql_query2
        session["params"] = params
        
    else:
        # Handle initial page load or no filters submitted
        # sql_query = session.get('sql_query', "SELECT COUNT(*) FROM dbo._unimarc WHERE Proj = 'CAEN'")
        sort = session.get("sort", "order by z001_x0")
        sortype = session.get("sortype", "ASC")
        bookmark_filter = session.get("bookmark_filter", "ALL")
        sql_query = session.get(
            "sql_query", f"SELECT COUNT(*) FROM {table} WHERE Proj = ?  {addParam}"
        )
        sql_query2 = session.get(
            "sql_query2",
            f"""
            SELECT a.*, CASE WHEN b.book_id IS NOT NULL THEN 1 ELSE 0 END AS bookmarked, 
            Row_Number() Over ({sort} {sortype}) AS Rows 
            FROM {table} a
            LEFT JOIN bookmark_notices b
                ON b.book_id=a.ID and b.[user]='{session.get("name")}' and  b.proj='{session.get("proj")}'
            WHERE a.Proj = ? {addParam}
        """,
        )
        params = session.get("params", [proj])
        # if chk_test == '1':
        #     params.append(chk_test)
    cursor.execute(query1, proj)
    rows = cursor.fetchall()
    selected_dossier = session.get("selected_dossier")
    for row in rows:
        selected_attr = ' selected' if row[0] == selected_dossier else ''
        html_content_fil += f'<option value="{row[0]}" {selected_attr}>{row[0]}</option>'

    cursor.execute(
        f"""SELECT traitement FROM {table} where proj=? {addParam} group by traitement""",
        proj
    )
    rows = cursor.fetchall()
    selected_traitement = session.get("selected_traitement")
    for row in rows:
        selected_attr = ' selected' if row[0] == selected_traitement else ''
        process += f'<option value="{row[0]}" {selected_attr}>{row[0]}</option>'

    cursor.execute(
        f"SELECT {field} FROM {table} where proj=? and datalength({field})>0 {addParam} group by {field}",
        proj
    )
    rows = cursor.fetchall()
    selected_type = session.get("selected_type")
    for row in rows:
        selected_attr = ' selected' if row[0] == selected_type else ''
        anotype += f'<option value="{row[0]}" {selected_attr}>{row[0]}</option>'
    # Execute SQL query for total records
    print(session.get("sql_query2",""))
    #print(params)
    #print(addParam)
    cursor.execute(sql_query, params)
    count_result = cursor.fetchone()
    total_records = count_result[0] if count_result else 0

    # Pagination logic
    total_records_per_page = 20
    offset = (page_no - 1) * total_records_per_page
    total_no_of_pages = math.ceil(total_records / total_records_per_page)
    previous_page = page_no - 1 if page_no > 1 else 1
    next_page = page_no + 1 if page_no < total_no_of_pages else total_no_of_pages
    second_last = total_no_of_pages - 1

    # Modify sql_query2 for pagination
    sql_query2 += f" {sort} {sortype} OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
    pagination_params = params + [offset, total_records_per_page]   
    print(sql_query2,pagination_params)
    # Execute SQL query for records
    cursor.execute(sql_query2, pagination_params)
    recordsPrint = cursor.fetchall()
    session["total_records"]=total_records
    # Generate HTML content for records
    if recordsPrint:
        html_content += (
            "<table class='table table-striped table-bordered border-top' style=''>"
        )
        if language == "fr":
            html_content += "<thead><tr>"
            html_content += "<th style='width:15px;'></th>"
            html_content += "<th>Lots</th>"
            html_content += "<th>Dossier</th>"
            html_content += "<th>Image</th>"
            html_content += "<th>Traitement</th>"
            html_content += "<th>QCote</th>"
            html_content += "<th>Type</th>"
            html_content += "<th>Anomalie</th>"
            html_content += "<th>Réponse</th>"
            html_content += "<th>Action</th>"
            html_content += "</tr></thead>"
            html_content += "<tbody>"
        else:
            html_content += "<thead><tr>"
            html_content += "<th></th>"
            html_content += "<th>Lots</th>"
            html_content += "<th>Folder</th>"
            html_content += "<th>Image</th>"
            html_content += "<th>Process</th>"
            html_content += "<th>QCote</th>"
            html_content += "<th>Type</th>"
            html_content += "<th>Anomalie</th>"
            html_content += "<th>Response</th>"
            html_content += "<th>Action</th>"
            html_content += "</tr></thead>"
            html_content += "<tbody>"

        for index, row in enumerate(recordsPrint):
            row_dict = dict(zip([column[0] for column in cursor.description], row))
            html_content += "<tr>"
            recid = row_dict.get("ID", "") 
            is_bookmarked = row_dict.get("bookmarked", 0)  # bookmark notices 
            checked_attr = "checked" if is_bookmarked else ""

            html_content += f"""
            <td>
              <input type='checkbox' id='star_{recid}'  data-id='{recid}' class='star-checkbox' {checked_attr}>
              <label for='star_{recid}' class='star-label'>&#9733;</label>
            </td>
            """
            for column_name in [
                "Lot",
                "Folder",
                "z001_x0",
                "traitement",
                "QCote",
                f"{field}",
                f"{field2}",
                "Ano_AnsCode",
            ]:
                # Check for None and replace with an empty string
                value = row_dict.get(column_name, "")
                if value is None:
                    value = ""
                html_content += f"<td>{value}</td>"
            row_id = row_dict.get("Rows", "")
            html_content += f"<td><a href='form-edit?list={row_id}' class='btn-sm btn-primary btn-flat'><i class='fa fa-solid fa-edit'></i></a></td>"
            html_content += "</tr>"
        html_content += "</tbody></table>"
    else:
        if language == "fr":
            html_content += "<p>Aucun enregistrement trouvé</p>"
        else:
            html_content += "<p>No Record Found!</p>"

    # total project notices count
    queryCount = f"select count(*) from {table} where proj=?"
    noticeAll = cursor.execute(queryCount, proj)
    countNotices = noticeAll.fetchone()
    AllCount = countNotices[0]

    # Close the cursor and connection

    cursor.close()
 

    return render_template(
        "base2.html",
        page_no=page_no,
        total_no_of_pages=total_no_of_pages,
        total_records=total_records,
        html_content=html_content,
        html_content_fil=html_content_fil,
        process=process,
        anotype=anotype,
        translations=translations[language],
        lang=language,
        langButton=langButton,
        allcount=AllCount,
    )
    
    
# Notice Bookmark logic
@app.route("/save_bookmark", methods=["POST"])
def save_bookmark():
    cnxn = pyodbc.connect(conn_str)
    data = request.get_json()    
    user = session.get("name")  # Prefer session for security
    proj = session.get("proj")
    book_id = data.get("book_id")
    checked = data.get("checked")

    if not user or not proj or not book_id:
        return jsonify({"success": False, "error": "Missing data"}), 400

    try:
        
        cursor = cnxn.cursor()
        user = session.get("name")
        proj = session.get("proj")
        book_id = data.get("book_id")
        checked = data.get("checked")
        if checked:
            # Insert only if it doesn't already exist
            cursor.execute("""
                IF NOT EXISTS (
                    SELECT 1 FROM bookmark_notices
                    WHERE [user] = ? AND proj = ? AND book_id = ?
                )
                BEGIN
                    INSERT INTO bookmark_notices ([user], proj, book_id)
                    VALUES (?, ?, ?)
                END
            """, (user, proj, book_id, user, proj, book_id))
        else:
            # Delete bookmark
            cursor.execute("""
                DELETE FROM bookmark_notices
                WHERE [user] = ? AND proj = ? AND book_id = ?
            """, (user, proj, book_id))

        cursor.commit()
        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

    finally:
        cursor.close()
        cnxn.close()
    
    
# Notice stages from OCR to Delivery
@app.route("/stage", methods=["GET", "POST"])
def stage():
    language = request.args.get("lang", session["lang"])
    proj_type = session.get("projtype")
    proj = session.get("proj", "")
    if proj_type == "unimarc":
        field = "u990_b"
        field2 = "u990_c"
        table = "dbo._unimarc"
    else:
        field = "z990_b"
        field2 = "z990_c"
        table = "dbo._intermarc"
    # language = request.args.get("lang", app.config["DEFAULT_LANGUAGE"])
    if language not in app.config["LANGUAGES"]:
        language = app.config["DEFAULT_LANGUAGE"]
        session.pop("lang")
        session["lang"] = language

    en_flag_url = url_for('static', filename='assets/images/us_flag.png')
    fr_flag_url = url_for('static', filename='assets/images/fr_flag.png')   

    if language == "fr":
        langButton = f"""<button class="btn btn-primary dropdown-toggle" type="button" id="dropdownMenuButton" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                             <img class="form-control-sm" src="{fr_flag_url}">French
                            </button>
                             <div class="dropdown-menu" aria-labelledby="dropdownMenuButton">
                                <a class="dropdown-item" href="?lang=en"><img class="form-control-sm" src="{en_flag_url}">English</a>
                             </div>"""
    else:
        langButton = f"""<button class="btn btn-primary dropdown-toggle" type="button" id="dropdownMenuButton" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                             <img class="form-control-sm" src="{en_flag_url}">English
                            </button>
                             <div class="dropdown-menu" aria-labelledby="dropdownMenuButton">
                                <a class="dropdown-item" href="?lang=fr"><img class="form-control-sm" src="{fr_flag_url}">French</a>
                             </div>"""
    cnxn = pyodbc.connect(conn_str)
    cursor = cnxn.cursor()
    html_content_fil = ""  # Initialize html_content variable
    process = ""
    anotype = ""

    # Initialize page_no variable
    # page_no = 1
    cursor.execute(f"SELECT lot FROM {table} where proj=? group by lot", proj)
    rows = cursor.fetchall()
    for row in rows:
        html_content_fil += f'<option value="{row[0]}">{row[0]}</option>'

    cursor.execute(
        f"SELECT traitement FROM {table} where proj=? group by traitement",
        proj,
    )
    rows = cursor.fetchall()
    for row in rows:
        process += f'<option value="{row[0]}">{row[0]}</option>'

    cursor.execute(
        f"SELECT {field} FROM {table} where proj=? and datalength({field})>0 group by {field}",
        session["proj"],
    )
    rows = cursor.fetchall()

    for row in rows:
        anotype += f'<option value="{row[0]}">{row[0]}</option>'

    html_content = ""
    # html_process = ""
    # icons = ["scan-outline", "book-outline", "search-outline", "pricetag-outline",
    #  "search-outline", "mail-outline", "mail-outline", "mail-outline", "mail-outline"]
    page_no = int(request.args.get("page_no", 1))  # Get current page number
    session["listpage_no"] = page_no

    if request.method == "POST" and "filters" in request.form:
        session.pop("sort", None)
        session.pop("sortype", None)
        session.pop("params", None)
        session.pop("sql_query", None)
        session.pop("sql_query2", None)
        session.pop("total_records",None)
        # Retrieve form data
        dossier = request.form["dossier"]
        traitement = request.form["traitement"]
        types = request.form["type"]
        anscode = request.form["anscode"]
        searchword = request.form["searchword"]
        keycol = request.form["keycol"]
        sort = request.form.get("sort", "order by z001_x0")
        # Default sort column if not provided
        session["sort"] = sort
        sortype = request.form.get("sortype", "ASC")
        session["sortype"] = sortype

        # Build SQL query based on form data
        sql_query = (
            f"SELECT COUNT(*) FROM {table} WHERE Proj = ?",
            proj,
        )
        sql_query2 = f"""
            SELECT *, 
            Row_Number() Over ({sort} {sortype}) AS Rows 
            FROM {table}
            WHERE Proj = {proj}
        """.format(
            sort=sort, sortype=sortype
        )
        params = []

        if dossier != "ALL":
            sql_query += " AND Lot = ?"
            sql_query2 += " AND Lot = ?"
            params.append(dossier)
        if traitement != "ALL":
            sql_query += " AND traitement = ?"
            sql_query2 += " AND traitement = ?"
            params.append(traitement)
        if types != "ALL":
            sql_query += " AND u990_b = ?"
            sql_query2 += " AND u990_b = ?"
            params.append(types)
        if anscode != "ALL":
            if anscode == "TODO":
                sql_query += " AND (Ano_AnsCode IS NULL OR Ano_AnsCode = '')"
                sql_query2 += " AND (Ano_AnsCode IS NULL OR Ano_AnsCode = '')"
            else:
                sql_query += " AND Ano_AnsCode = ?"
                sql_query2 += " AND Ano_AnsCode = ?"
                params.append(anscode)
        if searchword:
            sql_query += f" AND {keycol} COLLATE Latin1_General_CI_AI LIKE ?"
            sql_query2 += f" AND {keycol} COLLATE Latin1_General_CI_AI LIKE ?"
            params.append(f"%{searchword}%")

        # Save queries and params in session
        session["sql_query"] = sql_query
        session["sql_query2"] = sql_query2
        session["params"] = params

    else:
        # Handle initial page load or no filters submitted
        # sql_query = session.get('sql_query', "SELECT COUNT(*) FROM dbo._unimarc WHERE Proj = 'CAEN'")
        sort = session.get("sort", "order by z001_x0")
        sortype = session.get("sortype", "ASC")
        print(sort)
        sql_query = session.get(
            "sql_query", f"SELECT COUNT(*) FROM {table} WHERE Proj = ?"
        )
        sql_query2 = session.get(
            "sql_query2",
            f"""
            SELECT *, 
            Row_Number() Over ({sort} {sortype}) AS Rows 
            FROM {table} 
            WHERE Proj =?
        """.format(
                sort=sort, sortype=sortype
            ),
        )
        params = session.get("params", [proj])
        # if not sql_query and not sql_query2

    # Execute SQL query for total records
    #print(sql_query)
    #print(params)
    cursor.execute(sql_query, params)
    total_records = cursor.fetchone()[0]

    # Pagination logic
    total_records_per_page = 20
    offset = (page_no - 1) * total_records_per_page
    total_no_of_pages = math.ceil(total_records / total_records_per_page)
    previous_page = page_no - 1 if page_no > 1 else 1
    next_page = page_no + 1 if page_no < total_no_of_pages else total_no_of_pages
    second_last = total_no_of_pages - 1

    # Modify sql_query2 for pagination
    sql_query2 += " ORDER BY z001_x0 OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
    pagination_params = params + [offset, total_records_per_page]
    print(sql_query2)
    # Execute SQL query for records
    cursor.execute(sql_query2, pagination_params)
    recordsPrint = cursor.fetchall()

    # Generate HTML content for records
    if recordsPrint:
        html_content += "<table class='table  table-bordered border-top' style=''>"
        html_content += "<thead><tr>"
        html_content += "<th>Folder</th>"
        html_content += "<th>Image</th>"
        html_content += "<th>Traitement</th>"
        html_content += "<th style='text-align:center;'>Stages</th>"
        html_content += "<th style='text-align:center;' hidden>Percentage</th>"
        html_content += "</tr></thead>"
        html_content += "<tbody>"
        # html_process += f"""<ul>
        # 					<li class="active" id="icon1"><ion-icon name="scan-outline"></ion-icon></li>
        # 					<li class="active" id="icon2"><ion-icon name="book-outline"></ion-icon></li>
        # 					<li class="active" id="icon3"><ion-icon name="search-outline"></ion-icon></li>
        # 					<li class="active blink-border" id="icon4"><ion-icon name="pricetag-outline"></ion-icon></li>
        # 					<li id="icon5"><ion-icon name="search-outline"></ion-icon></li>
        # 					<li id="icon5"><ion-icon name="mail-outline"></ion-icon></li>
        # 					<li id="icon5"><ion-icon name="mail-outline"></ion-icon></li>
        # 					<li id="icon5"><ion-icon name="mail-outline"></ion-icon></li>
        # 					<li id="icon5"><ion-icon name="mail-outline"></ion-icon></li>
        # 					</ul>"""
        for row in recordsPrint:
            row_dict = dict(zip([column[0] for column in cursor.description], row))
            html_content += "<tr>"
            for column_name in [
                "Folder",
                "z001_x0",
                "traitement",
            ]:
                html_content += "<td>" + str(row_dict.get(column_name, "")) + "</td>"
            row_id = row_dict.get("Rows", "")
            # html_content += f"<td><a href='form-edit?list={row_id}' class='btn-sm btn-primary'><i class='fa-solid fa-edit'></i></a></td>"
            traitement_value = str(row_dict.get("traitement", ""))
            completed_steps = 0
            percentage = 0
            if traitement_value == "NE PAS TRAITER":
                completed_steps = 4
                percentage = completed_steps * 11.1
            elif traitement_value == "import" or traitement_value == "IMPORT":
                completed_steps = 4
                percentage = completed_steps * 11.1
            elif traitement_value != "import":
                completed_steps = 5
                percentage = completed_steps * 11.1
            else:
                completed_steps = 4
                percentage = completed_steps * 11.1
            html_content += f"""<td>
                                <div class='stepper-wrapper col-md-6'>"""
            for i in range(0, 9):
                if i < completed_steps:
                    html_content += f"""<div class='stepper-item completed'>
                                    <div class='step-counter'></div>                                    
                                    </div>"""
                else:
                    html_content += f"""<div class='stepper-item'>
                                    <div class='step-counter'></div>                                    
                                    </div>"""

            html_content += f"""<div class='stepper-item'><div class='step-counters' alt='Delivery'>{percentage}%</div></div>
                            </div></td>"""
            html_content += f"""<td hidden>{completed_steps}</td></tr>"""
        html_content += "</tbody></table>"
    else:
        html_content += "<p>No records found</p>"

    # total project notices count
    queryCount = f"select count(*) from {table} where proj=?"
    noticeAll = cursor.execute(queryCount, session["proj"])
    countNotices = noticeAll.fetchone()
    AllCount = countNotices[0]

    # Close the cursor and connection
    cursor.close()
    cnxn.close()

    return render_template(
        "stage.html",
        page_no=page_no,
        total_no_of_pages=total_no_of_pages,
        total_records=total_records,
        html_content=html_content,
        html_content_fil=html_content_fil,
        process=process,
        anotype=anotype,
        percentage=percentage,
        translations=translations[language],
        lang=language,
        langButton=langButton,
        allcount=AllCount,
    )

# Template view Dummy (only for Test)
@app.route("/base")
def renderBase():
    return render_template("base.html")

# Image
@app.route("/render")
def renderTemplate():
    return render_template("table-export.html", now=datetime.utcnow())


@app.route("/dashboard")
def renderDashboard():
    return render_template("hometest.html", now=datetime.utcnow())


@app.route("/ocr", methods=["GET", "POST"])
def OCR():
    cnxn = pyodbc.connect(conn_str)
    cursor = cnxn.cursor()
    # Establish database connection
    proj_type = session.get("projtype")
    proj = session.get("proj", "")
    language = request.args.get("lang", session["lang"])
    proj_type = session.get("projtype")
    proj = session.get("proj", "")
    if proj_type == "unimarc":
        field = "u990_b"
        field2 = "u990_c"
        table = "dbo._unimarc"
    else:
        field = "z990_b"
        field2 = "z990_c"
        table = "dbo._intermarc"
    # language = request.args.get("lang", app.config["DEFAULT_LANGUAGE"])
    if language not in app.config["LANGUAGES"]:
        language = app.config["DEFAULT_LANGUAGE"]
        session.pop("lang")
        session["lang"] = language
    
    en_flag_url = url_for('static', filename='assets/images/us_flag.png')
    fr_flag_url = url_for('static', filename='assets/images/fr_flag.png')   

    if language == "fr":
        langButton = f"""<button class="btn btn-primary dropdown-toggle" type="button" id="dropdownMenuButton" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                             <img class="form-control-sm" src="{fr_flag_url}">French
                            </button>
                             <div class="dropdown-menu" aria-labelledby="dropdownMenuButton">
                                <a class="dropdown-item" href="?lang=en"><img class="form-control-sm" src="{en_flag_url}">English</a>
                             </div>"""
    else:
        langButton = f"""<button class="btn btn-primary dropdown-toggle" type="button" id="dropdownMenuButton" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                             <img class="form-control-sm" src="{en_flag_url}">English
                            </button>
                             <div class="dropdown-menu" aria-labelledby="dropdownMenuButton">
                                <a class="dropdown-item" href="?lang=fr"><img class="form-control-sm" src="{fr_flag_url}">French</a>
                             </div>"""

    query = f"select *,Row_Number() over (order by id) as rowNo FROM dbo.PAR5_OCR"
    cursor.execute(query)
    recordsPrint = cursor.fetchall()
    html_content = ""
    if recordsPrint:
        html_content += (
            "<table class='table table-striped table-bordered border-top' style=''>"
        )
        if language == "fr":
            html_content += "<thead><tr>"
            html_content += "<th>Dossier</th>"
            html_content += "<th>Image</th>"
            html_content += "<th>Author</th>"
            html_content += "<th>TC</th>"
            html_content += "<th>Title</th>"
            html_content += "<th>TC</th>"
            html_content += "<th>Address</th>"
            html_content += "<th>TC</th>"
            html_content += "<th>Format</th>"
            html_content += "<th>TC</th>"
            html_content += "<th>Cote</th>"
            html_content += "<th>TC</th>"
            html_content += "<th>VersoDetails</th>"
            html_content += "<th>TC</th>"
            html_content += "<th>Info</th>"
            html_content += "<th>TC</th>"
            html_content += "<th>Action</th>"
            html_content += "</tr></thead>"
            html_content += "<tbody>"
        else:
            html_content += "<thead><tr>"
            html_content += "<th>Dossier</th>"
            html_content += "<th>Image</th>"
            html_content += "<th>Author</th>"
            html_content += "<th>TC</th>"
            html_content += "<th>Title</th>"
            html_content += "<th>TC</th>"
            html_content += "<th>Address</th>"
            html_content += "<th>TC</th>"
            html_content += "<th>Format</th>"
            html_content += "<th>TC</th>"
            html_content += "<th>Cote</th>"
            html_content += "<th>TC</th>"
            html_content += "<th>VersoDetails</th>"
            html_content += "<th>TC</th>"
            html_content += "<th>Info</th>"
            html_content += "<th>TC</th>"
            html_content += "<th>Action</th>"
            html_content += "</tr></thead>"
            html_content += "<tbody>"

        for row in recordsPrint:
            row_dict = dict(zip([column[0] for column in cursor.description], row))
            html_content += "<tr>"
            for column_name in [
                "folder",
                "Image",
                "Author",
                "Author_c",
                "Title",
                "Title_c",
                "Adresse",
                "Adresse_c",
                "Author",
                "Author_c",
                "Format_OCR",
                "Format_c",
                "ExtraDetails",
                "ExtraDetails_c",
                "VersoDetails",
                "VersoDetails_c",
            ]:
                # Check for None and replace with an empty string
                value = row_dict.get(column_name, "")
                if value is None:
                    value = ""
                # Convert _c fields to percentage format if they contain numeric values
                if column_name.endswith("_c"):
                    try:
                        numeric_value = float(value)
                        value = f"{int(numeric_value * 100)}%"
                    except ValueError:
                        pass  # Keep the original value if conversion fails

                html_content += f"<td>{value}</td>"
            row_id = row_dict.get("rowNo", "")
            html_content += f"<td><a href='roi?img={row_id}' class='btn-sm btn-primary'><i class='fa fa-solid fa-edit'></i></a></td>"
            html_content += "</tr>"
        html_content += "</tbody></table>"

    # total project notices count
    queryCount = f"select count(*) from {table} where proj=?"
    noticeAll = cursor.execute(queryCount, session["proj"])
    countNotices = noticeAll.fetchone()
    AllCount = countNotices[0]
    # Close the cursor and connection
    cursor.close()
    cnxn.close()
    return render_template(
        "ocr.html",
        translations=translations[language],
        lang=language,
        langButton=langButton,
        allcount=AllCount,
        html_content=html_content,
    )


@app.route("/roi", methods=["GET", "POST"])
def renderROI():
    language = request.args.get("lang", session["lang"])
    proj_type = session.get("projtype")
    proj = session.get("proj", "")
    if proj_type == "unimarc":
        field = "u990_b"
        field2 = "u990_c"
        table = "dbo._unimarc"
    else:
        field = "z990_b"
        field2 = "z990_c"
        table = "dbo._intermarc"
    # language = request.args.get("lang", app.config["DEFAULT_LANGUAGE"])
    if language not in app.config["LANGUAGES"]:
        language = app.config["DEFAULT_LANGUAGE"]
        session.pop("lang")
        session["lang"] = language
    # language Button
    en_flag_url = url_for('static', filename='assets/images/us_flag.png')
    fr_flag_url = url_for('static', filename='assets/images/fr_flag.png')   

    if language == "fr":
        langButton = f"""<button class="btn btn-primary dropdown-toggle" type="button" id="dropdownMenuButton" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                             <img class="form-control-sm" src="{fr_flag_url}">French
                            </button>
                             <div class="dropdown-menu" aria-labelledby="dropdownMenuButton">
                                <a class="dropdown-item" href="?lang=en"><img class="form-control-sm" src="{en_flag_url}">English</a>
                             </div>"""
    else:
        langButton = f"""<button class="btn btn-primary dropdown-toggle" type="button" id="dropdownMenuButton" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                             <img class="form-control-sm" src="{en_flag_url}">English
                            </button>
                             <div class="dropdown-menu" aria-labelledby="dropdownMenuButton">
                                <a class="dropdown-item" href="?lang=fr"><img class="form-control-sm" src="{fr_flag_url}">French</a>
                             </div>"""
    # execute query
    cnxn = pyodbc.connect(conn_str)
    cursor = cnxn.cursor()
    img = request.args.get("img", 1)
    query = """with ts as (select *,Row_Number() over (order by id) as rowNo FROM dbo.PAR5_OCR) 
                select * from ts where rowNo=?"""
    cursor.execute(query, img)
    row = cursor.fetchone()

    if row:

        def safe_eval(value):
            if value is not None:
                try:
                    return eval(value)
                except (SyntaxError, NameError):
                    return None  # Return None if the value can't be evaluated
            return None  # Return None if the value is None

        def safe_int(value):
            if value is not None:
                try:
                    return int(value)
                except (ValueError, TypeError):
                    return None  # Return None if the value can't be converted
            return None  # Return None if the value is None

        imageNo = row[1] if row[1] is not None else ""
        folder = row[24] if row[24] is not None else ""
        author = row[2] if row[2] is not None else ""
        author_con = f"{int(row[4] * 100)}" if row[4] is not None else ""
        title = row[5] if row[5] is not None else ""
        title_con = f"{int(row[7] * 100)}" if row[7] is not None else ""
        address = row[8] if row[8] is not None else ""
        address_con = f"{int(row[10] * 100)}" if row[10] is not None else ""
        format = row[11] if row[11] is not None else ""
        format_con = f"{int(row[13] * 100)}" if row[13] is not None else ""
        cote = row[14] if row[14] is not None else ""
        cote_con = f"{int(row[16] * 100)}" if row[16] is not None else ""
        point = [
            {
                "coordinates": safe_eval(row[3]),  # Convert string to list
                "text": row[2],
                "confidence": int(row[4]),
            },
            {
                "coordinates": safe_eval(row[6]),  # Convert string to list
                "text": row[5],
                "confidence": safe_int(row[7]),
            },
            {
                "coordinates": safe_eval(row[9]),  # Convert string to list
                "text": row[8],
                "confidence": safe_int(row[10]),
            },
            {
                "coordinates": safe_eval(row[12]),  # Convert string to list
                "text": row[11],
                "confidence": safe_int(row[13]),
            },
            {
                "coordinates": safe_eval(row[15]),  # Convert string to list
                "text": row[14],
                "confidence": safe_int(row[16]),
            },
            # for box in row
        ]
        # Filter out entries with any None value in coordinates, text, or confidence
        filtered_boxes = [
            box
            for box in point
            if box["coordinates"] is not None
            and box["text"]
            and box["confidence"] is not None
        ]
    # total project notices count
    queryCount = f"select count(*) from {table} where proj=?"
    noticeAll = cursor.execute(queryCount, session["proj"])
    countNotices = noticeAll.fetchone()
    AllCount = countNotices[0]

    return render_template(
        "ocr-edit.html",
        imageNo=imageNo,
        folder=folder,
        author=author,
        author_con=author_con,
        title=title,
        title_con=title_con,
        address=address,
        address_con=address_con,
        format=format,
        format_con=format_con,
        cote=cote,
        cote_con=cote_con,
        point=json.dumps(filtered_boxes),
        translations=translations[language],
        lang=language,
        langButton=langButton,
        allcount=AllCount,
    )


@app.route("/get_suggestions", methods=["POST"])
def get_suggestions():
    try:
        data = request.get_json()

        user_input = data.get("user_input", "")

        library = [
            "Abel",
            "Abraham",
            "Achille",
            "Adel",
            "Ademar",
            "Adhemar",
            "Adolf",
            "Adrien",
            "Agénor",
            "Aimé",
            "Alain",
            "Albert",
            "Albertet",
            "Alexandre",
            "Alexis",
            "Alfred",
            "Allain",
            "Alphonse",
            "Alphonse Joseph",
            "Alvin",
            "Amable",
            "Amédée",
            "Anatole",
            "André",
            "André-Marie",
            "Ange",
            "Anicet",
            "Antoine",
            "Anton",
            "Antonin",
            "Armand",
            "Arnaud",
            "Arnaut",
            "Arsène",
            "Arthur",
            "Aubin",
            "Auguste",
            "Augustin",
            "Aurèle",
            "Aurélien",
            "Aymard",
            "Aymeric",
            "Balthazar",
            "Baptiste",
            "Barthélemy",
            "Bastien",
            "Baudouin",
            "Benjamin",
            "Benoît",
            "Bernard",
            "Bertrand",
            "Blanchard",
            "Bruno",
            "Calixte",
            "Calvin",
            "Camille",
            "Camille Alphonse",
            "Candide",
            "Carolus",
            "Cédric",
            "Celestin",
            "Cesar",
            "Charle",
            "Charles",
            "Charles-Édouard",
            "Charlot",
            "Christian",
            "Christophe",
            "Claude",
            "Claude-Henri",
            "Clement",
            "Clovis",
            "Constant",
            "Cyrille",
            "Damien",
            "Daniel",
            "Danton",
            "David",
            "Delbert",
            "Denis",
            "Désiré",
            "Didier",
            "Dieudonné",
            "Dominique",
            "Donatien",
            "Edgar",
            "Edgard",
            "Edmé",
            "Edmond",
            "Édouard",
            "Élie",
            "Élisée",
            "Émile",
            "Émilien",
            "Emmanuel",
            "Éric",
            "Ernest",
            "Erwan",
            "Étienne",
            "Fabien",
            "Fabrice",
            "Félicien",
            "Felix",
            "Ferdinand",
            "Fernand",
            "Flavien",
            "Fleury",
            "Florent",
            "Florian",
            "Florimond",
            "Francis",
            "Franck",
            "François",
            "François-Marie",
            "François-Xavier",
            "Frank",
            "Frédéric",
            "Fulbert",
            "Fulgence",
            "Gabriel",
            "Gaël",
            "Gaillard",
            "Gaspard",
            "Gaston",
            "Gédéon",
            "Geoffrey",
            "Georges",
            "Gérald",
            "Gérard",
            "Gerbaud",
            "Germain",
            "Ghislain",
            "Gilbert",
            "Gilles",
            "Godfrey",
            "Grégoire",
            "Guillaume",
            "Guy",
            "Hadrien",
            "Harold",
            "Hector",
            "Henri",
            "Herbert",
            "Hervé",
            "Hilaire",
            "Hippolyte",
            "Honoré",
            "Horace",
            "Hubert",
            "Hugo",
            "Hugues",
            "Hyacinthe",
            "Ignace",
            "Isidore",
            "Ivo",
            "Jacquelin",
            "Jacques",
            "Jacques-Désiré",
            "Jacques-Marie",
            "Jacquet",
            "James",
            "Jean",
            "Jean-André",
            "Jean-Antoine",
            "Jean-Baptiste",
            "Jean-Baptiste-Alphonse",
            "Jean-Bernard",
            "Jean-Charles",
            "Jean-Christophe",
            "Jean-Claude",
            "Jean-Denis",
            "Jean-Emmanuel",
            "Jean-Étienne",
            "Jean-François",
            "Jean-Guy",
            "Jean-Henri",
            "Jean-Jacques",
            "Jean-Joseph",
            "Jean-Julien",
            "Jean-Louis",
            "Jean-Luc",
            "Jean-Marc",
            "Jean-Marie",
            "Jean-Martin",
            "Jean-Michel",
            "Jean-Nicolas",
            "Jean-Noël",
            "Jean-Pascal",
            "Jean-Paul",
            "Jean-Philippe",
            "Jean-Pierre",
            "Jean-René",
            "Jean-Robert",
            "Jean-Sébastien",
            "Jean-Yves",
            "Jérémie",
            "Jérémy",
            "Jerome",
            "Joël",
            "Jonathan",
            "Jules",
            "Julien",
            "Julien-Joseph",
            "Just",
            "Justin",
            "Lauren",
            "Laurence",
            "Laurent",
            "Lazare",
            "Léandre",
            "Léo",
            "Leon",
            "Léon",
            "Loïc",
            "Lothaire",
            "Louis",
            "Louis-Alphonse",
            "Louis-Étienne",
            "Loup",
            "Luc",
            "Lucas",
            "Lucien",
            "Ludo",
            "Ludovic",
            "Mainard",
            "Manuel",
            "Marc",
            "Marc-André",
            "Marcel",
            "Marcellin",
            "Marco",
            "Mario",
            "Martin",
            "Mathieu",
            "Matthias",
            "Matthieu",
            "Maurice",
            "Maurille",
            "Maxence",
            "Maxime",
            "Maximilien",
            "Maynard",
            "Medard",
            "Melvin",
            "Michel",
            "Michel-Ange",
            "Mikaël",
            "Moise",
            "Napoleon",
            "Nicodème",
            "Nicolas",
            "Noe",
            "Noel",
            "Norbert",
            "Odilon",
            "Olivier",
            "Pacôme",
            "Pascal",
            "Patrice",
            "Patrick",
            "Paul",
            "Paul-Antoine",
            "Paul-Louis",
            "Paul-Marie",
            "Philibert",
            "Philippe",
            "Phillippe",
            "Pierre",
            "Pierre-Édouard",
            "Pierre-Julien",
            "Pierre-Marie",
            "Pierre-Paul",
            "Pierre-Simon",
            "Pierre-Yves",
            "Pierrick",
            "Profiat",
            "Prosper",
            "Quentin",
            "Raimond",
            "Rainier",
            "Raoul",
            "Raphael",
            "Raymond",
            "Réal",
            "Réjean",
            "Rémy",
            "René",
            "Reynald",
            "Robert",
            "Roger",
            "Roland",
            "Romain",
            "Roman",
            "Roméo",
            "Romuald",
            "Salome",
            "Samuel",
            "Sébastien",
            "Ségolène",
            "Seraphin",
            "Servais",
            "Severin",
            "Simon",
            "Stéphane",
            "Stéphen",
            "Sylvain",
            "Sylvestre",
            "Tancrède",
            "Théodore",
            "Théodule",
            "Thibaut",
            "Thierry",
            "Thomas",
            "Timothée",
            "Titouan",
            "Toussaint",
            "Ulysse",
            "Valentin",
            "Vianney",
            "Victor",
            "Vincent",
            "Virgile",
            "Xavier",
            "Yacine",
            "Yann",
            "Yannick",
            "Yvan",
            "Yves",
            "Yvon",
            "Zacharie",
        ]

        # Get a list of suggestions with their scores
        suggestions_with_scores = process.extract(user_input, library, limit=5)

        # Filter out suggestions with a score below a certain threshold (e.g., 70)
        filtered_suggestions = [
            suggestion for suggestion, score in suggestions_with_scores if score >= 70
        ]

        return jsonify({"suggestions": filtered_suggestions})

    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/form-edit", methods=["GET", "POST"])
def edit_form():
    chkTestVlaue = session.get("chk_test")
    if chkTestVlaue == "1":
        addParam = " AND chkTest='1'"
    elif chkTestVlaue == "2": 
        addParam = " AND Ano_med_send ='1'"  
    else: 
        addParam=""
    # Establish database connection
    proj_type = session.get("projtype")
    proj = session.get("proj", "")    
    language = request.args.get("lang", session["lang"])
    proj_type = session.get("projtype")
    proj = session.get("proj", "")
    total_records=session.get("total_records","")
    if proj_type == "unimarc":
        field = "u990_b"
        field2 = "u990_c"
        table = "dbo._unimarc"
    else:
        field = "z990_b"
        field2 = "z990_c"
        table = "dbo._intermarc"
    # language = request.args.get("lang", app.config["DEFAULT_LANGUAGE"])
    if language not in app.config["LANGUAGES"]:
        language = app.config["DEFAULT_LANGUAGE"]
        session.pop("lang")
        session["lang"] = language
    # language Button
    en_flag_url = url_for('static', filename='assets/images/us_flag.png')
    fr_flag_url = url_for('static', filename='assets/images/fr_flag.png')   

    if language == "fr":
        langButton = f"""<button class="btn btn-primary dropdown-toggle" type="button" id="dropdownMenuButton" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                             <img class="form-control-sm" src="{fr_flag_url}">French
                            </button>
                             <div class="dropdown-menu" aria-labelledby="dropdownMenuButton">
                                <a class="dropdown-item" href="?lang=en"><img class="form-control-sm" src="{en_flag_url}">English</a>
                             </div>"""
    else:
        langButton = f"""<button class="btn btn-primary dropdown-toggle" type="button" id="dropdownMenuButton" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                             <img class="form-control-sm" src="{en_flag_url}">English
                            </button>
                             <div class="dropdown-menu" aria-labelledby="dropdownMenuButton">
                                <a class="dropdown-item" href="?lang=fr"><img class="form-control-sm" src="{fr_flag_url}">French</a>
                             </div>"""
    listpage_no = session.get("listpage_no", 1)
    cnxn = pyodbc.connect(conn_str)
    cursor = cnxn.cursor()
    if not session["name"]:
        return index()
    try:
        # Fetching page number from query params with a default value of 1
        list_no = int(request.args.get("list", 1))
        list_prev = list_no - 1
        list_next = list_no + 1
        sort = session.get("sort", "order by z001_x0")
        sortype = session.get("sortype", "ASC")
        params = session.get("params", [proj])
        # params = params.append(list_no)
        # Prepare SQL query using session values with safe parameter insertion
        # Ensure params is a list

        queryCount = f"select count(*) from {table} where proj=?"
        noticeAll = cursor.execute(queryCount, session["proj"])
        countNotices = noticeAll.fetchone()
        AllCount = countNotices[0]
        
        
        queryCountNextButton = f"select count(*) from {table} where proj=? {addParam}" 
        nextAllCount = cursor.execute(queryCountNextButton, session["proj"])
        nextNotices = nextAllCount.fetchone()
        allNextCount = nextNotices[0]
        print(allNextCount)
        if not isinstance(params, list):
            params = []
        params.append(list_no)

        sql_query2 = session.get(
            "sql_query2",
            f"""
            SELECT a.*, CASE WHEN b.book_id IS NOT NULL THEN 1 ELSE 0 END AS bookmarked, 
            Row_Number() Over ({sort} {sortype}) AS Rows 
            FROM {table} a
            LEFT JOIN bookmark_notices b
                ON b.book_id=a.ID and b.[user]='{session.get("name")}' and  b.proj='{session.get("proj")}'
            WHERE a.Proj = ? {addParam}
        """.format(
                sort=sort, sortype=sortype
            ),
        )
        # print(sql_query2)
        # print(AllCount)
        query = f"""
            WITH object_rows AS ({sql_query2})
            SELECT * FROM object_rows WHERE Rows = ? {addParam}
        """        
        cursor.execute(query, params)
        
        row = cursor.fetchone()
        #if(list_no)
        if row:
            
            # Map columns by name using cursor.description
            columns = [desc[0] for desc in cursor.description]
            row_dict = dict(zip(columns, row))

            # Get the bookmarked status
            is_bookmarked = row_dict.get("bookmarked", 0)
            checked_attr = "checked" if is_bookmarked == 1 else ""
            
            # Map row values to variables
            idValue = int(row[0]) if row[0] is not None else ""
            recid = int(row[1]) if row[1] is not None else ""
            proj = str(row[4]) if row[4] is not None else ""
            dossier = row[5] if row[5] is not None else ""
            image = row[2] if row[2] is not None else ""
            traitement = row[3] if row[3] is not None else ""
            qcote = row[13] if row[13] is not None else ""
            txtBrut = row[11] if row[11] is not None else ""
            ano = row[109] if row[109] is not None else ""
            anscode = row[110] if row[110] is not None else ""
            anocode = row[125] if row[125] is not None else ""
            anoanswer = row[126] if row[126] is not None else ""
            readable = row[119] if row[119] is not None else ""
            # Use regex to find all URLs
            site_url = ""

            urls = []
            if readable:
                urls = re.findall(r"(https?://\S+)", readable)

            if urls:
                for url in urls:
                    site_url = url
                    # If you want to process only the first URL, you can break the loop
                    break

            # api_key = "a77d51086fb7455dbc9b8284573e7feb"
            # endpoint = "https://aurexusformprocessocr.cognitiveservices.azure.com/"

            # Initialize the Form Recognizer client
            # document_analysis_client = DocumentAnalysisClient(
            #     endpoint=endpoint, credential=AzureKeyCredential(api_key)
            # )

            # response = requests.get(f"https://aurexus.net/auximages/CAEN/{dossier}/{image}")
            # image_data = response.content

            # Analyze the image
            # poller = document_analysis_client.begin_analyze_document(
            #     "prebuilt-document", document=image_data
            # )
            # result = poller.result()

            # Print the extracted content
            # for page in result.pages:
            #     for line in page.lines:
            #         print(line.content)

            # Render the template with the fetched data
            if total_records == list_no:
                disabled = "disabled"
            else:
                disabled = ""
                   
            proj = session["proj"]
            return render_template(
                "form-edit.html",
                proj=proj,
                idValue=idValue,
                recid=recid,
                dossier=dossier,
                image=image,
                traitement=traitement,
                qcote=qcote,
                txtBrut=txtBrut,
                ano=ano,
                anoanswer=anoanswer,
                anscode=anscode,
                anocode=anocode,
                readable=readable,
                image_link=f"https://aurexus.net/auximages/{proj}/{dossier}/{image}",
                img_link=f"https://aurexus.net/auximages/{proj}/{dossier}/",
                listpage_no=listpage_no,
                list_prev=list_prev,
                list_next=list_next,
                site_url=site_url,
                translations=translations[language],
                lang=language,
                langButton=langButton,
                allcount=AllCount,
                disable=disabled,
                checked_attr=checked_attr,
                allNextCount=allNextCount,
            )
        else:
            # Handle case where no row is found
            return "No data found for the specified page number.", 404

    except Exception as e:
        # Handle any other exceptions
        return str(e), 500

    finally:
        # Ensure the connection is closed
        cursor.close()
        cnxn.close()

#Save Response 
@app.route('/save_data', methods=['POST'])
def save_data():
    try:
        value = request.json.get('value')  # raw SQL query
        rec_id = request.json.get('Id')    # ID to use in the update

        projtype = session.get("projtype", "")
        projlist = session.get("proj", "")        
        
        if projtype == "unimarc":
            field = "u990_b"
            field2 = "u990_c"
            table = "dbo._unimarc"
        else:
            field = "z990_b"
            field2 = "z990_c"
            table = "dbo._intermarc"
        
        # Connect to database
        cnxn = pyodbc.connect(conn_str)
        cursor = cnxn.cursor()

        # Run incoming query (already constructed on frontend)
        if value:
            cursor.execute(value)

        # Clean and update the answer field 
        #query = f"""UPDATE {table} SET Ano_AnsCode = ?, Ano_Answer = ? WHERE ID = ?"""
        #cursor.execute(query, (anocode, anscode, ID))

        cnxn.commit()
        cursor.close()
        cnxn.close()

        return jsonify({'status': 1, 'message': 'Successfully Saved.'})
    
    except Exception as e:
        print("❌ Update Error:", e)
        return jsonify({'status': 0, 'message': 'Form submission failed, please try again.', 'error': str(e)})






#Image Prestagging, Next Previous Images Views
@app.route('/api/images/<folder>/<image>')
def get_image_prestageList(folder, image):
    cnxn = pyodbc.connect(conn_str)
    cursor = cnxn.cursor()
    proj = session.get("proj", "")  # Must be set earlier

    query = """
        WITH ordered_images AS (
            SELECT image,
                   ROW_NUMBER() OVER (ORDER BY image) AS row_num
            FROM _imageScan
            WHERE folder = ? AND proj = ?
        ),
        target_row AS (
            SELECT row_num FROM ordered_images WHERE image = ?
        )
        SELECT image
        FROM ordered_images
        WHERE row_num BETWEEN 
              (SELECT row_num FROM target_row) - 5 AND 
              (SELECT row_num FROM target_row) + 5
        ORDER BY row_num
    """

    try:
        result = cursor.execute(query, (folder, proj, image)).fetchall()
        images = [row[0] for row in result]  # Access first column (image)
        return jsonify(images)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        cnxn.close()
        
        
#CSV Download      
    
@app.route('/download_csv', methods=['GET'])
def download_csv():
    chkTestVlaue = session.get("chk_test")
    if chkTestVlaue == "1":
        addParam = " AND chkTest='1'"
    elif chkTestVlaue == "2":
        addParam = " AND Ano_med_send ='1'"
    else:
        addParam = ""

    cnxn = pyodbc.connect(conn_str)
    cursor = cnxn.cursor()
    proj_type = session.get("projtype")
    proj = session.get("proj", "")
    sort = session.get("sort", "order by z001_x0")
    sortype = session.get("sortype", "ASC")
    

    if proj_type == "unimarc":
        field = "u990_b"
        field2 = "u990_c"
        table = "dbo._unimarc"
    else:
        field = "z990_b"
        field2 = "z990_c"
        table = "dbo._intermarc"
    sql_query = session.get(
            "sql_query", f"SELECT COUNT(*) FROM {table} WHERE Proj = ?  {addParam}"
        )
   
    if not sql_query:
        return "Filter session not found. Please apply filters before downloading CSV.", 400

    # Replace COUNT with full query
    sql_query = sql_query.replace("SELECT COUNT(*)", f"""SELECT ROW_NUMBER() OVER ({sort} {sortype}) AS ID,
                                                        ID AS RID, Lot, CONCAT(folder, '.') AS folder, z001_x0, traitement, qcote, 
                                                        Deriv_Id, {field}, {field2}, notice_readable, Ano_AnsCode, Ano_Answer""")
    params = session.get("params", [proj])
    cursor.execute(sql_query, params)

    def generate():
        # Add UTF-8 BOM
        yield '\ufeff'
        writer = csv.writer(io.StringIO(), delimiter=',')
        header = ["ID", "RID", "Lot", "Dossier", "Image", "Traitement", "Cote", "Deriv_Id", "AnoCode", "AnoMsg", "Notice", "AnoAnswerCode", "AnoAnswer"]
        yield ','.join(header) + '\n'

        while True:
            rows = cursor.fetchmany(10000)
            if not rows:
                break
            for row in rows:
                buffer = io.StringIO()
                writer = csv.writer(buffer)
                writer.writerow(row)
                yield buffer.getvalue()

    return Response(
        stream_with_context(generate()),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=AUREXUS_EXPORT_{proj}.csv'
        }
    )

# Serve HTML file for CSV upload
@app.route('/upload')
def upload_form():
    language = request.args.get("lang", session["lang"])
    return render_template('upload.html',lang=language,translations=translations[language])

# Update database using data from CSV
@app.route('/update-data', methods=['POST'])
def update_data():
    if 'file' not in request.files:
        return "No file part", 400

    file = request.files['file']

    if file.filename == '':
        return "No selected file", 400

    if file and file.filename.endswith('.csv'):
        # Read the CSV file into a DataFrame
        df = pd.read_csv(file)   

        try:
            cnxn = pyodbc.connect(conn_str)
            cursor = cnxn.cursor()

            # Assuming CSV has columns 'column1', 'column2', and 'id' matching your table structure
            for index, row in df.iterrows():
                cursor.execute('''
                    UPDATE your_table
                    SET column1 = ?, column2 = ?
                    WHERE id = ?
                ''', row['column1'], row['column2'], row['id'])

            # Commit the transaction
            cnxn.commit()

        except pyodbc.Error as e:
            # If any error occurs, return error message and status code
            return f"Database error: {e}", 500

        finally:
            # Ensure the cursor and connection are properly closed
            cursor.close()
            cnxn.close()

        return "Data updated successfully!", 200

    return "Invalid file format. Please upload a CSV.", 400

@app.route("/analyze_image", methods=["POST"])
def analyze_image():
    data = request.json
    image = data.get("image")

    if not image:
        return jsonify({"error": "dossier and image are required"}), 400

    try:
        response = requests.get(image)
        image_data = response.content

        # Analyze the image
        poller = document_analysis_client.begin_analyze_document(
            "prebuilt-document", document=image_data
        )
        result = poller.result()

        # Extract and return the content
        extracted_content = []
        for page in result.pages:
            for line in page.lines:
                extracted_content.append(line.content)

        return jsonify({"content": extracted_content})

    except Exception as e:
        return jsonify({"error": str(e)}), 500



# Project Management APP Starts Here (UPID) -------------------------------------------#
@app.route("/login2")
def loginProject():
    return render_template("login2.html")

@app.route("/projLogin", methods=["POST", "GET"])
def projLogin():
    if request.method == "POST":
        name = request.form.get("user")
        password = request.form.get("pass")
        cnxn = pyodbc.connect(conn_str)
        cursor = cnxn.cursor()
        cursor.execute(
            "select * from dbo.User_table where Username=? and Password=?",
            (name, password),
        )

        row = cursor.fetchone()

        if row:
            session["Role"] = row.Role
            session["proUsername"] = name
            session["team"] = row.Team
            return redirect(url_for("projects"))  # Redirect to the projects route
        else:
            return render_template(
                "login2.html", message="Please Check the Credential's"
            )
    return render_template("login2.html")

@app.route("/projects")
def projects():
    cnxn = pyodbc.connect(conn_str)
    cursor = cnxn.cursor()
    # session.pop('name', None)
    role=session.get("Role","")
    if role!="Admin":
        disable="disabled"
    else:
        disable=""
    query = f"select * from aurexUPID order by ID desc"
    cursor.execute(query)
    recordsPrint = cursor.fetchall()
    html_content = ""
    if recordsPrint:
        for row in recordsPrint:           
            row_dict = dict(zip([column[0] for column in cursor.description], row))
            # Determine if the row should be editable or not based on UPID
            value_upid = row_dict.get("UPID", "")
            chkWord = "" if role == "Admin" or session["team"] in value_upid else "disabled"  # Enable or disable edit button based on UPID
            editCell = "class='edit'" if role == "Admin" or session["team"] in value_upid else ""
            html_content += "<tr>"
            for column_name in [
                "ID",
                "UPID",
                "Project Name",
                "Start Date",
                "Client Name",
                "Short Description",
                "Geo Location",
                "Project Folder Link",
                "Tracksheet Link",
                "Other Link",
                
            ]:
                # Check for None and replace with an empty string
                value = row_dict.get(column_name, "")
                    
                # Explicitly check if the value is None and replace it with an empty string
                if value is None or value == "":
                    value = "-"
                if column_name == "UPID":
                    html_content += f"<td ><div {editCell} id='[{column_name}]_{row_dict.get('ID', '')} '><b class=''>{value}</b></div></td>"
                elif column_name == "ID":
                    html_content += f"<td hidden>{value}</td>"
                elif column_name == "Project Folder Link":
                    if value != "-":
                        html_content += f"<td ><div {editCell} id='[{column_name}]_{row_dict.get('ID', '')}' data-original-url='{value}'><a href='{value}' target='_blank' class='btn badge badge-light border border-primary {chkWord}' data-original-url='{value}'>Project Link</a></div></td>"
                    else:
                        html_content += f"<td ><div {editCell}' id='[{column_name}]_{row_dict.get('ID', '')}' data-original-url='{value}'>{value}</div></td>"
                elif column_name == "Tracksheet Link":
                    if value != "-":
                        html_content += f"<td ><div {editCell} id='[{column_name}]_{row_dict.get('ID', '')}' data-original-url='{value}'><a href='{value}' target='_blank' class='btn badge badge-light border border-primary {chkWord}'>Tracksheet Link</a></div></td>"
                    else:
                        html_content += f"<td ><div {editCell} id='[{column_name}]_{row_dict.get('ID', '')}' data-original-url='{value}'>{value}</div></td>"
                elif column_name == "Other Link":
                    if value != "-":
                        html_content += f"<td ><div  {editCell} id='[{column_name}]_{row_dict.get('ID', '')}' data-original-url='{value}'><a href='{value}' target='_blank' class='btn badge badge-light border border-primary {chkWord}'>Other Link</a></div></td>"
                    else:
                        html_content += f"<td ><div  {editCell} id='[{column_name}]_{row_dict.get('ID', '')}' data-original-url='{value}'>{value}</div></td>"
                else:
                    html_content += f"<td ><div {editCell} id='[{column_name}]_{row_dict.get('ID', '')} '>{value}</div></td>"
            html_content += f"""
                <td style="width:83px;">
                    <a href='{url_for('addprojects', id=row_dict.get('ID', ''))}'                     
                    class='btn btn-primary btn-sm btn-flat edit-btn shadow {chkWord}'
                    data-id='{row_dict.get('ID', '')}'
                    data-upid='{row_dict.get('UPID', '')}'
                    data-project-name='{row_dict.get('Project Name', '')}'
                    data-start-date='{row_dict.get('Start Date', '')}'
                    data-client-name='{row_dict.get('Client Name', '')}'
                    data-short-description='{row_dict.get('Short Description', '')}'
                    data-project-folder='{row_dict.get('Project Folder Link', '')}'
                    data-tracksheet-link='{row_dict.get('Tracksheet Link', '')}'
                    data-other-link='{row_dict.get('Other Link', '')}' >
                    <i class='fa fa-solid fa-edit' ></i>
                    </a>
                    <button class="btn btn-danger btn-flat btn-sm delete-btn" data-id="{row_dict.get('ID', '')}" {disable}><i class='fa fa-solid fa-trash'></i></button>
                </td>
                """
            html_content += "</tr>"
    return render_template("projects.html", html_content=html_content)

@app.route("/tabledashboard")
def tableDashboard():
    cnxn = pyodbc.connect(conn_str)
    cursor = cnxn.cursor()
    project = cursor.execute("select count(*) from aurexUPID")
    currentProject = project.fetchone()[0]
    return render_template("tableDashboard.html",currentProject=currentProject)

@app.route('/export')
def export():
    # Get the search keyword from the request
    keyword = request.args.get("keyword", "")

    # Connect to the database
    cnxn = pyodbc.connect(conn_str)
    cursor = cnxn.cursor()

    # Query to search for projects matching the keyword
    query = """
        SELECT * FROM aurexUPID 
        WHERE [Project Name] LIKE ? OR [Short Description] LIKE ? OR UPID LIKE ?
        ORDER BY ID DESC
    """
    cursor.execute(query, ("%" + keyword + "%", "%" + keyword + "%", "%" + keyword + "%"))
    records = cursor.fetchall()

    # Get column names
    columns = [column[0] for column in cursor.description]

    # Create a CSV file
    csv_file = StringIO()
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(columns)
    for row in records:
        csv_writer.writerow(row)

    # Close the database connection
    cursor.close()
    cnxn.close()

    # Create a response with the CSV file
    response = send_file(
        BytesIO(csv_file.getvalue().encode('utf-8')),
        mimetype="text/csv",
        as_attachment=True,
        download_name="export.csv"
    )
    return response

@app.route("/search")
def search():
    # Get the search keyword from the AJAX request
    keyword = request.args.get("keyword", "")

    # Connect to the database
    cnxn = pyodbc.connect(conn_str)
    cursor = cnxn.cursor()
    role=session.get("Role","")
    if role!="Admin":
        disable="disabled"
    else:
        disable = ""
    # Query to search for projects matching the keyword in either "Project Name" or "Short Description"
    query = """
        SELECT * FROM aurexUPID 
        WHERE [Project Name] LIKE ? OR [Short Description] LIKE ? OR UPID LIKE ?
        ORDER BY ID DESC
    """
    cursor.execute(
        query, ("%" + keyword + "%", "%" + keyword + "%", "%" + keyword + "%")
    )
    records = cursor.fetchall()

    # Prepare HTML content for the table rows
    html_content = ""
    for row in records:
        # Determine if the row should be editable or not based on UPID
        
        row_dict = dict(zip([column[0] for column in cursor.description], row))
        value_upid = row_dict.get("UPID", "")
        chkWord = "" if role == "Admin" or session["team"] in value_upid else "disabled"  # Enable or disable edit button based on UPID
        editCell = "class='edit'" if role == "Admin" or session["team"] in value_upid else ""
        html_content += "<tr>"
        for column_name in [
            "ID",
            "UPID",
            "Project Name",
            "Start Date",
            "Client Name",
            "Short Description",
            "Project Folder Link",
            "Tracksheet Link",
            "Other Link",
        ]:
            # Check for None and replace with an empty string
            value = row_dict.get(column_name, "")
            # Explicitly check if the value is None and replace it with an empty string
            if value is None:
                value = "-"
            if column_name == "UPID":
                html_content += f"<td ><div  {editCell} id='[{column_name}]_{row_dict.get('ID', '')} '><b class=''>{value}</b></div></td>"
            elif column_name == "ID":
                html_content += f"<td hidden>{value}</td>"
            elif column_name == "Project Folder Link":
                if value != "-":
                    html_content += f"<td ><div  {editCell} id='[{column_name}]_{row_dict.get('ID', '')}' data-original-url='{value}'><a href='{value}' target='_blank' class='btn badge badge-light border border-primary {chkWord}' data-original-url='{value}'>Project Link</a></div></td>"
                else:
                    html_content += f"<td ><div  {editCell} id='[{column_name}]_{row_dict.get('ID', '')}' data-original-url='{value}'>{value}</div></td>"
            elif column_name == "Tracksheet Link":
                if value != "-":
                    html_content += f"<td ><div  {editCell} id='[{column_name}]_{row_dict.get('ID', '')}' data-original-url='{value}'><a href='{value}' target='_blank' class='btn badge badge-light border border-primary {chkWord}'>Tracksheet Link</a></div></td>"
                else:
                    html_content += f"<td ><div  {editCell} id='[{column_name}]_{row_dict.get('ID', '')}' data-original-url='{value}'>{value}</div></td>"
            elif column_name == "Other Link":
                if value != "-" or value == "":
                    html_content += f"<td ><div  {editCell} id='[{column_name}]_{row_dict.get('ID', '')}' data-original-url='{value}'><a href='{value}' target='_blank' class='btn badge badge-light border border-primary {chkWord}'>Other Link</a></div></td>"
                else:
                    html_content += f"<td ><div  {editCell} id='[{column_name}]_{row_dict.get('ID', '')}' data-original-url='{value}'>{value}</div></td>"
            else:
                html_content += f"<td ><div  {editCell} id='[{column_name}]_{row_dict.get('ID', '')} '>{value}</div></td>"

        html_content += f"""
            <td style="width:83px;">
                <a href='{url_for('addprojects', id=row_dict.get('ID', ''))}'                   
                   class='btn btn-primary btn-sm btn-flat edit-btn shadow {chkWord}'
                   data-id='{row_dict.get('ID', '')}'
                   data-upid='{row_dict.get('UPID', '')}'
                   data-project-name='{row_dict.get('Project Name', '')}'
                   data-start-date='{row_dict.get('Start Date', '')}'
                   data-client-name='{row_dict.get('Client Name', '')}'
                   data-short-description='{row_dict.get('Short Description', '')}'
                   data-project-folder='{row_dict.get('Project Folder Link', '')}'
                   data-tracksheet-link='{row_dict.get('Tracksheet Link', '')}'
                   data-other-link='{row_dict.get('Other Link', '')}' >
                   <i class='fa fa-solid fa-edit'></i>
                </a>
                <button class="btn btn-danger btn-flat btn-sm delete-btn" data-id="{row_dict.get('ID', '')}" {disable}><i class='fa fa-solid fa-trash'></i></button>
            </td>
            """
        html_content += "</tr>"

    # Close the database connection
    cursor.close()
    cnxn.close()

    # Return the HTML content to the client
    return jsonify(html_content=html_content)

@app.route("/update", methods=["POST"])
def update_record():
    # Connect to the database
    cnxn = pyodbc.connect(conn_str)
    # Retrieve POST parameters
    field = request.form.get("field")
    value = request.form.get("value")
    editid = request.form.get("id")

    if field and value and editid:
        # Use parameterized query to prevent SQL injection
        query = f"UPDATE aurexUPID SET {field} = ? WHERE ID = ?"
        params = (value, editid)
        try:
            with cnxn.cursor() as cursor:
                cursor.execute(query, params)
                cnxn.commit()
            # Successful update
            return jsonify(success=1)
        except Exception as e:
            print(f"Error: {e}")
            # Error in update
            return jsonify(success=0)
    else:
        # Invalid or missing parameters
        return jsonify(success=0)

@app.route("/deleteProject", methods=["POST"])
def deleteProject():
    project_id = request.form.get("id")

    # Open database connection and delete the row
    cnxn = pyodbc.connect(conn_str)
    cursor = cnxn.cursor()

    # Execute delete query
    cursor.execute("DELETE FROM aurexUPID WHERE ID = ?", (project_id,))
    cnxn.commit()  # Commit the transaction

    # Check if the delete was successful
    if cursor.rowcount > 0:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False})

@app.route("/add_project", methods=['GET', 'POST'])
@app.route("/add_project/<int:id>", methods=['GET', 'POST'])
def add_project(id=None):
    # Connect to the database
    cnxn = pyodbc.connect(conn_str)

    # Retrieve form data
    upid = request.form.get("upid")
    project_name = request.form.get("project_name")
    start_date = request.form.get("start_date")
    client_name = request.form.get("client_name")
    short_description = request.form.get("short_description")
    project_folder_link = request.form.get("project_folder_link")
    tracksheet_link = request.form.get("tracksheet_link")
    other_link = request.form.get("other_link")
    geo_location = request.form.get("geo_location")

    # Check required fields
    if not upid or not project_name or not client_name:
        return jsonify(
            success=0,
            message="UPID, Project Name, and Client Name are required fields.",
        )
    if id is None:
        # Prepare the SQL query for inserting data
        query = """
        INSERT INTO aurexUPID (UPID, [Project Name], [Start Date], [Client Name], [Short Description], [Project Folder Link], [Tracksheet Link], [Other Link],[Geo Location])
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            upid,
            project_name,
            start_date,
            client_name,
            short_description,
            project_folder_link,
            tracksheet_link,
            other_link,
            geo_location,
        )
    else:
          # Update existing project
            query = """
            UPDATE aurexUPID
            SET UPID = ?, [Project Name] = ?, [Start Date] = ?, [Client Name] = ?, [Short Description] = ?, [Project Folder Link] = ?, [Tracksheet Link] = ?, [Other Link] = ?, [Geo Location]=?
            WHERE ID = ?
            """
            params = (
                upid,
                project_name,
                start_date,
                client_name,
                short_description,
                project_folder_link,
                tracksheet_link,
                other_link,
                geo_location,
                id
            )

    try:
        with cnxn.cursor() as cursor:
            # Execute the parameterized query
            cursor.execute(query, params)
            cnxn.commit()
        # Successful insertion
        # return jsonify(success=1, message="Project added successfully.")
        return redirect(url_for("projects"))
    except Exception as e:
        print(f"Error: {e}")
        # Error in insertion
        return jsonify(success=0, message="Failed to add project.")

@app.route("/checkExist", methods=["POST"])
def checkExist():

    # Connect to the database
    cnxn = pyodbc.connect(conn_str)
    # Get Value From POST
    value = request.form.get("value", "")
    query = f"select * from aurexUPID where UPID=? or [Project Name]=?"
    params = (value, value)
    cursor.execute(query, params)
    records = cursor.fetchall()
    if len(records) >= 1:
        return jsonify(success=1)
    else:
        return jsonify(success=0)

@app.route("/autocomplete_projects", methods=["GET","POST"])
def autocomplete_projects():
    term = request.args.get("term", "")
    
    try:
        # Connect to the database
        cnxn = pyodbc.connect(conn_str)
        cursor = cnxn.cursor()
        
        # Query to get matching project names
        query = """
            SELECT CONCAT([Project Name], ' | ', UPID) AS project_info 
            FROM aurexUPID 
            WHERE [Project Name] LIKE ? OR UPID LIKE ?
        """
        cursor.execute(
            query,
            (
                "%" + term + "%",
                "%" + term + "%",
            ),
        )

        # Fetch results and handle empty case
        rows = cursor.fetchall()
        if rows:
            projects = [row[0] for row in rows]  # List of project names
        else:
            projects = []

        # Close the cursor and connection
        cursor.close()
        cnxn.close()

        # Return the list as JSON
        return jsonify(projects)
    
    except pyodbc.Error as e:
        # Log the error and return a server error response
        app.logger.error(f"Database error: {e}")
        return jsonify({"error": "Internal server error"}), 500
    
    except Exception as e:
        # Catch any other exceptions
        app.logger.error(f"Unexpected error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/addprojects", methods=['GET'])
@app.route("/addprojects/<int:id>", methods=['GET'])
def addprojects(id=None):
    # Connect to the database
    cnxn = pyodbc.connect(conn_str)
    cursor = cnxn.cursor()

    if id:
        query = "select * from aurexUPID where ID=?"
        cursor.execute(query,id)        
        proj_info = cursor.fetchone()
        if not proj_info:
            return "Project not found", 404
        # Render template with project details for editing
        return render_template("add_project.html", proj_info = proj_info, edit = True)
    else:
        return render_template("add_project.html", edit = False)

@app.route("/dbProjectTable")
def dbProjectTable():
    return render_template("dbTableCreation.html")
        
@app.route("/checkyolo")
def checkyolo():
    image_url = request.args.get('image_url', '')
    extracted_text = request.args.get('extracted_text', '')  # Ensure it gets the text
    db_txt = request.args.get('db_txt', '')  # Ensure it gets the text
    final_text=urllib.parse.unquote(extracted_text)
    db_text_final = urllib.parse.unquote(db_txt)
    return render_template("yolotest.html", image_url=image_url, extracted_text=final_text, db_txt=db_text_final)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part'
    file = request.files['file']
    if file.filename == '':
        return 'No selected file'
    if file:
        image = Image.open(file)
        image = np.array(image)

        # Run inference on the image
        results = model(image)

        # Collect detected objects to ensure no duplicate plotting
        detected_objects = []

        # Iterate through the detected objects
        for result in results:
            boxes = result.boxes.xyxy.cpu().numpy()  # Get bounding boxes
            confidences = result.boxes.conf.cpu().numpy()  # Get confidence scores
            class_ids = result.boxes.cls.cpu().numpy()  # Get class IDs

            for box, confidence, class_id in zip(boxes, confidences, class_ids):
                x1, y1, x2, y2 = map(int, box)
                detected_objects.append((class_id, x1, y1, x2, y2, confidence))
                
        filtered_texts = {}  # Dictionary for extracted texts
        extracted_texts = []
        
        # Load dataset from CSV
        csv_path = "dataset.csv"  
        df = pd.read_csv(csv_path, dtype=str, encoding='ISO-8859-1')

        # Process detected objects
        for class_id, x1, y1, x2, y2, confidence in detected_objects:
            # Draw bounding box
            cv2.rectangle(image, (x1, y1), (x2, y2), (255, 0, 0), 2)

            # Label the bounding box
            label = f"Class {class_id} ({confidence:.2f})"
            cv2.putText(image, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

            # Extract and preprocess ROI for OCR
            roi = image[y1:y2, x1:x2]
            gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            gray_roi = cv2.threshold(gray_roi, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
            gray_roi = cv2.medianBlur(gray_roi, 3)

            # Use EasyOCR for text extraction
            result = reader.readtext(gray_roi)
            extracted_text = result[0][-2] if result else "[No text detected]"
            
            # Store extracted text
            extracted_texts.append(extracted_text)

            # Categorize extracted text
            if class_id == 0:
                filtered_texts["NOM"] = extracted_text
            elif class_id == 1:
                filtered_texts["PRENOM"] = extracted_text
            elif class_id == 2:
                filtered_texts["MATRICULE"] = extracted_text  

            # Annotate image with extracted text
            cv2.putText(image, extracted_text, (x1, y2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # Handle case where no text is found
        if not filtered_texts:
            filtered_texts = {"NOM": "[No text detected]", "PRENOM": "[No text detected]", "MATRICULE": "[No text detected]"}

        # Join extracted texts
        extracted_txt = "<br>".join([f"<b>{key}</b>: {value}" for key, value in filtered_texts.items()])
        extracted_encoded = urllib.parse.quote(extracted_txt)  # Encode extracted text
        
        # Lookup NOM & PRENOM using MATRICULE
        matched_nom, matched_prenom = "[Not Found]", "[Not Found]"

        if "MATRICULE" in filtered_texts:
            matricule = filtered_texts["MATRICULE"].strip()  # Remove extra spaces

            print(f"Extracted Matricule: '{matricule}'")  # Debug print

            # Convert CSV column to string and strip spaces
            df["Matricule"] = df["Matricule"].astype(str).str.strip()
            

            # Check if extracted matricule exists in dataset
            match = df[df["Matricule"] == matricule]

            if not match.empty:
                
                matched_nom = match.iloc[0]["Nom"]
                print(matched_nom)
                matched_prenom = match.iloc[0]["Prenom"]
                print(matched_prenom)
            else:
                print("Matricule not found in dataset!")  # Debug print

        # Prepare matched text output
        db_txt = f"<b>NOM</b>: {matched_nom}<br><b>PRENOM</b>: {matched_prenom}"
        

        # Convert and save processed image
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(image)
        output_path = "static/processed_image.jpg"
        image.save(output_path)
        print(f"Saved processed image at: {output_path}")

        # Redirect with both extracted & matched texts
        return redirect(url_for('checkyolo', image_url=output_path, extracted_text=extracted_encoded, db_txt=db_txt))

        
    
@app.route('/display/<filename>')
def display_image(filename):
    return redirect(url_for('static', filename='processed_image.jpg'), code=301)
    
    
@app.route("/ftp")
def ftp():
    cnxn = pyodbc.connect(conn_str)
    cursor = cnxn.cursor()    
    query = f"select * from [dbo].[ImgServerPath]"
    cursor.execute(query)
    recordsPrint = cursor.fetchall()
    html_content = ""
    if recordsPrint:
        for row in recordsPrint:           
            row_dict = dict(zip([column[0] for column in cursor.description], row))
            # Determine if the row should be editable or not based on UPID            
            html_content += "<tr>"
            for column_name in [
            
                "ID",
                "proj",
                "base_path",
                "ftp_host",
                "ftp_user",
                "ftp_path"
                
            ]:
                # Check for None and replace with an empty string
                value = row_dict.get(column_name, "")
                    
                # Explicitly check if the value is None and replace it with an empty string
                if value is None or value == "":
                    value = "-"
                if column_name == "ID":
                    html_content += f"<td ><div id='[{column_name}]_{row_dict.get('ID', '')} '><b class=''>{value}</b></div></td>"
                elif column_name == "proj":
                    html_content += f"<td>{value}</td>"
                elif column_name == "ftp_host":
                    html_content += f"<td>{value}</td>"
                elif column_name == "ftp_user":
                    html_content += f"<td>{value}</td>"
                elif column_name == "ftp_path":
                    html_content += f"<td>{value}</td>"    
                elif column_name == "base_path":
                    html_content += f"<td>{value}</td>"
                
            html_content += f"""
                <td style="width:100px;">
                    <a href='{url_for('addprojects', id=row_dict.get('ID', ''))}'                     
                    class='btn btn-danger btn-sm btn-flat edit-btn shadow '
                    data-id='{row_dict.get('ID', '')}'>
                    <i class='fa fa-solid fa-refresh' ></i>
                    </a>
                </td>
                """
            html_content += "</tr>"
    return render_template("ftp.html", html_content=html_content)
    
      
@app.route("/dbTableEdit")
def dbTableEdit():
    return render_template("dbTableEdit.html")


@app.route("/logout")
def logout():
    # session.pop('name', None)
    return redirect(url_for("index"))


@app.route("/logout2")
def logout2():
    return redirect(url_for('login2'))
import zoom_client  # This represents a zoom-compatible Python client


#import zoom_client  # This represents a zoom-compatible Python client




#@app.route('/z3950_query')
#def z3950_query():
#    try:
#        response = requests.get("https://catalogue.bnf.fr/api/SRU", params={
#            "version": "1.2",
#            "operation": "searchRetrieve",
#            "query": 'title all "esmeralda"'
#        })

#        if response.ok:
#            return response.text
#        else:
#            return f"SRU request failed: {response.status_code}"
#    except Exception as e:
#        return f"Error: {e}"




def get_ftps_connection():
    ftps = FTP_TLS()
    ftps.set_debuglevel(2)
    ftps.connect(FTP_HOST, 21, timeout=300)  # Standard FTP port
    ftps.auth()  # Explicit TLS
    ftps.prot_p()  # Switch to secure data connection
    ftps.login(FTP_USER, FTP_PASS)
    ftps.set_pasv(True)  # Optional: Use passive mode
    return ftps
  

def list_folders():
    ftps = get_ftps_connection()
    ftp_root_dir = "/" + session.get("proj", "") + "/"
    ftps.cwd(ftp_root_dir)

    folders = []
    ftps.retrlines('LIST', lambda x: folders.append(x.split()[-1]) if x.startswith('d') else None)
    ftps.quit()
    return folders

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', s)]

def list_images(folder):
    ftps = get_ftps_connection()
    ftp_root_dir = "/" + session.get("proj", "") + "/"  # Define again here
    ftps.cwd(ftp_root_dir + folder)
    files = ftps.nlst()
    ftps.quit()
    
    image_files = [f for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))]
    return sorted(image_files, key=natural_sort_key)

@app.route('/imageGallery')
def imageGallery():
    proj_type = session.get("projtype")
    proj = session.get("proj", "")
    if proj_type == "unimarc":
        field = "u990_b"
        field2 = "u990_c"
        table = "dbo._unimarc"
    else:
        field = "z990_b"
        field2 = "z990_c"
        table = "dbo._intermarc"    
    # Connect safely to the database
    try:
        cnxn = pyodbc.connect(conn_str)
        cursor = cnxn.cursor()
        queryCount = f"SELECT COUNT(*) FROM {table} WHERE proj=?"
        cursor.execute(queryCount, (proj,))
        countNotices = cursor.fetchone()
        AllCount = countNotices[0] if countNotices else 0
        cursor.close()
        cnxn.close()
    except Exception as db_err:
        print("⚠️ DB error:", db_err)
        AllCount = 0  # fallback if DB fails
    language = request.args.get("lang", session["lang"])
    # Language Handling
    if language not in app.config["LANGUAGES"]:
        language = app.config["DEFAULT_LANGUAGE"]
        session["lang"] = language
    else:
        session["lang"] = language
    # Generate URLs for flag images
    en_flag_url = url_for('static', filename='assets/images/us_flag.png')
    fr_flag_url = url_for('static', filename='assets/images/fr_flag.png')
    if language == "fr":
        langButton = f"""<button class="btn btn-primary dropdown-toggle" type="button" id="dropdownMenuButton" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                             <img class="form-control-sm" src="{fr_flag_url}">French
                            </button>
                             <div class="dropdown-menu" aria-labelledby="dropdownMenuButton">
                                <a class="dropdown-item" href="?lang=en"><img class="form-control-sm" src="{en_flag_url}">English</a>
                             </div>"""
    else:
        langButton = f"""<button class="btn btn-primary dropdown-toggle" type="button" id="dropdownMenuButton" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                             <img class="form-control-sm" src="{en_flag_url}">English
                            </button>
                             <div class="dropdown-menu" aria-labelledby="dropdownMenuButton">
                                <a class="dropdown-item" href="?lang=fr"><img class="form-control-sm" src="{fr_flag_url}">French</a>
                             </div>"""
    
    ftp_root_dir = "/" + session.get("proj", "") + "/"  # Define here again
    try:
        folders = list_folders()
        selected_folder = request.args.get('folder', folders[0] if folders else None)
        images = list_images(selected_folder) if selected_folder else []
        selected_image = request.args.get('image', images[0] if images else None)

        image_url = None
        if selected_folder and selected_image:
            image_url = f"ftp://{FTP_USER}:{FTP_PASS}@{FTP_HOST}{ftp_root_dir}{selected_folder}/{selected_image}"

        return render_template('imageGallery.html',
                               folders=folders,
                               selected_folder=selected_folder,
                               images=images,
                               selected_image=selected_image,
                               image_url=image_url,
                               translations=translations[language],
                               lang=language,
                               langButton=langButton,
                               allcount=AllCount)
    except Exception as e:
        error_message = "⚠️ Could not connect to Image server or retrieve data."
        print("Server error:", e)  # Optional: log the actual error
        return render_template("imageGallery.html", 
                               folders=[], 
                               selected_folder=None,
                               images=[], 
                               selected_image=None,
                               image_url=None,
                               error=error_message,                               
                               translations=translations[language],
                               lang=language,
                               langButton=langButton,
                               allcount=AllCount)
@app.route('/api/images/<folder>/<image>')
def api_images(folder, image):
    images = list_images(folder)
    return jsonify(images)
    
@app.route('/download/image/<folder>/<filename>')
def download_image(folder, filename):
    try:
        ftp = get_ftps_connection()
        ftp_root_dir = "/" + session.get("proj", "") + "/"
        ftp.cwd(ftp_root_dir + folder)

        image_stream = BytesIO()
        ftp.retrbinary(f"RETR {filename}", image_stream.write)
        ftp.quit()
        image_stream.seek(0)

        return send_file(image_stream, download_name=filename, as_attachment=True)
    except Exception as e:
        print("Download image error:", e)
        return "Error downloading image", 500

@app.route('/download/folder/<folder>')
def download_folder(folder):
    try:
        ftp = get_ftps_connection()
        ftp_root_dir = "/" + session.get("proj", "") + "/"
        ftp.cwd(ftp_root_dir + folder)

        files = ftp.nlst()
        image_files = [f for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))]

        zip_stream = BytesIO()
        with zipfile.ZipFile(zip_stream, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for filename in image_files:
                file_stream = BytesIO()
                ftp.retrbinary(f"RETR {filename}", file_stream.write)
                file_stream.seek(0)
                zipf.writestr(filename, file_stream.read())

        ftp.quit()
        zip_stream.seek(0)

        zip_name = f"{folder}.zip"
        return send_file(zip_stream, download_name=zip_name, as_attachment=True)
    except Exception as e:
        print("Download folder error:", e)
        return "Error downloading folder", 500        


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000,debug=True)
    # app.run()
