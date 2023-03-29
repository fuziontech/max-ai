import os
import logging
from typing import Optional

import openai

from dotenv import load_dotenv
from slack_bolt import App
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import create_engine, String, Column


load_dotenv()

## Initialize OpenAI
openai.api_key = os.environ.get("OPENAI_TOKEN")
models = [m.id for m in openai.Model.list()["data"]]
print(f"Available models: {', '.join(models)}")

## "gpt-4" and "gpt-3.5-turbo" are the two we'll use here

# Initializes your app with your bot token and signing secret
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
)

## Models

engine = create_engine("sqlite://chats.sqlite", echo=True)

class Base(DeclarativeBase):
    __abstract__ = True
    id = Column(String, primary_key=True)


class Chat(Base):
    __tablename__ = "chats"
    # slack, web, etc
    chat_product = Column(String)
    channel = Column(String)
    thread = Column(String)
    user = Column(String)



# Add functionality here
# @app.event("app_home_opened") etc
@app.event("app_home_opened")
def update_home_tab(client, event, logger):
    try:
        # views.publish is the method that your app uses to push a view to the Home tab
        client.views_publish(
            # the user that opened your app's app home
            user_id=event["user"],
            # the view object that appears in the app home
            view={
                "type": "home",
                "callback_id": "home_view",
                # body of the view
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*Welcome to your _App's Home_* :tada:",
                        },
                    },
                    {"type": "divider"},
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "This button won't do much for now but you can set up a listener for it using the `actions()` method and passing its unique `action_id`. See an example in the `examples` folder within your Bolt app.",
                        },
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "Click me!"},
                            }
                        ],
                    },
                ],
            },
        )

    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")


def summarize_thread(thread):
    prompt = f"""The following is a conversation in which the first person asks a question. Eventually, after the second person may ask some clairfying questions to gain more context, a solution may be reached.
    There may be multiple questions and solutions in the conversation, but only quesitons from the initial person should be considered relevant - questions from other people are just for
    clarifications about the first user's problem. Summarize each question and its solution succintly, excluding distinct user information but mostly just parsing out the relevant content,
    the question that was asked in detail including important context, and the eventual solution. If no solution seems to have been reached, say 'contact PostHog support'.
    Respond in the format of:
    Question: <question>
    Solution: <solution>
    Here is the conversation: {thread}"""
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}]
    )
    return completion.choices[0].message.content


@app.command("/summarize")
def handle_summarize_slash_command(ack, say, command):
    ack()
    say(text="Hi there")


@app.event("message")
def handle_message_events(body, logger, say):
    print("~~~~~~~~~hi~~~~")
    event_type = body["event"]["channel_type"]
    print(event_type)
    if event_type == "im":
        say("Hi there! I love direct messages")
    # event = body["event"]
    # if "thread_ts" in event:
    #   thread_ts = event["thread_ts"]
    #   thread = app.client.conversations_replies(channel=event["channel"], ts=thread_ts)
    #   print(thread)
    #   thread = [(msg['user'], msg['text']) for msg in thread['messages']]
    #   if "please summarize this" in event['text'].lower():
    #     summary = summarize_thread(thread)
    #     say(text=summary, thread_ts=thread_ts)


@app.event("app_mention")
def handle_app_mention_events(body, logger, say):
    logger.info(body)
    print(body)
    event = body["event"]
    if "thread_ts" in event:
        thread_ts = event["thread_ts"]
        thread = app.client.conversations_replies(
            channel=event["channel"], ts=thread_ts
        )
        print(thread)
        thread = [(msg["user"], msg["text"]) for msg in thread["messages"]]
        if "please summarize this" in event["text"].lower():
            summary = summarize_thread(thread)
            say(text=summary, thread_ts=thread_ts)


# Start your app
if __name__ == "__main__":
    app.start(port=int(os.environ.get("PORT", 3000)))
