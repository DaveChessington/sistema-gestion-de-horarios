from app.extensions import db


class Plantel(db.Model):
    __tablename__ = "planteles"

    id_plantel = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
