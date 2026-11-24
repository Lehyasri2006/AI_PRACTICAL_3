from flask import Flask
from routes.tank_routes import tank_bp

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

# Register the modular routing blueprint
app.register_blueprint(tank_bp)

if __name__ == '__main__':
    # Serve on loopback address at port 8080
    app.run(debug=True, host='localhost', port=8080)
