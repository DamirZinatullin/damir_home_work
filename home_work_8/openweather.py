"""
== OpenWeatherMap ==

OpenWeatherMap — онлайн-сервис, который предоставляет бесплатный API
для доступа к данным о текущей погоде, прогнозам, для web-сервисов
и мобильных приложений. Архивные данные доступны только на коммерческой
основе. В качестве источника данных используются официальные метеорологические
службы
данные из метеостанций аэропортов, и данные с частных метеостанций.

Необходимо решить следующие задачи:

== Получение APPID ==
    Чтобы получать данные о погоде необходимо получить бесплатный APPID.

    Предлагается 2 варианта (по желанию):
    - получить APPID вручную
    - автоматизировать процесс получения APPID,
        используя дополнительную библиотеку GRAB (pip install grab)

        Необходимо зарегистрироваться на сайте openweathermap.org:
        https://home.openweathermap.org/users/sign_up

        Войти на сайт по ссылке:
        https://home.openweathermap.org/users/sign_in

        Свой ключ "вытащить" со страницы отсюда:
        https://home.openweathermap.org/api_keys

        Ключ имеет смысл сохранить в локальный файл, например, "app.id"


== Получение списка городов ==
    Список городов может быть получен по ссылке:
    http://bulk.openweathermap.org/sample/city.list.json.gz

    Далее снова есть несколько вариантов (по желанию):
    - скачать и распаковать список вручную
    - автоматизировать скачивание (ulrlib) и распаковку списка
     (воспользоваться модулем gzip
      или распаковать внешним архиватором, воспользовавшись модулем subprocess)

    Список достаточно большой. Представляет собой JSON-строки:
{"_id":707860,"name":"Hurzuf","country":"UA","coord":{"lon":34.283333,
"lat":44.549999}}
{"_id":519188,"name":"Novinki","country":"RU","coord":{"lon":37.666668,
"lat":55.683334}}


== Получение погоды ==
    На основе списка городов можно делать запрос к сервису по id города.
И тут как раз понадобится APPID.
By city ID
Examples of API calls:
http://api.openweathermap.org/data/2.5/weather?id=2172797&appid=b1b15e8
8fa797225412429c1c50c122a

Для получения температуры по Цельсию:
http://api.openweathermap.org/data/2.5/weather?id=520068&units=metric&
appid=b1b15e88fa797225412429c1c50c122a

Для запроса по нескольким городам сразу:
http://api.openweathermap.org/data/2.5/group?id=524901,703448,2643743&units=
metric&appid=b1b15e88fa797225412429c1c50c122a


Данные о погоде выдаются в JSON-формате
{"coord":{"lon":38.44,"lat":55.87},
"weather":[{"id":803,"main":"Clouds","description":"broken clouds",
"icon":"04n"}], "base":"cmc stations","main":{"temp":280.03,"pressure":1006,
"humidity":83, "temp_min":273.15,"temp_max":284.55},
"wind":{"speed":3.08,"deg":265,"gust":7.2},"rain":{"3h":0.015},
"clouds":{"all":76},"dt":1465156452,"sys":{"type":3,"id":57233,
"message":0.0024,"country":"RU","sunrise":1465087473,"sunset":1465149961},
"id":520068,"name":"Noginsk","cod":200}


== Сохранение данных в локальную БД ==
Программа должна позволять:
1. Создавать файл базы данных SQLite со следующей структурой данных
   (если файла базы данных не существует):

    Погода
        id_города           INTEGER PRIMARY KEY
        Город               VARCHAR(255)
        Дата                DATE
        Температура         INTEGER
        id_погоды           INTEGER                 # weather.id из JSON-данных

2. Выводить список стран из файла и предлагать пользователю выбрать страну
(ввиду того, что список городов и стран весьма велик
 имеет смысл запрашивать у пользователя имя города или страны
 и искать данные в списке доступных городов/стран (регуляркой))

3. Скачивать JSON (XML) файлы погоды в городах выбранной страны
4. Парсить последовательно каждый из файлов и добавлять данные о погоде в базу
   данных. Если данные для данного города и данного дня есть в базе - обновить
   температуру в существующей записи.


При повторном запуске скрипта:
- используется уже скачанный файл с городами;
- используется созданная база данных, новые данные добавляются и обновляются.


При работе с XML-файлами:

Доступ к данным в XML-файлах происходит через пространство имен:
<forecast ... xmlns="http://weather.yandex.ru/forecast ...>

Чтобы работать с пространствами имен удобно пользоваться такими функциями:

    # Получим пространство имен из первого тега:
    def gen_ns(tag):
        if tag.startswith('{'):
            ns, tag = tag.split('}')
            return ns[1:]
        else:
            return ''

    tree = ET.parse(f)
    root = tree.getroot()

    # Определим словарь с namespace
    namespaces = {'ns': gen_ns(root.tag)}

    # Ищем по дереву тегов
    for day in root.iterfind('ns:day', namespaces=namespaces):
        ...

"""
import json
import sqlite3
import requests
import datetime


