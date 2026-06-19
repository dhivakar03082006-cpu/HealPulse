from flask import Flask, render_template_string, request, redirect, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import math
import os

app = Flask(__name__)
app.secret_key = "hospital_ultra_secure_key_2026"

# ---------------- DATABASE ROUTINES ----------------
def init_db():
    conn = sqlite3.connect("hospital.db")
    c = conn.cursor()

    c.execute("DROP TABLE IF EXISTS reviews")
    c.execute("DROP TABLE IF EXISTS appointments")
    c.execute("DROP TABLE IF EXISTS doctors")
    c.execute("DROP TABLE IF EXISTS hospitals")
    c.execute("DROP TABLE IF EXISTS users")

    # 1. Users Security Table
    c.execute("""
    CREATE TABLE users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    # 2. Comprehensive Hospitals Table
    c.execute("""
    CREATE TABLE hospitals(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        state TEXT,
        city TEXT,
        type TEXT,
        lat REAL,
        lng REAL,
        beds INTEGER,
        wait_time INTEGER
    )
    """)

    # 3. Dedicated Doctor Metadata Table
    c.execute("""
    CREATE TABLE doctors(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hospital_id INTEGER,
        name TEXT,
        specialty TEXT,
        experience INTEGER,
        status TEXT,
        FOREIGN KEY(hospital_id) REFERENCES hospitals(id)
    )
    """)

    # 4. Integrated Appointments System
    c.execute("""
    CREATE TABLE appointments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        doctor_id INTEGER,
        date TEXT,
        time_slot TEXT,
        visit_type TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(doctor_id) REFERENCES doctors(id)
    )
    """)

    # 5. Multi-User Reviews Table
    c.execute("""
    CREATE TABLE reviews(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hospital_id INTEGER,
        username TEXT,
        rating INTEGER,
        review_text TEXT,
        FOREIGN KEY(hospital_id) REFERENCES hospitals(id)
    )
    """)

    # Seed Nationwide Public Data
    hospitals_data = [
        ("JIPMER Hospital", "Puducherry", "Puducherry", "Central Government Multi-Speciality", 11.9560, 79.8005, 38, 40),
        ("IGMCRI Hospital", "Puducherry", "Kathirkamam", "Government Medical College & Hospital", 11.9511, 79.7954, 15, 65),
        ("Apollo Hospital", "Tamil Nadu", "Chennai", "Private Multi-Speciality", 13.0604, 80.2496, 25, 15),
        ("MIOT International", "Tamil Nadu", "Chennai", "Orthopedic & Trauma Care", 13.0223, 80.1844, 0, 105), 
        ("CMC Hospital", "Tamil Nadu", "Vellore", "Charitable General Hospital", 12.9249, 79.1356, 45, 35),
        ("AIIMS Hospital", "Delhi", "New Delhi", "Government Apex Medical Center", 28.5672, 77.2100, 8, 140),
        ("Fortis Hospital", "Karnataka", "Bangalore", "Private Super-Speciality", 12.9226, 77.5994, 22, 20),
        ("Kokilaben Dhirubhai Ambani Hospital", "Maharashtra", "Mumbai", "Private Multi-Speciality", 19.1313, 72.8253, 19, 45)
    ]
    c.executemany("INSERT INTO hospitals(name,state,city,type,lat,lng,beds,wait_time) VALUES (?,?,?,?,?,?,?,?)", hospitals_data)
    
    # Seed Professional Doctor Rosters
    doctors_data = [
        (1, "Dr. Mahaveer Prasad", "Chest & Lung Specialist", 24, "Available Now"),
        (1, "Dr. Shailesh Kumar", "Heart Specialist (Cardiologist)", 19, "Available Now"),
        (2, "Dr. Kanna Sharma", "Child Specialist (Pediatrician)", 12, "Available Now"),
        (3, "Dr. K. R. Balakrishnan", "Heart Specialist (Cardiologist)", 28, "Available Now"),
        (3, "Dr. Sudha Nair", "Brain & Nerve Specialist", 16, "In Surgery"),
        (4, "Dr. S. S. Mohanty", "Bone & Joint Specialist", 22, "Available Now"),
        (5, "Dr. George Mathews", "Child Specialist (Pediatrician)", 19, "On Break"),
        (6, "Dr. Randeep Guleria", "Chest & Lung Specialist", 31, "Available Now"),
        (7, "Dr. Vivek Jawali", "Heart Specialist (Cardiologist)", 26, "Available Now"),
        (8, "Dr. Suresh Advani", "Cancer Specialist (Oncologist)", 35, "Available Now")
    ]
    c.executemany("INSERT INTO doctors(hospital_id,name,specialty,experience,status) VALUES (?,?,?,?,?)", doctors_data)

    # Seed Patient Reviews 
    reviews_data = [
        (1, "Nitin J.", 5, "Excellent infrastructure and very helpful doctors at JIPMER."),
        (3, "Rajesh Kumar", 5, "World class heart diagnostics department setup."),
        (4, "Amit Patel", 2, "Good emergency facilities but long waiting lines.")
    ]
    c.executemany("INSERT INTO reviews(hospital_id,username,rating,review_text) VALUES (?,?,?,?)", reviews_data)

    conn.commit()
    conn.close()

# Keep database fresh on script boot
init_db()

# ---------------- HEALTHCARE AI MAPPING LOGIC ----------------
def parse_symptoms_to_specialty(user_input):
    input_lower = user_input.lower()
    if any(word in input_lower for word in ["heart", "cardiac", "chest pain", "bp", "pulse", "palpitations"]):
        return "Heart Specialist (Cardiologist)"
    if any(word in input_lower for word in ["brain", "nerve", "stroke", "paralysis", "headache", "seizure", "spinal"]):
        return "Brain & Nerve Specialist"
    if any(word in input_lower for word in ["bone", "fracture", "joint", "knee", "back pain", "spine", "leg break"]):
        return "Bone & Joint Specialist"
    if any(word in input_lower for word in ["child", "baby", "pediatric", "infant", "fever kid", "son", "daughter"]):
        return "Child Specialist (Pediatrician)"
    if any(word in input_lower for word in ["breath", "lung", "asthma", "cough", "covid", "respiratory", "wheezing"]):
        return "Chest & Lung Specialist"
    if any(word in input_lower for word in ["cancer", "tumor", "chemo", "oncology"]):
        return "Cancer Specialist (Oncologist)"
    return "General Physician"

def ai_triage_engine(user_message):
    msg = user_message.lower()
    mapping = {
        "Heart Specialist (Cardiologist)": ["heart", "cardiac", "chest pain", "bp", "pulse", "palpitations", "artery"],
        "Brain & Nerve Specialist": ["brain", "nerve", "stroke", "paralysis", "headache", "seizure", "migraine", "dizzy"],
        "Bone & Joint Specialist": ["bone", "fracture", "joint", "knee", "back pain", "spine", "ligament", "muscle pain", "leg break"],
        "Child Specialist (Pediatrician)": ["child", "baby", "pediatric", "infant", "fever kid", "toddler", "vaccine", "son", "daughter"],
        "Chest & Lung Specialist": ["breath", "lung", "asthma", "cough", "covid", "respiratory", "wheezing"],
        "Cancer Specialist (Oncologist)": ["cancer", "tumor", "chemo", "oncology", "malignant", "biopsy"]
    }
    for specialty, keywords in mapping.items():
        if any(keyword in msg for keyword in keywords):
            return specialty
    return "General Physician"

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)

# ---------------- CLEAN PUBLIC UI DESIGN ----------------
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>HealPulse | Smart Hospital Finder & AI Triage</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

    <style>
        :root {
            --bg-base: #070c19;
            --glass-card: rgba(20, 29, 51, 0.8);
            --border-glow: rgba(0, 198, 255, 0.2);
            --neon-blue: #00c6ff;
            --neon-red: #ef4444;
            --neon-green: #10b981;
            --neon-yellow: #eab308;
        }

        body { margin: 0; font-family: 'Segoe UI', system-ui, sans-serif; background: radial-gradient(circle at top, #0f2244, var(--bg-base)); color: #f3f4f6; padding-bottom: 60px; background-attachment: fixed; }
        body::before { content: ''; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-image: linear-gradient(rgba(0, 198, 255, 0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 198, 255, 0.02) 1px, transparent 1px); background-size: 40px 40px; z-index: -1; pointer-events: none; }
        
        .sos-bar { position: sticky; top: 0; z-index: 9999; background: rgba(10, 17, 34, 0.95); backdrop-filter: blur(12px); border-bottom: 2px solid var(--neon-red); padding: 14px 5%; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 30px rgba(239, 68, 68, 0.2); }
        .sos-btn { background: linear-gradient(90deg, #dc2626, #ef4444); color: white; border: none; padding: 12px 28px; font-weight: bold; border-radius: 30px; cursor: pointer; box-shadow: 0 0 15px rgba(239, 68, 68, 0.5); animation: pulse-glow 2s infinite; display: flex; align-items: center; gap: 8px; }
        
        .container { width: 92%; max-width: 1400px; margin: 30px auto; padding: 25px; border-radius: 24px; backdrop-filter: blur(20px); background: rgba(255,255,255,0.01); border: 1px solid rgba(255,255,255,0.03); }
        
        .hospital-hero-art {
            width: 100%;
            height: 180px;
            background: linear-gradient(135deg, rgba(0, 198, 255, 0.2), rgba(0, 114, 255, 0.4)), url('https://images.unsplash.com/photo-1587351021759-3e566b6af7cc?q=80&w=1200&auto=format&fit=crop');
            background-size: cover;
            background-position: center;
            border-radius: 20px;
            margin-bottom: 25px;
            border: 1px solid var(--border-glow);
            display: flex;
            align-items: center;
            padding-left: 40px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.4);
        }
        
        .search-container { display: grid; grid-template-columns: 2fr 2fr 1fr; gap: 15px; margin: 25px 0; }
        .input-box { padding: 16px; border-radius: 12px; background: #0b1121; border: 1px solid #1e293b; color: white; font-size: 15px; width: 100%; box-sizing: border-box; }
        .input-box:focus { border-color: var(--neon-blue); outline: none; }
        .btn-query { padding: 16px; border-radius: 12px; background: linear-gradient(90deg, #00c6ff, #0072ff); border: none; color: white; font-weight: bold; font-size: 16px; cursor: pointer; transition: 0.3s; }
        .btn-query:hover { opacity: 0.9; box-shadow: 0 0 15px rgba(0, 198, 255, 0.4); }

        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap: 30px; margin-top: 25px; }
        .card { background: var(--glass-card); padding: 30px; border-radius: 24px; border: 1px solid var(--border-glow); position: relative; transition: all 0.3s ease; box-shadow: 0 15px 35px rgba(0,0,0,0.4); overflow: hidden; }
        .card::after { content: '✚'; position: absolute; bottom: -20px; right: -15px; font-size: 110px; color: rgba(0, 198, 255, 0.03); pointer-events: none; }
        .card:hover { transform: translateY(-5px); border-color: rgba(0, 198, 255, 0.4); box-shadow: 0 20px 40px rgba(0, 198, 255, 0.15); }
        .card.urgency-panic { border-color: rgba(239, 68, 68, 0.4); background: linear-gradient(180deg, rgba(28, 14, 20, 0.8) 0%, var(--glass-card) 100%); }

        .badge { position: absolute; top: 25px; right: 25px; padding: 6px 14px; border-radius: 30px; font-size: 12px; font-weight: bold; }
        .badge.green { background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid #10b981; }
        .badge.red { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid #ef4444; }

        .doctor-subgrid { display: flex; flex-direction: column; gap: 12px; margin: 15px 0; }
        .doctor-pill { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 14px; padding: 15px; display: flex; justify-content: space-between; align-items: center; transition: 0.2s; }
        .doctor-pill.targeted { border-color: var(--neon-yellow); background: rgba(234, 179, 8, 0.05); box-shadow: 0 0 12px rgba(234, 179, 8, 0.15); }
        .doc-status { font-size: 11px; padding: 3px 8px; border-radius: 20px; font-weight: bold; }
        .doc-status.online { background: rgba(16, 185, 129, 0.2); color: #34d399; }
        .doc-status.offline { background: rgba(239, 68, 68, 0.2); color: #f87171; }

        .review-stream { max-height: 140px; overflow-y: auto; background: rgba(0,0,0,0.2); padding: 12px; border-radius: 12px; margin-top: 15px; font-size: 13px; }
        .review-bubble { border-bottom: 1px solid rgba(255,255,255,0.05); padding: 8px 0; }
        
        /* Dynamic Wait-Time Color Mapping Rules (Clean CSS replacement for inline Jinja code) */
        .wait-txt { font-weight: bold; }
        .wait-txt[data-wait="high"] { color: var(--neon-red); }
        .wait-txt[data-wait="low"] { color: var(--neon-green); }

        /* ---------------- MOVABLE AI CHAT BOT UI ---------------- */
        .ai-chat-widget { position: fixed; bottom: 25px; right: 25px; width: 360px; height: 450px; background: rgba(11, 18, 36, 0.95); border: 1px solid var(--neon-blue); border-radius: 20px; box-shadow: 0 10px 40px rgba(0,198,255,0.3); z-index: 10000; display: flex; flex-direction: column; overflow: hidden; backdrop-filter: blur(15px); }
        .chat-header { background: linear-gradient(90deg, #00c6ff, #0072ff); padding: 15px; font-weight: bold; display: flex; justify-content: space-between; align-items: center; cursor: move; user-select: none; }
        .chat-messages { flex: 1; padding: 15px; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; font-size: 14px; }
        .msg { padding: 10px 14px; border-radius: 12px; max-width: 80%; line-height: 1.4; }
        .msg.bot { background: #1e293b; color: #f3f4f6; align-self: flex-start; border-bottom-left-radius: 2px; }
        .msg.user { background: var(--neon-blue); color: white; align-self: flex-end; border-bottom-right-radius: 2px; }
        .chat-input-area { padding: 10px; display: flex; background: #060a14; border-top: 1px solid #1e293b; }
        .chat-input-area input { flex: 1; background: transparent; border: none; padding: 15px; color: white; outline: none; }
        .chat-input-area button { background: var(--neon-blue); border: none; padding: 0 20px; color: white; font-weight: bold; cursor: pointer; }

        .time-slots-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin: 10px 0; }
        .slot-pill { background: #1e293b; border: 1px solid #334155; text-align: center; padding: 8px; font-size: 12px; border-radius: 8px; cursor: pointer; color: #cbd5e1; }
        .slot-pill.selected { background: rgba(0, 198, 255, 0.2); border-color: var(--neon-blue); color: white; }
        #map { height: 420px; border-radius: 24px; margin: 25px 0; border: 1px solid #1e293b; }
        .btn-action-primary { background: linear-gradient(90deg, #00c6ff, #0072ff); color: white; border: none; padding: 12px; border-radius: 10px; cursor: pointer; font-weight: bold; width: 100%; margin-top: 8px; }
        @keyframes pulse-glow { 0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); } 70% { box-shadow: 0 0 0 15px rgba(239, 68, 68, 0); } 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); } }
    </style>
</head>
<body>

<div class="sos-bar">
    <div style="display:flex; align-items:center; gap:10px;">
        <span style="font-size:22px; color:var(--neon-blue);">🩺</span>
        <h2 style="margin:0; font-weight:900; letter-spacing:0.5px; background:linear-gradient(90deg,#00c6ff,#00ffcc); -webkit-background-clip:text; -webkit-text-fill-color:transparent;">HealPulse Portal</h2>
    </div>
    {% if session.get('user') %}
        <button class="sos-btn" onclick="triggerSOS()">🚨 FIND CLOSEST EMERGENCY BED</button>
    {% endif %}
</div>

<div class="container">
    {% if not session.get('user') %}
    <div style="max-width: 420px; margin: 60px auto;">
        <h2 style="text-align:center; color: var(--neon-blue); margin-bottom:30px;">🔐 Secure Patient Portal Sign-In</h2>
        
        <form method="POST" action="/login" style="background: var(--glass-card); padding: 30px; border-radius: 24px; border: 1px solid rgba(0,198,255,0.15);">
            <h3>Secure Sign-In</h3>
            {% if error %}<p style="color:var(--neon-red); font-size:14px;">⚠️ {{error}}</p>{% endif %}
            <input name="username" placeholder="Enter Username" required class="input-box" style="margin-bottom:12px;">
            <input name="password" type="password" placeholder="Enter Password" required class="input-box" style="margin-bottom:15px;">
            <button type="submit" class="btn-query" style="width:100%;">Sign In</button>
        </form>

        <form method="POST" action="/register" style="margin-top:25px; background: var(--glass-card); padding: 30px; border-radius: 24px; border: 1px solid rgba(16,185,129,0.15);">
            <h3>Create New Patient Account</h3>
            <input name="username" placeholder="Choose Username" minlength="3" required class="input-box" style="margin-bottom:12px;">
            <input name="password" type="password" placeholder="Choose Password" minlength="4" required class="input-box" style="margin-bottom:15px;">
            <button type="submit" class="btn-query" style="width:100%; background: linear-gradient(90deg, #10b981, #059669);">Create Account</button>
        </form>
    </div>

    {% else %}
    <div class="hospital-hero-art">
        <div style="text-shadow: 0 4px 10px rgba(0,0,0,0.8);">
            <h1 style="margin:0; font-size:32px; font-weight:900; color:white;">Welcome to HealPulse, {{session['user']}}</h1>
            <p style="margin:5px 0 0 0; font-size:16px; color:#e2e8f0;">Find verified public hospitals and schedule consulting slots instantly.</p>
        </div>
    </div>

    <div style="display: flex; justify-content: space-between; align-items: center; margin-top:10px;">
        <h2>📍 Real-Time Regional Hospital Map</h2>
        <a href="/logout" style="color:var(--neon-red); text-decoration:none; font-weight:bold; font-size:15px; background:rgba(239,68,68,0.1); padding:8px 16px; border-radius:10px; border:1px solid rgba(239,68,68,0.2);">Sign Out</a>
    </div>

    <div id="map"></div>

    <h3>🔍 Smart Location Filter & Symptom Search</h3>
    <form method="GET" action="/" class="search-container">
        <input name="location" placeholder="🌍 Enter State or City (e.g. Puducherry, Chennai, Delhi)..." value="{{search_query}}" class="input-box">
        <input id="mainProblemField" name="problem" placeholder="🤒 What is your illness/symptom? (e.g. Heart ache, Back pain, Fever)..." value="{{problem_query}}" class="input-box">
        <input type="hidden" id="user_lat" name="user_lat" value="{{user_lat}}">
        <input type="hidden" id="user_lng" name="user_lng" value="{{user_lng}}">
        <button type="submit" class="btn-query">Search Now</button>
    </form>
    
    {% if targeted_specialty %}
    <p style="margin:-15px 0 15px 0; font-size:14px; color:var(--neon-yellow);">🎯 Auto-Matched Department found: <strong>{{targeted_specialty}}</strong></p>
    {% endif %}
    <p id="geo_status" style="font-size: 13px; color: #94a3b8; margin: -10px 0 20px 0;"></p>

    <div class="grid" id="hospital-grid">
        {% for h in hospitals %}
        <div class="card {% if h.beds == 0 %}urgency-panic{% endif %}" data-beds="{{h.beds}}" data-lat="{{h.lat}}" data-lng="{{h.lng}}">
            {% if h.beds > 0 %}
                <span class="badge green">🟢 {{h.beds}} Beds Free</span>
            {% else %}
                <span class="badge red">🚨 NO EMERGENCY BEDS LEFT</span>
            {% endif %}

            <h3 style="margin: 0 0 5px 0; color: #00c6ff; font-size:22px; max-width:70%;">{{h.name}}</h3>
            <span style="font-size:11px; text-transform:uppercase; background:rgba(0,198,255,0.1); padding:4px 10px; border-radius:6px; color:var(--neon-blue); font-weight:bold;">📍 {{h.city}}, {{h.state}}</span>
            <p style="margin: 12px 0 5px 0; font-size:14px; color:#94a3b8;">Hospital Type: <strong style="color:white;">{{h.type}}</strong></p>
            
            <p style="font-size:13px; color:#cbd5e1; margin:0 0 15px 0;">⏱️ Est. Emergency Room Wait: 
                <span class="wait-txt" data-wait="{% if h.wait_time > 60 %}high{% else %}low{% endif %}">{{h.wait_time}} Mins</span>
            </p>

            {% if h.distance is not none %}
                <p style="color: #f59e0b; margin:10px 0; font-size:14px; font-weight:bold;">🏎️ Distance from you: {{h.distance}} km</p>
            {% endif %}

            <h4 style="margin:20px 0 10px 0; color:#cbd5e1; font-size:14px; letter-spacing:0.5px;">👨‍⚕️ Available Specialist Doctors:</h4>
            <div class="doctor-subgrid">
                {% for doc in h.doctors_list %}
                <div class="doctor-pill {% if doc.specialty == targeted_specialty %}targeted{% endif %}">
                    <div>
                        <strong style="display:block; color:white; font-size:14px;">{{doc.name}}</strong>
                        <span style="font-size:12px; color:var(--neon-blue);">{{doc.specialty}}</span> • 
                        <span style="font-size:12px; color:#94a3b8;">{{doc.experience}} Yrs Experience</span>
                    </div>
                    <div>
                        <span class="doc-status {% if doc.status == 'Available Now' %}online{% else %}offline{% endif %}">{{doc.status}}</span>
                        {% if h.beds > 0 and doc.status == 'Available Now' %}
                        <button type="button" style="display:block; margin-top:5px; padding:5px 10px; font-size:11px; background:var(--neon-blue); border:none; border-radius:6px; color:white; cursor:pointer;" onclick="triggerModalBooking(this, {{doc.id}}, '{{doc.name}}', '{{doc.specialty}}')">Book</button>
                        {% endif %}
                    </div>
                </div>
                {% endfor %}
            </div>

            <h4 style="margin:20px 0 5px 0; color:#cbd5e1; font-size:13px;">💬 Patient Testimonials & Reviews:</h4>
            <div class="review-stream">
                {% if h.reviews_list %}
                    {% for rev in h.reviews_list %}
                    <div class="review-bubble">
                        <div style="display:flex; justify-content:space-between; color:var(--neon-yellow); font-size:12px; font-weight:bold; margin-bottom:2px;">
                            <span>👤 {{rev.username}}</span>
                            <span>{{ '★' * rev.rating }}</span>
                        </div>
                        <p style="margin:0; color:#94a3b8; line-height:1.4;">{{rev.review_text}}</p>
                    </div>
                    {% endfor %}
                {% else %}
                    <p style="color:#475569; margin:5px 0; font-style:italic;">No patient reviews logged yet.</p>
                {% endif %}
            </div>
            <button type="button" class="btn-action-primary" style="background:#1e293b; border:1px solid #334155;" onclick="openExternalRoutingMap({{h.lat}}, {{h.lng}})">🧭 Get Directions on Google Maps</button>
        </div>
        {% endfor %}
    </div>

    <div id="movableChatBot" class="ai-chat-widget">
        <div class="chat-header" id="chatHeaderHandle">
            <span>🤖 HealPulse AI Assistant</span>
            <span style="font-size:11px; color:#a7f3d0;">Drag Me Anywhere ✥</span>
        </div>
        <div class="chat-messages" id="chatWindow">
            <div class="msg bot">Hello! Describe your symptoms or what hurts, and I will instantly tell you which specialist department you need to see.</div>
        </div>
        <div class="chat-input-area">
            <input id="chatInput" placeholder="Type your symptoms here (e.g. Chest pain)..." onkeydown="if(event.key === 'Enter') sendChatMessage()">
            <button onclick="sendChatMessage()">Ask AI</button>
        </div>
    </div>

    <div id="bookingModal" style="display:none; position:fixed; inset:0; background:rgba(0,0,0,0.8); backdrop-filter:blur(10px); z-index:99999; align-items:center; justify-content:center;">
        <div class="card" style="width:100%; max-width:460px; border-color:var(--neon-blue);">
            <h3 style="margin-top:0;" id="modalDocName">Confirm Appointment Slot</h3>
            <p id="modalDocSpecialty" style="color:var(--neon-blue); margin-top:-10px; font-size:14px;"></p>
            <form method="POST" action="/book_appointment_node">
                <input type="hidden" name="doctor_id" id="modalDocId">
                <div class="visit-toggle-container" style="display:flex; background:#0f172a; padding:4px; border-radius:10px; border:1px solid #334155; margin:15px 0;">
                    <div class="visit-option active" style="flex:1; text-align:center; padding:8px; cursor:pointer;" onclick="setModeSelector(this, 'In-Person')">🏥 In-Person</div>
                    <div class="visit-option" style="flex:1; text-align:center; padding:8px; cursor:pointer;" onclick="setModeSelector(this, 'Virtual')">💻 Online Video Consult</div>
                </div>
                <input type="hidden" name="visit_type" id="modalVisitType" value="In-Person">
                <label style="font-size:12px; color:#94a3b8;">Choose Date:</label>
                <input type="date" name="book_date" required class="input-box" style="padding:10px; margin-bottom:12px;">
                <label style="font-size:12px; color:#94a3b8;">Select Preferred Time Block:</label>
                <input type="hidden" name="time_slot" id="modalTimeSlot" required>
                <div class="time-slots-grid">
                    <div class="slot-pill" onclick="selectTimePill(this, '09:00 AM')">09:00 AM</div>
                    <div class="slot-pill" onclick="selectTimePill(this, '11:30 AM')">11:30 AM</div>
                    <div class="slot-pill" onclick="selectTimePill(this, '03:30 PM')">03:30 PM</div>
                </div>
                <div style="display:flex; gap:10px; margin-top:20px;">
                    <button type="button" class="btn-query" style="background:#334155; flex:1;" onclick="closeModalWindow()">Go Back</button>
                    <button type="submit" class="btn-query" style="flex:2;">Confirm Appointment</button>
                </div>
            </form>
        </div>
    </div>

    <hr style="border:0; height:1px; background:rgba(255,255,255,0.05); margin:40px 0;">

    <div class="grid">
        <div class="card" style="background: rgba(8, 12, 24, 0.4);">
            <h3 style="margin-top:0;">📅 Your Scheduled Appointments</h3>
            {% if appointments %}
                {% for appt in appointments %}
                <div style="background: rgba(255,255,255,0.02); padding: 16px; margin-bottom: 12px; border-radius: 14px; display: flex; justify-content: space-between; align-items: center; border: 1px solid rgba(255,255,255,0.04);">
                    <div>
                        <h4 style="margin:0; color:var(--neon-green);">{{appt[0]}} ({{appt[1]}})</h4>
                        <span style="font-size:13px; color:#94a3b8; display:block; margin-top:4px;">Hospital: <strong>{{appt[2]}}</strong> • {{appt[3]}}</span>
                        <span style="font-size:12px; color:var(--neon-blue); display:block; margin-top:2px;">Date: {{appt[4]}} | Time: {{appt[5]}} | Mode: {{appt[6]}}</span>
                    </div>
                    <a href="/cancel_appointment_node/{{appt[7]}}"><button style="padding: 8px 14px; background:var(--neon-red); border:none; border-radius:8px; color:white; font-weight:bold; cursor:pointer; font-size:12px;">Cancel Slot</button></a>
                </div>
                {% endfor %}
            {% else %}
                <p style="color: #475569; font-size:14px; font-style:italic;">No upcoming medical appointments found.</p>
            {% endif %}
        </div>
        <div class="card" style="background: rgba(8, 12, 24, 0.4);">
            <h3 style="margin-top:0;">📈 Hospital Density Distribution Analytics</h3>
            <canvas id="chart" style="max-height: 240px;"></canvas>
        </div>
    </div>

    <script>
        var map = L.map('map').setView([11.9416, 79.8083], 6);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© OpenStreetMap contributors' }).addTo(map);

        var operationalGlobalList = [];
        {% for h in hospitals %}
            operationalGlobalList.push({ name: "{{h.name}}", lat: {{h.lat}}, lng: {{h.lng}}, beds: {{h.beds}} });
            L.marker([{{h.lat}}, {{h.lng}}]).addTo(map).bindPopup("<b>{{h.name}}</b><br>{{h.city}}<br>Beds: {{h.beds}}");
        {% endfor %}

        var clientLat = null, clientLng = null;
        window.onload = function() {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(function(pos) {
                    clientLat = pos.coords.latitude; clientLng = pos.coords.longitude;
                    document.getElementById('user_lat').value = clientLat; document.getElementById('user_lng').value = clientLng;
                    L.marker([clientLat, clientLng], {color: 'red'}).addTo(map).bindPopup("<b>Your Current Location</b>").openPopup();
                });
            }
            initializeDraggableWidget(document.getElementById("movableChatBot"), document.getElementById("chatHeaderHandle"));
        };

        function initializeDraggableWidget(widgetElem, handleElem) {
            let pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;
            handleElem.onmousedown = dragMouseDown;

            function dragMouseDown(e) {
                e = e || window.event;
                e.preventDefault();
                pos3 = e.clientX;
                pos4 = e.clientY;
                document.onmouseup = closeDragElement;
                document.onmousemove = elementDrag;
            }

            function elementDrag(e) {
                e = e || window.event;
                e.preventDefault();
                pos1 = pos3 - e.clientX;
                pos2 = pos4 - e.clientY;
                pos3 = e.clientX;
                pos4 = e.clientY;
                widgetElem.style.top = (widgetElem.offsetTop - pos2) + "px";
                widgetElem.style.left = (widgetElem.offsetLeft - pos1) + "px";
                widgetElem.style.bottom = "auto";
                widgetElem.style.right = "auto";
            }

            function closeDragElement() {
                document.onmouseup = null;
                document.onmousemove = null;
            }
        }

        function sendChatMessage() {
            let inputField = document.getElementById("chatInput");
            let text = inputField.value.trim();
            if(!text) return;

            let chatWindow = document.getElementById("chatWindow");
            
            let userDiv = document.createElement("div");
            userDiv.className = "msg user";
            userDiv.innerText = text;
            chatWindow.appendChild(userDiv);
            inputField.value = "";
            chatWindow.scrollTop = chatWindow.scrollHeight;

            fetch("/ai_triage_chat", {
                method: "POST",
                headers: { "Content-Type": "application/x-www-form-urlencoded" },
                body: "message=" + encodeURIComponent(text)
            })
            .then(res => res.json())
            .then(data => {
                let botDiv = document.createElement("div");
                botDiv.className = "msg bot";
                botDiv.innerHTML = data.reply;
                chatWindow.appendChild(botDiv);
                chatWindow.scrollTop = chatWindow.scrollHeight;
                
                if(data.specialty) {
                    document.getElementById("mainProblemField").value = data.specialty;
                }
            });
        }

        function triggerSOS() {
            if (!clientLat || !clientLng) return;
            let targetNode = null; let minDistanceVal = Infinity;
            operationalGlobalList.forEach(function(h) {
                if (h.beds > 0) {
                    let d = computeNativeHaversine(clientLat, clientLng, h.lat, h.lng);
                    if (d < minDistanceVal) { minDistanceVal = d; targetNode = h; }
                }
            });
            if (targetNode) openExternalRoutingMap(targetNode.lat, targetNode.lng);
        }

        function computeNativeHaversine(lat1, lon1, lat2, lon2) {
            let R = 6371;
            let dLat = (lat2-lat1) * Math.PI / 180; let dLon = (lon2-lon1) * Math.PI / 180;
            let a = Math.sin(dLat/2) * Math.sin(dLat/2) + Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLon/2) * Math.sin(dLon/2);
            return R * (2 * Math.atan2(math.sqrt(a), math.sqrt(1-a)));
        }

        function openExternalRoutingMap(tLat, tLng) {
            let url = "https://www.google.com/maps/dir/?api=1&destination=" + tLat + "," + tLng;
            if (clientLat && clientLng) { url += "&origin=" + clientLat + "," + clientLng; }
            window.open(url, '_blank');
        }

        function triggerModalBooking(btn, docId, docName, docSpecialty) {
            document.getElementById('modalDocId').value = docId;
            document.getElementById('modalDocName').innerText = "Schedule with " + docName;
            document.getElementById('modalDocSpecialty').innerText = "Speciality: " + docSpecialty;
            document.getElementById('bookingModal').style.display = 'flex';
        }
        function closeModalWindow() { document.getElementById('bookingModal').style.display = 'none'; }
        function setModeSelector(el, mode) {
            let p = el.parentElement; p.querySelectorAll('.visit-option').forEach(o => o.classList.remove('active'));
            el.classList.add('active'); document.getElementById('modalVisitType').value = mode;
        }
        function selectTimePill(el, val) {
            let p = el.parentElement; p.querySelectorAll('.slot-pill').forEach(s => s.classList.remove('selected'));
            el.classList.add('selected'); document.getElementById('modalTimeSlot').value = val;
        }

        var ctx = document.getElementById('chart').getContext('2d');
        new Chart(ctx,{
            type:'doughnut',
            data:{
                labels: {{labels|safe}},
                datasets:[{
                    data: {{values|safe}},
                    backgroundColor:["#00c6ff","#10b981","#f59e0b","#ef4444","#8b5cf6","#ec4899","#3b82f6","#6366f1"]
                }]
            },
            options: { plugins: { legend: { labels: { color: 'white' } } } }
        });
    </script>
    {% endif %}
</div>
</body>
</html>
"""

