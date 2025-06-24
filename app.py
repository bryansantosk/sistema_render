from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from datetime import date

app = Flask(__name__)
app.secret_key = 'chave_super_secreta'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///banco.db'
db = SQLAlchemy(app)

# MODELOS
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), nullable=False)
    senha = db.Column(db.String(80), nullable=False)

class Categoria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), nullable=False)

class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    custo = db.Column(db.Float, nullable=False)
    preco_varejo = db.Column(db.Float, nullable=False)
    preco_atacado = db.Column(db.Float, nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria.id'))
    categoria = db.relationship('Categoria')

class Venda(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(20), nullable=False)
    forma_pagamento = db.Column(db.String(20), nullable=False)
    observacoes = db.Column(db.Text)
    total = db.Column(db.Float, nullable=False)
    itens = db.Column(db.Text, nullable=False)

class Caixa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(20), unique=True)
    saldo_inicial = db.Column(db.Float, default=0)
    aberto = db.Column(db.Boolean, default=True)

class Lancamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(20))
    tipo = db.Column(db.String(10))  # entrada ou saida
    descricao = db.Column(db.String(120))
    valor = db.Column(db.Float)

# LOGIN

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nome = request.form.get('nome', '')
        senha = request.form.get('senha', '')
        user = Usuario.query.filter_by(nome=nome, senha=senha).first()
        if user:
            session['usuario_id'] = user.id
            return redirect(url_for('index'))
        else:
            flash('Credenciais inválidas.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html')

# PRODUTOS
@app.route('/produtos')
@login_required
def produtos():
    lista = Produto.query.all()
    return render_template('produtos.html', produtos=lista)

@app.route('/novo_produto', methods=['GET', 'POST'])
@login_required
def novo_produto():
    categorias = Categoria.query.all()
    if request.method == 'POST':
        nome = request.form['nome']
        custo = float(request.form['custo'])
        varejo = float(request.form['varejo'])
        atacado = float(request.form['atacado'])
        categoria_id = request.form['categoria']
        produto = Produto(nome=nome, custo=custo, preco_varejo=varejo, preco_atacado=atacado, categoria_id=categoria_id)
        db.session.add(produto)
        db.session.commit()
        return redirect(url_for('produtos'))
    return render_template('novo_produto.html', categorias=categorias)

@app.route('/categorias', methods=['GET', 'POST'])
@login_required
def categorias():
    if request.method == 'POST':
        nome = request.form['nome']
        nova = Categoria(nome=nome)
        db.session.add(nova)
        db.session.commit()
        flash("Categoria adicionada.")
        return redirect(url_for('categorias'))
    todas = Categoria.query.order_by(Categoria.nome).all()
    return render_template('categorias.html', categorias=todas)

@app.route('/categorias/excluir/<int:id>', methods=['POST'])
@login_required
def excluir_categoria(id):
    cat = Categoria.query.get(id)
    if cat:
        db.session.delete(cat)
        db.session.commit()
    return redirect(url_for('categorias'))

# VENDAS
@app.route('/vendas', methods=['GET', 'POST'])
@login_required
def vendas():
    produtos = Produto.query.all()
    hoje = date.today().strftime('%Y-%m-%d')
    if request.method == 'POST':
        forma = request.form['forma_pagamento']
        obs = request.form['observacoes']
        total = float(request.form['total'])
        itens = request.form['itens']
        venda = Venda(data=hoje, forma_pagamento=forma, observacoes=obs, total=total, itens=itens)
        db.session.add(venda)
        caixa = Caixa.query.filter_by(data=hoje).first()
        if caixa:
            lanc = Lancamento(data=hoje, tipo='entrada', descricao='Venda', valor=total)
            db.session.add(lanc)
        db.session.commit()
        return redirect(url_for('vendas'))
    return render_template('vendas.html', produtos=produtos)

# CAIXA
@app.route('/caixa')
@login_required
def caixa():
    hoje = date.today().strftime('%Y-%m-%d')
    caixa = Caixa.query.filter_by(data=hoje).first()
    vendas = Venda.query.filter_by(data=hoje).all()
    total_vendas = sum(v.total for v in vendas)
    lancamentos = Lancamento.query.filter_by(data=hoje).all()
    total_despesas = sum(l.valor for l in lancamentos if l.tipo == 'saida')
    total_entradas = sum(l.valor for l in lancamentos if l.tipo == 'entrada')
    saldo_atual = 0
    if caixa:
        saldo_atual = caixa.saldo_inicial + total_vendas + total_entradas - total_despesas
    return render_template('caixa.html', caixa=caixa, total_vendas=total_vendas,
                           total_despesas=total_despesas, total_entradas=total_entradas,
                           saldo_atual=saldo_atual, lancamentos=lancamentos)

