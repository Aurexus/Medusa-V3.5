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
image_bp = Blueprint('imageapp', __name__, url_prefix='/imageapp')
BASE_IMAGE_URL = "https://zadig.aurexus.com/AD37/37273/"
from flask import current_app
# Load the Translation files
def load_translations():
    base_dir = os.path.dirname(os.path.abspath(__file__))  # directory of this file
    translations_path = os.path.join(base_dir, "..", "translations.json")
    with open(translations_path, "r", encoding="utf-8") as f:
        return json.load(f)

# Assign Translation JSON
translations = load_translations()

@image_bp.route('/')
def image_home():
    return render_template("imglogin.html")
#Check login Information and Assign the value in session

@image_bp.route("/champhome", methods=["POST", "GET"])
def imghome():
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
            return redirect(url_for("imageapp.champdash"))
        else:
            return render_template(
                "login.html", message="Please Check the Credential's"
            )
    #  ADD THIS to handle GET requests
    return render_template("login.html")

@image_bp.route('/champdash')
def champdash():
    language = request.args.get("lang", session["lang"])
    if language not in current_app.config["LANGUAGES"]:
        language = current_app.config["DEFAULT_LANGUAGE"]
        session["lang"] = language
    else:
        session["lang"] = language
    return render_template("champagneindex.html",translations=translations[session["lang"]],)  

    
#@image_bp.route('/imageGallery')
#def imageGallery():
    
    #return render_template("champagneGallery.html")  


@image_bp.route('/imageGallery')
def imageGallery():
    proj_type = session.get("projtype")
    proj = session.get("proj", "")

    user_id = session.get("name")
    language = request.args.get("lang", session["lang"])
    if language not in current_app.config["LANGUAGES"]:
        language = current_app.config["DEFAULT_LANGUAGE"]
        session["lang"] = language
    else:
        session["lang"] = language
    bookmarks = []
    if user_id:
        try:
            cnxn = pyodbc.connect(conn_str)
            cursor = cnxn.cursor()
            cursor.execute("SELECT folder, image FROM dbo.ImageBookmarks WHERE user_id=?", (user_id,))
            bookmarks = [(row[0], row[1]) for row in cursor.fetchall()]
            bookmark_set = {(f, i) for f, i in bookmarks}   # a true set of tuples
            cursor.close()
            cnxn.close()
        except:
            pass
    
    
    
    try:
        folders = get_folders_from_db()
        selected_folder = request.args.get('folder', folders[0] if folders else None)
        images = get_images_from_db(selected_folder) if selected_folder else []
        selected_image = request.args.get('image', images[0] if images else None)

        # Build the URL directly to the hosted image
        
        image_url = None
        if selected_folder and selected_image:
            image_url = f"{BASE_IMAGE_URL}/{proj}/{selected_folder}/{selected_image}"

        return render_template("champagneGallery.html",
                               folders=folders,
                               selected_folder=selected_folder,
                               images=images,
                               selected_image=selected_image,
                               image_url=image_url,
                               translations=translations[session["lang"]],
                               lang=session["lang"],
                               bookmarks=bookmarks,
                               bookmark_set=bookmark_set)
    except Exception as e:
        print("⚠️ Could not retrieve data:", e)
        return render_template("champagneGallery.html", folders=[], images=[], selected_image=None,image_url=image_url,
                               translations=translations[session["lang"]],
                               lang=session["lang"],
                               # add your notice count if needed
                               bookmarks=[],
                               bookmark_set=set())    
                               

@image_bp.route('/call/images/<folder>/<active_image>')
def call_images(folder, active_image):   
    proj = session.get("proj", "")
    filter_type = request.args.get("filter", "all")

    try:
        if filter_type == "bookmarks" and "name" in session:
            user_id = session["name"]
            cnxn = pyodbc.connect(conn_str)
            cursor = cnxn.cursor()
            cursor.execute("""
                SELECT image FROM dbo.ImageBookmarks
                WHERE user_id=? AND folder=?
                ORDER BY image
            """, (user_id, folder))
            images = [row[0] for row in cursor.fetchall()]
            cursor.close()
            cnxn.close()
        else:
            images = get_images_from_db(folder)  # all images

        if not images:
            return jsonify([])

        if active_image not in images:
            return jsonify(images[:8])

        idx = images.index(active_image)
        start = max(0, idx - 4)
        end = min(len(images), idx + 5)

        window = images[start:end]
        return jsonify(window)

    except Exception as e:
        print("⚠️ DB error in /call/images:", e)
        return jsonify([])



