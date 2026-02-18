from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
import json
import os
from datetime import datetime
import plotly.graph_objs as go
import plotly.express as px
from plotly.utils import PlotlyJSONEncoder
import calendar

app = Flask(__name__)

# File paths
EXPENSES_FILE = 'expenses.json'
BUDGET_FILE = 'budget.json'
INCOME_FILE = 'income.json'

# Categories
CATEGORIES = ['Food', 'Transport', 'Shopping', 'Entertainment', 'Bills', 'Healthcare', 'Education', 'Other']

def load_expenses():
    """Load expenses from JSON file"""
    if os.path.exists(EXPENSES_FILE):
        try:
            with open(EXPENSES_FILE, 'r') as f:
                content = f.read()
                if content.strip():
                    return json.loads(content)
        except json.JSONDecodeError:
            print("Error reading expenses.json, returning empty list")
            return []
    return []

def save_expenses(expenses):
    """Save expenses to JSON file"""
    try:
        with open(EXPENSES_FILE, 'w') as f:
            json.dump(expenses, f, indent=2)
    except Exception as e:
        print(f"Error saving expenses: {e}")

def load_budget():
    """Load budget from JSON file"""
    if os.path.exists(BUDGET_FILE):
        try:
            with open(BUDGET_FILE, 'r') as f:
                content = f.read()
                if content.strip():
                    return json.loads(content)
        except json.JSONDecodeError:
            print("Error reading budget.json, returning default budget")
            return {cat: 0 for cat in CATEGORIES}
    return {cat: 0 for cat in CATEGORIES}

def save_budget(budget):
    """Save budget to JSON file"""
    try:
        with open(BUDGET_FILE, 'w') as f:
            json.dump(budget, f, indent=2)
    except Exception as e:
        print(f"Error saving budget: {e}")

def load_income():
    """Load monthly income from JSON file"""
    if os.path.exists(INCOME_FILE):
        try:
            with open(INCOME_FILE, 'r') as f:
                content = f.read()
                if content.strip():
                    data = json.loads(content)
                    return data.get('monthly_income', 0)
        except json.JSONDecodeError:
            print("Error reading income.json, returning 0")
            return 0
    return 0

def save_income(monthly_income):
    """Save monthly income to JSON file"""
    try:
        with open(INCOME_FILE, 'w') as f:
            json.dump({'monthly_income': monthly_income}, f, indent=2)
    except Exception as e:
        print(f"Error saving income: {e}")

def get_current_month_expenses(expenses):
    """Filter expenses for current month only"""
    if not expenses:
        return []
    
    now = datetime.now()
    current_year = now.year
    current_month = now.month
    
    monthly_expenses = []
    for exp in expenses:
        exp_date = datetime.strptime(exp['date'], '%Y-%m-%d')
        if exp_date.year == current_year and exp_date.month == current_month:
            monthly_expenses.append(exp)
    
    return monthly_expenses

def analyze_expenses(expenses, budget, monthly_income):
    """Analyze expenses and generate insights for current month"""
    
    # Filter for current month only
    monthly_expenses = get_current_month_expenses(expenses)
    
    # Get current month info
    now = datetime.now()
    month_name = calendar.month_name[now.month]
    year = now.year
    
    if not monthly_expenses:
        return {
            'total_spent': 0,
            'total_budget': sum(budget.values()),
            'remaining': sum(budget.values()),
            'monthly_income': monthly_income,
            'money_left': monthly_income,
            'category_totals': {cat: 0 for cat in CATEGORIES},
            'tips': ['Start logging your expenses to get personalized tips!'],
            'month_name': month_name,
            'year': year,
            'savings': monthly_income - sum(budget.values()) if monthly_income > 0 else 0
        }
    
    df = pd.DataFrame(monthly_expenses)
    df['amount'] = pd.to_numeric(df['amount'])
    
    # Calculate totals
    total_spent = df['amount'].sum()
    total_budget = sum(budget.values())
    remaining_budget = total_budget - total_spent
    money_left = monthly_income - total_spent
    planned_savings = monthly_income - total_budget if monthly_income > 0 else 0
    
    # Category totals
    category_totals = df.groupby('category')['amount'].sum().to_dict()
    for cat in CATEGORIES:
        if cat not in category_totals:
            category_totals[cat] = 0
    
    # Generate tips
    tips = generate_tips(category_totals, budget, total_spent, total_budget, monthly_income, money_left)
    
    return {
        'total_spent': round(total_spent, 2),
        'total_budget': total_budget,
        'remaining': round(remaining_budget, 2),
        'monthly_income': monthly_income,
        'money_left': round(money_left, 2),
        'category_totals': category_totals,
        'tips': tips,
        'month_name': month_name,
        'year': year,
        'savings': round(planned_savings, 2)
    }

