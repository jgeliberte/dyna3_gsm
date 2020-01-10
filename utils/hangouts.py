import asyncio 
import hangups
import os
import sys

class HangoutNotification():
    def __init__(self):
        self.CONVERSATION_ID = 'UgyImgnHZYS2sAK-K_J4AaABAQ'
        self.REFRESH_TOKEN_PATH = '/home/pi/.cache/hangups/refresh_token.txt'
        try:
            self.cookies = hangups.auth.get_auth_stdin(self.REFRESH_TOKEN_PATH)
            self.client = hangups.Client(self.cookies)
        except Exception as err:
            print("--------------------")
            print(">> Network Error.")
            print(">> Script Exiting...")
            print("--------------------")
            sys.exit(0)

    def send_notification(self, message):
        self.client.on_connect.add_observer(lambda: asyncio.async(self.send_message(self.client, message)))
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.client.connect())

    @asyncio.coroutine
    def send_message(self, client, message):
        request = hangups.hangouts_pb2.SendChatMessageRequest(
            request_header=client.get_request_header(),
            event_request_header=hangups.hangouts_pb2.EventRequestHeader(
                conversation_id=hangups.hangouts_pb2.ConversationId(
                    id=self.CONVERSATION_ID
                ),
                client_generated_id=client.get_client_generated_id(),
            ),
            message_content=hangups.hangouts_pb2.MessageContent(
                segment=[hangups.ChatMessageSegment(message).serialize()],
            ),
        )
        try:
            yield from client.send_chat_message(request)
        finally:
            yield from client.disconnect()