class WeatherDb:
    def __init__(self, name_of_db: str):
        self.conn = sqlite3.connect(name_of_db)
        self.cur = self.conn.cursor()
        self.name_of_db = name_of_db

    def make_db(self):
        success = False
        try:
            self.conn.execute("""
                create table project (
                    id_города       text primary key,
                    Город           varchar(255),
                    Дата            date,
                    Температура     integer,
                    id_погоды       integer
                );
                """)
            print('База данных {} создана'.format(self.name_of_db))
            success = True
        except sqlite3.OperationalError:
            pass
        return success

    def __str__(self):
        self.conn.row_factory = sqlite3.Row
        self.cur.execute("select * from project")
        str_to_output = ''
        for row in self.cur.fetchall():
            city_id, name, date, temperature, id_weather = row
            str_to_output += 'id_города:{}, Город:{}, Дата:{}, Темп:{}, ' \
                             'id погоды:{}\n'.format(city_id, name, date,
                                                     temperature, id_weather)
        return str_to_output

    def insert_data(self, json_from_open_weather: dict):
        self.conn.execute("""
                    insert into project (id_города, Город , Дата,
                    Температура, id_погоды) VALUES (?,?,?,?,?)""",
                          (json_from_open_weather['id'],
                           json_from_open_weather['name'],
                           datetime.datetime.fromtimestamp(
                               json_from_open_weather['dt']),
                           json_from_open_weather['main']['temp'],
                           json_from_open_weather['weather'][0]['id']
                           )
                          )
        self.conn.commit()
        access = True
        return access

    def update_data(self, json_from_open_weather: dict):
        self.cur.execute(
            "update project set Температура=:Температура, Дата=:Дата, "
            "id_погоды=:id_погоды where id_города=:id_города",
            {'Температура': json_from_open_weather['main']['temp'],
             'Дата': datetime.datetime.fromtimestamp(
                 json_from_open_weather['dt']),
             'id_погоды': json_from_open_weather['weather'][0]['id'],
             'id_города': json_from_open_weather['id']})
        self.conn.commit()

    def close_db(self):
        self.conn.close()


class FindWeather:
    def __init__(self):
        self.list_of_countries = None
        self.id_of_selected_cities = []
        self.response_json = None
        with open('city.list.json', 'r', encoding='UTF-8')as f:
            self.load_of_city_list = json.load(f)

    def make_list_of_countries(self):
        countries = set([el['country'] for el in self.load_of_city_list])
        countries.remove('')
        return sorted(countries)

    # def find_id_of_selected_cities_in_country(self, country: str,
    #                                           cities: list):

    def make_response_json(self, country: str, cities: list):
        selected_cities = []
        for city in cities:
            for el in self.load_of_city_list:
                if el['name'] == city and el['country'] == country:
                    selected_cities.append(el)
            self.id_of_selected_cities = [el['id'] for el in
                                          selected_cities]
        if len(self.id_of_selected_cities) > 1:
            response = requests.get(
                'http://api.openweathermap.org/data/2.5/group',
                params={'id': ','.join(
                    map(str, self.id_of_selected_cities)),
                    'units': 'metric',
                    'appid': '7bdac68cd4f963bf98aa0d44d3dfddf8'})
        else:
            response = requests.get(
                'http://api.openweathermap.org/data/2.5/weather',
                params={'id': str(self.id_of_selected_cities[0]),
                        'units': 'metric',
                        'appid': '7bdac68cd4f963bf98aa0d44d3dfddf8'})
        self.response_json = response.json()
        print(response.url)
        return self.response_json


if __name__ == '__main__':
    name_of_db = 'weather.db'
    weather_db = WeatherDb(name_of_db)
    weather_finder = FindWeather()
    print(weather_finder.make_list_of_countries())
    while len(weather_finder.id_of_selected_cities) == 0:
        country = input('Введите обозначение страны')
        cities = (input('Введите название городов через пробел')).split()
        try:
            weather_finder.make_response_json(country,cities)
        except IndexError:
            continue
    weather_db.make_db()
    if len(weather_finder.id_of_selected_cities) > 1:
        for city in weather_finder.response_json['list']:
            try:
                weather_db.insert_data(city)
            except sqlite3.IntegrityError:
                weather_db.update_data(city)
    else:
        try:
            weather_db.insert_data(weather_finder.response_json)
        except sqlite3.IntegrityError:
            weather_db.update_data(weather_finder.response_json)
    print(weather_db)