def generate_tips(category_totals, budget, total_spent, total_budget, monthly_income, money_left):
    """Generate personalized saving tips"""
    tips = []
    
    # Income vs Spending check
    if monthly_income > 0:
        if total_spent > monthly_income:
            overspend = total_spent - monthly_income
            tips.append(f"🚨 ALERT: You've spent ${overspend:.2f} more than your monthly income! Urgent action needed.")
        elif money_left < monthly_income * 0.1:
            tips.append(f"⚠️ Warning: Only ${money_left:.2f} left from your monthly income. Be careful with spending!")
        elif money_left > monthly_income * 0.2:
            savings_percent = (money_left / monthly_income) * 100
            tips.append(f"💰 Excellent! You still have ${money_left:.2f} ({savings_percent:.1f}%) remaining this month.")
    
    # Budget check
    if total_spent > total_budget:
        overspend = total_spent - total_budget
        tips.append(f"⚠️ You're over your monthly budget by ${overspend:.2f}. Review your spending!")
    
    # Category-specific tips
    for category, spent in category_totals.items():
        if spent == 0:
            continue
            
        category_budget = budget.get(category, 0)
        
        if category_budget > 0 and spent > category_budget:
            over = spent - category_budget
            percentage = (over / category_budget) * 100
            tips.append(f"💡 {category}: ${over:.2f} ({percentage:.1f}%) over budget. Try to cut back here.")
        
        # Specific category tips
        if category == 'Food' and spent > 300:
            tips.append(f"🍽️ Food expenses are ${spent:.2f} this month. Meal planning could save you 20-30%.")
        
        if category == 'Transport' and spent > 200:
            tips.append(f"🚗 Transport costs ${spent:.2f}. Consider carpooling or public transit to save.")
        
        if category == 'Entertainment' and spent > 150:
            tips.append(f"🎬 Entertainment: ${spent:.2f}. Look for free activities or share subscriptions.")
        
        if category == 'Shopping' and spent > 250:
            tips.append(f"🛍️ Shopping: ${spent:.2f}. Try the 30-day rule before buying non-essentials.")
    
    # Saving tips
    if total_budget > 0 and monthly_income > 0:
        savings_rate = ((monthly_income - total_spent) / monthly_income) * 100 if total_spent < monthly_income else 0
        
        if savings_rate > 20:
            tips.append(f"✅ Outstanding! You're saving {savings_rate:.1f}% of your income this month.")
        elif savings_rate > 10:
            tips.append(f"👍 Good job! Saving {savings_rate:.1f}%. Try to reach 20% for financial security.")
        elif savings_rate > 0:
            tips.append(f"📊 Currently saving {savings_rate:.1f}%. Aim for at least 10-20% monthly savings.")
    
    # General tips
    if len(tips) < 3:
        tips.extend([
            "💰 Track every expense - small purchases add up quickly!",
            "📅 Review your spending weekly to stay on track.",
            "🎯 Set specific savings goals to stay motivated."
        ])
    
    return tips[:6]  # Return top 6 tips

@app.route('/')
def index():
    """Render main page"""
    return render_template('index.html', categories=CATEGORIES)

@app.route('/api/expenses', methods=['GET'])
def get_expenses():
    """Get all expenses"""
    expenses = load_expenses()
    budget = load_budget()
    monthly_income = load_income()
    analysis = analyze_expenses(expenses, budget, monthly_income)
    
    # Only return current month's expenses for display
    monthly_expenses = get_current_month_expenses(expenses)
    
    return jsonify({
        'expenses': monthly_expenses,
        'analysis': analysis
    })

