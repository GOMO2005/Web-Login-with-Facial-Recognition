from flask import Flask, render_template, request, redirect, url_for, session
import cv2
import base64
import sqlite3
import numpy as np
import face_recognition
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secure session management

# Database setup
def create_db():
    conn = sqlite3.connect('user_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (username TEXT, face_data BLOB)''')
    conn.commit()
    conn.close()

# Root Route
@app.route('/')
def home():
    return redirect(url_for('login'))  # Redirect to the login page

# Route for Registration Page
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        
        # Capture face via webcam
        face_data = capture_face()
        
        if face_data:
            # Store face data securely
            store_face_data(username, face_data)
            return redirect(url_for('login'))
        else:
            return render_template('register.html', error="Failed to capture face. Please try again.")
    
    return render_template('register.html')

def capture_face():
    camera = cv2.VideoCapture(0)
    ret, frame = camera.read()
    if ret:
        _, buffer = cv2.imencode('.jpg', frame)
        encoded_face = base64.b64encode(buffer).decode('utf-8')
        camera.release()  # Release camera after capturing the image
        return encoded_face
    camera.release()  # Release the camera if capture failed
    return None

def store_face_data(username, face_data):
    conn = sqlite3.connect('user_data.db')
    c = conn.cursor()
    c.execute("INSERT INTO users (username, face_data) VALUES (?, ?)", (username, face_data))
    conn.commit()
    conn.close()

# Route for Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        
        # Capture face via webcam
        captured_face = capture_face()
        
        if captured_face and compare_faces(username, captured_face):
            # Store the username in session for successful login
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Face mismatch. Retry or use PIN.")
    
    return render_template('login.html')

def compare_faces(username, captured_face):
    # Retrieve stored face data from DB
    conn = sqlite3.connect('user_data.db')
    c = conn.cursor()
    c.execute("SELECT face_data FROM users WHERE username = ?", (username,))
    stored_face = c.fetchone()
    conn.close()
    
    if stored_face:
        # Decode stored face data
        stored_face_bytes = base64.b64decode(stored_face[0])
        np_array = np.frombuffer(stored_face_bytes, dtype=np.uint8)
        stored_image = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
        
        # Decode captured face data
        captured_face_img = base64.b64decode(captured_face)
        np_array = np.frombuffer(captured_face_img, dtype=np.uint8)
        captured_image = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
        
        # Get face encodings
        stored_face_encoding = face_recognition.face_encodings(stored_image)
        captured_face_encoding = face_recognition.face_encodings(captured_image)

        if stored_face_encoding and captured_face_encoding:
            # Compare the encodings (tolerance: how close the matches should be)
            match = face_recognition.compare_faces([stored_face_encoding[0]], captured_face_encoding[0])
            return match[0]
    return False

# Route for Dashboard (protected)
@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    return f"Welcome {session['username']} to your dashboard!"

if __name__ == '__main__':
    create_db()  # Ensure DB is set up when app starts
    app.run(debug=True)
