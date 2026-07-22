from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5001)  # Usamos un puerto diferente (5001) para catalog service si corre en paralelo
