"""Punto de entrada: python app.py  ->  http://localhost:5000/api/v1"""
from api import crear_app

app = crear_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
