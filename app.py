# app.py
# Para executar este aplicativo:
# 1. Crie uma pasta chamada 'templates' no mesmo diretório deste arquivo.
# 2. Salve todos os arquivos .html e o arquivo schema.sql dentro da pasta 'templates'.
# 3. APAGUE o ficheiro 'livro_caixa.db' antigo, se ele existir.
# 4. Instale o Flask: pip install Flask
# 5. No terminal, execute: python app.py (isto irá criar um novo ficheiro .db com a estrutura correta)
# 6. Abra seu navegador e acesse: http://127.0.0.1:5000

import sqlite3
import uuid
import copy
from datetime import datetime, timedelta
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, session, flash, g, jsonify
from collections import defaultdict

# --- Configuração da Aplicação e Banco de Dados ---
DATABASE = 'livro_caixa.db'
app = Flask(__name__)
app.secret_key = 'sua-chave-secreta-super-segura-aqui'

DEFAULT_CATEGORIES = {
    "Receitas (Entradas de Dinheiro)": [
        "Vendas de Produtos/Serviços", "Recebimento de Duplicatas", "Juros Recebidos",
        "Receitas Financeiras", "Aportes de Capital", "Empréstimos Obtidos",
        "Recebimento de Aluguéis", "Devolução de Impostos", "Doações/Patrocínios",
        "Outras Receitas"
    ],
    "Despesas (Saídas de Dinheiro)": [
        "Compras de Mercadorias/Insumos", "Pagamento de Fornecedores", "Salários e Encargos",
        "Aluguel/Leasing", "Contas de Luz, Água, Internet, Telefone", "Impostos e Taxas",
        "Manutenção e Reparos", "Seguros", "Serviços Terceirizados",
        "Combustível/Transporte", "Outras Despesas Operacionais"
    ],
    "Movimentações Financeiras": [
        "Depósitos Bancários", "Saque em Espécie", "Transferências entre Contas",
        "Aplicações Financeiras", "Resgate de Investimentos", "Pagamento de Empréstimos",
        "Recebimento de Empréstimos"
    ],
    "Ajustes e Regularizações": [
        "Ajustes de Caixa (Sobra/Falta)", "Estornos de Lançamentos",
        "Correção de Valores", "Provisões para Perdas"
    ],
    "Categorias Específicas": [
        "Retiradas do Proprietário (Pró-labore/Distribuição de Lucros)",
        "Doações Realizadas", "Multas e Juros Pagos", "Reembolsos de Funcionários"
    ]
}

