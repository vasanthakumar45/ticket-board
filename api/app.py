import os

import psycopg2
from flask import Flask, jsonify, request

app = Flask(__name__)

APP_ENV = os.getenv("APP_ENV", "local")
PRIORITIES = ("low", "medium", "high")


def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        dbname=os.getenv("DB_NAME", "tickets"),
        user=os.getenv("DB_USER", "ticketuser"),
        password=os.getenv("DB_PASSWORD", "ticketpass"),
        connect_timeout=3,
    )


def run_query(sql, params=None, fetch=False):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "CREATE TABLE IF NOT EXISTS tickets ("
                "id SERIAL PRIMARY KEY, "
                "title TEXT NOT NULL, "
                "priority TEXT NOT NULL DEFAULT 'medium', "
                "status TEXT NOT NULL DEFAULT 'open', "
                "created_at TIMESTAMP DEFAULT NOW())"
            )
            cur.execute(sql, params)
            rows = cur.fetchall() if fetch else None
        conn.commit()
        return rows
    finally:
        conn.close()


@app.route("/api/health")
def health():
    return jsonify(status="UP")


@app.route("/api/version")
def version():
    return jsonify(env=APP_ENV, version="v2")


@app.route("/api/tickets", methods=["GET"])
def list_tickets():
    try:
        rows = run_query(
            "SELECT id, title, priority, status FROM tickets ORDER BY id DESC LIMIT 50",
            fetch=True,
        )
        return jsonify(
            [{"id": r[0], "title": r[1], "priority": r[2], "status": r[3]} for r in rows]
        )
    except psycopg2.Error:
        return jsonify(error="Database not reachable"), 503


@app.route("/api/tickets", methods=["POST"])
def create_ticket():
    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()
    priority = str(data.get("priority", "medium")).lower()
    if not title:
        return jsonify(error="title is required"), 400
    if priority not in PRIORITIES:
        return jsonify(error="priority must be low, medium or high"), 400
    try:
        rows = run_query(
            "INSERT INTO tickets (title, priority) VALUES (%s, %s) RETURNING id",
            (title, priority),
            fetch=True,
        )
        return jsonify(id=rows[0][0], title=title, priority=priority, status="open"), 201
    except psycopg2.Error:
        return jsonify(error="Database not reachable"), 503


@app.route("/api/tickets/<int:ticket_id>/close", methods=["POST"])
def close_ticket(ticket_id):
    try:
        rows = run_query(
            "UPDATE tickets SET status = 'closed' WHERE id = %s RETURNING id",
            (ticket_id,),
            fetch=True,
        )
        if not rows:
            return jsonify(error="ticket not found"), 404
        return jsonify(id=ticket_id, status="closed")
    except psycopg2.Error:
        return jsonify(error="Database not reachable"), 503


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
