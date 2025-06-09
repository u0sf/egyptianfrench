from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import pandas as pd
import os
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///students.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx'}

# Create uploads directory if it doesn't exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Create backups directory if it doesn't exist
if not os.path.exists('backups'):
    os.makedirs('backups')

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database Models
class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    students = db.relationship('Student', backref='department', lazy=True)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_authenticated = db.Column(db.Boolean, default=True)
    is_anonymous = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return str(self.id)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seat_number = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=False)
    grades = db.relationship('Grade', backref='student', lazy=True)

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=False)
    grades = db.relationship('Grade', backref='subject', lazy=True)

class Grade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    grade = db.Column(db.Float, nullable=False)

class News(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500))
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.now)

class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500))
    date_achieved = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    file_url = db.Column(db.String(500), nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

def init_db():
    with app.app_context():
        # Drop all tables
        db.drop_all()
        # Create all tables
        db.create_all()
        
        # Create default admin user
        admin = User(username='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

# Initialize database
init_db()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def calculate_status(grades):
    if not grades:
        return 'No Grades'
    return 'Pass' if all(grade.grade >= 50 for grade in grades) else 'Fail'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Student Routes
@app.route('/')
def home():
    news = News.query.order_by(News.date_posted.desc()).all()
    achievements = Achievement.query.order_by(Achievement.date_achieved.desc()).all()
    return render_template('home.html', news=news, achievements=achievements)

@app.route('/results', methods=['POST'])
def results():
    seat_number = request.form.get('seat_number')
    student = Student.query.filter_by(seat_number=seat_number).first()
    
    if not student:
        flash('Student not found!', 'error')
        return redirect(url_for('home'))
    
    grades = Grade.query.filter_by(student_id=student.id).all()
    status = calculate_status(grades)
    
    return render_template('results.html', student=student, grades=grades, status=status)

# Admin Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        
        flash('Invalid username or password!', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    selected_department = request.args.get('department', '')
    students = []
    subjects = []
    
    if selected_department:
        department = Department.query.filter_by(name=selected_department).first()
        if department:
            students = Student.query.filter_by(department_id=department.id).all()
            subjects = Subject.query.filter_by(department_id=department.id).all()
    
    return render_template('admin_dashboard.html', 
                         students=students, 
                         subjects=subjects, 
                         calculate_status=calculate_status,
                         selected_department=selected_department)

@app.route('/admin/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        flash('No file uploaded!', 'error')
        return redirect(url_for('admin_dashboard'))
    
    file = request.files['file']
    department_name = request.form.get('department')
    
    if not department_name:
        flash('Please select a department!', 'error')
        return redirect(url_for('admin_dashboard'))
    
    if file.filename == '':
        flash('No file selected!', 'error')
        return redirect(url_for('admin_dashboard'))
    
    if not file.filename.endswith('.xlsx'):
        flash('Please upload an Excel file (.xlsx)!', 'error')
        return redirect(url_for('admin_dashboard'))
    
    try:
        df = pd.read_excel(file)
        
        # Get or create department
        department = Department.query.filter_by(name=department_name).first()
        if not department:
            department = Department(name=department_name)
            db.session.add(department)
            db.session.commit()
        
        # Get subject names from Excel columns (excluding first two columns)
        subject_names = df.columns[2:].tolist()
        
        # Get all existing subjects for this department
        existing_subjects = Subject.query.filter_by(department_id=department.id).all()
        existing_subject_names = [subject.name for subject in existing_subjects]
        
        # Delete subjects that are not in the new Excel file
        for subject in existing_subjects:
            if subject.name not in subject_names:
                # Delete all grades for this subject
                Grade.query.filter_by(subject_id=subject.id).delete()
                # Delete the subject
                db.session.delete(subject)
        
        # Create new subjects if they don't exist
        for subject_name in subject_names:
            subject = Subject.query.filter_by(name=subject_name, department_id=department.id).first()
            if not subject:
                subject = Subject(name=subject_name, department_id=department.id)
                db.session.add(subject)
        
        db.session.commit()
        
        for _, row in df.iterrows():
            seat_number = str(row[0])
            name = str(row[1])
            
            student = Student.query.filter_by(seat_number=seat_number, department_id=department.id).first()
            if not student:
                student = Student(seat_number=seat_number, name=name, department_id=department.id)
                db.session.add(student)
                db.session.commit()
            
            # Process grades for each subject
            for subject_name in subject_names:
                grade_value = row[subject_name]
                if pd.notna(grade_value):  # Check if grade is not NaN
                    subject = Subject.query.filter_by(name=subject_name, department_id=department.id).first()
                    existing_grade = Grade.query.filter_by(
                        student_id=student.id,
                        subject_id=subject.id
                    ).first()
                    
                    if existing_grade:
                        existing_grade.grade = float(grade_value)
                    else:
                        new_grade = Grade(
                            student_id=student.id,
                            subject_id=subject.id,
                            grade=float(grade_value)
                        )
                        db.session.add(new_grade)
        
        db.session.commit()
        flash('Grades uploaded successfully!', 'success')
        
    except Exception as e:
        flash(f'Error uploading file: {str(e)}', 'error')
    
    return redirect(url_for('admin_dashboard', department=department_name))

@app.route('/admin/add_student', methods=['POST'])
@login_required
def add_student():
    seat_number = request.form.get('seat_number')
    name = request.form.get('name')
    
    if Student.query.filter_by(seat_number=seat_number).first():
        flash('Student with this seat number already exists!', 'error')
    else:
        student = Student(seat_number=seat_number, name=name)
        db.session.add(student)
        db.session.commit()
        flash('Student added successfully!', 'success')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_grade', methods=['POST'])
@login_required
def add_grade():
    student_id = request.form.get('student_id')
    subject_name = request.form.get('subject')
    grade_value = request.form.get('grade')
    
    subject = Subject.query.filter_by(name=subject_name).first()
    if not subject:
        subject = Subject(name=subject_name)
        db.session.add(subject)
        db.session.commit()
    
    grade = Grade(
        student_id=student_id,
        subject_id=subject.id,
        grade=float(grade_value)
    )
    db.session.add(grade)
    db.session.commit()
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/edit_grade/<int:grade_id>', methods=['POST'])
@login_required
def edit_grade(grade_id):
    grade = Grade.query.get_or_404(grade_id)
    grade.grade = float(request.form.get('grade'))
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_grade/<int:grade_id>')
@login_required
def delete_grade(grade_id):
    grade = Grade.query.get_or_404(grade_id)
    db.session.delete(grade)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_all_grades')
@login_required
def delete_all_grades():
    Grade.query.delete()
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_all_students')
@login_required
def delete_all_students():
    Grade.query.delete()
    Student.query.delete()
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/news/add', methods=['GET', 'POST'])
@login_required
def add_news():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        image_url = request.form.get('image_url')
        
        news = News(title=title, content=content, image_url=image_url)
        db.session.add(news)
        db.session.commit()
        flash('News added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('add_news.html')

@app.route('/admin/news/delete/<int:news_id>')
@login_required
def delete_news(news_id):
    news = News.query.get_or_404(news_id)
    db.session.delete(news)
    db.session.commit()
    flash('News deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/achievement/add', methods=['GET', 'POST'])
@login_required
def add_achievement():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        image_url = request.form.get('image_url')
        
        achievement = Achievement(title=title, description=description, image_url=image_url)
        db.session.add(achievement)
        db.session.commit()
        flash('Achievement added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('add_achievement.html')

@app.route('/admin/achievement/delete/<int:achievement_id>')
@login_required
def delete_achievement(achievement_id):
    achievement = Achievement.query.get_or_404(achievement_id)
    db.session.delete(achievement)
    db.session.commit()
    flash('Achievement deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/schedule/add', methods=['GET', 'POST'])
@login_required
def add_schedule():
    if request.method == 'POST':
        title = request.form.get('title')
        file = request.files.get('file')
        
        if file:
            # Create directories if they don't exist
            os.makedirs('uploads/schedules', exist_ok=True)
            
            # Secure the filename
            filename = secure_filename(file.filename)
            file_url = os.path.join('uploads', 'schedules', filename)
            
            # Save file
            file.save(file_url)
            
            schedule = Schedule(title=title, file_url=file_url)
            db.session.add(schedule)
            db.session.commit()
            flash('Schedule added successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
    
    return render_template('add_schedule.html')

@app.route('/admin/schedule/delete/<int:schedule_id>')
@login_required
def delete_schedule(schedule_id):
    schedule = Schedule.query.get_or_404(schedule_id)
    db.session.delete(schedule)
    db.session.commit()
    flash('Schedule deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/schedule/delete_all', methods=['POST'])
@login_required
def delete_all_schedules():
    schedules = Schedule.query.all()
    for schedule in schedules:
        # Remove the file from the filesystem if it exists
        try:
            if os.path.exists(schedule.file_url):
                os.remove(schedule.file_url)
        except Exception as e:
            pass  # Ignore file errors
        db.session.delete(schedule)
    db.session.commit()
    flash('تم حذف جميع الجداول بنجاح!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/schedules')
def schedules():
    schedules = Schedule.query.order_by(Schedule.date_posted.desc()).all()
    return render_template('schedules.html', schedules=schedules)

@app.route('/grades')
def grades():
    return render_template('grades.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Create admin user if not exists
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin')
            admin.set_password('admin')
            db.session.add(admin)
            db.session.commit()
    app.run(debug=True) 