import json
import os

from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

user_database = os.path.join(os.path.dirname(__file__), 'database', 'user.json')
ponto_database = os.path.join(os.path.dirname(__file__), 'database', 'ponto.json')


def check_user_credentials(email, password):
    # Read the user data from the text file and check if the credentials match
    try:
        with open(user_database, 'r', encoding="utf-8") as db:
            data = json.load(db)
            for user in data:
                if user.get('email') == email and user.get('password') == password:
                    return user

    except Exception as ex:
        print("Error on check_user_credentials: ", ex)
    return False


@app.route('/sidi_ponto/v1/cadastro', methods=['POST'])
def cadastro():
    data = json.loads(request.data)

    if 'name' in data and 'email' in data and 'password' in data:
        with open(user_database, 'r', encoding='utf-8') as db:
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
            'password': data['password']
        }
        user_ponto = {
            'user_id': user_id,
            'pontos': [],
            'faltas': []
        }

        try:
            with open(user_database, 'r+', encoding='utf-8') as db:
                users_db = json.load(db)
                users_db.append(user)
                db.seek(0)
                json.dump(users_db, db, indent=4)
            with open(ponto_database, 'r+', encoding='utf-8') as db:
                pontos_db = json.load(db)
                pontos_db.append(user_database)
                db.seek(0)
                json.dump(pontos_db, db, indent=4)
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
    with open(user_database, 'r', encoding='utf-8') as db:
        emails_lista = []
        for user in json.load(db):
            emails_lista.append(user['email'])
        response = jsonify({'emails': emails_lista, 'status_code': 200}), 200
        return response


@app.route('/sidi_ponto/v1/change_password', methods=['PUT'])
def change_password():
    data = json.loads(request.data)
    with open(user_database, 'r+', encoding='utf-8') as db:
        users_db = json.load(db)
        for user in users_db:
            if data['email'] in user['email']:
                user['password'] = data['password']
                db.seek(0)
                json.dump(users_db, db, indent=4)
                db.truncate()
                response = jsonify({'message': 'Senha trocada com sucesso', 'status_code': 200}), 200
                return response
            else:
                response = jsonify({'message': 'Email não encontrado', 'status_code': 404}), 400
                return response


@app.route('/sidi_ponto/v1/pontos/<int:user_id>', methods=['GET'])
def get_all_pontos(user_id):
    with open(ponto_database, 'r', encoding='utf-8') as db:
        for pontos_db in json.load(db):
            if pontos_db['user_id'] == user_id:
                user, user_pontos, user_faltas = pontos_db.values()
                response = jsonify({"user": user, "pontos": user_pontos,
                                    "faltas": user_faltas, 'status_code': 200}), 200
                return response


@app.route('/sidi_ponto/v1/pontos/<int:user_id>/', methods=['GET'])
def get_ponto_data(user_id):
    data = request.args.get('dt')
    with open(ponto_database, 'r', encoding='utf-8') as db:
        for pontos_db in json.load(db):
            if pontos_db['user_id'] == user_id:
                user_pontos = pontos_db.get('pontos')
                for ponto_data in user_pontos:
                    if ponto_data['data'] == data:
                        response = jsonify({'ponto': ponto_data, 'status_code': 200}), 200
                        return response
                response = jsonify({"message": 'data não encontrada/registrada', 'status_code': 404}), 404
                return response


@app.route('/sidi_ponto/v1/pontos/<int:user_id>', methods=['POST'])
def save_entrada(user_id):
    data = json.loads(request.data)
    with open(ponto_database, 'r+', encoding='utf-8') as db:
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
                json.dump(pontos_db, db, indent=4)
                db.truncate()
                reponse = jsonify({'message': 'ponto salvo', 'status_code': 200}), 200
                return reponse


@app.route('/sidi_ponto/v1/pontos/<int:user_id>', methods=['PUT'])
def save_saida(user_id):
    data = json.loads(request.data)
    with open(ponto_database, 'r+', encoding='utf-8') as db:
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
                        json.dump(pontos_db, db, indent=4)
                        db.truncate()
                        response = jsonify({'message': 'horario de saida registrado', 'status_code': 200}), 200
                        return response
                response = jsonify({'message': 'data não encontrada/registrada', 'status_code': 404}), 404
                return response


@app.route('/sidi_ponto/v1/pontos/<int:user_id>/', methods=['PUT'])
def ajustrar_ponto(user_id):
    entrada = request.args.get('ent')
    date = request.args.get('dt')
    data = json.loads(request.data)
    with open(ponto_database, 'r+', encoding='utf-8') as db:
        pontos_db = json.load(db)
        for pontos in pontos_db:
            if pontos['user_id'] == user_id:
                user_pontos = pontos.get('pontos')
                for ponto_data in user_pontos:
                    if ponto_data['data'] == date:
                        if entrada:
                            ponto_data['horario_entrada'] = data['horario']
                            ponto_data['location_entrada'] = data['location']
                        else:
                            ponto_data['horario_saida'] = data['horario']
                            ponto_data['location_saida'] = data['location']
                        ponto_data['justificativa'] = data['justificativa']
                        db.seek(0)
                        json.dump(pontos_db, db, indent=4)
                        db.truncate()
                        response = jsonify({'message': 'ponto ajustrado', 'status_code': 200}), 200
                        return response
                response = jsonify({'message': 'data não encontrada/registrada', 'status_code': 404}), 404
                return response


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
