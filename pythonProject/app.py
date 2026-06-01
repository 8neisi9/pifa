# app.py - Основной файл приложения Flask
import os
from datetime import datetime
from functools import wraps
from flask import (Flask, render_template, redirect, url_for, flash, request,
                   session, abort)
from flask_login import (LoginManager, login_user, logout_user, login_required,
                         current_user)
from flask_wtf.csrf import CSRFProtect  # ДОБАВЛЕНО
from werkzeug.utils import secure_filename
from config import Config
from models import db, User, Address, Category, Product, Order, OrderItem
from forms import (RegistrationForm, LoginForm, ProfileForm, AddressForm,
                   ProductForm, CategoryForm, CheckoutForm, SearchForm,
                   OrderStatusForm)

# Создание экземпляра приложения
app = Flask(__name__)
app.config.from_object(Config)

# Инициализация расширений
db.init_app(app)

# ДОБАВЛЕНО: Инициализация CSRF защиты
csrf = CSRFProtect(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите для доступа к этой странице.'
login_manager.login_message_category = 'warning'


@login_manager.user_loader
def load_user(user_id):
    """Загрузка пользователя для Flask-Login"""
    return User.query.get(int(user_id))


def admin_required(f):
    """Декоратор для проверки прав администратора"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Доступ запрещен. Требуются права администратора.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)

    return decorated_function


def allowed_file(filename):
    """Проверка допустимости расширения файла"""
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def get_cart():
    """Получение корзины из сессии"""
    if 'cart' not in session:
        session['cart'] = {}
    return session['cart']


def get_cart_items():
    """Получение товаров корзины с деталями"""
    cart = get_cart()
    items = []
    total = 0

    for product_id, quantity in cart.items():
        product = Product.query.get(int(product_id))
        if product:
            subtotal = product.price * quantity
            items.append({
                'product': product,
                'quantity': quantity,
                'subtotal': subtotal
            })
            total += subtotal

    return items, total


def get_cart_count():
    """Получение количества товаров в корзине"""
    cart = get_cart()
    return sum(cart.values())


# Контекстный процессор для передачи данных во все шаблоны
@app.context_processor
def inject_globals():
    """Добавление глобальных переменных в шаблоны"""
    categories = Category.query.order_by(Category.name).all()
    cart_count = get_cart_count()
    return dict(
        categories=categories,
        cart_count=cart_count,
        current_year=datetime.now().year
    )


# ============================================================================
# ПУБЛИЧНЫЕ МАРШРУТЫ
# ============================================================================

@app.route('/')
def index():
    """Главная страница"""
    # Популярные товары (последние 8 с наличием)
    popular_products = Product.query.filter(
        Product.is_active == True,
        Product.stock > 0
    ).order_by(Product.created_at.desc()).limit(8).all()

    # Категории для отображения на главной
    categories = Category.query.all()

    return render_template('index.html',
                           popular_products=popular_products,
                           categories=categories)
@app.route('/accept-cookies', methods=['POST'])
def accept_cookies():
    """Принятие политики куки"""
    session['cookies_accepted'] = True
    return redirect(request.referrer or url_for('index'))

@app.route('/catalog')
def catalog():
    """Каталог товаров"""
    page = request.args.get('page', 1, type=int)

    # Параметры фильтрации и сортировки
    category_id = request.args.get('category_id', 0, type=int)
    query = request.args.get('query', '', type=str)
    sort = request.args.get('sort', 'name_asc', type=str)

    # Базовый запрос
    products_query = Product.query.filter(Product.is_active == True)

    # Фильтр по категории
    if category_id > 0:
        products_query = products_query.filter(Product.category_id == category_id)

    # Поиск по названию и артикулу
    if query:
        search_term = f'%{query}%'
        products_query = products_query.filter(
            db.or_(
                Product.name.ilike(search_term),
                Product.article.ilike(search_term)
            )
        )

    # Сортировка
    if sort == 'name_asc':
        products_query = products_query.order_by(Product.name.asc())
    elif sort == 'name_desc':
        products_query = products_query.order_by(Product.name.desc())
    elif sort == 'price_asc':
        products_query = products_query.order_by(Product.price.asc())
    elif sort == 'price_desc':
        products_query = products_query.order_by(Product.price.desc())
    elif sort == 'newest':
        products_query = products_query.order_by(Product.created_at.desc())

    # Пагинация
    pagination = products_query.paginate(
        page=page,
        per_page=app.config['PRODUCTS_PER_PAGE'],
        error_out=False
    )

    # Форма поиска
    search_form = SearchForm()

    # Текущая категория для заголовка
    current_category = None
    if category_id > 0:
        current_category = Category.query.get(category_id)

    return render_template('catalog.html',
                           products=pagination.items,
                           pagination=pagination,
                           search_form=search_form,
                           current_category=current_category,
                           query=query,
                           sort=sort,
                           category_id=category_id)


@app.route('/category/<int:category_id>')
def category(category_id):
    """Товары категории"""
    return redirect(url_for('catalog', category_id=category_id))


@app.route('/search')
def search():
    """Поиск товаров"""
    query = request.args.get('query', '', type=str)
    return redirect(url_for('catalog', query=query))


@app.route('/product/<int:product_id>')
def product(product_id):
    """Страница товара"""
    product = Product.query.get_or_404(product_id)

    if not product.is_active:
        flash('Этот товар недоступен.', 'warning')
        return redirect(url_for('catalog'))

    # Похожие товары из той же категории
    related_products = Product.query.filter(
        Product.category_id == product.category_id,
        Product.id != product.id,
        Product.is_active == True
    ).limit(4).all()

    return render_template('product.html',
                           product=product,
                           related_products=related_products)


# ============================================================================
# КОРЗИНА
# ============================================================================

@app.route('/cart')
def cart():
    """Страница корзины"""
    items, total = get_cart_items()
    return render_template('cart.html', items=items, total=total)


@app.route('/cart/add/<int:product_id>', methods=['POST'])
def cart_add(product_id):
    """Добавление товара в корзину"""
    product = Product.query.get_or_404(product_id)

    if not product.is_active or product.stock <= 0:
        flash('Этот товар недоступен для заказа.', 'error')
        return redirect(request.referrer or url_for('catalog'))

    cart = get_cart()
    product_id_str = str(product_id)

    # Получаем количество из формы (по умолчанию 1)
    quantity = request.form.get('quantity', 1, type=int)
    if quantity < 1:
        quantity = 1

    # Проверяем наличие на складе
    current_qty = cart.get(product_id_str, 0)
    new_qty = current_qty + quantity

    if new_qty > product.stock:
        new_qty = product.stock
        flash(f'В корзину добавлено максимально доступное количество: {product.stock} шт.', 'warning')
    else:
        flash(f'Товар "{product.name}" добавлен в корзину.', 'success')

    cart[product_id_str] = new_qty
    session['cart'] = cart
    session.modified = True

    return redirect(request.referrer or url_for('catalog'))


@app.route('/cart/update/<int:product_id>', methods=['POST'])
def cart_update(product_id):
    """Обновление количества товара в корзине"""
    product = Product.query.get_or_404(product_id)
    cart = get_cart()
    product_id_str = str(product_id)

    if product_id_str not in cart:
        flash('Товар не найден в корзине.', 'error')
        return redirect(url_for('cart'))

    action = request.form.get('action', '')
    current_qty = cart[product_id_str]

    if action == 'increase':
        new_qty = current_qty + 1
        if new_qty > product.stock:
            flash('Достигнуто максимальное количество товара.', 'warning')
            new_qty = product.stock
        cart[product_id_str] = new_qty
    elif action == 'decrease':
        new_qty = current_qty - 1
        if new_qty <= 0:
            del cart[product_id_str]
            flash(f'Товар "{product.name}" удален из корзины.', 'info')
        else:
            cart[product_id_str] = new_qty

    session['cart'] = cart
    session.modified = True

    return redirect(url_for('cart'))


@app.route('/cart/remove/<int:product_id>', methods=['POST'])
def cart_remove(product_id):
    """Удаление товара из корзины"""
    cart = get_cart()
    product_id_str = str(product_id)

    if product_id_str in cart:
        product = Product.query.get(product_id)
        del cart[product_id_str]
        session['cart'] = cart
        session.modified = True
        flash(f'Товар "{product.name if product else ""}" удален из корзины.', 'info')

    return redirect(url_for('cart'))


@app.route('/cart/clear', methods=['POST'])
def cart_clear():
    """Очистка корзины"""
    session['cart'] = {}
    session.modified = True
    flash('Корзина очищена.', 'info')
    return redirect(url_for('cart'))


# ============================================================================
# АВТОРИЗАЦИЯ
# ============================================================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Регистрация пользователя"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = RegistrationForm()

    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            phone=form.phone.data
        )
        user.set_password(form.password.data)

        db.session.add(user)
        db.session.commit()

        flash('Регистрация успешно завершена! Теперь вы можете войти.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Вход пользователя"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if user is None or not user.check_password(form.password.data):
            flash('Неверный email или пароль.', 'error')
            return redirect(url_for('login'))

        if user.is_blocked:
            flash('Ваш аккаунт заблокирован. Обратитесь к администратору.', 'error')
            return redirect(url_for('login'))

        login_user(user, remember=form.remember_me.data)

        # Перенаправление на запрошенную страницу
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('index')

        flash(f'Добро пожаловать, {user.username}!', 'success')
        return redirect(next_page)

    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    """Выход пользователя"""
    logout_user()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('index'))


# ============================================================================
# ЛИЧНЫЙ КАБИНЕТ
# ============================================================================

@app.route('/cabinet')
@login_required
def cabinet():
    """Личный кабинет - главная"""
    # Последние заказы
    recent_orders = Order.query.filter_by(user_id=current_user.id) \
        .order_by(Order.order_date.desc()).limit(5).all()

    # Статистика
    total_orders = Order.query.filter_by(user_id=current_user.id).count()
    completed_orders = Order.query.filter_by(
        user_id=current_user.id,
        status='выполнен'
    ).count()

    return render_template('cabinet/dashboard.html',
                           recent_orders=recent_orders,
                           total_orders=total_orders,
                           completed_orders=completed_orders)


@app.route('/cabinet/orders')
@login_required
def cabinet_orders():
    """История заказов"""
    page = request.args.get('page', 1, type=int)

    orders = Order.query.filter_by(user_id=current_user.id) \
        .order_by(Order.order_date.desc()) \
        .paginate(page=page, per_page=app.config['ORDERS_PER_PAGE'], error_out=False)

    return render_template('cabinet/orders.html', orders=orders)


@app.route('/cabinet/order/<int:order_id>')
@login_required
def cabinet_order_detail(order_id):
    """Детали заказа"""
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    return render_template('cabinet/order_detail.html', order=order)


@app.route('/cabinet/profile', methods=['GET', 'POST'])
@login_required
def cabinet_profile():
    """Редактирование профиля"""
    form = ProfileForm(obj=current_user)

    if form.validate_on_submit():
        # Проверка уникальности email и username
        if form.username.data != current_user.username:
            existing_user = User.query.filter_by(username=form.username.data).first()
            if existing_user:
                flash('Это имя пользователя уже занято.', 'error')
                return render_template('cabinet/profile.html', form=form)

        if form.email.data != current_user.email:
            existing_user = User.query.filter_by(email=form.email.data).first()
            if existing_user:
                flash('Этот email уже зарегистрирован.', 'error')
                return render_template('cabinet/profile.html', form=form)

        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.phone = form.phone.data

        # Изменение пароля
        if form.new_password.data:
            if not form.current_password.data:
                flash('Для изменения пароля введите текущий пароль.', 'error')
                return render_template('cabinet/profile.html', form=form)

            if not current_user.check_password(form.current_password.data):
                flash('Неверный текущий пароль.', 'error')
                return render_template('cabinet/profile.html', form=form)

            current_user.set_password(form.new_password.data)
            flash('Пароль успешно изменен.', 'success')

        db.session.commit()
        flash('Профиль успешно обновлен.', 'success')
        return redirect(url_for('cabinet_profile'))

    return render_template('cabinet/profile.html', form=form)


@app.route('/cabinet/addresses', methods=['GET', 'POST'])
@login_required
def cabinet_addresses():
    """Управление адресами доставки"""
    form = AddressForm()

    if form.validate_on_submit():
        # Если новый адрес по умолчанию, сбрасываем остальные
        if form.is_default.data:
            Address.query.filter_by(user_id=current_user.id).update({'is_default': False})

        address = Address(
            user_id=current_user.id,
            address_line=form.address_line.data,
            city=form.city.data,
            postal_code=form.postal_code.data,
            is_default=form.is_default.data
        )
        db.session.add(address)
        db.session.commit()

        flash('Адрес успешно добавлен.', 'success')
        return redirect(url_for('cabinet_addresses'))

    addresses = Address.query.filter_by(user_id=current_user.id).all()
    return render_template('cabinet/addresses.html', form=form, addresses=addresses)


@app.route('/cabinet/addresses/delete/<int:address_id>', methods=['POST'])
@login_required
def cabinet_address_delete(address_id):
    """Удаление адреса"""
    address = Address.query.filter_by(id=address_id, user_id=current_user.id).first_or_404()
    db.session.delete(address)
    db.session.commit()
    flash('Адрес удален.', 'info')
    return redirect(url_for('cabinet_addresses'))


@app.route('/cabinet/addresses/set-default/<int:address_id>', methods=['POST'])
@login_required
def cabinet_address_set_default(address_id):
    """Установка адреса по умолчанию"""
    # Сбрасываем все адреса
    Address.query.filter_by(user_id=current_user.id).update({'is_default': False})

    # Устанавливаем выбранный
    address = Address.query.filter_by(id=address_id, user_id=current_user.id).first_or_404()
    address.is_default = True
    db.session.commit()

    flash('Адрес по умолчанию обновлен.', 'success')
    return redirect(url_for('cabinet_addresses'))


# ============================================================================
# ОФОРМЛЕНИЕ ЗАКАЗА
# ============================================================================

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    """Оформление заказа"""
    items, total = get_cart_items()

    if not items:
        flash('Ваша корзина пуста.', 'warning')
        return redirect(url_for('cart'))

    form = CheckoutForm()

    # Заполняем список адресов
    addresses = Address.query.filter_by(user_id=current_user.id).all()
    form.address_id.choices = [(0, 'Выберите сохраненный адрес')] + [
        (a.id, a.get_full_address()) for a in addresses
    ]

    # Предзаполнение данных
    if request.method == 'GET':
        form.phone.data = current_user.phone or ''
        form.email.data = current_user.email

    if form.validate_on_submit():
        # Определение адреса доставки
        delivery_address = ''

        if form.delivery_type.data == 'самовывоз':
            delivery_address = 'Самовывоз со склада'
        else:
            # ИСПРАВЛЕНО: добавлена проверка на None
            if form.address_id.data and form.address_id.data > 0:
                address = Address.query.get(form.address_id.data)
                if address:
                    delivery_address = address.get_full_address()
            elif form.new_address.data:
                parts = [form.new_address.data]
                if form.new_city.data:
                    parts.append(form.new_city.data)
                if form.new_postal_code.data:
                    parts.append(form.new_postal_code.data)
                delivery_address = ', '.join(parts)

                # Сохранение нового адреса если отмечено
                if form.save_address.data:
                    new_addr = Address(
                        user_id=current_user.id,
                        address_line=form.new_address.data,
                        city=form.new_city.data,
                        postal_code=form.new_postal_code.data
                    )
                    db.session.add(new_addr)
            else:
                flash('Укажите адрес доставки.', 'error')
                return render_template('checkout.html', form=form, items=items, total=total)

        # Создание заказа
        order = Order(
            user_id=current_user.id,
            total_amount=total,
            delivery_address=delivery_address,
            delivery_type=form.delivery_type.data,
            payment_type='наличные при получении',
            comment=form.comment.data,
            phone=form.phone.data,
            email=form.email.data,
            status='новый'
        )
        db.session.add(order)
        db.session.flush()  # Получаем ID заказа

        # Добавление позиций заказа
        cart = get_cart()
        for product_id_str, quantity in cart.items():
            product = Product.query.get(int(product_id_str))
            if product:
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=quantity,
                    price_at_time=product.price
                )
                db.session.add(order_item)

                # Уменьшение остатка на складе
                product.stock -= quantity

        db.session.commit()

        # Очистка корзины
        session['cart'] = {}
        session.modified = True

        flash(f'Заказ #{order.id} успешно оформлен!', 'success')
        return redirect(url_for('order_success', order_id=order.id))

    return render_template('checkout.html', form=form, items=items, total=total)


@app.route('/order/success/<int:order_id>')
@login_required
def order_success(order_id):
    """Страница успешного оформления заказа"""
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    return render_template('order_success.html', order=order)


# ============================================================================
# АДМИН-ПАНЕЛЬ
# ============================================================================

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    """Админ-панель - главная"""
    # Статистика
    total_products = Product.query.count()
    total_orders = Order.query.count()
    total_users = User.query.count()
    new_orders = Order.query.filter_by(status='новый').count()

    # Последние заказы
    recent_orders = Order.query.order_by(Order.order_date.desc()).limit(5).all()

    # Товары с низким остатком
    low_stock_products = Product.query.filter(
        Product.stock < 5,
        Product.is_active == True
    ).all()

    return render_template('admin/dashboard.html',
                           total_products=total_products,
                           total_orders=total_orders,
                           total_users=total_users,
                           new_orders=new_orders,
                           recent_orders=recent_orders,
                           low_stock_products=low_stock_products)


# --- Управление товарами ---

@app.route('/admin/products')
@login_required
@admin_required
def admin_products():
    """Список товаров в админке"""
    page = request.args.get('page', 1, type=int)
    category_id = request.args.get('category_id', 0, type=int)
    query = request.args.get('query', '', type=str)

    products_query = Product.query

    if category_id > 0:
        products_query = products_query.filter(Product.category_id == category_id)

    if query:
        search_term = f'%{query}%'
        products_query = products_query.filter(
            db.or_(
                Product.name.ilike(search_term),
                Product.article.ilike(search_term)
            )
        )

    products = products_query.order_by(Product.created_at.desc()) \
        .paginate(page=page, per_page=app.config['PRODUCTS_PER_PAGE'], error_out=False)

    categories = Category.query.all()

    return render_template('admin/products.html',
                           products=products,
                           categories=categories,
                           current_category_id=category_id,
                           query=query)


@app.route('/admin/products/add', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_product_add():
    """Добавление товара"""
    form = ProductForm()

    if form.validate_on_submit():
        # Проверка уникальности артикула
        existing = Product.query.filter_by(article=form.article.data).first()
        if existing:
            flash('Товар с таким артикулом уже существует.', 'error')
            return render_template('admin/product_form.html', form=form, title='Добавление товара')

        product = Product(
            article=form.article.data,
            name=form.name.data,
            description=form.description.data,
            price=form.price.data,
            category_id=form.category_id.data if form.category_id.data > 0 else None,
            brand=form.brand.data,
            color=form.color.data,
            weight=form.weight.data,
            dimensions=form.dimensions.data,
            stock=form.stock.data,
            is_active=form.is_active.data
        )

        # Загрузка изображения
        if form.image.data:
            file = form.image.data
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Добавляем timestamp для уникальности
                filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                product.image_url = filename

        db.session.add(product)
        db.session.commit()

        flash(f'Товар "{product.name}" успешно добавлен.', 'success')
        return redirect(url_for('admin_products'))

    return render_template('admin/product_form.html', form=form, title='Добавление товара')


@app.route('/admin/products/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_product_edit(product_id):
    """Редактирование товара"""
    product = Product.query.get_or_404(product_id)
    form = ProductForm(obj=product)

    if form.validate_on_submit():
        # Проверка уникальности артикула (исключая текущий товар)
        existing = Product.query.filter(
            Product.article == form.article.data,
            Product.id != product_id
        ).first()
        if existing:
            flash('Товар с таким артикулом уже существует.', 'error')
            return render_template('admin/product_form.html', form=form,
                                   title='Редактирование товара', product=product)

        product.article = form.article.data
        product.name = form.name.data
        product.description = form.description.data
        product.price = form.price.data
        product.category_id = form.category_id.data if form.category_id.data > 0 else None
        product.brand = form.brand.data
        product.color = form.color.data
        product.weight = form.weight.data
        product.dimensions = form.dimensions.data
        product.stock = form.stock.data
        product.is_active = form.is_active.data

        # Загрузка нового изображения
        if form.image.data:
            file = form.image.data
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

                # Удаление старого изображения
                if product.image_url:
                    old_path = os.path.join(app.config['UPLOAD_FOLDER'], product.image_url)
                    if os.path.exists(old_path):
                        os.remove(old_path)

                product.image_url = filename

        db.session.commit()
        flash(f'Товар "{product.name}" успешно обновлен.', 'success')
        return redirect(url_for('admin_products'))

    return render_template('admin/product_form.html', form=form,
                           title='Редактирование товара', product=product)


@app.route('/admin/products/delete/<int:product_id>', methods=['POST'])
@login_required
@admin_required
def admin_product_delete(product_id):
    """Удаление товара"""
    product = Product.query.get_or_404(product_id)

    # Удаление изображения
    if product.image_url:
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], product.image_url)
        if os.path.exists(image_path):
            os.remove(image_path)

    db.session.delete(product)
    db.session.commit()

    flash(f'Товар "{product.name}" удален.', 'info')
    return redirect(url_for('admin_products'))


# --- Управление категориями ---

@app.route('/admin/categories')
@login_required
@admin_required
def admin_categories():
    """Список категорий"""
    categories = Category.query.order_by(Category.name).all()
    form = CategoryForm()
    return render_template('admin/categories.html', categories=categories, form=form)


@app.route('/admin/categories/add', methods=['POST'])
@login_required
@admin_required
def admin_category_add():
    """Добавление категории"""
    form = CategoryForm()

    if form.validate_on_submit():
        existing = Category.query.filter_by(name=form.name.data).first()
        if existing:
            flash('Категория с таким названием уже существует.', 'error')
            return redirect(url_for('admin_categories'))

        category = Category(
            name=form.name.data,
            description=form.description.data
        )
        db.session.add(category)
        db.session.commit()

        flash(f'Категория "{category.name}" создана.', 'success')

    return redirect(url_for('admin_categories'))


@app.route('/admin/categories/edit/<int:category_id>', methods=['POST'])
@login_required
@admin_required
def admin_category_edit(category_id):
    """Редактирование категории"""
    category = Category.query.get_or_404(category_id)

    name = request.form.get('name', '')
    description = request.form.get('description', '')

    if not name:
        flash('Название категории обязательно.', 'error')
        return redirect(url_for('admin_categories'))

    # Проверка уникальности
    existing = Category.query.filter(
        Category.name == name,
        Category.id != category_id
    ).first()
    if existing:
        flash('Категория с таким названием уже существует.', 'error')
        return redirect(url_for('admin_categories'))

    category.name = name
    category.description = description
    db.session.commit()

    flash(f'Категория "{category.name}" обновлена.', 'success')
    return redirect(url_for('admin_categories'))


@app.route('/admin/categories/delete/<int:category_id>', methods=['POST'])
@login_required
@admin_required
def admin_category_delete(category_id):
    """Удаление категории"""
    category = Category.query.get_or_404(category_id)

    # Проверяем, есть ли товары в этой категории
    if category.products.count() > 0:
        flash('Нельзя удалить категорию с товарами. Сначала переместите или удалите товары.', 'error')
        return redirect(url_for('admin_categories'))

    db.session.delete(category)
    db.session.commit()

    flash(f'Категория "{category.name}" удалена.', 'info')
    return redirect(url_for('admin_categories'))


# --- Управление заказами ---

@app.route('/admin/orders')
@login_required
@admin_required
def admin_orders():
    """Список заказов"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '', type=str)

    orders_query = Order.query

    if status:
        orders_query = orders_query.filter(Order.status == status)

    orders = orders_query.order_by(Order.order_date.desc()) \
        .paginate(page=page, per_page=app.config['ORDERS_PER_PAGE'], error_out=False)

    return render_template('admin/orders.html', orders=orders, current_status=status)


@app.route('/admin/orders/<int:order_id>')
@login_required
@admin_required
def admin_order_detail(order_id):
    """Детали заказа в админке"""
    order = Order.query.get_or_404(order_id)
    form = OrderStatusForm(obj=order)
    return render_template('admin/order_detail.html', order=order, form=form)


@app.route('/admin/orders/update/<int:order_id>', methods=['POST'])
@login_required
@admin_required
def admin_order_update(order_id):
    """Обновление статуса заказа"""
    order = Order.query.get_or_404(order_id)
    form = OrderStatusForm()

    if form.validate_on_submit():
        old_status = order.status
        order.status = form.status.data
        db.session.commit()

        flash(f'Статус заказа #{order.id} изменен с "{old_status}" на "{order.status}".', 'success')

    return redirect(url_for('admin_order_detail', order_id=order_id))


# --- Управление пользователями ---

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    """Список пользователей"""
    page = request.args.get('page', 1, type=int)
    query = request.args.get('query', '', type=str)

    users_query = User.query

    if query:
        search_term = f'%{query}%'
        users_query = users_query.filter(
            db.or_(
                User.username.ilike(search_term),
                User.email.ilike(search_term)
            )
        )

    users = users_query.order_by(User.registration_date.desc()) \
        .paginate(page=page, per_page=app.config['USERS_PER_PAGE'], error_out=False)

    return render_template('admin/users.html', users=users, query=query)


@app.route('/admin/users/toggle-block/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_user_toggle_block(user_id):
    """Блокировка/разблокировка пользователя"""
    user = User.query.get_or_404(user_id)

    # Нельзя заблокировать себя
    if user.id == current_user.id:
        flash('Вы не можете заблокировать самого себя.', 'error')
        return redirect(url_for('admin_users'))

    user.is_blocked = not user.is_blocked
    db.session.commit()

    status = 'заблокирован' if user.is_blocked else 'разблокирован'
    flash(f'Пользователь {user.username} {status}.', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/users/toggle-admin/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_user_toggle_admin(user_id):
    """Назначение/снятие прав администратора"""
    user = User.query.get_or_404(user_id)

    # Нельзя снять права с себя
    if user.id == current_user.id:
        flash('Вы не можете изменить свои права администратора.', 'error')
        return redirect(url_for('admin_users'))

    user.is_admin = not user.is_admin
    db.session.commit()

    status = 'назначен администратором' if user.is_admin else 'лишен прав администратора'
    flash(f'Пользователь {user.username} {status}.', 'success')
    return redirect(url_for('admin_users'))


# ============================================================================
# СОЗДАНИЕ БАЗЫ ДАННЫХ И ТЕСТОВЫХ ДАННЫХ
# ============================================================================

def init_db():
    """Инициализация базы данных"""
    with app.app_context():
        db.create_all()

        # Создание папки для загрузок
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

        # Создание администратора если его нет
        admin = User.query.filter_by(email='admin@pifstroiactiv.ru').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@pifstroiactiv.ru',
                phone='+7 (999) 123-45-67',
                is_admin=True
            )
            admin.set_password('admin123')
            db.session.add(admin)

            # Создание категорий
            categories_data = [
                ('Краски и лаки', 'Краски, лаки, грунтовки для внутренних и наружных работ'),
                ('Обои', 'Виниловые, флизелиновые, бумажные обои'),
                ('Цемент и смеси', 'Цемент, штукатурки, шпаклевки, клеевые смеси'),
                ('Кирпич и блоки', 'Кирпич строительный, облицовочный, блоки газобетонные'),
                ('Сухие смеси', 'Наливные полы, ровнители, клей для плитки'),
                ('Изоляция', 'Утеплители, гидроизоляция, пароизоляция'),
                ('Кровля', 'Кровельные материалы, черепица, профнастил'),
                ('Инструменты', 'Кисти, валики, шпатели, строительный инструмент')
            ]

            for name, desc in categories_data:
                category = Category(name=name, description=desc)
                db.session.add(category)

            db.session.commit()

            # Создание тестовых товаров
            products_data = [
                ('KR-001', 'Краска интерьерная белая 10л', 'Высококачественная интерьерная краска для стен и потолков',
                 2500.00, 1, 'Dulux', 'Белый', 14.0, '10 литров', 50),
                ('KR-002', 'Краска фасадная морозостойкая 20л', 'Фасадная краска для наружных работ', 4500.00, 1,
                 'Tikkurila', 'Белый', 28.0, '20 литров', 30),
                ('OB-001', 'Обои виниловые "Классика"', 'Виниловые обои на флизелиновой основе', 1800.00, 2, 'Rasch',
                 'Бежевый', 1.5, '10.05м x 0.53м', 100),
                ('OB-002', 'Обои флизелиновые под покраску', 'Обои под покраску, структурные', 2200.00, 2, 'Erfurt',
                 'Белый', 1.2, '25м x 1.06м', 75),
                ('CM-001', 'Цемент М500 50кг', 'Портландцемент высокой прочности', 450.00, 3, 'Holcim', None, 50.0,
                 'Мешок 50кг', 200),
                ('CM-002', 'Штукатурка гипсовая 30кг', 'Универсальная гипсовая штукатурка', 380.00, 3, 'Knauf', None,
                 30.0, 'Мешок 30кг', 150),
                ('KR-003', 'Кирпич красный М150', 'Кирпич керамический рядовой полнотелый', 18.00, 4, 'ЛСР', 'Красный',
                 3.5, '250x120x65мм', 5000),
                ('KR-004', 'Газобетонный блок D500', 'Газобетонный стеновой блок', 180.00, 4, 'Ytong', 'Серый', 18.0,
                 '600x300x200мм', 500),
                ('SS-001', 'Наливной пол самовыравнивающийся', 'Быстротвердеющий наливной пол', 650.00, 5, 'Ceresit',
                 None, 25.0, 'Мешок 25кг', 80),
                ('SS-002', 'Клей для плитки усиленный', 'Клей для керамической плитки и керамогранита', 420.00, 5,
                 'Mapei', None, 25.0, 'Мешок 25кг', 120),
                (
                'IZ-001', 'Утеплитель минеральная вата', 'Базальтовая теплоизоляция', 1200.00, 6, 'Rockwool', None, 8.5,
                '1000x600x50мм, упаковка', 60),
                ('IZ-002', 'Пенополистирол ПСБ-С 25', 'Пенопласт для утепления фасадов', 150.00, 6, 'Penoplex', 'Белый',
                 0.5, '1000x1000x50мм', 200),
                ('KV-001', 'Металлочерепица Монтеррей', 'Кровельное покрытие с полимерным покрытием', 550.00, 7,
                 'Grand Line', 'Коричневый', 4.5, '1180x350мм', 150),
                ('IN-001', 'Набор малярных кистей', 'Комплект кистей для покраски (5 шт)', 450.00, 8, 'Color Expert',
                 None, 0.3, 'Набор', 40),
                ('IN-002', 'Валик малярный 250мм', 'Валик с полиамидным ворсом', 320.00, 8, 'Профи', None, 0.2, '250мм',
                 60),
            ]

            for data in products_data:
                product = Product(
                    article=data[0],
                    name=data[1],
                    description=data[2],
                    price=data[3],
                    category_id=data[4],
                    brand=data[5],
                    color=data[6],
                    weight=data[7],
                    dimensions=data[8],
                    stock=data[9],
                    is_active=True
                )
                db.session.add(product)

            db.session.commit()
            print('База данных инициализирована с тестовыми данными.')
            print('Администратор: admin@pifstroiactiv.ru / admin123')


# Обработчики ошибок
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500


# Запуск приложения
if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)