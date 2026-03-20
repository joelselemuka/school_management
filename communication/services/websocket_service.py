from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


class WebSocketService:

    @staticmethod
    def push(user_id, payload):

        channel_layer = get_channel_layer()

        async_to_sync(channel_layer.group_send)(
            f"user_{user_id}",
            {
                "type": "notify",
                "payload": payload
            }
        )
