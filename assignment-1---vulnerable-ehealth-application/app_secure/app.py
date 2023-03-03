from datetime import date
import datetime 
import re

from flask import Flask, flash, render_template, request, url_for, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, TextAreaField, DateField
from wtforms.validators import InputRequired, Email, Length, ValidationError
from flask_bootstrap import Bootstrap
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import random
import string
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ThisIsAVerySecretKey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
Bootstrap(app)
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

#class Todo(db.Model):
#    id = db.Column(db.Integer, primary_key = True)
#    content = db.Column(db.String(200), nullable = False)
#    date_created = db.Column(db.DateTime, default = datetime.utcnow)
#
#    def __repr__(self):
#        return '<Task %r>' % self.id
with app.app_context():
    db.create_all()


class Exams(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    code = db.Column(db.String(100), nullable = False)
    content = db.Column(db.String(250), nullable = False)



class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(15), unique = True, nullable = False)
    password = db.Column(db.String(80), nullable = False)
    gender = db.Column(db.String(10), nullable = False)
    full_name = db.Column(db.String(80), nullable = False)
    email = db.Column(db.String(50), unique = True, nullable = False)
    admin = db.Column(db.Boolean, default = False)

    def __repr__(self):
        return '<User %r>' % self.username

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    speciality = db.Column(db.String(40), nullable = False)
    date = db.Column(db.String(11), nullable = False)
    time = db.Column(db.String(20), nullable = False)
    doctor = db.Column(db.String(20), nullable = False)
    patient = db.Column(db.String(20), nullable = False)

    def __repr__(self):
        return '<Appointment %r>' % self.id

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def get_random_string(length):
    # choose from all lowercase letter
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str


class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(30), nullable = False)
    email = db.Column(db.String(50), nullable = False)
    message = db.Column(db.String(300), nullable = False)
    code = get_random_string(10)

    def __repr__(self):
        return '<Ticket %r>' % self.id
class TicketForm(FlaskForm):
    name = StringField('Name', validators = [InputRequired(), Length(min = 4, max = 30)])
    email = StringField('Email', validators = [InputRequired(), Email(message = 'Invalid email'), Length(max = 50)])
    message = TextAreaField('Message', validators = [InputRequired(), Length(min = 4, max = 300)], )

class LoginForm(FlaskForm):
    username = StringField('username', validators = [InputRequired(), Length(min = 4, max = 20)])
    password = PasswordField('password', validators = [InputRequired(), Length(min = 8, max = 80)])
    remember = BooleanField('remember me')

class ExamForm(FlaskForm):
    code = StringField('Code', validators = [InputRequired()])

def password_check(form,field):
    password = form.password.data
    if len(password)< 4:
        raise ValidationError('Password must be at lest 8 letters long')
    elif re.search('[0-9]',password) is None:
        raise ValidationError('Password must contain a number')
    elif re.search('[A-Z]',password) is None:
        raise ValidationError('Password must have one uppercase letter')

class RegisterForm(FlaskForm):
    gender = SelectField('Gender', choices=(('Male'),('Female'),('Other'),('Prefer not to say')))
    email = StringField('Email', validators = [InputRequired(), Email(message = 'Invalid email'), Length(max = 50)])
    full_name = StringField('Full name', validators = [InputRequired(), Length(min = 3, max = 50)])
    username = StringField('Username', validators = [InputRequired(), Length(min = 4, max = 15)])
    password = PasswordField('Password', validators = [InputRequired(), password_check])

class AppointmentForm(FlaskForm):

    date = DateField('Date', validators = [InputRequired()])
    speciality = SelectField('Speciality', choices=(('Cardiology'),('Dermatology'),('Gastroenterology'),('General Surgery'),('Neurology'),('Oncology'),('Orthopedics'),('Otolaryngology'),('Pediatrics'),('Psychiatry'),('Urology')))
    time = SelectField('Time', validators = [InputRequired()], choices = (('9:00'),('10:00'),('11:00'),('12:00'),('13:00'),('14:00'),('15:00'),('16:00'),('17:00')))
    doctor = SelectField('Doctor', validators = [InputRequired()], choices = (('Dr. John Francis'),('Dr. Lane Andrew'),('Dr. Jack German'),('Dr. Bill Green'),('Dr. Joe Orthen'),('Dr. Jim Toe')))
    patient = StringField('Patient')

class InsertDoctorsForm(FlaskForm):
    gender = SelectField('Gender', choices=(('Male'),('Female'),('Other'),('Prefer not to say')))
    email = StringField('Email', validators = [InputRequired(), Email(message = 'Invalid email'), Length(max = 50)])
    full_name = StringField('Full name', validators = [InputRequired(), Length(min = 3, max = 50)])
    username = StringField('Username', validators = [InputRequired(), Length(min = 4, max = 15)])
    password = PasswordField('Password', validators = [InputRequired(), Length(min = 8, max = 80)])
    admin = BooleanField('Admin')

