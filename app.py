import os
import sys
import traceback
from flask import Flask, render_template, request, redirect, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Try importing Supabase with error handling
try:
    from supabase import create_client, Client
    print("✅ Supabase imported successfully")
except ImportError as e:
    print(f"❌ Failed to import Supabase: {e}")
    sys.exit(1)

# Try importing dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ dotenv loaded successfully")
except ImportError:
    print("⚠️ python-dotenv not available, using environment variables directly")

app = Flask(__name__)

# Configuration with error checking
try:
    app.secret_key = os.getenv("SECRET_KEY")
    if not app.secret_key:
        print("❌ WARNING: SECRET_KEY not set!")
        app.secret_key = "fallback-secret-key-change-this"
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url:
        print("❌ ERROR: SUPABASE_URL not set!")
        raise ValueError("Missing SUPABASE_URL environment variable")
    
    if not supabase_key:
        print("❌ ERROR: SUPABASE_KEY not set!")
        raise ValueError("Missing SUPABASE_KEY environment variable")
    
    print(f"✅ Environment variables loaded:")
    print(f"   SUPABASE_URL: {supabase_url[:20]}...")
    print(f"   SUPABASE_KEY: {supabase_key[:20]}...")
    
    # Initialize Supabase client
    supabase: Client = create_client(supabase_url, supabase_key)
    print("✅ Supabase client created successfully")
    
except Exception as e:
    print(f"❌ Configuration error: {e}")
    supabase = None

# Slide content data with new structure
SLIDES_CONTENT = {
    1: {
        "title": "Introduction to the Internet",
        "content": [
            "Global network of interconnected computers",
            "Uses standardized communication protocols (TCP/IP)",
            "Enables worldwide information sharing and communication",
            "Infrastructure supporting various services and applications"
        ],
        "quiz": {
            "questions": [
                {
                    "id": 1,
                    "question": "What protocol does the Internet primarily use for communication?",
                    "options": ["HTTP", "TCP/IP", "FTP", "DNS"],
                    "correct": 1
                },
                {
                    "id": 2,
                    "question": "What is the main purpose of the Internet?",
                    "options": [
                        "Entertainment only",
                        "Worldwide information sharing and communication",
                        "Gaming purposes",
                        "Email only"
                    ],
                    "correct": 1
                },
                {
                    "id": 3,
                    "question": "The Internet is described as:",
                    "options": [
                        "A single computer",
                        "A local network",
                        "A global network of interconnected computers",
                        "A software application"
                    ],
                    "correct": 2
                }
            ]
        }
    },
    2: {
        "title": "Hardware Components",
        "content": [
            "Servers - Powerful computers that provide services and store data",
            "Routers - Direct data traffic between networks",
            "Cables - Physical connections (fiber optic, ethernet, etc.)",
            "Data centers - Large facilities housing servers and networking equipment"
        ],
        "quiz": {
            "questions": [
                {
                    "id": 1,
                    "question": "What is the primary function of routers?",
                    "options": [
                        "Store data permanently",
                        "Direct data traffic between networks",
                        "Display web pages",
                        "Create websites"
                    ],
                    "correct": 1
                },
                {
                    "id": 2,
                    "question": "Data centers are used for:",
                    "options": [
                        "Gaming only",
                        "Housing servers and networking equipment",
                        "Personal computers",
                        "Mobile phones"
                    ],
                    "correct": 1
                },
                {
                    "id": 3,
                    "question": "Which of these is NOT a type of cable used in networking?",
                    "options": [
                        "Fiber optic",
                        "Ethernet",
                        "Power cable",
                        "Coaxial"
                    ],
                    "correct": 2
                }
            ]
        }
    }
}

def get_user_role(user_id):
    """Get user role from database"""
    try:
        response = supabase.table("users").select("role").eq("id", user_id).execute()
        if response.data:
            return response.data[0].get("role", "student")
        return "student"
    except:
        return "student"

