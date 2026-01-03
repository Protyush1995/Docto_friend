from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from src.app import create_app


def verify_mongodb():
    """Check if MongoDB is reachable before starting Flask."""
    try:
        client = MongoClient(
            "mongodb://localhost:27017",
            serverSelectionTimeoutMS=1000
        )
        client.admin.command("ping")
        print("MongoDB is running and reachable.")
        return True

    except ConnectionFailure:
        print("MongoDB is NOT running or unreachable.")
        return False


def start_flask():
    """Start the Flask application."""
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000)


if __name__ == "__main__":
    print("Checking MongoDB connection...")
    if verify_mongodb():
        start_flask()
    else:
        print("Flask will NOT start because MongoDB is unavailable.")
