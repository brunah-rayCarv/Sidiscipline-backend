import json
import os

from flask import Flask, jsonify, request, send_file
from werkzeug.utils import secure_filename
from flask_cors import CORS

from datetime import date, timedelta

app = Flask(__name__)
CORS(app)

USER_DATABASE = os.path.join(os.path.dirname(__file__), 'database', 'user.json')
PONTO_DATABASE = os.path.join(os.path.dirname(__file__), 'database', 'ponto.json')
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')


def check_user_credentials(email, password):
    # Read the user data from the text file and check if the credentials match
    try:
        with open(USER_DATABASE, 'r', encoding="utf-8") as db:
            data = json.load(db)
            for user in data:
                if user.get('email') == email and user.get('password') == password:
                    return user

    except Exception as ex:
        print("Error on check_user_credentials: ", ex)
    return False


def check_for_absent(user_id):
    today = date.today()
    yesterday = today - timedelta(days=1)
    try:
        with open(PONTO_DATABASE, 'r+', encoding='utf-8') as db:
            pontos_db = json.load(db)
            for pontos in pontos_db:
                if pontos['user_id'] == user_id:
                    if not pontos['faltas'] != [] \
                            or pontos['faltas'][-1]['data'] != '{}/{}/{}'.format(yesterday.day,
                                                                                 yesterday.month,
                                                                                 yesterday.year):
                        user_pontos = pontos.get('pontos')
                        day, month, year = user_pontos[-1]['data'].split('/')
                        user_faltas = pontos.get('faltas')
                        abs_day, abs_month, abs_year = user_faltas[-1]['data'].split('/')
                        last_absent = date(int(abs_year), int(abs_month), int(abs_day))
                        last_date = date(int(year), int(month), int(day))
                        diff_days = (yesterday - last_date).days
                        if diff_days > 0 and last_absent != yesterday:
                            for i in range(1, diff_days + 1):
                                absent_date = last_date + timedelta(days=i)
                                absent = {
                                    'data': '{:02d}/{:02d}/{}'.format(absent_date.day,
                                                                      absent_date.month,
                                                                      absent_date.year),
                                    'situacao': 'não justificado',
                                    'anexo': []
                                }
                                pontos['faltas'].append(absent)
                            db.seek(0)
                            json.dump(pontos_db, db, indent=4, ensure_ascii=False)
                            db.truncate()
    except Exception as ex:
        print('Erro on check_for_absent', ex)


@app.route('/sidi_ponto/v1/cadastro', methods=['POST'])
def cadastro():
    data = json.loads(request.data)

    if 'name' in data and 'email' in data and 'password' in data:
        with open(USER_DATABASE, 'r', encoding='utf-8') as db:
            users_db = json.load(db)
            for user in users_db:
                if data['email'] in user['email']:
                    response = jsonify({'message': 'E-mail ja registrado', 'status_code': 200}), 200
                    return response
            user_id = len(users_db) + 1
        user = {
            'id': user_id,
            'name': data['name'],
            'email': data['email'],
            'password': data['password'],
            'avatar': ''
        }
        user_ponto = {
            'user_id': user_id,
            'pontos': [],
            'faltas': []
        }

        try:
            with open(USER_DATABASE, 'r+', encoding='utf-8') as db:
                users_db = json.load(db)
                users_db.append(user)
                db.seek(0)
                json.dump(users_db, db, indent=4, ensure_ascii=False)
            with open(PONTO_DATABASE, 'r+', encoding='utf-8') as db:
                pontos_db = json.load(db)
                pontos_db.append(user_ponto)
                db.seek(0)
                json.dump(pontos_db, db, indent=4, ensure_ascii=False)
            response = jsonify({'message': 'Usuário cadastrado com sucesso!', 'status_code': 201}), 201
            return response
        except Exception as ex:
            print('Error on cadastro: ', ex)

    response = jsonify({'message': 'Erro nome, email, or senha', 'status_code': 400}), 400
    return response


@app.route('/sidi_ponto/v1/login', methods=['POST'])
def login():
    data = json.loads(request.data)

    if 'email' in data and 'password' in data:
        email = data['email']
        password = data['password']

        user = check_user_credentials(email, password)
        if user:
            check_for_absent(user['id'])
            response = jsonify({'message': 'Login successful!', 'status_code': 200, 'user': user}), 200
            return response
        else:
            response = jsonify({'message': 'Invalid email or password', 'status_code': 401}), 401
            return response
    else:
        response = jsonify({'message': 'Missing email or password', 'status_code': 400}), 400
        return response


@app.route('/sidi_ponto/v1/emails', methods=['GET'])
def emails():
    with open(USER_DATABASE, 'r', encoding='utf-8') as db:
        emails_lista = []
        for user in json.load(db):
            emails_lista.append(user['email'])
        response = jsonify({'emails': emails_lista, 'status_code': 200}), 200
        return response


