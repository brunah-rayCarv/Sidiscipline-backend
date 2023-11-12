import json
import os

from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

user_database = os.path.join(os.path.dirname(__file__), 'database', 'user.json')


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
            user_id = len(data) + 1
        user = {
            'id': user_id,
            'name': data['name'],
            'email': data['email'],
            'password': data['password']
        }

        try:
            with open(user_database, 'r+', encoding='utf-8') as db:
                users_db = json.load(db)
                users_db.append(user)
                db.seek(0)
                json.dump(users_db, db, indent=4)
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


@app.route('/sidi_ponto/v1/users', methods=['GET'])
def users():
    with open(user_database, 'r', encoding='utf-8') as db:
        return json.load(db)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