class SearchDoc(FlaskForm):
    name = StringField('Name', validators = [Length(min = 0, max = 200)])

@app.route('/admin', methods = ['GET', 'POST'])
def admin():
    form = InsertDoctorsForm()

    if form.validate_on_submit():
        admin = User(username = form.username.data, password = generate_password_hash (form.password.data, method='pbkdf2:sha256', salt_length=8), gender = form.gender.data, full_name = form.full_name.data, email = form.email.data, admin = form.admin.data)
        db.session.add(admin)
        db.session.commit()
        print("Admin added")
        return '<h1>Admin added</h1>'

    return render_template('admin.html', form = form)

@app.route('/', methods=['POST', 'GET'])
def index():
    return render_template('index.html')
@app.route('/ticket', methods=['POST', 'GET'])
def ticket():
    form = TicketForm()
    if form.validate_on_submit():
        ticket = Ticket(name = form.name.data, email = form.email.data, message = form.message.data)
        db.session.add(ticket)
        db.session.commit()
        return redirect('/')
    else:
        return render_template('ticket.html', form = form)

@app.route('/all_tickets', methods=['POST', 'GET'])
def alltickets():
    tickets = Ticket.query.all()
    users = User.query.all()

    return render_template('all_tickets.html', tickets = tickets, users = users)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            password = user.password
            if check_password_hash(password, form.password.data):
                login_user(user, remember = form.remember.data)
                return redirect(url_for('dashboard'))
        return '<h1>Invalid username or password</h1>'
    return render_template('login.html', form=form)

@app.route('/exams', methods=['GET', 'POST'])
@login_required
def exams():
    form = ExamForm()

    if form.validate_on_submit():
        exam = Exams.query.filter_by(code=form.code.data).first()
        if exam:
            return render_template('result_exam.html', exam = exam)
        else:
            flash('Exam not found')
            return redirect(url_for('exams', form = form))

    return render_template('exams.html', form = form)

@app.route('/result_exam', methods=['GET', 'POST'])
def result_exam():
    return render_template('result_exam.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = RegisterForm()
    if form.validate_on_submit():
        # passar a data à db quando for instanciado um novo user
        new_user = User(username = form.username.data,gender = form.gender.data, full_name = form.full_name.data, email = form.email.data, password = generate_password_hash (form.password.data))
        db.session.add(new_user)
        db.session.commit()
        return '<h1>new user has been created</h1>'

    return render_template('signup.html', form=form)

@app.route('/dashboard')
@login_required     # só se pode entar na dashboard se estiver logado
def dashboard():
    return render_template('dashboard.html', name=current_user.full_name, gender = current_user.gender)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/makeAppointment', methods=['GET', 'POST'])
@login_required
def makeAppointment():
    form = AppointmentForm()
    if form.validate_on_submit():
        data_toda = form.date.data
        data = data_toda.strftime("%d/%m/%Y")
        appointment = Appointment(date = data, speciality = form.speciality.data, time = form.time.data, doctor = form.doctor.data, patient = current_user.full_name)
        db.session.add(appointment)
        db.session.commit()
        return redirect('/allAppointments')
    return render_template('makeAppointment.html', form = form, name = current_user.full_name)


@app.route('/allAppointments', methods=['GET', 'POST'])
def allAppointments():
    if(Appointment.query.filter_by(patient=current_user.full_name) != None):
        appointments = Appointment.query.filter_by(patient=current_user.full_name).all()
        return render_template('allAppointments.html', appointments = appointments, name = current_user.full_name)
    return render_template('allAppointments.html')

@app.route('/doctors', methods=['GET', 'POST'])
def doctors():
    form = SearchDoc()
    print(f"{form.name.data} e {form.validate_on_submit()}")
    if form.validate_on_submit() and form.name.data != "":
        doctors = User.query.filter_by(admin=True, full_name=form.name.data).all()
        if doctors:
            admins = []
            for doc in doctors:
                admins.append(doc.full_name)
            return render_template('doctors.html', doctors = admins, form = form)
        else:
            flash(f'Doctor {form.name.data} not found')
            return render_template('doctors.html', doctors = [], form = form)
    else:
        flash('')
        doctors = User.query.filter_by(admin=True).all()
        admins = []
        for doc in doctors:
            admins.append(doc.full_name)
        return render_template('doctors.html', doctors = admins, form = form)


if __name__ == '__main__':
    app.run(debug=True, port = 3000)