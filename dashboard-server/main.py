from app import create_app
from config import Config

app = create_app()

if __name__ == "__main__":
    print("Starting app...")
    app.run(debug=True, port=Config.PORT, host=Config.HOST)