def get_activated_slides():
    """Get list of activated slides"""
    try:
        response = supabase.table("slide_activations").select("*").execute()
        if response.data:
            return {item["slide_number"]: item for item in response.data}
        return {}
    except:
        return {}

def is_slide_activated(slide_number):
    """Check if a specific slide is activated"""
    activated_slides = get_activated_slides()
    return slide_number in activated_slides and activated_slides[slide_number].get("is_active", False)

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/signup", methods=["POST"])
def signup():
    try:
        print("🔄 Signup attempt started")
        
        # Check if Supabase is available
        if not supabase:
            print("❌ Supabase client not available")
            flash("Database connection error. Please try again later.", "danger")
            return redirect("/")
        
        # Get form data
        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role", "student")  # Default to student
        
        print(f"📧 Email: {email}")
        print(f"🔒 Password length: {len(password) if password else 0}")
        print(f"👤 Role: {role}")
        
        if not email or not password:
            print("❌ Missing email or password")
            flash("Email and password are required.", "danger")
            return redirect("/")
        
        # Validate role
        if role not in ["student", "teacher"]:
            role = "student"
        
        # Hash the password
        print("🔄 Hashing password...")
        pw_hash = generate_password_hash(password)
        print("✅ Password hashed successfully")
        
        # Insert into Supabase
        print("🔄 Inserting user into database...")
        response = supabase.table("users").insert({
            "email": email,
            "password_hash": pw_hash,
            "role": role
        }).execute()
        
        print(f"📊 Database response: {response}")
        
        # Check for errors in response
        if hasattr(response, 'error') and response.error:
            print(f"❌ Database error: {response.error}")
            if "duplicate key" in str(response.error).lower():
                flash("An account with this email already exists.", "warning")
            else:
                flash(f"Sign-up error: {response.error}", "danger")
            return redirect("/")
        
        # Check if we got data back
        if not response.data or len(response.data) == 0:
            print("❌ No data returned from database")
            flash("Account creation failed. Please try again.", "danger")
            return redirect("/")
        
        # Success case
        user_data = response.data[0]
        user_id = user_data.get("id")
        user_role = user_data.get("role")
        
        if not user_id:
            print("❌ No user ID in response")
            flash("Account creation failed. Please try again.", "danger")
            return redirect("/")
        
        print(f"✅ User created successfully with ID: {user_id} and role: {user_role}")
        
        # Set session
        session["user"] = user_id
        session["email"] = email
        session["role"] = user_role
        flash(f"Welcome! Your {user_role} account has been created successfully.", "success")
        
        # Redirect based on role
        if user_role == "teacher":
            return redirect("/teacher_dashboard")
        else:
            return redirect("/dashboard")
        
    except Exception as e:
        print(f"❌ Signup error: {e}")
        print(f"📍 Traceback: {traceback.format_exc()}")
        flash("An unexpected error occurred during signup. Please try again.", "danger")
        return redirect("/")

