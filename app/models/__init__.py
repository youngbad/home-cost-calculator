from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

# Association table for shared wallets (Many-to-Many between User and Wallet)
wallet_shares = db.Table(
    "wallet_shares",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("wallet_id", db.Integer, db.ForeignKey("wallets.id"), primary_key=True),
)

# Association table for many-to-many between Expense and Tag
expense_tags = db.Table(
    "expense_tags",
    db.Column("expense_id", db.Integer, db.ForeignKey("expenses.id"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tags.id"), primary_key=True),
)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    owned_wallets = db.relationship("Wallet", backref="owner", lazy="dynamic", cascade="all, delete-orphan")
    shared_wallets = db.relationship("Wallet", secondary=wallet_shares, backref=db.backref("shared_users", lazy="dynamic"))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256")

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Wallet(db.Model):
    __tablename__ = "wallets"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.String(256), nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    expenses = db.relationship("Expense", backref="wallet", lazy="dynamic", cascade="all, delete-orphan")


class Tag(db.Model):
    __tablename__ = "tags"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)

    def to_dict(self):
        return {"id": self.id, "name": self.name}


class Expense(db.Model):
    __tablename__ = "expenses"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    category = db.Column(db.String(64), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    
    wallet_id = db.Column(db.Integer, db.ForeignKey("wallets.id"), nullable=False)

    tags = db.relationship("Tag", secondary=expense_tags, backref="expenses", lazy="subquery")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "amount": self.amount,
            "date": self.date.isoformat(),
            "notes": self.notes or "",
            "tags": [t.to_dict() for t in self.tags],
            "wallet_id": self.wallet_id
        }
