# forms.py - Формы Flask-WTF
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (StringField, PasswordField, TextAreaField, FloatField,
                     IntegerField, SelectField, BooleanField, SubmitField,
                     HiddenField, RadioField)
from wtforms.validators import (DataRequired, Email, Length, EqualTo,
                                ValidationError, Optional, NumberRange)
from models import User, Category


class RegistrationForm(FlaskForm):
    """Форма регистрации пользователя"""
    username = StringField('Имя пользователя', validators=[
        DataRequired(message='Это поле обязательно'),
        Length(min=3, max=80, message='Имя должно быть от 3 до 80 символов')
    ])
    email = StringField('Email', validators=[
        DataRequired(message='Это поле обязательно'),
        Email(message='Введите корректный email')
    ])
    phone = StringField('Телефон', validators=[
        Optional(),
        Length(max=20, message='Телефон не должен превышать 20 символов')
    ])
    password = PasswordField('Пароль', validators=[
        DataRequired(message='Это поле обязательно'),
        Length(min=6, message='Пароль должен быть не менее 6 символов')
    ])
    password2 = PasswordField('Повторите пароль', validators=[
        DataRequired(message='Это поле обязательно'),
        EqualTo('password', message='Пароли должны совпадать')
    ])
    # Согласие на обработку персональных данных
    agree_policy = BooleanField('Согласие с политикой конфиденциальности', validators=[
        DataRequired(message='Необходимо принять политику конфиденциальности')
    ])
    submit = SubmitField('Зарегистрироваться')

    def validate_username(self, username):
        """Проверка уникальности имени пользователя"""
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Это имя пользователя уже занято')

    def validate_email(self, email):
        """Проверка уникальности email"""
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Этот email уже зарегистрирован')


class LoginForm(FlaskForm):
    """Форма входа"""
    email = StringField('Email', validators=[
        DataRequired(message='Это поле обязательно'),
        Email(message='Введите корректный email')
    ])
    password = PasswordField('Пароль', validators=[
        DataRequired(message='Это поле обязательно')
    ])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')


class ProfileForm(FlaskForm):
    """Форма редактирования профиля"""
    username = StringField('Имя пользователя', validators=[
        DataRequired(message='Это поле обязательно'),
        Length(min=3, max=80, message='Имя должно быть от 3 до 80 символов')
    ])
    email = StringField('Email', validators=[
        DataRequired(message='Это поле обязательно'),
        Email(message='Введите корректный email')
    ])
    phone = StringField('Телефон', validators=[
        Optional(),
        Length(max=20)
    ])
    current_password = PasswordField('Текущий пароль (для изменения пароля)', validators=[
        Optional()
    ])
    new_password = PasswordField('Новый пароль', validators=[
        Optional(),
        Length(min=6, message='Пароль должен быть не менее 6 символов')
    ])
    new_password2 = PasswordField('Повторите новый пароль', validators=[
        Optional(),
        EqualTo('new_password', message='Пароли должны совпадать')
    ])
    submit = SubmitField('Сохранить изменения')


class AddressForm(FlaskForm):
    """Форма адреса доставки"""
    address_line = StringField('Адрес (улица, дом, квартира)', validators=[
        DataRequired(message='Это поле обязательно'),
        Length(max=255)
    ])
    city = StringField('Город', validators=[
        Optional(),
        Length(max=100)
    ])
    postal_code = StringField('Почтовый индекс', validators=[
        Optional(),
        Length(max=20)
    ])
    is_default = BooleanField('Сделать адресом по умолчанию')
    submit = SubmitField('Сохранить адрес')


