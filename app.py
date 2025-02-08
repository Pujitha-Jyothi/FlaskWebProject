from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta 
import mysql.connector

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os
from flask import send_file

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for session management


import mysql.connector

'''def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",  # Replace with your MySQL username
        password="Puji@2004",  # Replace with your MySQL password
        database="firstdb"
    )
'''



# Database connection
db = mysql.connector.connect(
    host="localhost",
    user="root",  
    password="Puji@2004",  
    database="firstdb"
)



@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        cursor = db.cursor(dictionary=True)
        
        # Check if the user is a student
        cursor.execute("SELECT * FROM students WHERE student_roll_number = %s AND password = %s", (username, password))
        student = cursor.fetchone()
        
        if student:
            session['student_roll_number'] = student['student_roll_number']
            session['student_name'] = student['student_name']
            session['student_room_number'] = student['room_number']
            cursor.close()
            return redirect(url_for('student_home'))
        
        # Check if the user is a warden
        cursor.execute("SELECT * FROM warden WHERE warden_id = %s AND password = %s", (username, password))
        warden = cursor.fetchone()
        
        if warden:
            session['warden_name'] = warden['warden_name']
            session['warden_id'] = warden['warden_id']
            cursor.close()
            return redirect(url_for('warden_home'))
        
        # Check if the user is a management staff
        cursor.execute("SELECT * FROM management WHERE username = %s AND password = %s", (username, password))
        management = cursor.fetchone()
        
        if management:
            session['management_username'] = management['username']
            cursor.close()
            return redirect(url_for('management_home'))
        
        cursor.close()
        return "Invalid credentials, Please try again."

    return render_template('login.html')




@app.route('/student_home')
def student_home():
    if 'student_roll_number' in session:
        student_name = session.get('student_name')
        student_roll_number = session.get('student_roll_number')
        student_room_number = session.get('student_room_number')
        return render_template('student_home.html', 
                               student_name=student_name, 
                               student_roll_number=student_roll_number, 
                               student_room_number=student_room_number)
    else:
        return redirect(url_for('login'))


@app.route('/warden_home')
def warden_home():
    if 'warden_name' in session:
        warden_name = session.get('warden_name')
        return render_template('warden_home.html', warden_name=warden_name)
    else:
        return redirect(url_for('login'))


@app.route('/management_home')
def management_home():
    return render_template('management_home.html')


