from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    session,
    redirect,
    url_for
)
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image
from pypdf import PdfReader
import os
import uuid
from io import BytesIO
import psycopg

from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from database import (
    get_db_connection,
    create_database,
    save_document_context,
    get_document_context
)

# ==========================================
# LOAD ENVIRONMENT
# ==========================================

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "nahor-development-secret"
)
# ==========================================
# LOGIN MANAGER
# ==========================================

login_manager = LoginManager()

login_manager.init_app(app)

login_manager.login_view = "login"
app.config["MAX_CONTENT_LENGTH"] = 15 * 1024 * 1024


# ==========================================
# GEMINI CLIENT
# ==========================================

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError(
        "GEMINI_API_KEY is missing from .env"
    )

client = genai.Client(
    api_key=api_key
)


CHAT_MODEL = "gemini-2.5-flash"


# ==========================================
# NAHOR INSTRUCTIONS
# ==========================================

SYSTEM_INSTRUCTION = """
You are NAHOR, a careful, helpful and transparent AI assistant.

IMPORTANT RULES:

1. Never invent information about a person.

2. Never invent someone's gender, university role, profession,
biography, achievements, political affiliation, or personal details.

3. When reliable information is unavailable, clearly say that
you cannot verify the information.

4. When Google Search grounding is enabled, actively use the provided
search results to answer the user's question.

5. For public usernames, public profiles, organizations, websites,
news, and other publicly available information, summarize any relevant
information found through search grounding.

6. Do not claim that you cannot browse or search the web when Google
Search grounding is enabled. If search results are insufficient, say
that you could not find enough reliable public information.

7. Never invent private information, hidden account data, private
messages, precise private locations, passwords, or other non-public data.

8. Distinguish clearly between verified public information and
unverified claims or similarly named accounts.
9. Do not claim that an uploaded photograph proves a person's identity.

10. Analyze images only from visible information.

11. Use conversation history for follow-up questions.

12. Be transparent about uncertainty.

13. Give clear and useful answers.

Your name is NAHOR.
"""


# ==========================================
# CONVERSATION MEMORY
# ==========================================

def get_history(chat_id):
    if not chat_id:
        return []

    connection = get_db_connection()
    messages = connection.execute(
        """
        SELECT role, message
        FROM messages
        WHERE user_id = %s AND chat_id = %s
        ORDER BY id DESC
        LIMIT 20
        """,
        (current_user.id, chat_id)
    ).fetchall()
    connection.close()

    messages = list(reversed(messages))
    return [
        {"role": row["role"], "message": row["message"]}
        for row in messages
    ]


def build_prompt(user_message, chat_id):
    history = get_history(chat_id)
    recent_history = history[-12:]
    conversation = ""

    for item in recent_history:
        conversation += f"{item['role']}: {item['message']}\n"

    return f"""
{SYSTEM_INSTRUCTION}

PREVIOUS CONVERSATION:

{conversation}

CURRENT USER MESSAGE:

{user_message}

NAHOR RESPONSE:
"""


def save_to_history(user_message, ai_response, chat_id):
    connection = get_db_connection()

    connection.execute(
        """
        INSERT INTO messages (user_id, chat_id, role, message)
        VALUES (%s, %s, %s, %s)
        """,
        (current_user.id, chat_id, "User", user_message[:4000])
    )

    connection.execute(
        """
        INSERT INTO messages (user_id, chat_id, role, message)
        VALUES (%s, %s, %s, %s)
        """,
        (current_user.id, chat_id, "NAHOR", ai_response[:8000])
    )

    chat = connection.execute(
        """
        SELECT title
        FROM chats
        WHERE id = %s AND user_id = %s
        """,
        (chat_id, current_user.id)
    ).fetchone()

    if chat and chat["title"] == "New Chat":
        new_title = user_message.strip()

        if len(new_title) > 40:
            new_title = new_title[:40] + "..."

        connection.execute(
            """
            UPDATE chats
            SET title = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND user_id = %s
            """,
            (new_title, chat_id, current_user.id)
        )
    else:
        connection.execute(
            """
            UPDATE chats
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND user_id = %s
            """,
            (chat_id, current_user.id)
        )

    connection.commit()
    connection.close()


# ==========================================
# PDF READER
# ==========================================

def read_pdf(pdf_file):

    reader = PdfReader(
        pdf_file.stream
    )

    text = ""

    for page in reader.pages:

        page_text = page.extract_text()

        if page_text:
            text += page_text + "\n"

    return text[:100000]