@app.route('/api/expenses', methods=['POST'])
def add_expense():
    """Add new expense"""
    try:
        data = request.json
        print(f"Received expense data: {data}")
        
        expenses = load_expenses()
        
        expense = {
            'id': len(expenses) + 1,
            'date': data.get('date', datetime.now().strftime('%Y-%m-%d')),
            'category': data['category'],
            'amount': float(data['amount']),
            'description': data.get('description', '')
        }
        
        expenses.append(expense)
        save_expenses(expenses)
        
        budget = load_budget()
        monthly_income = load_income()
        analysis = analyze_expenses(expenses, budget, monthly_income)
        
        print(f"Expense added successfully: {expense}")
        
        return jsonify({
            'success': True,
            'expense': expense,
            'analysis': analysis
        })
    except Exception as e:
        print(f"Error adding expense: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/expenses/<int:expense_id>', methods=['DELETE'])
def delete_expense(expense_id):
    """Delete expense"""
    expenses = load_expenses()
    expenses = [e for e in expenses if e['id'] != expense_id]
    save_expenses(expenses)
    
    budget = load_budget()
    monthly_income = load_income()
    analysis = analyze_expenses(expenses, budget, monthly_income)
    
    return jsonify({
        'success': True,
        'analysis': analysis
    })

@app.route('/api/budget', methods=['GET'])
def get_budget():
    """Get budget"""
    return jsonify(load_budget())

@app.route('/api/budget', methods=['POST'])
def set_budget():
    """Set budget"""
    budget = request.json
    save_budget(budget)
    
    expenses = load_expenses()
    monthly_income = load_income()
    analysis = analyze_expenses(expenses, budget, monthly_income)
    
    return jsonify({
        'success': True,
        'analysis': analysis
    })

@app.route('/api/income', methods=['GET'])
def get_income():
    """Get monthly income"""
    return jsonify({'monthly_income': load_income()})

@app.route('/api/income', methods=['POST'])
def set_income():
    """Set monthly income"""
    data = request.json
    monthly_income = float(data.get('monthly_income', 0))
    save_income(monthly_income)
    
    expenses = load_expenses()
    budget = load_budget()
    analysis = analyze_expenses(expenses, budget, monthly_income)
    
    return jsonify({
        'success': True,
        'monthly_income': monthly_income,
        'analysis': analysis
    })

@app.route('/api/visualizations', methods=['GET'])
def get_visualizations():
    """Generate visualizations for current month"""
    expenses = load_expenses()
    monthly_expenses = get_current_month_expenses(expenses)
    budget = load_budget()
    
    if not monthly_expenses:
        return jsonify({'charts': {}})
    
    df = pd.DataFrame(monthly_expenses)
    df['amount'] = pd.to_numeric(df['amount'])
    
    # Category pie chart
    category_totals = df.groupby('category')['amount'].sum()
    pie_chart = go.Figure(data=[go.Pie(
        labels=category_totals.index,
        values=category_totals.values,
        hole=0.3
    )])
    pie_chart.update_layout(title='Spending by Category (This Month)')
    
    # Budget vs Actual bar chart
    categories = list(budget.keys())
    budget_vals = [budget[cat] for cat in categories]
    actual_vals = [category_totals.get(cat, 0) for cat in categories]
    
    bar_chart = go.Figure(data=[
        go.Bar(name='Budget', x=categories, y=budget_vals),
        go.Bar(name='Actual', x=categories, y=actual_vals)
    ])
    bar_chart.update_layout(
        title='Monthly Budget vs Actual Spending',
        barmode='group',
        xaxis_title='Category',
        yaxis_title='Amount ($)'
    )
    
    # Time series
    df['date'] = pd.to_datetime(df['date'])
    daily_spending = df.groupby('date')['amount'].sum().reset_index()
    
    line_chart = go.Figure(data=go.Scatter(
        x=daily_spending['date'],
        y=daily_spending['amount'],
        mode='lines+markers'
    ))
    line_chart.update_layout(
        title='Daily Spending Trend (This Month)',
        xaxis_title='Date',
        yaxis_title='Amount ($)'
    )
    
    return jsonify({
        'charts': {
            'pie': json.loads(json.dumps(pie_chart, cls=PlotlyJSONEncoder)),
            'bar': json.loads(json.dumps(bar_chart, cls=PlotlyJSONEncoder)),
            'line': json.loads(json.dumps(line_chart, cls=PlotlyJSONEncoder))
        }
    })

@app.route('/api/export', methods=['GET'])
def export_data():
    """Export current month expenses to CSV"""
    expenses = load_expenses()
    monthly_expenses = get_current_month_expenses(expenses)
    
    if not monthly_expenses:
        return jsonify({'error': 'No expenses to export for this month'}), 400
    
    df = pd.DataFrame(monthly_expenses)
    now = datetime.now()
    csv_file = f'expenses_{now.strftime("%B_%Y")}.csv'
    df.to_csv(csv_file, index=False)
    
    return send_file(csv_file, as_attachment=True, download_name=csv_file)

if __name__ == '__main__':
    app.run(debug=True, port=5000)