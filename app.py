from flask import Flask, render_template, request, jsonify
import speech_recognition as sr
from dotenv import load_dotenv
import os
import firebase_admin
from firebase_admin import credentials, firestore
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains import LLMChain
from langchain_core.messages import AIMessage, HumanMessage

# Load environment and Firebase
load_dotenv()
app = Flask(__name__)
cred = credentials.Certificate("key.json")
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
db = firestore.client()

# OpenAI setup
llm = ChatOpenAI(model_name="gpt-3.5-turbo", openai_api_key=os.getenv("OPENAI_API_KEY"))

prompt = ChatPromptTemplate.from_messages([
    ("system", "You're a native speaker. Be brief, 1-2 sentence replies."),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}")
])
summarizer_prompt = ChatPromptTemplate.from_messages([
    ("system", "Rate the user's fluency 1-10, then give 3 specific improvement tips based on exact phrases."),
    MessagesPlaceholder(variable_name="chat_history")
])
translator_prompt = ChatPromptTemplate.from_messages([
    ("system", "Translate to English only."),
    ("human", "{input}")
])

chain = prompt | llm
summarizer = summarizer_prompt | llm
translator = translator_prompt | llm

chat_history = []

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/speak", methods=["POST"])
def speak():
    language = request.form.get("language")
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        audio = recognizer.listen(source, timeout=5)
    try:
        text = recognizer.recognize_google(audio, language=language)
        return jsonify({"text": text})
    except:
        return jsonify({"text": ""})

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json["text"]
    translated = translator.invoke({"input": user_input}).content

    response = chain.invoke({
        "input": user_input,
        "chat_history": chat_history
    })

    chat_history.extend([
        HumanMessage(content=user_input),
        AIMessage(content=response.content)
    ])

    return jsonify({
        "translated": translated,
        "response": response.content
    })

@app.route("/end", methods=["POST"])
def end():
    feedback = summarizer.invoke({"chat_history": chat_history}).content
    score = int(feedback[0])
    db.collection("gstavya").document("stats").update({"tot_score": firestore.Increment(score)})
    db.collection("gstavya").document("stats").update({"plays": firestore.Increment(1)})
    doc = db.collection("gstavya").document("stats").get().to_dict()
    avg = round(doc["tot_score"] / doc["plays"], 2)
    db.collection("gstavya").document("stats").update({"avg_score": avg})
    db.collection("gstavya").document("stats").update({"feedback": firestore.ArrayUnion([feedback])})
    return jsonify({"feedback": feedback})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('index'))
    return render_template('dashboard.html', user=session['user'])

@app.route('/login', methods=['POST'])
def login():
    id_token = request.json.get('idToken')
    try:
        decoded_token = auth.verify_id_token(id_token)
        user = auth.get_user(decoded_token['uid'])
        session['user'] = {'uid': user.uid, 'email': user.email}
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 401

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return jsonify({'success': True}), 200


if __name__ == "__main__":
    app.run(debug=True)
