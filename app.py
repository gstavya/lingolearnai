import speech_recognition as sr
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import OpenAI
from dotenv import load_dotenv
import os
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import AIMessage, HumanMessage

import firebase_admin
from firebase_admin import firestore
from firebase_admin import credentials
from firebase_admin import db
import streamlit as st
import time

cred = credentials.Certificate('key.json')

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
db = firestore.client()

load_dotenv()
llm = ChatOpenAI(
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    model_name="gpt-3.5-turbo"
    )

chat_history = []
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You will serve as a native speaker in a specific language. You should know exactly what to talk about (e.g. cars, sports, recent events). Never ask them what they want to talk about. Guide the conversation with specific topics and questions but be brief! Your responses should be relatively short and specific. Max 1-2 sentences!!
            """,
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
    ]
)

prompt2 = ChatPromptTemplate.from_messages([
    ("system", """
    You will be given a conversation with a user and an AI assistant.
    Keep in mind that the conversation is transcribed from an audio, meaning that there will be some "ums" and "ahms." Do not judge the user based on these.
    Your goal is to help the user, as they are not fluent at the language.
    Start with a number from 1 to 10 rating the user's performance. This should be the first character of your response. 1 is horrible, didn't even respond, and 10 is excellent, fluent speaker level.
    Then, provide a list of 3 super specific things that they can improve. No general suggestions. Every suggestion must be followed by a citation of a part of the conversation. Make no suggestions about punctuation, capitalization, or accents, as again, this text you are given is not written by the user, but instead spoken and then written down.
     """),
    MessagesPlaceholder(variable_name="chat_history")
])

prompt3 = ChatPromptTemplate.from_messages([
    ("system", """
    You will be given text in a specific language and will have to return a response translating the text back into English.
    Only return the text back into English, nothing else at all.
    """),
    ("human", "{input}")
])

chain = prompt | llm

summarizer = prompt2 | llm

translator = prompt3 | llm

speech = sr.Recognizer()

import subprocess

def text_to_speech(language, command):
    voice = ""
    if language == "es":
        voice = "Diego"
    elif language == "fr":
        voice = "Aude"
    elif language == "hi":
        voice = "Kiyara"
    else:
        voice = "Daniel"
    subprocess.run(["say", "-v", voice, command])
def understand_voice(language):
    voice_text = ""
    with sr.Microphone() as source:
        print("I'm listening ... ")
        audio = speech.listen(source, 5)
    try:
        voice_text = speech.recognize_google(audio, language=language)
    except sr.UnknownValueError:
        pass
    except sr.RequestError as e:
        print('Network error.')
    return voice_text

st.set_page_config(page_title="Language Bot", layout="wide")
page = st.sidebar.selectbox("Navigation", ["Chat", "Statistics"])

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "language" not in st.session_state:
    st.session_state.language = ""
if "start_time" not in st.session_state:
    st.session_state.start_time = time.time()

import time
    
if page == "Chat":
    st.title("🌍 Practice Speaking a Language")

    if st.session_state.language == "":
        st.write("Click to set the language you want to practice:")

        if st.button("🎙️ Detect Language"):
            lang = understand_voice(language="en").lower()
            if "spanish" in lang:
                st.session_state.language = "es"
            elif "french" in lang:
                st.session_state.language = "fr"
            elif "hindi" in lang or "hendy" in lang:
                st.session_state.language = "hi"
            else:
                st.warning("Unsupported language. Please try again.")

    else:
        st.success(f"Practicing: {st.session_state.language.upper()}")

        if st.button("🔚 End Conversation"):
            end_time = time.time()
            elapsed = round(end_time - st.session_state.start_time, 2)
            db.collection("gstavya").document("stats").update({"time_spent": firestore.Increment(elapsed)})
            db.collection("gstavya").document("stats").update({"plays": firestore.Increment(1)})

            feedback = summarizer.invoke({"chat_history": st.session_state.chat_history}).content
            score = int(feedback[0])
            db.collection("gstavya").document("stats").update({"tot_score": firestore.Increment(score)})
            doc = db.collection("gstavya").document("stats").get().to_dict()
            avg = round(doc["tot_score"] / doc["plays"], 2)
            db.collection("gstavya").document("stats").update({"avg_score": avg})
            db.collection("gstavya").document("stats").update({"feedback": firestore.ArrayUnion([feedback])})

            st.success("Session ended. Feedback:\n\n" + feedback)
            st.stop()

        if st.button("🎤 Speak"):
            user_input = understand_voice(st.session_state.language)
            if user_input.strip() == "":
                st.warning("Didn't catch that.")
            else:
                st.chat_message("user").write(user_input)

                translated = translator.invoke({"input": user_input}).content
                if "bye" in translated.lower():
                    end_time = time.time()
                    elapsed = round(end_time - st.session_state.start_time, 2)
                    db.collection("gstavya").document("stats").update({"time_spent": firestore.Increment(elapsed)})
                    db.collection("gstavya").document("stats").update({"plays": firestore.Increment(1)})

                    feedback = summarizer.invoke({"chat_history": st.session_state.chat_history}).content
                    score = int(feedback[0])
                    db.collection("gstavya").document("stats").update({"tot_score": firestore.Increment(score)})
                    doc = db.collection("gstavya").document("stats").get().to_dict()
                    avg = round(doc["tot_score"] / doc["plays"], 2)
                    db.collection("gstavya").document("stats").update({"avg_score": avg})
                    db.collection("gstavya").document("stats").update({"feedback": firestore.ArrayUnion([feedback])})

                    st.success("Session ended. Feedback:\n\n" + feedback)
                    st.stop()

                response = chain.invoke({"input": user_input, "chat_history": st.session_state.chat_history})
                st.chat_message("assistant").write(response.content)

                text_to_speech(st.session_state.language, response.content)

                st.session_state.chat_history.extend([
                    HumanMessage(content=user_input),
                    AIMessage(content=response.content),
                ])

# Statistics Page
elif page == "Statistics":
    st.title("📊 Usage Statistics")
    doc = db.collection("gstavya").document("stats").get()
    if doc.exists:
        stats = doc.to_dict()
        st.metric("Total Time Spent (s)", stats.get("time_spent", 0))
        st.metric("Number of Sessions", stats.get("plays", 0))
        st.metric("Average Score", stats.get("avg_score", 0))

        with st.expander("📝 All Feedback"):
            feedbacks = stats.get("feedback", [])
            for f in feedbacks:
                st.markdown(f"- {f}")
    else:
        st.warning("No data found in Firebase.")