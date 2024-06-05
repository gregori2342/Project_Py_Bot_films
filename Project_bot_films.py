import sqlite3
from bs4 import BeautifulSoup
import requests
import telebot
from telebot import types
import re

# Настройка Telegram-бота
bot = telebot.TeleBot("6561249829:AAHCEZs6RDtaN7tHMy3oHORYvtb0bdb9nDg")

# Создание или подключение к базе данных
conn = sqlite3.connect('movies32.db', check_same_thread=False)
cursor = conn.cursor()

# Создание таблицы для хранения информации о фильмах
cursor.execute('''
CREATE TABLE IF NOT EXISTS movies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    genre TEXT,
    year TEXT
)
''')
conn.commit()


def save_to_db(title, genre, year):
    cursor.execute('''
    INSERT INTO movies (title, genre, year)
    VALUES (?, ?, ?)
    ''', (title, genre, year))
    conn.commit()


def get_html(url):
    response = requests.get(url)
    html = response.text
    soup = BeautifulSoup(html, 'html.parser')
    return soup


def parse_page(soup):
    items = soup.select("div.movieItem_info")
    for item in items:
        title = item.select_one("a").text.strip()
        genre = item.select_one(".movieItem_genres").text.strip() if item.select_one(
            ".movieItem_genres") else "Не указано"
        year = item.select_one(".movieItem_year").text.strip() if item.select_one(".movieItem_year") else "Не указано"

        save_to_db(title, genre, year)


def parse_kinopoisk():
    url = "https://www.kinopoisk.ru/lists/movies/top250/"
    soup = get_html(url)
    items = soup.select("div.styles_root__ti07r")[:10]
    for item in items:
        title = item.select_one("a.styles_link__3QJ5g").text.strip()
        genre = item.select_one("span.styles_text__1uF7h").text.strip() if item.select_one(
            "span.styles_text__1uF7h") else "Не указано"
        year = item.select_one("span.styles_year__19pAE").text.strip() if item.select_one(
            "span.styles_year__19pAE") else "Не указано"

        save_to_db(title, genre, year)


def main():
    base_url = "https://www.kinoafisha.info/rating/movies/"
    for page in range(1, 8):
        url = f"{base_url}?page={page}"
        print(f"Парсинг страницы: {url}")
        soup = get_html(url)
        parse_page(soup)


# Регулярное выражение для поддержки частичных совпадений
def regexp(expr, item):
    reg = re.compile(expr, re.IGNORECASE)
    return reg.search(item) is not None


conn.create_function("REGEXP", 2, regexp)


def show_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(row_width=2)
    btn1 = types.KeyboardButton("Выбрать жанр")
    btn2 = types.KeyboardButton("Топ фильмов")
    markup.add(btn1, btn2)
    bot.send_message(chat_id, "Выберите действие:", reply_markup=markup)


@bot.message_handler(commands=['start'])
def start(message):
    show_main_menu(message.chat.id)


@bot.message_handler(commands=['stop'])
def stop(message):
    bot.send_message(message.chat.id, "Бот остановлен.")
    bot.stop_polling()


@bot.message_handler(func=lambda message: message.text == "Выбрать жанр")
def choose_genre(message):
    markup = types.ReplyKeyboardMarkup(row_width=2)
    btn1 = types.KeyboardButton("Боевик")
    btn2 = types.KeyboardButton("Фантастика")
    btn3 = types.KeyboardButton("Драма")
    btn4 = types.KeyboardButton("Комедия")
    btn5 = types.KeyboardButton("Анимация")
    btn6 = types.KeyboardButton("Триллер")
    btn7 = types.KeyboardButton("Закончить выбор")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6, btn7)
    bot.send_message(message.chat.id, "Выберите жанры:", reply_markup=markup)


selected_genres = []


@bot.message_handler(
    func=lambda message: message.text in ["Боевик", "Фантастика", "Драма", "Комедия", "Анимация", "Триллер"])
def add_genre(message):
    global selected_genres
    selected_genres.append(message.text)
    bot.send_message(message.chat.id, f"Добавлен жанр: {message.text}")


@bot.message_handler(func=lambda message: message.text == "Закончить выбор")
def finish_choosing_genres(message):
    global selected_genres, current_movie_index, movies_by_genre
    if selected_genres:
        current_movie_index = 0
        genres_str = '|'.join([f'.*{genre}.*' for genre in selected_genres])
        cursor.execute('SELECT title, genre, year FROM movies WHERE genre REGEXP ? AND genre != "Не указано"',
                       (genres_str,))
        movies_by_genre = cursor.fetchall()
        if movies_by_genre:
            send_movie(message.chat.id)
        else:
            bot.send_message(message.chat.id, "Нет фильмов с выбранными жанрами.")
            show_main_menu(message.chat.id)
    else:
        bot.send_message(message.chat.id, "Вы не выбрали ни одного жанра.")
        show_main_menu(message.chat.id)


current_movie_index = 0
movies_by_genre = []


def send_movie(chat_id):
    global current_movie_index
    if current_movie_index < len(movies_by_genre):
        movie = movies_by_genre[current_movie_index]
        markup = types.ReplyKeyboardMarkup(row_width=2)
        btn1 = types.KeyboardButton("Буду смотреть")
        btn2 = types.KeyboardButton("Подскажи что-то ещё")
        markup.add(btn1, btn2)
        bot.send_message(chat_id, f"Название: {movie[0]}\nЖанры: {movie[1]}\nГод: {movie[2]}", reply_markup=markup)
    else:
        bot.send_message(chat_id, "Больше нет фильмов с выбранными жанрами.")
        show_main_menu(chat_id)


@bot.message_handler(func=lambda message: message.text in ["Буду смотреть", "Подскажи что-то ещё"])
def movie_response(message):
    global current_movie_index, selected_genres, movies_by_genre
    if message.text == "Буду смотреть":
        bot.send_message(message.chat.id, "Отлично! Приятного просмотра!")
        selected_genres = []
        movies_by_genre = []
        show_main_menu(message.chat.id)
    elif message.text == "Подскажи что-то ещё":
        current_movie_index += 1
        if current_movie_index < len(movies_by_genre):
            send_movie(message.chat.id)
        else:
            bot.send_message(message.chat.id, "Больше нет фильмов с выбранными жанрами.")
            selected_genres = []
            movies_by_genre = []
            show_main_menu(message.chat.id)


@bot.message_handler(func=lambda message: message.text == "Топ фильмов")
def show_top_movies(message):
    bot.send_message(message.chat.id, "Топ фильмов с Кинопоиска:")
    cursor.execute('SELECT title, genre, year FROM movies LIMIT 10')
    movies = cursor.fetchall()
    for movie in movies:
        bot.send_message(message.chat.id, f"Название: {movie[0]}\nЖанры: {movie[1]}\nГод: {movie[2]}")
    show_main_menu(message.chat.id)


if __name__ == '__main__':
    # Запуск парсинга и сохранения данных в базу
    main()
    parse_kinopoisk()
    # Запуск бота
    bot.polling()

# Закрытие соединения с базой данных при завершении работы
conn.close()