@image_bp.route('/api/folders')
def api_folders():
    proj = session.get("proj", "")
    filter_type = request.args.get("filter", "all")

    try:
        if filter_type == "bookmarks" and "name" in session:
            user_id = session["name"]
            cnxn = pyodbc.connect(conn_str)
            cursor = cnxn.cursor()
            cursor.execute("""
                SELECT DISTINCT folder 
                FROM dbo.ImageBookmarks 
                WHERE user_id=?
                ORDER BY folder
            """, (user_id,))
            folders = [row[0] for row in cursor.fetchall()]
            cursor.close()
            cnxn.close()
        else:
            folders = get_folders_from_db(proj)

        return jsonify(folders)

    except Exception as e:
        print("⚠️ DB error in /api/folders:", e)
        return jsonify([])

        
@image_bp.route('/api/bookmark', methods=['POST'])
def add_bookmark():
    if "name" not in session:
        return jsonify({"error": "Not logged in"}), 401

    user_id = session["name"]
    folder = request.json.get("folder")
    image = request.json.get("image")

    if not folder or not image:
        return jsonify({"error": "Missing data"}), 400

    try:
        cnxn = pyodbc.connect(conn_str)
        cursor = cnxn.cursor()

        # Check if already exists
        cursor.execute("""
            SELECT COUNT(*) FROM dbo.ImageBookmarks
            WHERE user_id=? AND folder=? AND image=?
        """, (user_id, folder, image))
        exists = cursor.fetchone()[0]

        if not exists:
            cursor.execute("""
                INSERT INTO dbo.ImageBookmarks (user_id, folder, image) 
                VALUES (?, ?, ?)
            """, (user_id, folder, image))
            cnxn.commit()
            msg = "Ajouté aux favoris avec succès"
        else:
            msg = "Déjà ajouté aux favoris"

        cursor.close()
        cnxn.close()
        return jsonify({"message": msg})

    except Exception as e:
        print("DB error:", e)
        return jsonify({"error": "Database error"}), 500


@image_bp.route('/api/bookmarks', methods=['GET'])
def get_bookmarks():
    if "name" not in session:
        return jsonify([])

    user_id = session["name"]

    try:
        cnxn = pyodbc.connect(conn_str)
        cursor = cnxn.cursor()
        cursor.execute("SELECT folder, image FROM dbo.ImageBookmarks WHERE user_id=?", (user_id,))
        bookmarks = [{"folder": row[0], "image": row[1]} for row in cursor.fetchall()]
        cursor.close()
        cnxn.close()
        return jsonify(bookmarks)
    except Exception as e:
        print("DB error:", e)
        return jsonify([])


@image_bp.route('/api/bookmark/delete', methods=['POST'])
def delete_bookmark():
    if "name" not in session:
        return jsonify({"error": "Not logged in"}), 401

    user_id = session["name"]
    folder = request.json.get("folder")
    image = request.json.get("image")

    try:
        cnxn = pyodbc.connect(conn_str)
        cursor = cnxn.cursor()
        cursor.execute("""
            DELETE FROM dbo.ImageBookmarks WHERE user_id=? AND folder=? AND image=?
        """, (user_id, folder, image))
        cnxn.commit()
        cursor.close()
        cnxn.close()
        return jsonify({"message": "Favori supprimé"})
    except Exception as e:
        print("DB error:", e)
        return jsonify({"error": "Database error"}), 500


def get_folders_from_db():
    cnxn = pyodbc.connect(conn_str)
    cursor = cnxn.cursor()
    cursor.execute("""
        SELECT DISTINCT Dossier 
        FROM [dbo].[ad37]       
        ORDER BY Dossier
    """)
    folders = [row[0] for row in cursor.fetchall()]
    cursor.close()
    cnxn.close()
    return folders


def get_images_from_db(folder):
    cnxn = pyodbc.connect(conn_str)
    cursor = cnxn.cursor()
    cursor.execute("""
        SELECT image 
        FROM [dbo].[ad37]
        WHERE  dossier=?
        ORDER BY image
    """, (folder,))
    images = [row[0] for row in cursor.fetchall()]
    cursor.close()
    cnxn.close()
    return images
