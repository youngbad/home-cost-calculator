from flask import Blueprint, jsonify, request
from app import db
from app.models import Tag

tags_bp = Blueprint("tags", __name__)


@tags_bp.route("/api", methods=["GET"])
def api_list():
    tags = Tag.query.order_by(Tag.name).all()
    return jsonify([t.to_dict() for t in tags])


@tags_bp.route("/api", methods=["POST"])
def api_create():
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip().lower()
    if not name:
        return jsonify({"error": "Tag name is required."}), 400
    if Tag.query.filter_by(name=name).first():
        return jsonify({"error": "Tag already exists."}), 409
    tag = Tag(name=name)
    db.session.add(tag)
    db.session.commit()
    return jsonify(tag.to_dict()), 201


@tags_bp.route("/api/<int:tag_id>", methods=["DELETE"])
def api_delete(tag_id):
    tag = db.session.get(Tag, tag_id)
    if tag is None:
        from flask import abort
        abort(404)
    db.session.delete(tag)
    db.session.commit()
    return jsonify({"message": "Deleted"}), 200
