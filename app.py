'''
Sets up the Flask application.
Defines the /budget route to display the form and handle form submissions.
Prints form data to the terminal upon successful submission.
Redirects to the same page to clear the form and prevent resubmission issues.

To run the code, copy and paste this:
export SECRET_KEY=$(python3 -c 'import os; print(os.urandom(24))')
python3 app.py
'''

import os
import sqlite3
from flask import Flask, render_template, redirect, url_for, request, jsonify
from forms import BudgetForm
import openai

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback_secret_key')

openai.api_key = ""

# Function to create the database table
def create_table():
    conn = sqlite3.connect('budgetbuddy.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS budget (
            id INTEGER PRIMARY KEY,
            income REAL,
            housing_utilities REAL,
            communication REAL,
            transportation REAL,
            education REAL,
            savings REAL,
            food REAL,
            entertainment REAL,
            health_personal_care REAL,
            clothing_laundry REAL,
            debt_payments REAL
        )
    ''')
    conn.commit()
    conn.close()

# Function to insert data into the database
def insert_budget_data(form_data):
    conn = sqlite3.connect('budgetbuddy.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO budget (income, housing_utilities, communication, transportation, education, savings, food, entertainment, health_personal_care, clothing_laundry, debt_payments)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', [float(data) for data in form_data])
    conn.commit()
    conn.close()

@app.route('/', methods=['GET', 'POST'])
def home():
    form = BudgetForm()
    if form.validate_on_submit():
        income = float(form.income.data)
        expenses = {
            'Needs': float(form.housing_utilities.data) + float(form.food.data) + float(form.transportation.data) + float(form.communication.data) + float(form.education.data) + float(form.health_personal_care.data),
            'Wants': float(form.entertainment.data) + float(form.clothing_laundry.data),
            'Savings or Debt Repayment': float(form.savings.data) + float(form.debt_payments.data)
        }
        percentages = {category: (amount / income) * 100 for category, amount in expenses.items()}
        ideal_amounts = {
            'Needs': income * 0.50,
            'Wants': income * 0.30,
            'Savings or Debt Repayment': income * 0.20
        }
        
        # Insert data into the database
        form_data = (
            form.income.data,
            form.housing_utilities.data,
            form.communication.data,
            form.transportation.data,
            form.education.data,
            form.savings.data,
            form.food.data,
            form.entertainment.data,
            form.health_personal_care.data,
            form.clothing_laundry.data,
            form.debt_payments.data
        )
        insert_budget_data(form_data)
        # Redirect to the summary page
        return redirect(url_for('summary'))
        
    return render_template('home.html', form=form)

@app.route('/chatbot')
def chatbot_site():
    return render_template('chatbot.html')

@app.route('/chat', methods=['POST'])
def chatbot():
    user_input = request.json.get('message')
    
    if user_input.lower() == 'exit':
        response = {"message": "Goodbye!"}
    else:
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Your name is Bud. Introduce yourself only on the first message. You are a financial planner tasked with helping the user make smarter financial decisions."},
                    {"role": "system", "content": "Limit your responses to 500 characters"}, 
                    {"role": "system", "content": "Be friendly and make sure your responses are clear and simple. Someone with no financial knowledge should understand"},
                    {"role": "system", "content": "Your audience is college students. Tailor your responses to the finances and situations of the typical American college student"},
                    {"role": "system", "content": "Offer practical tips and examples whenever possible."},
                    {"role": "system", "content": "If the user asks about budgeting, tell them about the 50/20/30 budget rule"}, 
                    {"role": "user", "content": user_input}
                ]
            )
            message = response['choices'][0]['message']['content'].strip()
            response = {"message": message}
        except Exception as e:
            response = {"message": "Something went wrong"}
    
    return jsonify(response)

def get_last_row():
    conn = sqlite3.connect("budgetbuddy.db")
    c = conn.cursor()
    c.execute('SELECT * FROM budget ORDER BY id DESC LIMIT 1')
    last_row = c.fetchone()
    conn.close()
    return last_row

@app.route('/summary')
def summary():
    last_row = get_last_row()
    if last_row:
        income = last_row[1]
        expenses = last_row[2:]
        
        needs = expenses[0] + expenses[5] + expenses[2] + expenses[1] + expenses[3] + expenses[7]
        wants = expenses[6] + expenses[8]
        savings_or_debt = expenses[4] + expenses[9]

        actual_amounts = {
            'Needs': needs,
            'Wants': wants,
            'Savings or Debt Repayment': savings_or_debt
        }

        actual_percentages = {
            'Needs': (needs / income) * 100 if income > 0 else 0,
            'Wants': (wants / income) * 100 if income > 0 else 0,
            'Savings or Debt Repayment': (savings_or_debt / income) * 100 if income > 0 else 0
        }

        ideal_amounts = {
            'Needs': income * 0.50,
            'Wants': income * 0.30,
            'Savings or Debt Repayment': income * 0.20
        }

        ideal_percentages = {
            'Needs': 50,
            'Wants': 30,
            'Savings or Debt Repayment': 20
        }
    else:
        income = 0
        expenses = []
        actual_amounts = {'Needs': 0, 'Wants': 0, 'Savings or Debt Repayment': 0}
        actual_percentages = {'Needs': 0, 'Wants': 0, 'Savings or Debt Repayment': 0}
        ideal_amounts = {'Needs': 0, 'Wants': 0, 'Savings or Debt Repayment': 0}
        ideal_percentages = {'Needs': 0, 'Wants': 0, 'Savings or Debt Repayment': 0}

    return render_template('summary.html', income=income, expenses = expenses, actual_amounts = actual_amounts, actual_percentages=actual_percentages, ideal_amounts=ideal_amounts, ideal_percentages=ideal_percentages)


if __name__ == '__main__':
    create_table()  # Create the database table if it doesn't exist
    app.run(debug=True)
    
