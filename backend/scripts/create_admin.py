from getpass import getpass

from sqlalchemy import select

from app.auth.security import hash_password
from app.db.database import SessionLocal
from app.db.models import Customer, User


def main():
    with SessionLocal() as db:
        customer_id = int(input("Customer ID: "))
        email = input("Admin email: ").strip()
        password = getpass("Admin password: ")

        if len(password) < 8:
            raise ValueError("Password must have at least 8 characters")

        if not db.get(Customer, customer_id):
            raise ValueError("Customer does not exist")

        if db.scalar(select(User).where(User.email == email)):
            raise ValueError("Email already registered")

        admin = User(
            email=email,
            hashed_password=hash_password(password),
            role="admin",
            customer_id=customer_id,
        )

        db.add(admin)
        db.commit()
        print("Admin account created")


if __name__ == "__main__":
    main()