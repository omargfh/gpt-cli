#!/usr/bin/env python3
from openai import OpenAI
import os
from sys import argv
import argparse as ap
from Crypto.Cipher import AES
import json
import base64

profiles = None
exitImmediate = True
with open(os.path.join(os.path.dirname(__file__), "gpt.profiles.json"), "r") as f:
    profiles = json.loads(f.read())

# Parse command line arguments
parser = ap.ArgumentParser(description="GPT-3.5 CLI")
parser.add_argument("-i", "--input", help="Chat file")
parser.add_argument("-m", "--model", help="Model", default="gpt-3.5-turbo")
parser.add_argument("-p", "--profile", help="Profile", default="unix-commands")
parser.add_argument("-c", "--chat", help="As chat session", default=False)
parser.add_argument("-q", "--query", help="Query", nargs=ap.REMAINDER)
parser.parse_args()

# Get the arguments
args = parser.parse_args()
chat = args.input
model = args.model
profile = args.profile
query = args.query
exitImmediate = not args.chat

# Validate the arguments
allowed_models = ["gpt-3.5-turbo", "gpt-4"]
if model not in allowed_models:
    parser.error(f"Invalid model name `{model}`. Must be one of {allowed_models}")
if profile not in profiles:
    parser.error(f"Invalid profile name `{profile}`. Must be one of {profiles.keys()}")

def pad(s, length=16):
    return (''.join([*s] + ["-"] * (length - len(s) % length)))[:length]

RoleMap={
    "User": "You",
    "Assistant": "Assistant",
    "Bot": "GPT"
}
class ChatFile():
    fpath = os.path.join(os.path.dirname(__file__), "chat.encrypted.json")
    def __init__(self, payload, fpath=None):
        self.payload = payload
        self.fpath = fpath or self.fpath

    @staticmethod
    def AsTempFile():
        if os.path.exists(ChatFile.fpath):
            return ChatFile.FromEncrypted(ChatFile.fpath)
        os.makedirs(os.path.dirname(ChatFile.fpath), exist_ok=True)
        with open(ChatFile.fpath, "w") as f:
            f.write(ChatFile.encrypt("[]"))
        return ChatFile([], fpath=None)

    @staticmethod
    def decrypt(fpath):
        with open(os.path.join(os.path.dirname(__file__), fpath), "r") as f:
            chat = f.read()
            # Decrypt the chat file
            key = pad(os.environ.get("OPENAI_API_KEY")).encode("utf-8")

            iv = bytes(16)
            cipher = AES.new(key, AES.MODE_CBC, iv)
            chat = chat.encode("utf-8")
            chat = base64.b64decode(chat)
            chat = cipher.decrypt(chat)
            chat = chat.decode("utf-8")
            chat = chat.rstrip("-")
            return chat

    @staticmethod
    def NewFile(fpath):
        with open(os.path.join(os.path.dirname(__file__), fpath + ".encrypted.json"), "w") as f:
            f.write(ChatFile.encrypt("[]"))
        return ChatFile([], fpath=fpath)

    @staticmethod
    def FromEncrypted(fpath):
        ffpath = fpath + ".encrypted.json"
        try:
            chat = ChatFile.decrypt(ffpath)
        except FileNotFoundError:
            return ChatFile.NewFile(fpath)

        try:
            chat = json.loads(chat)
            print("Restoring chat histoy [latest 10 messages]\n")
            for message in chat[-10:]:
                print(f"{RoleMap[message['role'].capitalize()]}: {message['content']}")
            return ChatFile(chat)
        except TypeError:
            raise ValueError("Chat file is corrupted")

    def add_message(self, role, content):
        self.payload.append({"role": role, "content": content})
        self.save()
        return self


    @staticmethod
    def encrypt(content):
        key = pad(os.environ.get("OPENAI_API_KEY")).encode("utf-8")
        iv = bytes(16)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        content = pad(content, length=len(content) + 16 - len(content) % 16)
        chatContent = cipher.encrypt(content.encode("utf-8"))
        return base64.b64encode(chatContent).decode("utf-8")

    def save(self):
        chatContent = ChatFile.encrypt(json.dumps(self.payload))
        with open(self.fpath, "w") as f:
            f.write(chatContent)
        return self

class DummyFile(ChatFile):
    @staticmethod
    def encrypt(content):
        return content

    @staticmethod
    def new():
        d = DummyFile([], fpath=None)
        d.fpath = "dummy"
        return d

    def save(self):
        return self

# Load the chat file
if chat:
    chat = ChatFile.FromEncrypted(chat)
elif not exitImmediate:
    chat = ChatFile.AsTempFile()
else:
    chat = DummyFile.new()

# Load the query
query = query and " ".join(query)

class OpenAICLI():
    def __init__(self, chat, model, profile):
        self.chat = chat
        self.model = model
        self.profile = profile
        self.client = OpenAI(
            # This is the default and can be omitted
            api_key=os.environ.get("OPENAI_API_KEY"),
        )

    def get_profile(self):
        return profiles[self.profile]

    def complete(self, query):
        stream = self.client.chat.completions.create(
            messages=[
                *self.chat.payload,
                *self.get_profile(),
                {
                    "role": "user",
                    "content": query,
                }
            ],
            model=self.model,
            stream=True
        )
        output = ""
        print(RoleMap["Assistant"] + ": ", end="")
        for chunk in stream:
            if type(chunk.choices[0].delta.content) == str:
                output += chunk.choices[0].delta.content
                print(chunk.choices[0].delta.content or "", end="")

        if output[-1] != "\n":
            output += "\n"
            print()
        return output
if query and not exitImmediate:
    print(RoleMap["User"] + ": " + query + "\n")
while(True):
    if query in ["exit", "quit", "q"]:
        break
    if query:
        response = OpenAICLI(chat, model, profile).complete(query)
        chat.add_message("assistant", response)
        chat.add_message("user", query)
        if exitImmediate:
            break
    query = input(RoleMap["User"] + ": ")
    chat.add_message("assistant", query)
