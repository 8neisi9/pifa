# models.py - Модели базы данных SQLAlchemy
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Инициализация SQLAlchemy
db = SQLAlchemy()


class User(UserMixin, db.Model):
    """Модель пользователя"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20))
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_blocked = db.Column(db.Boolean, default=False)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)

    # Связи
    addresses = db.relationship('Address', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    orders = db.relationship('Order', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        """Установка хешированного пароля"""
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        """Проверка пароля"""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class Address(db.Model):
    """Модель адреса доставки"""
    __tablename__ = 'addresses'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    address_line = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(100))
    postal_code = db.Column(db.String(20))
    is_default = db.Column(db.Boolean, default=False)

    def get_full_address(self):
        """Получение полного адреса"""
        parts = [self.address_line]
        if self.city:
            parts.append(self.city)
        if self.postal_code:
            parts.append(self.postal_code)
        return ', '.join(parts)

    def __repr__(self):
        return f'<Address {self.address_line}>'


class Category(db.Model):
    """Модель категории товаров"""
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)

    # Связь с товарами
    products = db.relationship('Product', backref='category', lazy='dynamic')

    def __repr__(self):
        return f'<Category {self.name}>'


class Product(db.Model):
    """Модель товара"""
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    article = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    brand = db.Column(db.String(100))
    color = db.Column(db.String(50))
    weight = db.Column(db.Float)  # Вес в кг
    dimensions = db.Column(db.String(100))  # Размеры
    stock = db.Column(db.Integer, default=0)  # Количество на складе
    image_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    def is_in_stock(self):
        """Проверка наличия на складе"""
        return self.stock > 0

    def get_stock_status(self):
        """Получение статуса наличия"""
        if self.stock > 10:
            return 'В наличии'
        elif self.stock > 0:
            return f'Осталось: {self.stock} шт.'
        else:
            return 'Нет в наличии'

    def __repr__(self):
        return f'<Product {self.name}>'


class Order(db.Model):
    """Модель заказа"""
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    status = db.Column(db.String(50), default='новый')
    total_amount = db.Column(db.Float, nullable=False)
    delivery_address = db.Column(db.String(500))
    delivery_type = db.Column(db.String(50))  # самовывоз или доставка курьером
    payment_type = db.Column(db.String(50), default='наличные при получении')
    comment = db.Column(db.Text)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))

    # Связь с позициями заказа
    items = db.relationship('OrderItem', backref='order', lazy='dynamic', cascade='all, delete-orphan')

    # Статусы заказа
    STATUSES = [
        ('новый', 'Новый'),
        ('в обработке', 'В обработке'),
        ('оплачен', 'Оплачен'),
        ('отправлен', 'Отправлен'),
        ('выполнен', 'Выполнен'),
        ('отменен', 'Отменен')
    ]

    def get_status_class(self):
        """Получение CSS-класса для статуса"""
        status_classes = {
            'новый': 'status-new',
            'в обработке': 'status-processing',
            'оплачен': 'status-paid',
            'отправлен': 'status-shipped',
            'выполнен': 'status-completed',
            'отменен': 'status-cancelled'
        }
        return status_classes.get(self.status, 'status-new')

    def get_items_count(self):
        """Получение количества позиций в заказе"""
        return sum(item.quantity for item in self.items)

    def __repr__(self):
        return f'<Order {self.id}>'


class OrderItem(db.Model):
    """Модель позиции заказа"""
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price_at_time = db.Column(db.Float, nullable=False)  # Цена на момент заказа

    # Связь с товаром
    product = db.relationship('Product', backref='order_items')

    def get_subtotal(self):
        """Получение суммы по позиции"""
        return self.quantity * self.price_at_time

    def __repr__(self):
        return f'<OrderItem {self.id}>'