# ---------------- ROUTING CONTROLLERS ----------------

@app.route("/", methods=["GET"])
def home():
    if "user" not in session:
        return render_template_string(HTML, error=None)

    loc_query = request.args.get("location", "")
    prob_query = request.args.get("problem", "")
    user_lat = request.args.get("user_lat", "")
    user_lng = request.args.get("user_lng", "")

    conn = sqlite3.connect("hospital.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT id FROM users WHERE username = ?", (session['user'],))
    user_row = c.fetchone()
    if not user_row:
        conn.close()
        session.pop("user", None)
        return redirect("/")
    user_id = user_row['id']

    targeted_specialty = None
    if prob_query:
        targeted_specialty = parse_symptoms_to_specialty(prob_query)

    base_hospital_query = "SELECT * FROM hospitals"
    params = []
    if loc_query:
        base_hospital_query += " WHERE state LIKE ? OR city LIKE ?"
        like_str = '%' + loc_query + '%'
        params.extend([like_str, like_str])

    c.execute(base_hospital_query, params)
    hospital_rows = c.fetchall()
    hospitals = [dict(row) for row in hospital_rows]

    filtered_hospitals_result_list = []
    for h in hospitals:
        c.execute("SELECT * FROM doctors WHERE hospital_id = ?", (h['id'],))
        doctors_list = [dict(d) for d in c.fetchall()]

        if targeted_specialty:
            has_matching_specialist = any(d['specialty'] == targeted_specialty for d in doctors_list)
            if not has_matching_specialist:
                continue

        c.execute("SELECT username, rating, review_text FROM reviews WHERE hospital_id = ?", (h['id'],))
        h['reviews_list'] = [dict(r) for r in c.fetchall()]
        h['doctors_list'] = doctors_list

        if user_lat and user_lng:
            h['distance'] = haversine(float(user_lat), float(user_lng), h['lat'], h['lng'])
        else:
            h['distance'] = None

        filtered_hospitals_result_list.append(h)

    if user_lat and user_lng:
        filtered_hospitals_result_list.sort(key=lambda x: x['distance'] if x['distance'] is not None else float('inf'))

    c.execute("""
        SELECT d.name, d.specialty, h.name, h.city, a.date, a.time_slot, a.visit_type, a.id
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        JOIN hospitals h ON d.hospital_id = h.id
        WHERE a.user_id = ?
    """, (user_id,))
    user_appointments = c.fetchall()

    c.execute("SELECT state, COUNT(*) FROM hospitals GROUP BY state")
    chart_data = c.fetchall()
    labels = [row[0] for row in chart_data]
    values = [row[1] for row in chart_data]

    conn.close()
    return render_template_string(
        HTML,
        hospitals=filtered_hospitals_result_list,
        appointments=user_appointments,
        labels=labels,
        values=values,
        search_query=loc_query,
        problem_query=prob_query,
        targeted_specialty=targeted_specialty,
        user_lat=user_lat,
        user_lng=user_lng
    )

