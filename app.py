# app.py
# Para executar este aplicativo:
# 1. Crie uma pasta chamada 'templates' no mesmo diretório deste arquivo.
# 2. Salve todos os arquivos .html dentro da pasta 'templates'.
# 3. Instale o Flask: pip install Flask
# 4. No terminal, execute: python app.py
# 5. Abra seu navegador e acesse: http://127.0.0.1:5000

# --- Importações das bibliotecas necessárias ---
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta
import uuid  # Para gerar IDs únicos para cada item
import copy  # Para criar cópias profundas dos objetos
from functools import wraps # Para criar decorators de autenticação
from werkzeug.security import generate_password_hash, check_password_hash # Para segurança de senhas

# --- Inicialização da Aplicação Flask ---
app = Flask(__name__)
app.secret_key = 'sua-chave-secreta-super-segura-aqui' 

# --- Armazenamento de Dados em Memória ---

# Lista de categorias padrão para novos usuários
DEFAULT_CATEGORIES = [
    {'name': 'Salário'}, {'name': 'Moradia'}, {'name': 'Alimentação'},
    {'name': 'Transporte'}, {'name': 'Lazer'}, {'name': 'Saúde'},
    {'name': 'Educação'}, {'name': 'Outros'}
]

# Dados iniciais para o usuário administrador
admin_categories = copy.deepcopy(DEFAULT_CATEGORIES)
for category in admin_categories:
    category['id'] = str(uuid.uuid4())

admin_transactions = [
    {'id': str(uuid.uuid4()), 'description': 'Receita Inicial Admin', 'amount': 1000.00, 'type': 'receita', 'category': 'Salário', 'date': '2025-07-06', 'due_date': '2025-07-06', 'status': 'recebido'},
    {'id': str(uuid.uuid4()), 'description': 'Despesa Inicial Admin', 'amount': 250.00, 'type': 'despesa', 'category': 'Moradia', 'date': '2025-07-10', 'due_date': '2025-07-10', 'status': 'pago'},
]

# Estrutura principal de dados
data = {
    "admin": {
        "password": generate_password_hash("admin"),
        "email": "artenio.reis@gmail.com",
        "role": "admin",
        "reset_token": None,
        "transactions": admin_transactions,
        "categories": admin_categories,
        "accounts": [{'id': str(uuid.uuid4()), 'name': 'Conta Padrão Admin'}],
        "credit_cards": [], "payment_methods": [], "clients": [], "suppliers": []
    }
}

# --- Funções Auxiliares e Decorators ---