# Mess schedule for both student and warden
@app.route('/mess')
def mess_schedule():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM mess_schedule")
    mess_data = cursor.fetchall()
    cursor.close()

    organized_data = {day: {'Breakfast': '', 'Lunch': '', 'Dinner': ''} for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']}
    for row in mess_data:
        organized_data[row['day_of_week']][row['meal_type']] = row['menu']
    
    return render_template('mess.html', organized_data=organized_data)


@app.route('/warden_mess')
def warden_mess():
    if 'warden_name' not in session:
        return redirect(url_for('login'))
    
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM mess_schedule")
    mess_data = cursor.fetchall()
    cursor.close()

    organized_data = {day: {'Breakfast': '', 'Lunch': '', 'Dinner': ''} for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']}
    for row in mess_data:
        organized_data[row['day_of_week']][row['meal_type']] = row['menu']

    return render_template('warden_mess.html', organized_data=organized_data)


@app.route('/update_mess', methods=['GET', 'POST'])
def update_mess():
    if 'warden_name' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        day_of_week = request.form['day_of_week']
        meal_type = request.form['meal_type']
        new_menu = request.form['new_menu']
        
        cursor = db.cursor()
        cursor.execute("""
            UPDATE mess_schedule 
            SET menu = %s 
            WHERE day_of_week = %s AND meal_type = %s
        """, (new_menu, day_of_week, meal_type))
        db.commit()
        cursor.close()
        return redirect(url_for('warden_mess'))

    return render_template('update_mess.html')


@app.route('/preference_form')
def preference_form():
    if 'student_roll_number' not in session:
        return redirect(url_for('login'))
    
    student_roll_number = session.get('student_roll_number')
    student_room_number = session.get('student_room_number')

    return render_template('preference_form.html', 
                           student_roll_number=student_roll_number, 
                           student_room_number=student_room_number)


@app.route('/submit_preference', methods=['POST'])
def submit_preference():
    roll_number = session.get('student_roll_number')
    if not roll_number:
        return redirect(url_for('login'))

    preference = request.form['preference']

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT room_number FROM students WHERE student_roll_number = %s", (roll_number,))
    student = cursor.fetchone()

    if student:
        room_number = student['room_number']
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO mess_preferences (roll_number, room_number, preference)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE preference = %s
        """, (roll_number, room_number, preference, preference))
        db.commit()
        cursor.close()
    else:
        return "Student not found!"

    return redirect(url_for('student_home'))


@app.route('/warden_preferences')
def warden_preferences():
    if 'warden_name' not in session:
        return redirect(url_for('login'))
    
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT roll_number, room_number, preference FROM mess_preferences ORDER BY room_number")
    preferences = cursor.fetchall()
    cursor.close()

    preference_count = {
        'Veg': 0,
        'Non-Veg': 0
    }
    for preference in preferences:
        if preference['preference'] == 'Veg':
            preference_count['Veg'] += 1
        elif preference['preference'] == 'Non-Veg':
            preference_count['Non-Veg'] += 1

    return render_template('warden_preferences.html', 
                           preferences=preferences, 
                           preference_count=preference_count)


@app.route('/clear_preferences', methods=['POST'])
def clear_preferences():
    if 'warden_name' not in session:
        return redirect(url_for('login'))

    cursor = db.cursor()
    cursor.execute("TRUNCATE TABLE mess_preferences")
    db.commit()
    cursor.close()
    return redirect(url_for('warden_preferences'))





#good with numbers but not with Vasavi@123
from flask import session, request, redirect, url_for, flash, render_template
from werkzeug.security import check_password_hash, generate_password_hash

from flask import session, request, redirect, url_for, flash, render_template
from werkzeug.security import check_password_hash, generate_password_hash

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    # Verify user role and set table information based on session data
    if 'student_roll_number' in session:
        user_role = 'student'
        table = 'students'
        user_id_column = 'student_roll_number'
        user_id = session['student_roll_number']
    elif 'warden_id' in session:
        user_role = 'warden'
        table = 'warden'
        user_id_column = 'warden_id'
        user_id = session['warden_id']
    elif 'username' in session:
        user_role = 'management'
        table = 'management'
        user_id_column = 'username'
        user_id = session['username']
    else:
        return redirect(url_for('login'))

    if request.method == 'POST':
        current_password = request.form['current_password'].strip()
        new_password = request.form['new_password'].strip()
        confirm_password = request.form['confirm_password'].strip()

        cursor = db.cursor(dictionary=True)
        cursor.execute(f"SELECT password FROM {table} WHERE {user_id_column} = %s", (user_id,))
        result = cursor.fetchone()
        
        if result:
            # Use check_password_hash to compare the current password
            #if check_password_hash(result['password'], current_password):
            if result['password'] == current_password:
                if new_password == confirm_password:
                    # Hash the new password before saving it
                    #hashed_new_password = generate_password_hash(new_password)
                    cursor.execute(f"UPDATE {table} SET password = %s WHERE {user_id_column} = %s", (new_password, user_id))
                    db.commit()
                    flash("Password changed successfully!", "success")
                else:
                    flash("New passwords do not match.", "error")
            else:
                flash("Current password is incorrect.", "error")
        else:
            flash("User not found in database.", "error")
        
        cursor.close()
        return redirect(url_for('change_password'))

    return render_template('change_password.html')









@app.route('/feedback_form', methods=['GET'])
def feedback_form():
    return render_template('feedback_form.html')


@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    feedback_text = request.form.get('feedback_text')
    roll_number = request.form.get('roll_number')  # Optional roll number
    category = request.form.get('category', 'General')  # Default to 'General' if no category is provided
    
    cursor = db.cursor()
    
    # Insert-ing feedback into the database
    query = "INSERT INTO feedback (feedback_text, roll_number, category, status) VALUES (%s, %s, %s, %s)"
    cursor.execute(query, (feedback_text, roll_number if roll_number else None, category, 'Pending'))
    
    db.commit()
    cursor.close()
    
    return redirect(url_for('student_feedback'))







@app.route('/student_feedback')
def student_feedback():
    student_roll_number = session.get('student_roll_number')  # Assuming the student roll number is stored in session

    cursor = db.cursor(dictionary=True)

    # Query to fetch both the student's feedback (with roll number) and anonymous feedback (with NULL roll number)
    query = """
    SELECT id, feedback_text, category, response, status, roll_number
    FROM feedback
    WHERE roll_number = %s OR roll_number IS NULL
    """
    cursor.execute(query, (student_roll_number,))
    feedbacks = cursor.fetchall()

    cursor.close()

    # Render the student's feedback history, passing both feedback entries with roll number and anonymous feedback
    return render_template('student_feedback.html', feedbacks=feedbacks, roll_number=student_roll_number)



#management side logic....

# Route to display all feedback history (no actions allowed)
@app.route('/view_feedback', methods=['GET'])
def view_feedback():
    cursor = db.cursor(dictionary=True)
    
    # Fetch all feedback
    query = "SELECT id, feedback_text, category, response, status, roll_number FROM feedback"
    cursor.execute(query)
    feedbacks = cursor.fetchall()
    
    cursor.close()
    
    return render_template('view_feedback.html', feedbacks=feedbacks)

# Route to handle resolved feedback (view only)
@app.route('/resolved_feedback', methods=['GET'])
def resolved_feedback():
    cursor = db.cursor(dictionary=True)

    # Fetch all resolved feedback
    query = "SELECT id, feedback_text, category, response, status, roll_number FROM feedback WHERE status = 'Resolved'"
    cursor.execute(query)
    feedbacks = cursor.fetchall()

    cursor.close()

    return render_template('resolved_feedback.html', feedbacks=feedbacks)

# Route to display pending feedback with options to respond and resolve
@app.route('/pending_feedback', methods=['GET', 'POST'])
def pending_feedback():
    cursor = db.cursor(dictionary=True)

    # Fetch all pending feedback
    query = "SELECT id, feedback_text, category, response, status, roll_number FROM feedback WHERE status = 'Pending'"
    cursor.execute(query)
    feedbacks = cursor.fetchall()

    cursor.close()

    return render_template('pending_feedback.html', feedbacks=feedbacks)

# Route to handle response submission by the management from pending feedbacks
@app.route('/respond_pending_feedback', methods=['POST'])
def respond_pending_feedback():
    feedback_id = request.form.get('feedback_id')  # Feedback ID to identify which feedback to update
    response = request.form.get('response')  # Management's response
    status = request.form.get('status')  # New status (e.g., 'Resolved') like that

    cursor = db.cursor()

    # Update the feedback with the management's response and new status
    query = "UPDATE feedback SET response = %s, status = %s WHERE id = %s"
    cursor.execute(query, (response, status, feedback_id))

    db.commit()
    cursor.close()

    return redirect(url_for('pending_feedback'))  # Redirect back to pending feedback page



#Study Hours...


#In app.py, here’s the route for the warden to add study hour schedules:


# Assuming db is already initialized and connected to your MySQL database

@app.route('/add_study_hour', methods=['GET', 'POST'])
def add_study_hour():
    if request.method == 'POST':
        branch = request.form['branch']
        subject = request.form['subject']
        faculty = request.form['faculty']
        classroom = request.form['classroom']
        time = request.form['time']
        date = request.form['date']
        year = request.form['year']

        cursor = db.cursor()
        
        # Check if the current day is Monday
        if datetime.now().strftime("%A") == "Monday":
            delete_all_records()  # Delete all records from the table
        
        # Insert new study hour
        query = "INSERT INTO study_hours_new (branch, subject, faculty, classroom, time, date, year) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(query, (branch, subject, faculty, classroom, time, date, year))
        db.commit()

        cursor.close()

        return redirect(url_for('warden_home'))

    return render_template('add_study_hour.html')

def delete_all_records():
    cursor = db.cursor()
    query = "Truncate table study_hours_new"  # Delete all records from the table
    cursor.execute(query)
    db.commit()
    cursor.close()



   




#3. Display Schedule for Students by Branch

# Route for students to view their study hour schedule for the current day
from datetime import datetime, timedelta  # Make sure to have this import

@app.route('/student_study_hours')
def student_study_hours():
    # Check if the student_roll_number is in the session
    if 'student_roll_number' in session:
        student_roll_number = session['student_roll_number']  # Get the roll number from the session
        
        cursor = db.cursor()
        
        # Fetch the student's year and branch from the students table
        cursor.execute("SELECT branch_name, year FROM students WHERE student_roll_number = %s", (student_roll_number,))
        student_info = cursor.fetchone()

        if student_info:
            branch_name, year = student_info  # Extract branch and year
            
            # Fetch the study hour schedule based on the student's branch and year
            cursor.execute("SELECT subject, faculty, classroom, time, date FROM study_hours_new WHERE branch = %s AND year = %s", (branch_name, year))
            study_hours = cursor.fetchall()
            
            cursor.close()
            
            return render_template('student_study_hours.html', study_hours=study_hours)

    return redirect(url_for('login'))  # Redirect to login if not logged in

        
            


            





#Gate Pass...
# Gate Pass Module

@app.route('/request_gate_pass', methods=['GET', 'POST'])
def request_gate_pass():
    # Check if student_roll_number is in session
    if 'student_roll_number' not in session:
        return "Student ID not found in session.", 400  # Error if not in session
    
    student_id = session.get('student_roll_number')  # Get student ID from session
    
    if request.method == 'POST':
        # Ensure `student_id` is not None or empty
        if not student_id:
            return "Invalid student ID.", 400

        # Other form data
        outing_type = request.form['outing_type']
        purpose = request.form['purpose']
        outing_time = request.form['outing_time']
        expected_return = request.form['expected_return']
        
        # Insert into database
        cursor = db.cursor()
        query = """INSERT INTO gate_pass1 (student_id, outing_type, purpose, outing_time, expected_return)
                   VALUES (%s, %s, %s, %s, %s)"""
        cursor.execute(query, (student_id, outing_type, purpose, outing_time, expected_return))
        db.commit()
        cursor.close()

        return redirect(url_for('view_gate_passes'))

    return render_template('request_gate_pass.html')



@app.route('/view_gate_passes')
def view_gate_passes():
    cursor = db.cursor()
    student_roll_number = session.get('student_roll_number')
    query = "SELECT student_id,outing_type,purpose,outing_time,expected_return,actual_return,status FROM gate_pass1 where student_id=%s OR student_id IS NULL"
    cursor.execute(query, (student_roll_number,))
    passes = cursor.fetchall()
    cursor.close()

    return render_template('view_gate_passes.html', passes=passes)



#Warden Actions on the requests...
@app.route('/warden_view_requests')
def warden_view_requests():
    cursor = db.cursor()
    cursor.execute("SELECT * FROM gate_pass1 WHERE status = 'Pending'")
    requests = cursor.fetchall()
    cursor.close()
    return render_template('warden_view_requests.html', requests=requests)





# Assuming you have a warden's name stored in session or passed through some other means
@app.route('/warden_accept_request/<int:id>', methods=['POST'])
def warden_accept_request(id):
    accepted_by = request.form['accepted_by']  # Gets the selected option from the dropdown
    student_name = "Student1"  # Fetch student name from the database
    regd_number = "S001"  # Fetch registration number from the database
    date_of_exit = "28/11/2024"  # Current date or based on the form data
    time_of_exit = "4:30 PM"  # Current time or based on the form data
    
    # Generate the exit slip PDF
    exit_pdf_path = generate_gate_pass_pdf(student_name, regd_number, date_of_exit, time_of_exit, "Exit")
    entry_pdf_path = generate_gate_pass_pdf(student_name, regd_number, date_of_exit, time_of_exit, "Entry")

    # Update database status to accepted and record who accepted it
    cursor = db.cursor()
    cursor.execute("UPDATE gate_pass1 SET status = 'Accepted', accepted_by = %s WHERE id = %s", (accepted_by, id))
    db.commit()
    cursor.close()
    
    # Render approval confirmation page with links to download PDFs
    return render_template(
        'approval_confirmation.html', 
        exit_filename=os.path.basename(exit_pdf_path), 
        entry_filename=os.path.basename(entry_pdf_path)
    )


@app.route('/warden_reject_request/<int:id>', methods=['POST'])
def warden_reject_request(id):
    cursor = db.cursor()  # Use the existing db connection directly
    # Record who rejected the request, assuming warden's name is available
    rejected_by = "Warden Name Here"  # Replace with actual warden's name retrieval if available
    cursor.execute("UPDATE gate_pass1 SET status = 'Rejected', accepted_by = %s WHERE id = %s", (rejected_by, id))  # Store the name of the person who rejected
    db.commit()  # Commit the changes to the database
    cursor.close()  # Close the cursor
    return redirect(url_for('warden_view_requests'))  # Redirect to the view requests page









def generate_gate_pass_pdf(student_name, regd_number, date_of_exit, time_of_exit, slip_type):
    filename = f"{slip_type}_slip_{regd_number}.pdf"
    filepath = os.path.join('static', 'gate_pass_slips', filename)
    
    # Create a PDF canvas
    c = canvas.Canvas(filepath, pagesize=letter)
    width, height = letter
    
    # Set title
    c.setFont("Helvetica-Bold", 12)
    c.drawString(200, height - 50, "SRI VASAVI ENGINEERING COLLEGE (AUTONOMOUS)")
    c.drawString(200, height - 70, "Pedatadepalli, TADEPALLIGUDEM - 534 101")
     # Slip type and student details
    c.setFont("Helvetica-Bold", 14)
    c.drawString(250, height - 100, f"{slip_type.upper()} SLIP - HOSTEL STUDENT")
    
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 130, f"NAME OF THE STUDENT: {student_name}")
    c.drawString(50, height - 150, f"REGD NUMBER: {regd_number}")
    c.drawString(50, height - 170, f"DATE & TIME OF {slip_type.upper()}: {date_of_exit} {time_of_exit}")
    # Verification and footer
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 200, "Verified by")
    c.drawString(50, height - 220, "M V N A S DURGA BHAVANI (NT-LH-01)")
    c.drawString(450, height - 220, "WARDEN")
    
    # Save the PDF
    c.save()
    return filepath



  





#Add this route to handle PDF file downloads:...

@app.route('/download_pdf')
def download_pdf():
    file = request.args.get('file')
    file_path = os.path.join('static', 'gate_pass_slips', file)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return "File not found.", 404


#Laundary Management...








@app.route('/manage_students', methods=['GET', 'POST'])
def manage_students():
    cursor = db.cursor(dictionary=True)

    if request.method == 'POST':
        if 'add_student' in request.form:
            roll_number = request.form['student_roll_number'].strip()
            name = request.form['student_name'].strip()
            password = request.form['password'].strip()  # Consider hashing the password
            room_number = request.form['room_number'].strip()
            branch_name = request.form['branch_name'].strip()
            year = request.form['year'].strip()

            # Insert new student into the database
            cursor.execute(
                "INSERT INTO students (student_roll_number, student_name, password, room_number, branch_name, year) VALUES (%s, %s, %s, %s, %s, %s)",
                (roll_number, name, password, room_number, branch_name, year)
            )
            db.commit()
            flash("Student added successfully!", "success")

        elif 'delete_student' in request.form:
            roll_number = request.form['student_roll_number'].strip()
            # Delete the student from the database
            cursor.execute("DELETE FROM students WHERE student_roll_number = %s", (roll_number,))
            db.commit()
            flash("Student deleted successfully!", "success")

    # Fetch all students to display in the template
    cursor.execute("SELECT * FROM students")
    students = cursor.fetchall()
    cursor.close()

    return render_template('manage_students.html', students=students)





    




@app.route('/accepted_requests', methods=['GET'])
def accepted_requests():
    cursor = db.cursor(dictionary=True)

    # Fetch all accepted gate pass requests
    query = "SELECT id, student_id, outing_type, purpose, outing_time, expected_return, accepted_by FROM gate_pass1 WHERE status = 'Accepted'"
    cursor.execute(query)
    requests = cursor.fetchall()

    cursor.close()

    return render_template('warden_accepted_requests.html', requests=requests)

@app.route('/rejected_requests', methods=['GET'])
def rejected_requests():
    cursor = db.cursor(dictionary=True)

    # Fetch all rejected gate pass requests
    query = "SELECT id, student_id, outing_type, purpose, outing_time, expected_return, accepted_by FROM gate_pass1 WHERE status = 'Rejected'"
    cursor.execute(query)
    requests = cursor.fetchall()

    cursor.close()

    return render_template('warden_rejected_requests.html', requests=requests)




@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('login'))




















# Main entry point of the application
if __name__ == '__main__':
    app.run(debug=True)
