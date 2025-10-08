from flask import Blueprint, render_template
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
    stream_with_context,
    after_this_request
)
conn_str = "Driver={ODBC Driver 17 for SQL Server};Server=tcp:aurexdb.database.windows.net;Database=AUREXDB1;Uid=db_su;Pwd={=!Aurexus21!=};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
cnxn = pyodbc.connect(conn_str)
cursor = cnxn.cursor()
champagne_bp = Blueprint('imageapp', __name__, url_prefix='/imageapp')

# Load the Translation files
def load_translations():
    base_dir = os.path.dirname(os.path.abspath(__file__))  # directory of this file
    translations_path = os.path.join(base_dir, "..", "translations.json")
    with open(translations_path, "r", encoding="utf-8") as f:
        return json.load(f)

# Assign Translation JSON
translations = load_translations()
@image_app.route('/')
def image_home():
    #return "Welcome to Champagne App!"
    #return render_template("champagne_OCR.html")
    return render_template("champlogin.html")
#Check login Information and Assign the value in session

@image_app.route("/champhome", methods=["POST", "GET"])
def champhome():
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
                """select proj_type,email from User_table
                where Username=?""",
                (name),
            )
            row = cursor.fetchone()

            if row:
                session["proj"] = row[0]
                session["projtype"] = row[0]
                session["email"] = row[1]
                
            else:
                # Handle the case where no row is found, if necessary
                session["proj"] = None
                session["projtype"] = None
                session["email"] = None
                
            session["lang"] = language
            # ✅ Redirect to your homepage view
            return redirect(url_for("champagne.champdash"))
        else:
            return render_template(
                "login.html", message="Please Check the Credential's"
            )
    #  ADD THIS to handle GET requests
    return render_template("login.html")

@image_app.route('/champdash')
def champdash():
    
    return render_template("champagneindex.html")  

    
@image_app.route('/imageGallery')
def imageGallery():
    
    return render_template("champagneGallery.html")  


@image_app.route('/ocrQC')
def ocrqc():
    
    return render_template("champagne_OCR - Copy.html")
    