@app.route("/login", methods=["POST"])
def login():
    try:
        print("🔄 Login attempt started")
        
        if not supabase:
            print("❌ Supabase client not available")
            flash("Database connection error. Please try again later.", "danger")
            return redirect("/")
        
        email = request.form.get("email")
        password = request.form.get("password")
        
        print(f"📧 Login email: {email}")
        
        if not email or not password:
            flash("Email and password are required.", "danger")
            return redirect("/")
        
        # Fetch user
        print("🔄 Fetching user from database...")
        response = supabase.table("users").select("*").eq("email", email).execute()
        
        print(f"📊 Login response: {response}")
        
        if not response.data:
            print("❌ No user found with this email")
            flash("No account found with that email.", "warning")
            return redirect("/")
        
        user = response.data[0]
        print(f"✅ User found: {user.get('id')} with role: {user.get('role')}")
        
        # Verify password
        if not check_password_hash(user["password_hash"], password):
            print("❌ Password verification failed")
            flash("Incorrect password.", "danger")
            return redirect("/")
        
        print("✅ Login successful")
        session["user"] = user["id"]
        session["email"] = email
        session["role"] = user.get("role", "student")
        flash(f"Welcome back! You've been logged in successfully as {session['role']}.", "success")
        
        # Redirect based on role
        if session["role"] == "teacher":
            return redirect("/teacher_dashboard")
        else:
            return redirect("/dashboard")
        
    except Exception as e:
        print(f"❌ Login error: {e}")
        print(f"📍 Traceback: {traceback.format_exc()}")
        flash("An unexpected error occurred during login. Please try again.", "danger")
        return redirect("/")

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        flash("Please log in to access the dashboard.", "warning")
        return redirect("/")
    
    # Redirect teachers to their dashboard
    if session.get("role") == "teacher":
        return redirect("/teacher_dashboard")
    
    try:
        user_id = session["user"]
        
        # Get user's quiz scores
        scores_response = supabase.table("quiz_scores").select("*").eq("user_id", user_id).execute()
        scores = scores_response.data if scores_response.data else []
        
        # Calculate progress
        slide_progress = {}
        total_score = 0
        for score in scores:
            slide_num = score["slide_number"]
            if slide_num not in slide_progress or score["score"] > slide_progress[slide_num]["score"]:
                slide_progress[slide_num] = score
        
        # Calculate total score
        for slide_num, score_data in slide_progress.items():
            total_score += score_data["score"]
        
        # Get activated slides for students
        activated_slides = get_activated_slides()
        
        return render_template("student_dashboard.html", 
                             user_email=session.get("email", ""),
                             slide_progress=slide_progress,
                             slides_content=SLIDES_CONTENT,
                             total_score=total_score,
                             activated_slides=activated_slides)
    except Exception as e:
        print(f"❌ Dashboard error: {e}")
        flash("Error loading dashboard.", "danger")
        return redirect("/")

@app.route("/teacher_dashboard")
def teacher_dashboard():
    if "user" not in session or session.get("role") != "teacher":
        flash("Access denied. Teacher account required.", "danger")
        return redirect("/")
    
    try:
        # Get all students and their progress
        students_response = supabase.table("users").select("id, email").eq("role", "student").execute()
        students = students_response.data if students_response.data else []
        
        # Get all quiz scores
        scores_response = supabase.table("quiz_scores").select("*, users(email)").execute()
        scores = scores_response.data if scores_response.data else []
        
        # Get activated slides
        activated_slides = get_activated_slides()
        
        # Calculate student progress
        student_progress = {}
        for student in students:
            student_id = student["id"]
            student_email = student["email"]
            student_scores = [score for score in scores if score["user_id"] == student_id]
            
            total_score = sum(score["score"] for score in student_scores)
            completed_slides = len(student_scores)
            
            student_progress[student_id] = {
                "email": student_email,
                "total_score": total_score,
                "completed_slides": completed_slides,
                "scores": {score["slide_number"]: score["score"] for score in student_scores}
            }
        
        return render_template("teacher_dashboard.html",
                             slides_content=SLIDES_CONTENT,
                             activated_slides=activated_slides,
                             student_progress=student_progress,
                             total_students=len(students))
    except Exception as e:
        print(f"❌ Teacher dashboard error: {e}")
        flash("Error loading teacher dashboard.", "danger")
        return redirect("/")