def get_db():
    """Abre uma nova conexão com o banco de dados se não houver uma."""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    """Fecha a conexão com o banco de dados ao final da requisição."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    """Inicializa o banco de dados com o schema definido."""
    with app.app_context():
        db = get_db()
        with app.open_resource('templates/schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()
        
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", ('admin',))
        if cursor.fetchone() is None:
            admin_password = generate_password_hash('admin')
            cursor.execute(
                "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
                ('admin', 'artenio.reis@gmail.com', admin_password, 'admin')
            )
            db.commit()
            
            admin_user = cursor.execute("SELECT id FROM users WHERE username = ?", ('admin',)).fetchone()
            if admin_user:
                admin_id = admin_user['id']
                for group, categories in DEFAULT_CATEGORIES.items():
                    for category_name in categories:
                        cursor.execute(
                            "INSERT INTO categories (user_id, name, category_group) VALUES (?, ?, ?)",
                            (admin_id, category_name, group)
                        )
                db.commit()
            print("Banco de dados inicializado e usuário 'admin' criado com categorias padrão.")

# --- Funções Auxiliares e Decorators ---
def parse_date(date_val):
    if isinstance(date_val, datetime): return date_val
    if not date_val or not isinstance(date_val, str): return None
    try: return datetime.strptime(date_val, '%Y-%m-%d')
    except (ValueError, TypeError): return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Por favor, faça login para acessar esta página.", "warning")
            return redirect(url_for('login'))
        if session['username'] not in [row['username'] for row in get_db().execute('SELECT username FROM users').fetchall()]:
            flash("Sua sessão é inválida. Por favor, faça login novamente.", "danger")
            session.clear()
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash("Você não tem permissão para acessar esta página.", "danger")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# --- Rotas de Autenticação e Usuários ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        db = get_db()
        username = request.form['username']
        password = request.form['password']
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()

        if user and check_password_hash(user['password_hash'], password):
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('index'))
        else:
            flash("Usuário ou senha inválidos.", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Você foi desconectado.", "info")
    return redirect(url_for('login'))

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        db = get_db()
        email = request.form['email']
        user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        
        if user:
            token = str(uuid.uuid4())
            db.execute('UPDATE users SET reset_token = ? WHERE id = ?', (token, user['id']))
            db.commit()
            return redirect(url_for('reset_password', token=token))
        else:
            flash("Nenhum usuário encontrado com este e-mail.", "danger")
            return redirect(url_for('forgot_password'))
    return render_template('forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE reset_token = ?', (token,)).fetchone()
    
    if not user:
        flash("Token de redefinição de senha inválido ou expirado.", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        new_password = request.form['password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            flash("As senhas não coincidem.", "danger")
            return render_template('reset_password.html', token=token)
        
        password_hash = generate_password_hash(new_password)
        db.execute('UPDATE users SET password_hash = ?, reset_token = NULL WHERE id = ?', (password_hash, user['id']))
        db.commit()
        flash("Sua senha foi redefinida com sucesso! Você já pode fazer login.", "success")
        return redirect(url_for('login'))

    return render_template('reset_password.html', token=token)

@app.route('/users', methods=['GET', 'POST'])
@admin_required
def manage_users():
    db = get_db()
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        
        if db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone() is not None:
            flash('Este nome de usuário já existe.', 'danger')
        elif db.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone() is not None:
            flash('Este e-mail já está em uso.', 'danger')
        else:
            db.execute(
                'INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)',
                (username, email, generate_password_hash(password), role)
            )
            db.commit()
            
            new_user = db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
            if new_user:
                new_user_id = new_user['id']
                for group, categories in DEFAULT_CATEGORIES.items():
                    for category_name in categories:
                        db.execute(
                            "INSERT INTO categories (user_id, name, category_group) VALUES (?, ?, ?)",
                            (new_user_id, category_name, group)
                        )
                db.commit()

            flash(f"Usuário '{username}' criado com sucesso!", "success")
        return redirect(url_for('manage_users'))

    users = db.execute('SELECT id, username, email, role FROM users WHERE username != "admin"').fetchall()
    return render_template('users.html', users=users)

@app.route('/users/delete/<int:user_id>')
@admin_required
def delete_user(user_id):
    db = get_db()
    db.execute('DELETE FROM users WHERE id = ?', (user_id,))
    db.commit()
    flash('Usuário excluído com sucesso.', 'success')
    return redirect(url_for('manage_users'))

@app.route('/users/reset/<username>')
@admin_required
def admin_reset_password(username):
    db = get_db()
    user_to_reset = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    if user_to_reset:
        token = str(uuid.uuid4())
        db.execute('UPDATE users SET reset_token = ? WHERE id = ?', (token, user_to_reset['id']))
        db.commit()
        reset_url = url_for('reset_password', token=token, _external=True)
        flash(f'Link de redefinição para {username}: {reset_url}', "info")
    else:
        flash("Usuário não encontrado.", "danger")
    return redirect(url_for('manage_users'))

# --- Rotas da Aplicação Financeira ---
@app.route('/')
@login_required
def index():
    db = get_db()
    user_id = session['user_id']
    
    transactions_from_db = db.execute(
        'SELECT * FROM transactions WHERE user_id = ? ORDER BY due_date DESC', (user_id,)
    ).fetchall()

    transactions = []
    for tx_row in transactions_from_db:
        tx_dict = dict(tx_row)
        tx_dict['date'] = parse_date(tx_dict['date'])
        tx_dict['due_date'] = parse_date(tx_dict['due_date'])
        transactions.append(tx_dict)

    total_income = db.execute(
        "SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type = 'receita' AND status IN ('pago', 'recebido')", (user_id,)
    ).fetchone()[0] or 0.0

    total_expense = db.execute(
        "SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type = 'despesa' AND status = 'pago'", (user_id,)
    ).fetchone()[0] or 0.0
    
    balance = total_income - total_expense
    
    categories_from_db = db.execute('SELECT name, category_group FROM categories WHERE user_id = ? ORDER BY category_group, name', (user_id,)).fetchall()
    
    categories_grouped = defaultdict(list)
    for cat in categories_from_db:
        categories_grouped[cat['category_group']].append(cat['name'])

    clients = db.execute('SELECT name FROM clients WHERE user_id = ? ORDER BY name', (user_id,)).fetchall()
    suppliers = db.execute('SELECT name FROM suppliers WHERE user_id = ? ORDER BY name', (user_id,)).fetchall()

    expenses_by_category = db.execute(
        "SELECT category, SUM(amount) as total FROM transactions WHERE user_id = ? AND type = 'despesa' AND status = 'pago' GROUP BY category",
        (user_id,)
    ).fetchall()
    
    pie_chart_data = {
        "labels": [row['category'] for row in expenses_by_category],
        "data": [row['total'] for row in expenses_by_category]
    }

    monthly_flow = {}
    today = datetime.today()
    for i in range(6):
        month = today - timedelta(days=30 * i)
        month_key = month.strftime("%Y-%m")
        monthly_flow[month_key] = {"income": 0, "expense": 0}

    all_paid_transactions = db.execute(
        "SELECT amount, type, date FROM transactions WHERE user_id = ? AND status IN ('pago', 'recebido') AND date IS NOT NULL",
        (user_id,)
    ).fetchall()

    for tx in all_paid_transactions:
        tx_date = datetime.strptime(tx['date'], '%Y-%m-%d')
        month_key = tx_date.strftime("%Y-%m")
        if month_key in monthly_flow:
            if tx['type'] == 'receita':
                monthly_flow[month_key]['income'] += tx['amount']
            else:
                monthly_flow[month_key]['expense'] += tx['amount']
    
    line_chart_labels = sorted(monthly_flow.keys())
    line_chart_data = [monthly_flow[key]['income'] - monthly_flow[key]['expense'] for key in line_chart_labels]
    line_chart_labels_formatted = [datetime.strptime(key, "%Y-%m").strftime("%b/%y") for key in line_chart_labels]

    line_chart_data_final = {
        "labels": line_chart_labels_formatted,
        "data": line_chart_data
    }

    return render_template(
        'index.html', 
        transactions=transactions,
        balance=balance,
        total_income=total_income,
        total_expense=total_expense,
        today_date=datetime.now().strftime('%Y-%m-%d'),
        categories_grouped=categories_grouped,
        clients=clients,
        suppliers=suppliers,
        pie_chart_data=pie_chart_data,
        line_chart_data=line_chart_data_final
    )

@app.route('/add', methods=['POST'])
@login_required
def add_transaction():
    db = get_db()
    user_id = session['user_id']
    
    is_paid = 'is_paid' in request.form
    payment_date = request.form.get('date')
    transaction_type = request.form['type']
    
    if is_paid:
        status = 'recebido' if transaction_type == 'receita' else 'pago'
        if not payment_date: payment_date = datetime.now().strftime('%Y-%m-%d')
    else:
        status = 'pendente'
        payment_date = None

    db.execute(
        'INSERT INTO transactions (user_id, description, amount, type, category, date, due_date, status, client_supplier) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (user_id, request.form['description'], float(request.form['amount']), transaction_type, request.form['category'], payment_date, request.form['due_date'], status, request.form.get('client_supplier'))
    )
    db.commit()
    flash("Lançamento adicionado com sucesso!", "success")
    return redirect(url_for('index'))

@app.route('/reports', methods=['GET'])
@login_required
def reports():
    db = get_db()
    user_id = session['user_id']
    today = datetime.now()
    start_date_str = request.args.get('start_date', today.replace(day=1).strftime('%Y-%m-%d'))
    end_date_str = request.args.get('end_date', today.strftime('%Y-%m-%d'))
    start_date = parse_date(start_date_str)
    end_date = parse_date(end_date_str)

    report_transactions = []
    if start_date and end_date:
        end_date_inclusive = end_date.replace(hour=23, minute=59, second=59)
        transactions_from_db = db.execute(
            "SELECT * FROM transactions WHERE user_id = ? AND date >= ? AND date <= ?",
            (user_id, start_date_str, end_date_str)
        ).fetchall()
        for tx_row in transactions_from_db:
            tx_dict = dict(tx_row)
            tx_dict['date'] = parse_date(tx_dict['date'])
            report_transactions.append(tx_dict)

    income_transactions = [t for t in report_transactions if t['type'] == 'receita']
    expense_transactions = [t for t in report_transactions if t['type'] == 'despesa']
    total_income = sum(t['amount'] for t in income_transactions)
    total_expense = sum(t['amount'] for t in expense_transactions)
    
    return render_template(
        'reports.html',
        start_date=start_date_str,
        end_date=end_date_str,
        income_transactions=sorted(income_transactions, key=lambda t: t.get('date') or datetime.min),
        expense_transactions=sorted(expense_transactions, key=lambda t: t.get('date') or datetime.min),
        total_income=total_income,
        total_expense=total_expense
    )

@app.route('/reports/detailed', methods=['GET'])
@login_required
def detailed_report():
    db = get_db()
    user_id = session['user_id']
    today = datetime.now()
    start_date_str = request.args.get('start_date', today.replace(day=1).strftime('%Y-%m-%d'))
    end_date_str = request.args.get('end_date', today.strftime('%Y-%m-%d'))
    start_date = parse_date(start_date_str)
    end_date = parse_date(end_date_str)

    report_transactions = []
    if start_date and end_date:
        end_date_inclusive = end_date.replace(hour=23, minute=59, second=59)
        transactions_from_db = db.execute(
            "SELECT * FROM transactions WHERE user_id = ? AND ( (date >= ? AND date <= ?) OR (due_date >= ? AND due_date <= ?) ) ORDER BY due_date",
            (user_id, start_date_str, end_date_str, start_date_str, end_date_str)
        ).fetchall()
        
        for tx_row in transactions_from_db:
            tx_dict = dict(tx_row)
            tx_dict['date'] = parse_date(tx_dict['date'])
            tx_dict['due_date'] = parse_date(tx_dict['due_date'])
            report_transactions.append(tx_dict)

    total_income = sum(t['amount'] for t in report_transactions if t['type'] == 'receita' and t['status'] in ['pago', 'recebido'])
    total_expense = sum(t['amount'] for t in report_transactions if t['type'] == 'despesa' and t['status'] in ['pago', 'recebido'])
    balance = total_income - total_expense

    return render_template(
        'detailed_report.html',
        start_date=start_date_str,
        end_date=end_date_str,
        transactions=report_transactions,
        total_income=total_income,
        total_expense=total_expense,
        balance=balance
    )

@app.route('/edit/<int:tx_id>', methods=['POST'])
@login_required
def edit_transaction(tx_id):
    db = get_db()
    user_id = session['user_id']
    
    transaction = db.execute('SELECT * FROM transactions WHERE id = ? AND user_id = ?', (tx_id, user_id)).fetchone()
    if transaction is None:
        flash("Lançamento não encontrado ou não pertence a você.", "danger")
        return redirect(url_for('index'))

    description = request.form['description']
    amount = float(request.form['amount'])
    due_date = request.form['due_date']
    category = request.form['category']
    transaction_type = request.form['type']
    client_supplier = request.form.get('client_supplier')
    is_paid = 'is_paid' in request.form
    payment_date = request.form.get('date')

    if is_paid:
        status = 'recebido' if transaction_type == 'receita' else 'pago'
        if not payment_date:
            payment_date = datetime.now().strftime('%Y-%m-%d')
    else:
        status = 'pendente'
        payment_date = None

    db.execute(
        'UPDATE transactions SET description = ?, amount = ?, type = ?, category = ?, date = ?, due_date = ?, status = ?, client_supplier = ? WHERE id = ?',
        (description, amount, transaction_type, category, payment_date, due_date, status, client_supplier, tx_id)
    )
    db.commit()
    flash("Lançamento atualizado com sucesso!", "success")
    return redirect(url_for('index'))

@app.route('/update_status/<int:tx_id>')
@login_required
def update_status(tx_id):
    db = get_db()
    user_id = session['user_id']
    
    transaction = db.execute('SELECT * FROM transactions WHERE id = ? AND user_id = ?', (tx_id, user_id)).fetchone()
    if transaction is None:
        flash("Lançamento não encontrado ou não pertence a você.", "danger")
        return redirect(url_for('index'))

    status = 'recebido' if transaction['type'] == 'receita' else 'pago'
    payment_date = datetime.now().strftime('%Y-%m-%d')
    
    db.execute(
        'UPDATE transactions SET status = ?, date = ? WHERE id = ?',
        (status, payment_date, tx_id)
    )
    db.commit()
    flash("Status do lançamento atualizado para pago.", "success")
    return redirect(url_for('index'))

@app.route('/delete/<int:tx_id>')
@login_required
def delete_transaction(tx_id):
    db = get_db()
    user_id = session['user_id']
    
    transaction = db.execute('SELECT id FROM transactions WHERE id = ? AND user_id = ?', (tx_id, user_id)).fetchone()
    if transaction:
        db.execute('DELETE FROM transactions WHERE id = ?', (tx_id,))
        db.commit()
        flash("Lançamento excluído com sucesso.", "info")
    else:
        flash("Lançamento não encontrado ou não pertence a você.", "danger")
        
    return redirect(url_for('index'))

# --- Rotas de Cadastro ---
@app.route('/add_category', methods=['POST'])
@login_required
def add_category():
    db = get_db()
    user_id = session['user_id']
    name = request.form['name']
    db.execute('INSERT INTO categories (user_id, name, category_group) VALUES (?, ?, ?)', (user_id, name, 'Categorias Personalizadas'))
    db.commit()
    flash("Categoria adicionada com sucesso!", "success")
    return redirect(url_for('index'))

@app.route('/add_account', methods=['POST'])
@login_required
def add_account():
    db = get_db()
    user_id = session['user_id']
    name = request.form['name']
    db.execute('INSERT INTO accounts (user_id, name) VALUES (?, ?)', (user_id, name))
    db.commit()
    flash("Conta adicionada com sucesso!", "success")
    return redirect(url_for('index'))

@app.route('/add_credit_card', methods=['POST'])
@login_required
def add_credit_card():
    db = get_db()
    user_id = session['user_id']
    name = request.form['name']
    db.execute('INSERT INTO credit_cards (user_id, name) VALUES (?, ?)', (user_id, name))
    db.commit()
    flash("Cartão de Crédito adicionado com sucesso!", "success")
    return redirect(url_for('index'))

@app.route('/add_payment_method', methods=['POST'])
@login_required
def add_payment_method():
    db = get_db()
    user_id = session['user_id']
    name = request.form['name']
    db.execute('INSERT INTO payment_methods (user_id, name) VALUES (?, ?)', (user_id, name))
    db.commit()
    flash("Forma de Pagamento adicionada com sucesso!", "success")
    return redirect(url_for('index'))

@app.route('/add_client', methods=['POST'])
@login_required
def add_client():
    db = get_db()
    user_id = session['user_id']
    name = request.form['name']
    db.execute('INSERT INTO clients (user_id, name) VALUES (?, ?)', (user_id, name))
    db.commit()
    flash("Cliente adicionado com sucesso!", "success")
    return redirect(url_for('index'))

@app.route('/add_supplier', methods=['POST'])
@login_required
def add_supplier():
    db = get_db()
    user_id = session['user_id']
    name = request.form['name']
    db.execute('INSERT INTO suppliers (user_id, name) VALUES (?, ?)', (user_id, name))
    db.commit()
    flash("Fornecedor adicionado com sucesso!", "success")
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