@app.route('/sidi_ponto/v1/change_password', methods=['PUT'])
def change_password():
    data = json.loads(request.data)
    with open(USER_DATABASE, 'r+', encoding='utf-8') as db:
        users_db = json.load(db)
        for user in users_db:
            if data['email'] in user['email']:
                user['password'] = data['password']
                db.seek(0)
                json.dump(users_db, db, indent=4, ensure_ascii=False)
                db.truncate()
                response = jsonify({'message': 'Senha trocada com sucesso', 'status_code': 200}), 200
                return response
            else:
                response = jsonify({'message': 'Email não encontrado', 'status_code': 404}), 400
                return response


def armazenar_avatar(user_id, file):
    _, ext = os.path.splitext(file.filename)
    for fname in os.listdir(os.path.join(UPLOAD_FOLDER, 'avatars')):
        if fname.startswith('avatar-{}'.format(user_id)):
            os.remove(os.path.join(UPLOAD_FOLDER, 'avatars', fname))
    file.filename = 'avatar-{}{}'.format(user_id, ext)
    save_path = os.path.join(UPLOAD_FOLDER, 'avatars', secure_filename(file.filename))
    file.save(save_path)
    return save_path


@app.route('/sidi_ponto/v1/<int:user_id>', methods=['POST'])
def upload_avatar(user_id):
    file = request.files.get('file')
    with open(USER_DATABASE, 'r+', encoding='utf-8') as db:
        users_db = json.load(db)
        for user in users_db:
            if user['id'] == user_id:
                path = armazenar_avatar(user_id, file)
                _, avatar = os.path.split(path)
                user['avatar'] = avatar
                db.seek(0)
                json.dump(users_db, db, indent=4, ensure_ascii=False)
                db.truncate()
                response = jsonify({'message': 'avatar salvo', 'avatar': user['avatar'], 'status_code': 200}), 200
                return response
        response = jsonify({'message': 'user não encontrado/registrada'})
        return response