# ==========================================
# USER MODEL
# ==========================================

class User(UserMixin):

    def __init__(
        self,
        user_id,
        name,
        username,
        email
    ):

        self.id = str(user_id)
        self.name = name
        self.username = username
        self.email = email


@login_manager.user_loader
def load_user(user_id):

    connection = get_db_connection()

    user = connection.execute(
        """
        SELECT id, name, username, email
        FROM users
        WHERE id = %s
        """,
        (user_id,)
    ).fetchone()

    connection.close()

    if user:

        return User(
            user["id"],
            user["name"],
            user["username"],
            user["email"]
        )

    return None

# ==========================================
# REGISTER
# ==========================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not all([name, username, email, password]):

            return render_template(
                "register.html",
                error="Please fill in every field."
            )

        password_hash = generate_password_hash(password)

        connection = get_db_connection()

        try:

            cursor = connection.execute(
                """
                INSERT INTO users
                (name, username, email, password)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (
                    name,
                    username,
                    email,
                    password_hash
                )
            )

            user_id = cursor.fetchone()["id"]
            connection.commit()

        except psycopg.IntegrityError:

            connection.close()

            return render_template(
                "register.html",
                error="That username or email is already registered."
            )

        connection.close()

        user = User(
            user_id,
            name,
            username,
            email
        )

        login_user(user)

        return redirect(url_for("home"))

    return render_template("register.html")


# ==========================================
# LOGIN
# ==========================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":

        login_value = request.form.get(
            "login",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        connection = get_db_connection()

        user = connection.execute(
            """
            SELECT *
            FROM users
            WHERE username = %s
            OR email = %s
            """,
            (
                login_value,
                login_value.lower()
            )
        ).fetchone()

        connection.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            logged_user = User(
                user["id"],
                user["name"],
                user["username"],
                user["email"]
            )

            login_user(logged_user)

            return redirect(url_for("home"))

        return render_template(
            "login.html",
            error="Incorrect username, email, or password."
        )

    return render_template("login.html")


# ==========================================
# LOGOUT
# ==========================================

@app.route("/logout")
@login_required
def logout():

    logout_user()

    session.clear()

    return redirect(url_for("login"))

# ==========================================
# HOME PAGE
# ==========================================

@app.route("/")
@login_required
def home():

    return render_template(
        "index.html",
        user=current_user
    )

# ==========================================
# CHAT ENDPOINT
# ==========================================

@app.route("/chat", methods=["POST"])
@login_required
def chat():
    try:
        chat_id = request.form.get("chat_id", type=int)

        if not chat_id:
            return jsonify({
                "response": "Please create or select a chat first."
            }), 400

        connection = get_db_connection()
        owned_chat = connection.execute(
            "SELECT id FROM chats WHERE id = %s AND user_id = %s",
            (chat_id, current_user.id)
        ).fetchone()
        connection.close()

        if not owned_chat:
            return jsonify({"response": "Chat not found."}), 404

        user_message = request.form.get("message", "").strip()
        web_search = request.form.get("web_search", "false") == "true"
        image_file = request.files.get("image")
        pdf_file = request.files.get("pdf")

        if pdf_file:
            pdf_text = read_pdf(pdf_file)

            if not pdf_text.strip():
                return jsonify({
                    "response": "I couldn't extract readable text from this PDF."
                }), 400

            question = user_message or "Summarize this document clearly."

            save_document_context(
                current_user.id,
                chat_id,
                pdf_file.filename or "Uploaded PDF",
                pdf_text
            )

            pdf_prompt = f"""
{build_prompt(question, chat_id)}

The user uploaded a PDF.

DOCUMENT CONTENT:

{pdf_text}

Answer the question using the document.
If the answer is not contained in the document, say that clearly.
"""

            response = client.models.generate_content(
                model=CHAT_MODEL,
                contents=pdf_prompt
            )
            answer = response.text
            save_to_history(question, answer, chat_id)
            return jsonify({"response": answer, "type": "pdf"})

        if image_file:
            image = Image.open(image_file.stream)
            question = user_message or "Analyze this image carefully."

            response = client.models.generate_content(
                model=CHAT_MODEL,
                contents=[
                    build_prompt(question, chat_id),
                    image
                ]
            )
            answer = response.text
            save_to_history(question, answer, chat_id)
            return jsonify({"response": answer, "type": "image"})

        if not user_message:
            return jsonify({
                "response": "Please type a message or upload a file."
            }), 400

        prompt = build_prompt(user_message, chat_id)

        document_context = get_document_context(
            current_user.id,
            chat_id
        )

        if document_context:
            document_followup_terms = (
                "pdf", "document", "point", "section", "chapter", "page",
                "clause", "paragraph", "above", "earlier", "previous",
                "explain", "simpler", "shorter", "summarize", "summary",
                "this", "that", "it", "consent"
            )

            normalized_message = user_message.lower().strip()

            is_document_followup = any(
                term in normalized_message
                for term in document_followup_terms
            )

            if is_document_followup:
                prompt = f"""
You are NAHOR. The user is continuing a conversation about an uploaded PDF.

IMPORTANT INSTRUCTIONS:
- Treat the user's current message as a follow-up about the active PDF.
- Resolve references such as "point 3", "this", "that", "it", "the document",
  "make it shorter", and "explain it" from the PDF and recent conversation.
- Answer the question directly.
- Do not ask the user to choose an example if the reference can be resolved
  from the PDF or recent chat history.
- If a numbered point is requested, identify the relevant numbered point from
  the document or the immediately preceding assistant summary.
- If the requested information truly does not exist in the PDF or recent
  conversation, say so clearly.

ACTIVE PDF:
Document name: {document_context["document_name"]}

PDF CONTENT:
{document_context["document_text"]}

RECENT CONVERSATION AND CURRENT USER MESSAGE:
{prompt}
"""


        if web_search:
            grounding_tool = types.Tool(
                google_search=types.GoogleSearch()
            )
            search_config = types.GenerateContentConfig(
                tools=[grounding_tool]
            )
            response = client.models.generate_content(
                model=CHAT_MODEL,
                contents=prompt,
                config=search_config
            )
            answer = response.text
            save_to_history(user_message, answer, chat_id)
            return jsonify({"response": answer, "type": "web"})

        response = client.models.generate_content(
            model=CHAT_MODEL,
            contents=prompt
        )
        answer = response.text
        save_to_history(user_message, answer, chat_id)
        return jsonify({"response": answer, "type": "text"})

    except Exception as error:
        print("NAHOR ERROR:", error)
        return jsonify({
            "response": f"Something went wrong: {str(error)}"
        }), 500


# ==========================================
# CREATE NEW CHAT
# ==========================================

@app.route("/chats/new", methods=["POST"])
@login_required
def create_new_chat():

    connection = get_db_connection()

    cursor = connection.execute(
        """
        INSERT INTO chats
        (user_id, title)
        VALUES (%s, %s)
        RETURNING id
        """,
        (
            current_user.id,
            "New Chat"
        )
    )

    chat_id = cursor.fetchone()["id"]
    connection.commit()

    connection.close()

    return jsonify({
        "success": True,
        "chat_id": chat_id,
        "title": "New Chat"
    })

# ==========================================
# GET USER CHAT LIST
# ==========================================

@app.route("/chats", methods=["GET"])
@login_required
def get_chats():

    connection = get_db_connection()

    chats = connection.execute(
        """
        SELECT id, title, created_at, updated_at
        FROM chats
        WHERE user_id = %s
        ORDER BY updated_at DESC, id DESC
        """,
        (current_user.id,)
    ).fetchall()

    connection.close()

    return jsonify({
        "chats": [
            {
                "id": row["id"],
                "title": row["title"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            }
            for row in chats
        ]
    })

# ==========================================
# LOAD CHAT HISTORY
# ==========================================

@app.route("/history/<int:chat_id>", methods=["GET"])
@login_required
def history(chat_id):
    connection = get_db_connection()

    chat = connection.execute(
        "SELECT id FROM chats WHERE id = %s AND user_id = %s",
        (chat_id, current_user.id)
    ).fetchone()

    if not chat:
        connection.close()
        return jsonify({"error": "Chat not found."}), 404

    messages = connection.execute(
        """
        SELECT role, message
        FROM messages
        WHERE user_id = %s AND chat_id = %s
        ORDER BY id ASC
        """,
        (current_user.id, chat_id)
    ).fetchall()
    connection.close()

    return jsonify({
        "chat_id": chat_id,
        "messages": [
            {"role": row["role"], "message": row["message"]}
            for row in messages
        ]
    })


# ==========================================
# CLEAR CURRENT CHAT
# ==========================================

@app.route(
    "/clear",
    methods=["POST"]
)
@login_required
def clear_chat():

    data = request.get_json(
        silent=True
    ) or {}

    chat_id = data.get(
        "chat_id"
    )

    if not chat_id:

        return jsonify({
            "success": False,
            "error": "No active chat selected."
        }), 400


    connection = get_db_connection()


    chat = connection.execute(
        """
        SELECT id
        FROM chats
        WHERE id = %s
        AND user_id = %s
        """,
        (
            chat_id,
            current_user.id
        )
    ).fetchone()


    if not chat:

        connection.close()

        return jsonify({
            "success": False,
            "error": "Chat not found."
        }), 404


    connection.execute(
        """
        DELETE FROM messages
        WHERE user_id = %s
        AND chat_id = %s
        """,
        (
            current_user.id,
            chat_id
        )
    )


    connection.commit()

    connection.close()


    return jsonify({
        "success": True
    })

# ==========================================
# RENAME CHAT
# ==========================================

@app.route("/chats/<int:chat_id>/rename", methods=["POST"])
@login_required
def rename_chat(chat_id):

    data = request.get_json(silent=True) or {}
    title = data.get("title", "").strip()

    if not title:
        return jsonify({
            "success": False,
            "error": "Title cannot be empty."
        }), 400

    connection = get_db_connection()

    connection.execute(
        """
        UPDATE chats
        SET title = %s
        WHERE id = %s
        AND user_id = %s
        """,
        (
            title[:60],
            chat_id,
            current_user.id
        )
    )

    connection.commit()
    connection.close()

    return jsonify({
        "success": True
    })


# ==========================================
# DELETE CHAT
# ==========================================

@app.route("/chats/<int:chat_id>/delete", methods=["POST"])
@login_required
def delete_chat(chat_id):

    connection = get_db_connection()

    connection.execute(
        """
        DELETE FROM messages
        WHERE chat_id = %s
        AND user_id = %s
        """,
        (
            chat_id,
            current_user.id
        )
    )

    connection.execute(
        """
        DELETE FROM chats
        WHERE id = %s
        AND user_id = %s
        """,
        (
            chat_id,
            current_user.id
        )
    )

    connection.commit()
    connection.close()

    return jsonify({
        "success": True
    })

# ==========================================
# IMAGE GENERATION
# ==========================================

@app.route("/generate-image", methods=["POST"])
@login_required
def generate_image():

    try:

        data = request.get_json(silent=True) or {}

        prompt = data.get("prompt", "").strip()

        if not prompt:

            return jsonify({
                "error": "Please describe the image you want to create."
            }), 400


        response = client.models.generate_content(

            model="gemini-2.5-flash-image",

            contents=prompt,

            config=types.GenerateContentConfig(
                response_modalities=[
                    "TEXT",
                    "IMAGE"
                ]
            )

        )


        generated_text = ""

        generated_image_url = None


        for part in response.candidates[0].content.parts:

            if getattr(part, "text", None):

                generated_text += part.text


            inline_data = getattr(
                part,
                "inline_data",
                None
            )


            if inline_data and inline_data.data:

                file_name = (
                    str(uuid.uuid4())
                    + ".png"
                )


                save_path = os.path.join(
                    app.static_folder,
                    "generated",
                    file_name
                )


                generated_image = Image.open(
                    BytesIO(
                        inline_data.data
                    )
                )


                generated_image.save(
                    save_path
                )


                generated_image_url = (
                    "/static/generated/"
                    + file_name
                )


        if not generated_image_url:

            return jsonify({
                "error":
                "The image model did not return an image."
            }), 502


        return jsonify({

            "response":
                generated_text
                or
                "Image generated successfully.",

            "image_url":
                generated_image_url

        })

    except Exception as error:

        error_text = str(error)

        print(
            "IMAGE GENERATION ERROR:",
            error_text
        )

        if (
            "429" in error_text
            or
            "RESOURCE_EXHAUSTED" in error_text
            or
            "quota" in error_text.lower()
        ):

            return jsonify({
                "error":
                "Image generation is temporarily unavailable because the API quota has been reached. Please try again later."
            }), 429


        return jsonify({
            "error":
                "Image generation failed. Please try again."
        }), 500
       
# ==========================================
# INITIALIZE DATABASE
# ==========================================

create_database()


# ==========================================
# RUN APP
# ==========================================

if __name__ == "__main__":
    app.run(debug=True)