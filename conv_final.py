from gtts import gTTS
import streamlit as st
import pygame
import re
import json
from PIL import Image
import os
import time
import tempfile

# Initialize pygame mixer
pygame.mixer.init()

def load_conversations_and_modifications():
    with open("data/conversations.json", "r", encoding='utf-8') as file:
        conversations_data = json.load(file)

    with open("data/chapter_modification.json", "r", encoding='utf-8') as file:
        modifications_data = json.load(file)

    modifications_dict = {modification['chapter']: modification for modification in modifications_data}

    return conversations_data, modifications_dict

knowledge_base, modifications_dict = load_conversations_and_modifications()

temp_files = []

def speak_text_mixed(text):
    if isinstance(text, str):
        clean_text = re.sub('<[^<]+?>', '', text)
        sentences = re.split(r'(?<=[^A-Z].[.?]) +(?=[A-Z])', clean_text)
        for sentence in sentences:
            if re.search("[\\uac00-\\ud7a3]", sentence):
                lang = 'ko'
            else:
                lang = 'en'
            tts = gTTS(text=sentence, lang=lang)
            with tempfile.NamedTemporaryFile(delete=True) as fp:
                temp_filename = f"{fp.name}.mp3"
                tts.save(temp_filename)
                pygame.mixer.music.load(temp_filename)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
    st.session_state.is_playing = False  

def find_next_bot_message(speakers_and_messages, selected_conversation):
    index_of_selected_conversation = speakers_and_messages.index(selected_conversation)
    if index_of_selected_conversation < len(speakers_and_messages) - 1:
        return speakers_and_messages[index_of_selected_conversation + 1]['message']
    else:
        return None

def prepare_speakers_and_messages(selected_chapter, chapter_conversations, modifications_dict):
    speakers_and_messages = [{'chapter': selected_chapter, 'speaker': message['speaker'], 'message': message['message']} 
                         for message in chapter_conversations 
                         if message['speaker'] == 'user']
    speakers_and_messages.insert(0, {'chapter': selected_chapter, 'speaker': "user", 'message': ""})

    if selected_chapter in modifications_dict:
        for add in modifications_dict[selected_chapter]['add']:
            speakers_and_messages.append({'chapter': selected_chapter, 'speaker': add['speaker'], 'message': add['message']})

        for remove in modifications_dict[selected_chapter]['remove']:
            speakers_and_messages = [i for i in speakers_and_messages if not (i['speaker'] == remove['speaker'] and i['message'] == remove['message'])]

    return speakers_and_messages

def handle_chapter_and_conversation_selection(knowledge_base):
    chapters = [data['chapter'] for data in knowledge_base]

    if "selected_chapter" not in st.session_state or st.session_state.selected_chapter not in chapters:
        st.session_state.selected_chapter = chapters[0]

    if st.session_state.selected_chapter in chapters:
        selected_chapter = st.selectbox(
            "Choose a chapter:",
            chapters,
            index=chapters.index(st.session_state.selected_chapter),
        )
        if st.session_state.selected_chapter != selected_chapter:
            st.session_state.selected_chapter = selected_chapter
            if "selected_message" in st.session_state:
                del st.session_state.selected_message
            if "chat_history" in st.session_state:
                del st.session_state.chat_history
            st.experimental_rerun()

    chapter_conversations = next((data['conversations'] for data in knowledge_base if data['chapter'] == st.session_state.selected_chapter), None)

    speakers_and_messages = prepare_speakers_and_messages(st.session_state.selected_chapter, chapter_conversations, modifications_dict)

    all_messages = [sm['message'] for sm in speakers_and_messages]
    if not all_messages:
        raise ValueError("all_messages is empty. Check the function prepare_speakers_and_messages.")

    if "" not in all_messages:
        raise ValueError("Empty string is not in all_messages. Check the function prepare_speakers_and_messages.")

    if "selected_message" not in st.session_state or st.session_state.selected_message not in all_messages:
        st.session_state.selected_message = all_messages[0]

    if st.session_state.selected_message in all_messages:
        selected_message = st.selectbox(
            "Choose a conversation:",
            all_messages,
            index=all_messages.index(st.session_state.selected_message) if st.session_state.selected_message != "" else 0,
        )
        if st.session_state.selected_message != selected_message:
            st.session_state.selected_message = selected_message
            st.experimental_rerun()

    if st.session_state.selected_chapter and st.session_state.selected_message and st.session_state.selected_message != "":
        chapter_name = st.session_state.selected_chapter
        chapter_data = next(chap_data for chap_data in knowledge_base if chap_data["chapter"] == chapter_name)
        speakers_and_messages = chapter_data["conversations"]

        return chapter_name, chapter_data, speakers_and_messages
    return None, None, None

def display_chat_history(chapter_data):
    selected_message = st.session_state.selected_message
    selected_conversation = []

    conversations = chapter_data["conversations"]
    for idx, conv in enumerate(conversations):
        if conv["message"] == selected_message:
            if idx + 1 < len(conversations):
                selected_conversation = [conversations[idx], conversations[idx+1]]
            break

    if not selected_conversation:
        st.write("Error: Selected message and the corresponding answer not found.")
        return

    if not hasattr(st.session_state, "chat_history"):
        st.session_state.chat_history = []

    st.session_state.chat_history.insert(0, {"conversation": selected_conversation, "is_new": True})

    for idx, conv in enumerate(st.session_state.chat_history):
        st.markdown("---")
        for i, msg in enumerate(conv["conversation"]):
            icon = "👩‍🦰" if msg['speaker'] == 'user' else "👩"
            message = msg['message'].replace('\n', '  \n')
            with st.container():
                if conv["is_new"]:
                    speak_text_mixed(message)
                st.markdown(f"{icon} {message}", unsafe_allow_html=True)

        if conv["is_new"]:
            st.session_state.chat_history[idx]["is_new"] = False

def main():
    st.title("English Again Conversations")

    _, chapter_data, speakers_and_messages = handle_chapter_and_conversation_selection(knowledge_base)

    if speakers_and_messages and chapter_data:
        display_chat_history(chapter_data)

def safe_delete(file):
    for _ in range(10):
        try:
            os.remove(file)
            print(f"Successfully deleted {file}")
            break
        except Exception as e:
            print(f"Failed to delete {file}: {e}")
            time.sleep(0.5)

if __name__ == "__main__":
    main()
    for file in temp_files:
        safe_delete(file)
