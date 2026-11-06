"""Add synthetic local demo records; never reset data or overwrite accounts."""
import argparse
from getpass import getpass
import os

from sqlalchemy import select
from sqlalchemy.engine import make_url

from app.auth.security import hash_password
from app.db.database import SessionLocal, get_settings
from app.db.models import Customer, Ticket, User


DEMO_EMAIL = 'admin@demo.example'


def seed_demo(db, password):
    if len(password) < 12:
        raise ValueError('Use a local demo password with at least 12 characters')
    with db.begin():
        if db.scalar(select(User.id).where(User.email == DEMO_EMAIL)) or db.scalar(
            select(Customer.id).where(Customer.email.in_(['ops@demo.example', 'ops@other-demo.example']))
        ):
            raise ValueError('Demo records already exist; refusing to overwrite')
        customer = Customer(name='Synthetic Acme Operations', email='ops@demo.example')
        other = Customer(name='Synthetic Other Tenant', email='ops@other-demo.example')
        db.add_all([customer, other])
        db.flush()
        admin = User(email=DEMO_EMAIL, customer_id=customer.id, role='admin', hashed_password=hash_password(password))
        own = Ticket(customer_id=customer.id, subject='Synthetic MFA recovery', description='Synthetic demo: help desk review required')
        foreign = Ticket(customer_id=other.id, subject='Synthetic other-tenant incident', description='Synthetic tenant isolation probe')
        db.add_all([admin, own, foreign])
        db.flush()
        result = {'ticket_id': own.id, 'foreign_ticket_id': foreign.id}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-local-demo', action='store_true', required=True)
    parser.parse_args()
    url = make_url(get_settings().database_url)
    if url.host not in {'localhost', '127.0.0.1', 'db'} or url.database != 'copilot_db':
        raise SystemExit('Refusing demo provisioning outside the documented local database')
    password = os.environ.get('DEMO_ADMIN_PASSWORD') or getpass('Choose a local demo password (12+ characters): ')
    try:
        with SessionLocal() as db:
            result = seed_demo(db, password)
    except Exception:
        raise SystemExit('Demo provisioning failed; verify migrations and that demo records do not already exist') from None
    print('Created synthetic records. Sign in as ' + DEMO_EMAIL + ' with your chosen password.')
    print('Own ticket:', result['ticket_id'], '; foreign test ticket:', result['foreign_ticket_id'])
    print('No model calls, document embeddings or external messages were generated.')


if __name__ == '__main__':
    main()