@app.route("/ai_triage_chat", methods=["POST"])
def ai_triage_chat():
    if "user" not in session:
        return jsonify({"reply": "Session closed."})
        
    user_message = request.form.get("message", "")
    specialty = ai_triage_engine(user_message)
    
    conn = sqlite3.connect("hospital.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("""
        SELECT d.name, h.name as hname, h.city 
        FROM doctors d 
        JOIN hospitals h ON d.hospital_id = h.id 
        WHERE d.specialty = ? AND d.status = 'Available Now' LIMIT 2
    """, (specialty,))
    matched_docs = c.fetchall()
    conn.close()
    
    if matched_docs:
        doc_suggestions = "<br><br><b>Available Specialists Found:</b>"
        for doc in matched_docs:
            doc_suggestions += f"<br>• {doc['name']} ({doc['hname']}, {doc['city']})"
        
        reply = f"Based on your symptoms, I recommend booking a <b>{specialty}</b>. I've updated your platform dashboard below to display these doctors. {doc_suggestions}"
    else:
        reply = f"Based on your symptoms, you should consult a <b>{specialty}</b>. Try checking nearby cities for available consulting physicians."

    return jsonify({"reply": reply, "specialty": specialty})

@app.route("/register", methods=["POST"])
def register():
    user = request.form["username"]
    pwd = request.form["password"]
    if len(user) < 3 or len(pwd) < 4:
        return render_template_string(HTML, error="Inputs are too short.")
    hashed_password = generate_password_hash(pwd, method="scrypt")
    conn = sqlite3.connect("hospital.db")
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users(username, password) VALUES (?,?)", (user, hashed_password))
        conn.commit()
        session["user"] = user
    except sqlite3.IntegrityError:
        conn.close()
        return render_template_string(HTML, error="Username is already taken.")
    conn.close()
    return redirect("/")

@app.route("/login", methods=["POST"])
def login():
    user = request.form["username"]
    pwd = request.form["password"]
    conn = sqlite3.connect("hospital.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (user,))
    row = c.fetchone()
    conn.close()
    if row and check_password_hash(row['password'], pwd):
        session["user"] = user
        return redirect("/")
    return render_template_string(HTML, error="Invalid username or password.")

@app.route("/book_appointment_node", methods=["POST"])
def book_appointment_node():
    if "user" not in session: return redirect("/")
    doc_id = request.form["doctor_id"]
    date = request.form["book_date"]
    time_slot = request.form["time_slot"]
    visit_type = request.form["visit_type"]

    conn = sqlite3.connect("hospital.db")
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username = ?", (session['user'],))
    user_id = c.fetchone()[0]

    c.execute("INSERT INTO appointments(user_id, doctor_id, date, time_slot, visit_type) VALUES (?,?,?,?,?)",
              (user_id, doc_id, date, time_slot, visit_type))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/cancel_appointment_node/<int:appt_id>")
def cancel_appointment_node(appt_id):
    if "user" not in session: return redirect("/")
    conn = sqlite3.connect("hospital.db")
    c = conn.cursor()
    c.execute("DELETE FROM appointments WHERE id = ?", (appt_id,))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)