@app.route('/abrir_caixa', methods=['POST'])
@login_required
def abrir_caixa():
    hoje = date.today().strftime('%Y-%m-%d')
    valor = float(request.form['valor'])
    novo = Caixa(data=hoje, saldo_inicial=valor, aberto=True)
    db.session.add(novo)
    db.session.commit()
    return redirect(url_for('caixa'))

@app.route('/fechar_caixa', methods=['POST'])
@login_required
def fechar_caixa():
    hoje = date.today().strftime('%Y-%m-%d')
    caixa = Caixa.query.filter_by(data=hoje).first()
    if caixa:
        caixa.aberto = False
        db.session.commit()
    return redirect(url_for('caixa'))

@app.route('/reabrir_caixa', methods=['POST'])
@login_required
def reabrir_caixa():
    hoje = date.today().strftime('%Y-%m-%d')
    caixa = Caixa.query.filter_by(data=hoje).first()
    if caixa:
        caixa.aberto = True
        db.session.commit()
    return redirect(url_for('caixa'))

@app.route('/lancamento_manual', methods=['POST'])
@login_required
def lancamento_manual():
    hoje = date.today().strftime('%Y-%m-%d')
    descricao = request.form['descricao']
    valor = float(request.form['valor'])
    tipo = request.form['tipo']
    lanc = Lancamento(data=hoje, tipo=tipo, descricao=descricao, valor=valor)
    db.session.add(lanc)
    db.session.commit()
    return redirect(url_for('caixa'))

@app.route('/caixas_anteriores')
@login_required
def caixas_anteriores():
    caixas = Caixa.query.order_by(Caixa.data.desc()).all()
    lista = []
    for c in caixas:
        vendas = Venda.query.filter_by(data=c.data).all()
        total_vendas = sum(v.total for v in vendas)
        lancamentos = Lancamento.query.filter_by(data=c.data).all()
        total_despesas = sum(l.valor for l in lancamentos if l.tipo == 'saida')
        total_entradas = sum(l.valor for l in lancamentos if l.tipo == 'entrada')
        saldo_final = c.saldo_inicial + total_vendas + total_entradas - total_despesas
        lista.append({
            'data': c.data,
            'aberto': c.aberto,
            'inicial': c.saldo_inicial,
            'vendas': total_vendas,
            'entradas': total_entradas,
            'despesas': total_despesas,
            'final': saldo_final
        })
    return render_template('caixas_anteriores.html', caixas=lista)

# RELATÓRIOS
@app.route('/relatorios')
@login_required
def relatorios():
    caixas = Caixa.query.order_by(Caixa.data).all()
    if not caixas:
        return render_template('relatorios.html', vendas_por_forma={}, top_produtos=[], despesas=[], comparativo=[])

    ultimo = caixas[-1]
    vendas = Venda.query.filter_by(data=ultimo.data).all()
    lancamentos = Lancamento.query.filter_by(data=ultimo.data).all()

    saldo_inicial = ultimo.saldo_inicial
    total_vendas = sum(v.total for v in vendas)
    total_despesas = sum(l.valor for l in lancamentos if l.tipo == 'saida')
    saldo_final = saldo_inicial + total_vendas - total_despesas

    formas = {}
    for v in vendas:
        formas[v.forma_pagamento] = formas.get(v.forma_pagamento, 0) + v.total

    todos_itens = []
    for v in vendas:
        todos_itens += v.itens.split(',')
    contagem = {}
    for item in todos_itens:
        nome = item.strip().split(' x')[0].lower()
        if nome:
            contagem[nome] = contagem.get(nome, 0) + 1
    top = sorted(contagem.items(), key=lambda x: x[1], reverse=True)[:3]

    despesas = [l for l in lancamentos if l.tipo == 'saida']

    comparativo = []
    meses = sorted(set(c.data[:7] for c in caixas))
    for mes in meses:
        cx_mes = [c for c in caixas if c.data.startswith(mes)]
        vendas_mes = sum(sum(v.total for v in Venda.query.filter_by(data=c.data)) for c in cx_mes)
        despesas_mes = sum(sum(l.valor for l in Lancamento.query.filter_by(data=c.data) if l.tipo == 'saida') for c in cx_mes)
        lucro = vendas_mes - despesas_mes
        comparativo.append({'mes': mes, 'vendas': vendas_mes, 'despesas': despesas_mes, 'lucro': lucro})

    return render_template('relatorios.html',
        saldo_inicial=saldo_inicial,
        total_vendas=total_vendas,
        total_despesas=total_despesas,
        saldo_final=saldo_final,
        vendas_por_forma=formas,
        top_produtos=top,
        despesas=despesas,
        comparativo=comparativo)

# EXECUTAR
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not Usuario.query.filter_by(nome='HGMOTO').first():
            novo_usuario = Usuario(nome='HGMOTO', senha='hgmotopecas2025')
            db.session.add(novo_usuario)
            db.session.commit()
    app.run(debug=True)
