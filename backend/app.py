import os
import pandas as pd
import joblib
import requests
from flask import (
    Flask,
    url_for,
    render_template,
    send_from_directory,
    redirect,
    flash,
    request
)
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, logout_user, login_required

from forms import InputForm
from authenticate_forms import  SignupForm, LoginForm
from models import db, User  # Import the database and User model


csv_path = os.path.join(os.path.dirname(__file__), '..', 'IPL dataset final.csv')
df = pd.read_csv(csv_path)



# Initialize Flask App
app = Flask(__name__, template_folder="../templates", static_folder="../static")

# Configure the App
app.config["SECRET_KEY"] = "avighyan"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"  # Use a production-ready database in deployment
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize Extensions
db.init_app(app)  # Bind the database to the app
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# Ensure app context is set when using the database
with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Load ML Model
model_path = os.path.join(os.path.dirname(__file__), "..", "model.joblib")
model = joblib.load(model_path)

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

@app.route("/")
@app.route("/home")
def home():
    return render_template("home.html", title="Home")

@app.route("/predict", methods=["GET", "POST"])
def predict():
    form = InputForm()
    message = ""

    if form.validate_on_submit():
        x_new = pd.DataFrame(dict(
            batting_team=[form.batting_team.data],
            bowling_team=[form.bowling_team.data],
            city=[form.city.data],
            runs_left=[form.runs_left.data],
            balls_left=[form.balls_left.data],
            wickets=[form.wickets.data],
            total_runs_x=[form.total_runs_x.data],
            crr=[form.crr.data],
            rrr=[form.rrr.data]
        ))

        prediction_prob = model.predict_proba(x_new)[0]
        winning_team = form.batting_team.data if prediction_prob[1] > prediction_prob[0] else form.bowling_team.data
        message = f"The predicted winning team is: {winning_team}"

    return render_template("predict.html", title="Predict", form=form, output=message)



@app.route("/cricketer_info")
def cricketer_info():
    search_query = request.args.get("search", "").lower()
    if search_query:
        filtered_df = df[df["Player"].str.lower().str.contains(search_query, na=False)]
    else:
        filtered_df = df

    players = filtered_df.to_dict(orient="records")

    # Add image URLs
    
    return render_template("players.html", players=players, search_query=search_query)


@app.route('/quiz_trivia')
def quiz_trivia():
    questions = [
        {"question": "Which team won the first IPL title in 2008?", "options": ["CSK", "RCB", "RR", "KKR"]},
        {"question": "Who has scored the most runs in IPL history?", "options": ["Virat Kohli", "Suresh Raina", "David Warner", "Rohit Sharma"]},
        {"question": "Which player has taken the most wickets in IPL history?", "options": ["Lasith Malinga", "Amit Mishra", "Dwayne Bravo", "Yuzvendra Chahal"]},
        {"question": "Which IPL team has won the most titles?", "options": ["CSK", "MI", "KKR", "SRH"]},
        {"question": "Who hit the fastest century in IPL history?", "options": ["Chris Gayle", "AB de Villiers", "David Warner", "Yusuf Pathan"]},
        {"question": "Which player has the highest individual score in an IPL match?", "options": ["Brendon McCullum", "Chris Gayle", "Virender Sehwag", "KL Rahul"]},
        {"question": "Which team holds the record for the highest total in an IPL match?", "options": ["RCB", "MI", "CSK", "SRH"]},
        {"question": "Who was the captain of MI when they won their first IPL title?", "options": ["Sachin Tendulkar", "Ricky Ponting", "Harbhajan Singh", "Rohit Sharma"]},
        {"question": "Which bowler has the best bowling figures in a single IPL match?", "options": ["Sohail Tanvir", "Alzarri Joseph", "Anil Kumble", "Sunil Narine"]},
        {"question": "Which Indian player won the first-ever Orange Cap?", "options": ["Sachin Tendulkar", "Virat Kohli", "Gautam Gambhir", "Shaun Marsh"]}
    ]

    correct_answers = ["RR", "Virat Kohli", "Yuzvendra Chahal", "CSK", "Chris Gayle", "Chris Gayle", "RCB", "Rohit Sharma", "Alzarri Joseph", "Shaun Marsh"]

    return render_template("trivia.html", questions=questions, correct_answers=correct_answers)



@app.route("/signup", methods=["GET", "POST"])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            flash("Email already registered!", "danger")
            return redirect(url_for("signup"))

        new_user = User(username=form.username.data, email=form.email.data)
        new_user.set_password(form.password.data)
        db.session.add(new_user)
        db.session.commit()

        flash("Successfully Registered! Please log in.", "success")
        return redirect(url_for("home"))
    return render_template("signup.html", title="Sign Up", form=form)

@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash("Logged in Successfully!", "success")
            return redirect(url_for("home"))
        else:
            flash("Incorrect email or password", "danger")
    return render_template("login.html", title="Login", form=form)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully.", "info")
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