@app.route("/activate_slide", methods=["POST"])
def activate_slide():
    if "user" not in session or session.get("role") != "teacher":
        return jsonify({"error": "Access denied"}), 403
    
    try:
        data = request.json
        slide_number = data.get("slide_number")
        is_active = data.get("is_active", True)
        
        if slide_number not in SLIDES_CONTENT:
            return jsonify({"error": "Invalid slide number"}), 400
        
        # Check if activation record exists
        existing = supabase.table("slide_activations").select("*").eq("slide_number", slide_number).execute()
        
        activation_data = {
            "slide_number": slide_number,
            "is_active": is_active,
            "activated_by": session["user"],
            "activated_at": datetime.utcnow().isoformat()
        }
        
        if existing.data:
            # Update existing record
            supabase.table("slide_activations").update(activation_data).eq("slide_number", slide_number).execute()
        else:
            # Insert new record
            supabase.table("slide_activations").insert(activation_data).execute()
        
        action = "activated" if is_active else "deactivated"
        return jsonify({"success": True, "message": f"Slide {slide_number} {action} successfully"})
        
    except Exception as e:
        print(f"❌ Slide activation error: {e}")
        return jsonify({"error": "Failed to update slide activation"}), 500

@app.route("/slide/<int:slide_number>")
def show_slide(slide_number):
    if "user" not in session:
        flash("Please log in to access slides.", "warning")
        return redirect("/")
    
    if slide_number not in SLIDES_CONTENT:
        flash("Slide not found.", "danger")
        return redirect("/dashboard")
    
    # Check if user is student and if slide is activated
    if session.get("role") == "student" and not is_slide_activated(slide_number):
        flash("This slide has not been activated by your teacher yet.", "warning")
        return redirect("/dashboard")
    
    slide_data = SLIDES_CONTENT[slide_number]
    total_slides = len(SLIDES_CONTENT)
    
            return render_template("integrated_slide.html", 
                         slide_number=slide_number,
                         slide_data=slide_data,
                         total_slides=total_slides,
                         user_role=session.get("role"),
                         activated_slides=get_activated_slides())

@app.route("/quiz/<int:slide_number>")
def show_quiz(slide_number):
    if "user" not in session:
        flash("Please log in to access quizzes.", "warning")
        return redirect("/")
    
    if slide_number not in SLIDES_CONTENT:
        flash("Quiz not found.", "danger")
        return redirect("/dashboard")
    
    # Check if user is student and if slide is activated
    if session.get("role") == "student" and not is_slide_activated(slide_number):
        flash("This quiz has not been activated by your teacher yet.", "warning")
        return redirect("/dashboard")
    
    # Get user's current total score
    user_id = session["user"]
    scores_response = supabase.table("quiz_scores").select("*").eq("user_id", user_id).execute()
    scores = scores_response.data if scores_response.data else []
    
    total_score = sum(score["score"] for score in scores)
    
    quiz_data = SLIDES_CONTENT[slide_number]["quiz"]
            return render_template("quiz.html", 
                         slide_number=slide_number,
                         quiz_data=quiz_data,
                         slide_title=SLIDES_CONTENT[slide_number]["title"],
                         total_score=total_score,
                         user_role=session.get("role"))

