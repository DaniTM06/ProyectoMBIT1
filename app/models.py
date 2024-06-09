from . import db

class Picture(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    path = db.Column(db.String(255), nullable=False)
    date = db.Column(db.DateTime, nullable=False)

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tag = db.Column(db.String(50), nullable=False)
    picture_id = db.Column(db.String(36), db.ForeignKey('picture.id'), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