def parse_date(date_val):
    if isinstance(date_val, datetime): return date_val
    if not date_val or not isinstance(date_val, str): return None
    try: return datetime.strptime(date_val, '%Y-%m-%d')
    except (ValueError, TypeError): return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash("Por favor, faça login para acessar esta página.", "warning")
            return redirect(url_for('login'))
        if session['username'] not in data:
            flash("Sua sessão é inválida. Por favor, faça login novamente.", "danger")
            session.clear()
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash("Por favor, faça login para acessar esta página.", "warning")
            return redirect(url_for('login'))
        username = session['username']
        user_data = data.get(username, {})
        if user_data.get('role') != 'admin':
            flash("Você não tem permissão para acessar esta página.", "danger")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# --- Rotas de Autenticação e Usuários ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = data.get(username)
        if user and check_password_hash(user['password'], password):
            session['username'] = username
            session['role'] = user['role']
            flash(f"Login bem-sucedido! Bem-vindo, {username}.", "success")
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
        email = request.form['email']
        user_to_reset = None
        for username, user_data in data.items():
            if user_data.get('email') == email:
                user_to_reset = user_data
                break
        if user_to_reset:
            token = str(uuid.uuid4())
            user_to_reset['reset_token'] = token
            return redirect(url_for('reset_password', token=token))
        else:
            flash("Nenhum usuário encontrado com este e-mail.", "danger")
            return redirect(url_for('forgot_password'))
    return render_template('forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user_to_reset = None
    for username, user_data in data.items():
        if user_data.get('reset_token') == token:
            user_to_reset = user_data
            break
    if not user_to_reset:
        flash("Token de redefinição de senha inválido ou expirado.", "danger")
        return redirect(url_for('login'))
    if request.method == 'POST':
        new_password = request.form['password']
        confirm_password = request.form['confirm_password']
        if new_password != confirm_password:
            flash("As senhas não coincidem.", "danger")
            return render_template('reset_password.html', token=token)
        user_to_reset['password'] = generate_password_hash(new_password)
        user_to_reset['reset_token'] = None
        flash("Sua senha foi redefinida com sucesso! Você já pode fazer login.", "success")
        return redirect(url_for('login'))
    return render_template('reset_password.html', token=token)

@app.route('/users', methods=['GET', 'POST'])
@admin_required
def manage_users():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        if username in data:
            flash("Este nome de usuário já existe.", "danger")
        elif any(u.get('email') == email for u in data.values()):
             flash("Este e-mail já está em uso por outro usuário.", "danger")
        else:
            new_user_categories = copy.deepcopy(DEFAULT_CATEGORIES)
            for category in new_user_categories:
                category['id'] = str(uuid.uuid4())
            data[username] = {
                "password": generate_password_hash(password), "email": email,
                "role": role, "reset_token": None, "transactions": [], 
                "categories": new_user_categories, "accounts": [], "credit_cards": [], 
                "payment_methods": [], "clients": [], "suppliers": []
            }
            flash(f"Usuário '{username}' criado com sucesso!", "success")
        return redirect(url_for('manage_users'))
    
    users_list = {u: d for u, d in data.items() if u != 'admin'}
    return render_template('users.html', users=users_list)

@app.route('/users/delete/<username>')
@admin_required
def delete_user(username):
    if username == 'admin':
        flash("O usuário administrador não pode ser excluído.", "danger")
    elif username in data:
        del data[username]
        flash(f"Usuário '{username}' excluído com sucesso.", "success")
    else:
        flash("Usuário não encontrado.", "danger")
    return redirect(url_for('manage_users'))

@app.route('/users/reset/<username>')
@admin_required
def admin_reset_password(username):
    user_to_reset = data.get(username)
    if user_to_reset:
        token = str(uuid.uuid4())
        user_to_reset['reset_token'] = token
        reset_url = url_for('reset_password', token=token, _external=True)
        flash(f'Link de redefinição para {username}: {reset_url}', "info")
    else:
        flash("Usuário não encontrado.", "danger")
    return redirect(url_for('manage_users'))

# --- Rotas da Aplicação Financeira ---

@app.route('/')
@login_required
def index():
    user_data = data.get(session['username'], {})
    local_transactions = copy.deepcopy(user_data.get('transactions', []))
    
    filter_date_str = request.args.get('filter_date')
    filter_type = request.args.get('filter_type')
    filter_status = request.args.get('filter_status')
    filtered_transactions = local_transactions
    if filter_date_str:
        filter_date = parse_date(filter_date_str)
        if filter_date:
            filtered_transactions = [t for t in filtered_transactions if parse_date(t.get('date')) == filter_date or parse_date(t.get('due_date')) == filter_date]
    if filter_type:
        filtered_transactions = [t for t in filtered_transactions if t['type'] == filter_type]
    if filter_status:
        if filter_status == 'pago':
            filtered_transactions = [t for t in filtered_transactions if t['status'] in ['pago', 'recebido']]
        else:
            filtered_transactions = [t for t in filtered_transactions if t['status'] == filter_status]

    sorted_transactions = sorted(filtered_transactions, key=lambda t: parse_date(t.get('due_date')) or datetime.min, reverse=True)
    for t in sorted_transactions:
        t['date'] = parse_date(t.get('date'))
        t['due_date'] = parse_date(t.get('due_date'))

    total_income = sum(t['amount'] for t in user_data.get('transactions', []) if t['type'] == 'receita' and t['status'] in ['recebido', 'pago'])
    total_expense = sum(t['amount'] for t in user_data.get('transactions', []) if t['type'] == 'despesa' and t['status'] == 'pago')
    balance = total_income - total_expense

    return render_template(
        'index.html', 
        transactions=sorted_transactions,
        balance=balance,
        total_income=total_income,
        total_expense=total_expense,
        today_date=datetime.now().strftime('%Y-%m-%d'),
        categories=sorted(user_data.get('categories', []), key=lambda c: c['name']),
        accounts=user_data.get('accounts', []),
        credit_cards=user_data.get('credit_cards', []),
        payment_methods=user_data.get('payment_methods', []),
        clients=user_data.get('clients', []),
        suppliers=user_data.get('suppliers', [])
    )

@app.route('/reports', methods=['GET'])
@login_required
def reports():
    user_data = data.get(session['username'], {})
    today = datetime.now()
    start_date_str = request.args.get('start_date', today.replace(day=1).strftime('%Y-%m-%d'))
    end_date_str = request.args.get('end_date', today.strftime('%Y-%m-%d'))
    start_date = parse_date(start_date_str)
    end_date = parse_date(end_date_str)

    report_transactions = []
    if start_date and end_date:
        end_date_inclusive = end_date.replace(hour=23, minute=59, second=59)
        for t in user_data.get('transactions', []):
            payment_date = parse_date(t.get('date'))
            # CORREÇÃO: Verifica se a data de pagamento existe antes de comparar
            if payment_date and start_date <= payment_date <= end_date_inclusive:
                report_transactions.append(t)

    income_transactions = [t for t in report_transactions if t['type'] == 'receita']
    expense_transactions = [t for t in report_transactions if t['type'] == 'despesa']
    total_income = sum(t['amount'] for t in income_transactions)
    total_expense = sum(t['amount'] for t in expense_transactions)
    
    for t in income_transactions: t['date'] = parse_date(t.get('date'))
    for t in expense_transactions: t['date'] = parse_date(t.get('date'))

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
    user_data = data.get(session['username'], {})
    today = datetime.now()
    start_date_str = request.args.get('start_date', today.replace(day=1).strftime('%Y-%m-%d'))
    end_date_str = request.args.get('end_date', today.strftime('%Y-%m-%d'))
    start_date = parse_date(start_date_str)
    end_date = parse_date(end_date_str)

    report_transactions = []
    if start_date and end_date:
        end_date_inclusive = end_date.replace(hour=23, minute=59, second=59)
        for t in user_data.get('transactions', []):
            payment_date = parse_date(t.get('date'))
            due_date = parse_date(t.get('due_date'))
            
            # CORREÇÃO: Verifica se as datas existem antes de comparar
            payment_in_range = payment_date and start_date <= payment_date <= end_date_inclusive
            due_in_range = due_date and start_date <= due_date <= end_date_inclusive

            if payment_in_range or due_in_range:
                report_transactions.append(t)

    sorted_transactions = sorted(report_transactions, key=lambda t: parse_date(t.get('due_date')) or datetime.min)
    
    total_income = sum(t['amount'] for t in sorted_transactions if t['type'] == 'receita' and t['status'] in ['pago', 'recebido'])
    total_expense = sum(t['amount'] for t in sorted_transactions if t['type'] == 'despesa' and t['status'] in ['pago', 'recebido'])
    balance = total_income - total_expense

    for t in sorted_transactions:
        t['date'] = parse_date(t.get('date'))
        t['due_date'] = parse_date(t.get('due_date'))

    return render_template(
        'detailed_report.html',
        start_date=start_date_str,
        end_date=end_date_str,
        transactions=sorted_transactions,
        total_income=total_income,
        total_expense=total_expense,
        balance=balance
    )

# --- Rotas para Adicionar, Atualizar e Deletar Dados ---

@app.route('/add', methods=['POST'])
@login_required
def add_transaction():
    user_data = data.get(session['username'], {})
    is_paid = 'is_paid' in request.form
    payment_date = request.form.get('date')
    transaction_type = request.form['type']
    
    if is_paid:
        status = 'recebido' if transaction_type == 'receita' else 'pago'
        if not payment_date: payment_date = datetime.now().strftime('%Y-%m-%d')
    else:
        status = 'pendente'
        payment_date = ''

    new_tx = {
        'id': str(uuid.uuid4()), 'description': request.form['description'],
        'amount': float(request.form['amount']), 'type': transaction_type,
        'category': request.form['category'], 'date': payment_date,
        'due_date': request.form['due_date'], 'status': status
    }
    user_data.setdefault('transactions', []).append(new_tx)
    flash("Lançamento adicionado com sucesso!", "success")
    return redirect(url_for('index'))

@app.route('/edit/<tx_id>', methods=['POST'])
@login_required
def edit_transaction(tx_id):
    user_data = data.get(session['username'], {})
    transaction_to_edit = None
    for tx in user_data.get('transactions', []):
        if tx['id'] == tx_id:
            transaction_to_edit = tx
            break

    if not transaction_to_edit:
        flash("Lançamento não encontrado.", "danger")
        return redirect(url_for('index'))

    transaction_to_edit['description'] = request.form['description']
    transaction_to_edit['amount'] = float(request.form['amount'])
    transaction_to_edit['due_date'] = request.form['due_date']
    transaction_to_edit['category'] = request.form['category']
    transaction_to_edit['type'] = request.form['type']
    
    is_paid = 'is_paid' in request.form
    payment_date = request.form.get('date')

    if is_paid:
        transaction_to_edit['status'] = 'recebido' if request.form['type'] == 'receita' else 'pago'
        transaction_to_edit['date'] = payment_date if payment_date else datetime.now().strftime('%Y-%m-%d')
    else:
        transaction_to_edit['status'] = 'pendente'
        transaction_to_edit['date'] = ''

    flash("Lançamento atualizado com sucesso!", "success")
    return redirect(url_for('index'))

@app.route('/update_status/<tx_id>')
@login_required
def update_status(tx_id):
    user_data = data.get(session['username'], {})
    for tx in user_data.get('transactions', []):
        if tx['id'] == tx_id:
            tx['status'] = 'recebido' if tx['type'] == 'receita' else 'pago'
            tx['date'] = datetime.now().strftime('%Y-%m-%d')
            break
    return redirect(url_for('index'))

@app.route('/delete/<tx_id>')
@login_required
def delete_transaction(tx_id):
    user_data = data.get(session['username'], {})
    user_data['transactions'] = [t for t in user_data.get('transactions', []) if t['id'] != tx_id]
    flash("Lançamento excluído com sucesso.", "info")
    return redirect(url_for('index'))

# --- Rotas de Cadastro ---
@app.route('/add_category', methods=['POST'])
@login_required
def add_category():
    user_data = data.get(session['username'], {})
    user_data.setdefault('categories', []).append({'id': str(uuid.uuid4()), 'name': request.form['name']})
    flash("Categoria adicionada com sucesso!", "success")
    return redirect(url_for('index'))

@app.route('/add_account', methods=['POST'])
@login_required
def add_account():
    user_data = data.get(session['username'], {})
    user_data.setdefault('accounts', []).append({'id': str(uuid.uuid4()), 'name': request.form['name']})
    flash("Conta adicionada com sucesso!", "success")
    return redirect(url_for('index'))

@app.route('/add_credit_card', methods=['POST'])
@login_required
def add_credit_card():
    user_data = data.get(session['username'], {})
    user_data.setdefault('credit_cards', []).append({'id': str(uuid.uuid4()), 'name': request.form['name']})
    flash("Cartão de Crédito adicionado com sucesso!", "success")
    return redirect(url_for('index'))

@app.route('/add_payment_method', methods=['POST'])
@login_required
def add_payment_method():
    user_data = data.get(session['username'], {})
    user_data.setdefault('payment_methods', []).append({'id': str(uuid.uuid4()), 'name': request.form['name']})
    flash("Forma de Pagamento adicionada com sucesso!", "success")
    return redirect(url_for('index'))

@app.route('/add_client', methods=['POST'])
@login_required
def add_client():
    user_data = data.get(session['username'], {})
    user_data.setdefault('clients', []).append({'id': str(uuid.uuid4()), 'name': request.form['name']})
    flash("Cliente adicionado com sucesso!", "success")
    return redirect(url_for('index'))

@app.route('/add_supplier', methods=['POST'])
@login_required
def add_supplier():
    user_data = data.get(session['username'], {})
    user_data.setdefault('suppliers', []).append({'id': str(uuid.uuid4()), 'name': request.form['name']})
    flash("Fornecedor adicionado com sucesso!", "success")
    return redirect(url_for('index'))

# --- Ponto de Entrada da Aplicação ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)





#if __name__ == '__main__':
   # app.run(debug=True)