class ProductForm(FlaskForm):
    """Форма товара (для админ-панели)"""
    article = StringField('Артикул', validators=[
        DataRequired(message='Это поле обязательно'),
        Length(max=50)
    ])
    name = StringField('Название', validators=[
        DataRequired(message='Это поле обязательно'),
        Length(max=200)
    ])
    description = TextAreaField('Описание', validators=[Optional()])
    price = FloatField('Цена (руб.)', validators=[
        DataRequired(message='Это поле обязательно'),
        NumberRange(min=0.01, message='Цена должна быть больше 0')
    ])
    category_id = SelectField('Категория', coerce=int, validators=[
        DataRequired(message='Выберите категорию')
    ])
    brand = StringField('Бренд', validators=[
        Optional(),
        Length(max=100)
    ])
    color = StringField('Цвет', validators=[
        Optional(),
        Length(max=50)
    ])
    weight = FloatField('Вес (кг)', validators=[
        Optional(),
        NumberRange(min=0, message='Вес не может быть отрицательным')
    ])
    dimensions = StringField('Размеры', validators=[
        Optional(),
        Length(max=100)
    ])
    stock = IntegerField('Количество на складе', validators=[
        DataRequired(message='Это поле обязательно'),
        NumberRange(min=0, message='Количество не может быть отрицательным')
    ])
    image = FileField('Изображение', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], 'Только изображения!')
    ])
    is_active = BooleanField('Товар активен')
    submit = SubmitField('Сохранить')

    def __init__(self, *args, **kwargs):
        super(ProductForm, self).__init__(*args, **kwargs)
        # Заполнение списка категорий
        self.category_id.choices = [(0, '-- Выберите категорию --')] + [
            (c.id, c.name) for c in Category.query.order_by(Category.name).all()
        ]


class CategoryForm(FlaskForm):
    """Форма категории"""
    name = StringField('Название категории', validators=[
        DataRequired(message='Это поле обязательно'),
        Length(max=100)
    ])
    description = TextAreaField('Описание', validators=[Optional()])
    submit = SubmitField('Сохранить')


class CheckoutForm(FlaskForm):
    """Форма оформления заказа"""
    delivery_type = RadioField('Способ доставки', choices=[
        ('самовывоз', 'Самовывоз (бесплатно)'),
        ('доставка курьером', 'Доставка курьером')
    ], default='самовывоз', validators=[DataRequired()])

    address_id = SelectField('Выберите адрес', coerce=int, validators=[Optional()])

    new_address = StringField('Или введите новый адрес', validators=[
        Optional(),
        Length(max=255)
    ])
    new_city = StringField('Город', validators=[
        Optional(),
        Length(max=100)
    ])
    new_postal_code = StringField('Почтовый индекс', validators=[
        Optional(),
        Length(max=20)
    ])
    save_address = BooleanField('Сохранить этот адрес')

    phone = StringField('Контактный телефон', validators=[
        DataRequired(message='Укажите телефон для связи'),
        Length(max=20)
    ])
    email = StringField('Email для уведомлений', validators=[
        DataRequired(message='Укажите email'),
        Email(message='Введите корректный email')
    ])

    comment = TextAreaField('Комментарий к заказу', validators=[
        Optional(),
        Length(max=1000)
    ])

    submit = SubmitField('Оформить заказ')


class SearchForm(FlaskForm):
    """Форма поиска"""
    query = StringField('Поиск', validators=[
        Optional(),
        Length(max=100)
    ])
    category_id = SelectField('Категория', coerce=int, validators=[Optional()])
    sort = SelectField('Сортировка', choices=[
        ('name_asc', 'По названию (А-Я)'),
        ('name_desc', 'По названию (Я-А)'),
        ('price_asc', 'По цене (возрастание)'),
        ('price_desc', 'По цене (убывание)'),
        ('newest', 'Сначала новые')
    ], default='name_asc')
    submit = SubmitField('Найти')

    def __init__(self, *args, **kwargs):
        super(SearchForm, self).__init__(*args, **kwargs)
        self.category_id.choices = [(0, 'Все категории')] + [
            (c.id, c.name) for c in Category.query.order_by(Category.name).all()
        ]


class OrderStatusForm(FlaskForm):
    """Форма изменения статуса заказа"""
    status = SelectField('Статус', choices=[
        ('новый', 'Новый'),
        ('в обработке', 'В обработке'),
        ('оплачен', 'Оплачен'),
        ('отправлен', 'Отправлен'),
        ('выполнен', 'Выполнен'),
        ('отменен', 'Отменен')
    ], validators=[DataRequired()])
    submit = SubmitField('Обновить статус')


class CartUpdateForm(FlaskForm):
    """Форма обновления количества в корзине"""
    quantity = HiddenField()
    submit = SubmitField()