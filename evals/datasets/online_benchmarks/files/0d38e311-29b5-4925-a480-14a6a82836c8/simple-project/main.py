from utils import greet_user
from models import User
from api import fetch_user_data
from config import API_KEY

def main():
    user = User("John Doe", 30)
    greet_user(user)
    user_data = fetch_user_data(user.name, API_KEY)
    print(f"User data: {user_data}")

if __name__ == "__main__":
    main()