@app.route("/submit_quiz", methods=["POST"])
def submit_quiz():
    if "user" not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    # Only students can submit quizzes
    if session.get("role") != "student":
        return jsonify({"error": "Only students can submit quizzes"}), 403
    
    try:
        data = request.json
        slide_number = data.get("slide_number")
        answers = data.get("answers", {})
        
        if slide_number not in SLIDES_CONTENT:
            return jsonify({"error": "Invalid slide number"}), 400
        
        # Check if slide is activated
        if not is_slide_activated(slide_number):
            return jsonify({"error": "This quiz is not activated"}), 403
        
        quiz_questions = SLIDES_CONTENT[slide_number]["quiz"]["questions"]
        
        # Calculate score
        correct_answers = 0
        total_questions = len(quiz_questions)
        
        for question in quiz_questions:
            question_id = str(question["id"])
            if question_id in answers and answers[question_id] == question["correct"]:
                correct_answers += 1
        
        score_percentage = (correct_answers / total_questions) * 100
        
        # Save score to database
        score_data = {
            "user_id": session["user"],
            "slide_number": slide_number,
            "score": score_percentage,
            "correct_answers": correct_answers,
            "total_questions": total_questions,
            "completed_at": datetime.utcnow().isoformat()
        }
        
        # Insert or update score
        existing_score = supabase.table("quiz_scores").select("*").eq("user_id", session["user"]).eq("slide_number", slide_number).execute()
        
        if existing_score.data:
            # Update existing score if new score is better
            if score_percentage > existing_score.data[0]["score"]:
                supabase.table("quiz_scores").update(score_data).eq("user_id", session["user"]).eq("slide_number", slide_number).execute()
        else:
            # Insert new score
            supabase.table("quiz_scores").insert(score_data).execute()
        
        # Get updated total score
        scores_response = supabase.table("quiz_scores").select("*").eq("user_id", session["user"]).execute()
        scores = scores_response.data if scores_response.data else []
        total_score = sum(score["score"] for score in scores)
        
        return jsonify({
            "success": True,
            "score": score_percentage,
            "correct_answers": correct_answers,
            "total_questions": total_questions,
            "total_score": total_score
        })
        
    except Exception as e:
        print(f"❌ Quiz submission error: {e}")
        return jsonify({"error": "Failed to submit quiz"}), 500

@app.route("/leaderboard")
def leaderboard():
    if "user" not in session:
        flash("Please log in to view leaderboard.", "warning")
        return redirect("/")
    
    try:
        # Get all scores with user emails (only students)
        scores_response = supabase.table("quiz_scores").select("*, users!inner(email, role)").eq("users.role", "student").execute()
        scores = scores_response.data if scores_response.data else []
        
        # Group by user and calculate total score
        user_totals = {}
        for score in scores:
            user_id = score["user_id"]
            email = score["users"]["email"]
            
            if user_id not in user_totals:
                user_totals[user_id] = {
                    "email": email,
                    "total_score": 0,
                    "completed_slides": 0
                }
            
            user_totals[user_id]["total_score"] += score["score"]
            user_totals[user_id]["completed_slides"] += 1
        
        # Calculate average and sort
        leaderboard_data = []
        for user_id, data in user_totals.items():
            avg_score = data["total_score"] / data["completed_slides"] if data["completed_slides"] > 0 else 0
            leaderboard_data.append({
                "email": data["email"],
                "avg_score": round(avg_score, 1),
                "completed_slides": data["completed_slides"],
                "total_score": round(data["total_score"], 1)
            })
        
        leaderboard_data.sort(key=lambda x: x["total_score"], reverse=True)
        
        return render_template("leaderboard.html", 
                             leaderboard=leaderboard_data,
                             user_role=session.get("role"))
        
    except Exception as e:
        print(f"❌ Leaderboard error: {e}")
        flash("Error loading leaderboard.", "danger")
        return redirect("/dashboard")

@app.route("/logout")
def logout():
    session.clear()
    flash("You've been logged out successfully.", "info")
    return redirect("/")

@app.route('/favicon.ico')
def favicon():
    return '', 204

# Health check endpoint
@app.route('/health')
def health():
    status = {
        "status": "healthy",
        "supabase": "connected" if supabase else "disconnected",
        "environment_vars": {
            "SECRET_KEY": "set" if os.getenv("SECRET_KEY") else "missing",
            "SUPABASE_URL": "set" if os.getenv("SUPABASE_URL") else "missing",
            "SUPABASE_KEY": "set" if os.getenv("SUPABASE_KEY") else "missing"
        }
    }
    return status

# Error handlers
@app.errorhandler(500)
def internal_error(error):
    print(f"❌ 500 Error: {error}")
    print(f"📍 Traceback: {traceback.format_exc()}")
    return "Internal Server Error - Check logs", 500

@app.errorhandler(404)
def not_found_error(error):
    return "Page not found", 404

if __name__ == "__main__":
    print("🚀 Starting Flask application...")
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)