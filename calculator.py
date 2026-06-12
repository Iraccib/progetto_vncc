from flask import Flask, request, jsonify
from prometheus_flask_exporter import PrometheusMetrics
import time

app = Flask(__name__)
metrics = PrometheusMetrics(app) # Strumentazione automatica delle metriche di latenza

@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.json
    time.sleep(0.3)
    result = data['value'] * 2
    return jsonify({'result': result})

if __name__ == '__main__':
	app.run(host='0.0.0.0', port=5000)