@app.route('/sidi_ponto/v1/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    data = json.loads(request.data)
    with open(USER_DATABASE, 'r+', encoding='utf-8') as db:
        users_db = json.load(db)
        for user in users_db:
            if user['id'] == user_id:
                user['name'] = data['username']
                user['email'] = data['email']
                user['password'] = data['password']
                db.seek(0)
                json.dump(users_db, db, indent=4, ensure_ascii=False)
                db.truncate()
                response = jsonify({'message': 'Dados do user atulizados', 'user': user, 'status_code': 200}), 200
                return response
        response = jsonify({'message': 'user não encontrado/registrada'})
        return response


@app.route('/sidi_ponto/v1/pontos/<int:user_id>', methods=['GET'])
def get_all_pontos(user_id):
    with open(PONTO_DATABASE, 'r', encoding='utf-8') as db:
        for pontos_db in json.load(db):
            if pontos_db['user_id'] == user_id:
                user, user_pontos, user_faltas = pontos_db.values()
                response = jsonify({"user": user, "pontos": user_pontos,
                                    "faltas": user_faltas, 'status_code': 200}), 200
                return response
        response = jsonify({'message': 'user não encontrado/registrado', 'status_code': 404}), 404
        return response


@app.route('/sidi_ponto/v1/pontos/<int:user_id>/', methods=['GET'])
def get_ponto_data(user_id):
    data = request.args.get('dt')
    with open(PONTO_DATABASE, 'r', encoding='utf-8') as db:
        for pontos_db in json.load(db):
            if pontos_db['user_id'] == user_id:
                user_pontos = pontos_db.get('pontos')
                for ponto_data in user_pontos:
                    if ponto_data['data'] == data:
                        response = jsonify({'ponto': ponto_data, 'status_code': 200}), 200
                        return response
                response = jsonify({"message": 'data não encontrada/registrada', 'status_code': 404}), 404
                return response
        response = jsonify({'message': 'user não encontrado/registrado', 'status_code': 404}), 404
        return response


@app.route('/sidi_ponto/v1/pontos/<int:user_id>', methods=['POST'])
def save_entrada(user_id):
    data = json.loads(request.data)
    with open(PONTO_DATABASE, 'r+', encoding='utf-8') as db:
        pontos_db = json.load(db)
        for pontos in pontos_db:
            if pontos['user_id'] == user_id:
                user_pontos = pontos.get('pontos')
                for ponto_data in user_pontos:
                    if ponto_data.get('data') == data['date']:
                        response = jsonify({'message': 'data já registrada', 'status_code': 200}), 200
                        return response
                novo_ponto = {
                    'data': data['date'],
                    'horario_entrada': data['entrada'],
                    'location_entrada': data['location'],
                    'horario_saida': '',
                    'location_saida': {}
                }
                user_pontos.append(novo_ponto)
                db.seek(0)
                json.dump(pontos_db, db, indent=4, ensure_ascii=False)
                db.truncate()
                reponse = jsonify({'message': 'ponto salvo', 'status_code': 200}), 200
                return reponse
        response = jsonify({'message': 'user não encontrado/registrado', 'status_code': 404}), 404
        return response


@app.route('/sidi_ponto/v1/pontos/<int:user_id>', methods=['PUT'])
def save_saida(user_id):
    data = json.loads(request.data)
    with open(PONTO_DATABASE, 'r+', encoding='utf-8') as db:
        pontos_db = json.load(db)
        for pontos in pontos_db:
            if pontos['user_id'] == user_id:
                user_pontos = pontos.get('pontos')
                for ponto_data in user_pontos:
                    if ponto_data['data'] == data['date']:
                        if ponto_data['horario_saida']:
                            response = jsonify({'message': 'horario de saida já foi registrado',
                                                'status_code': 200}), 200
                            return response
                        ponto_data['horario_saida'] = data['saida']
                        ponto_data['location_saida'] = data['location']
                        db.seek(0)
                        json.dump(pontos_db, db, indent=4, ensure_ascii=False)
                        db.truncate()
                        response = jsonify({'message': 'horario de saida registrado', 'status_code': 200}), 200
                        return response
                response = jsonify({'message': 'data não encontrada/registrada', 'status_code': 404}), 404
                return response
        response = jsonify({'message': 'user não encontrado/registrado', 'status_code': 404}), 404
        return response


@app.route('/sidi_ponto/v1/pontos/<int:user_id>/', methods=['PUT'])
def ajustrar_ponto(user_id):
    entrada = request.args.get('ent')
    date_request = request.args.get('dt')
    data = json.loads(request.data)
    with open(PONTO_DATABASE, 'r+', encoding='utf-8') as db:
        pontos_db = json.load(db)
        for pontos in pontos_db:
            if pontos['user_id'] == user_id:
                user_pontos = pontos.get('pontos')
                for ponto_data in user_pontos:
                    if ponto_data['data'] == date_request:
                        if entrada:
                            ponto_data['horario_entrada'] = data['horario']
                            ponto_data['location_entrada'] = data['location']
                        else:
                            ponto_data['horario_saida'] = data['horario']
                            ponto_data['location_saida'] = data['location']
                        ponto_data['justificativa'] = data['justificativa']
                        db.seek(0)
                        json.dump(pontos_db, db, indent=4, ensure_ascii=False)
                        db.truncate()
                        response = jsonify({'message': 'ponto ajustrado', 'status_code': 200}), 200
                        return response
                response = jsonify({'message': 'data não encontrada/registrada', 'status_code': 404}), 404
                return response
        response = jsonify({'message': 'user não encontrado/registrado', 'status_code': 404}), 404
        return response


def armazenar_anexo(user_id, file, date_request):
    try:
        if not os.path.isdir(os.path.join(UPLOAD_FOLDER, 'absent_attachment', str(user_id))):
            raise FileNotFoundError
    except FileNotFoundError:
        os.mkdir(os.path.join(UPLOAD_FOLDER, 'absent_attachment', str(user_id)))
    finally:
        file.filename = '{}-{}'.format(date_request, file.filename)
        save_path = os.path.join(UPLOAD_FOLDER, 'absent_attachment', str(user_id), secure_filename(file.filename))
        file.save(save_path)


@app.route('/sidi_ponto/v1/pontos/<int:user_id>/', methods=['POST'])
def upload_anexo_falta(user_id):
    date_request = request.args.get('dt')
    file = request.files.get('file')
    with open(PONTO_DATABASE, 'r+', encoding='utf-8') as db:
        pontos_db = json.load(db)
        for pontos in pontos_db:
            if pontos['user_id'] == user_id:
                user_faltas = pontos.get('faltas')
                for faltas_data in user_faltas:
                    if faltas_data['data'] == date_request:
                        armazenar_anexo(user_id, file, date_request)
                        anexo_path = os.listdir(os.path.join(UPLOAD_FOLDER, 'absent_attachment', str(user_id)))
                        faltas_data['anexo'] = anexo_path
                        faltas_data['situacao'] = 'em analise'
                        db.seek(0)
                        json.dump(pontos_db, db, indent=4, ensure_ascii=False)
                        db.truncate()
                        response = jsonify({'message': 'anexo salvo', 'status_code': 200}), 200
                        return response
                response = jsonify({'message': 'data não encontrada/registrada', 'status_code': 404}), 404
                return response
        response = jsonify({'message': 'user não encontrado/registrado', 'status_code': 404}), 404
        return response


@app.route('/sidi_ponto/v1/pontos/<user_id>/<folder>/<filename>', methods=['GET'])
def load_file(user_id, folder, filename):
    if folder == 'avatars':
        return send_file(os.path.join(UPLOAD_FOLDER, folder, filename))
    else:
        return send_file(os.path.join(UPLOAD_FOLDER, folder, user_id, filename))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
