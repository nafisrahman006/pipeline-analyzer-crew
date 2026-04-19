from crewai.tools import BaseTool
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import os


class SendSlackNotificationTool(BaseTool):
    name: str = "send_slack_notification"
    description: str = (
        "Sends a formatted notification message to a Slack channel. "
        "Input: message (string). Uses SLACK_CHANNEL env var."
    )

    def _run(self, message: str) -> str:
        token = os.getenv("SLACK_BOT_TOKEN")
        channel = os.getenv("SLACK_CHANNEL", "#devops-alerts")

        if not token:
            return f"[MOCK] Slack notification sent to {channel}:\n{message}"

        client = WebClient(token=token)
        try:
            client.chat_postMessage(
                channel=channel,
                text=message,
                blocks=[
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": message}
                    }
                ]
            )
            return f"Notification sent to {channel}"
        except SlackApiError as e:
            return f"Slack error: {e.response['error']}"
