#!/usr/bin/env python3.6
#
#   FFF Focusbot Slack Plugin
#   Copyright (C) 2019 Jan Lindblad
# 
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
# 
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
# 
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import logging
import slack
import ssl as ssl_lib
import certifi
import datetime
import json

from yang_client import restconf_client

class focus_message:
  def __init__(self, channel):
    self.channel = channel
    self.username = "focusbot"
    self.icon_emoji = ":tornado:"
    self.timestamp = ""

  def get_message_payload(self, user_name, channel_name, shout_text, notifications_count):
    failed = not shout_text ## If no shout_text, create failure message
    channel_name_full = channel_name.replace('__','/')
    subscriber_count_txt = ""
    if notifications_count:
      subscriber_count_txt = f" ({notifications_count} subscribers)"
    return {
      "ts": self.timestamp,
      "channel": self.channel,
      "username": self.username,
      "icon_emoji": self.icon_emoji if failed==False else ":dizzy_face:",
      "blocks": [
        {
          "type": "section",
          "text": {
            "type": "mrkdwn", # FIXME: plain text?
            "text": (
              f"*Shouting message to {channel_name_full}{subscriber_count_txt}*\n\n{shout_text}" if failed==False else f"*Failed at shouting message to {channel_name_full}{subscriber_count_txt}*"
            ),
          },
        }
      ],
    }

@slack.RTMClient.run_on(event="reaction_added")
def update_emoji(**payload):
  """Update the onboarding welcome message after receiving a "reaction_added"
  event from Slack. Update timestamp for welcome message as well.
  """

  focusbot.log.debug(f"update_emoji payload={payload}")
  #{'rtm_client': <slack.rtm.client.RTMClient object at 0x103447828>, 'web_client': <slack.web.client.WebClient object at 0x10dc797b8>, 
  # 'data': {'user': 'UNYEJ90P4', 'item': {'type': 'message', 'channel': 'CPRN1AQN7', 'ts': '1572936913.000600'}, 
  # 'reaction': 'slightly_smiling_face', 'item_user': 'UNYEJ90P4', 'event_ts': '1572936964.000900', 'ts': '1572936964.000900'}}

  data = payload["data"]
  web_client = payload["web_client"]
  channel_id = focusbot.safe_str(data["item"]["channel"])
  user_id = focusbot.safe_str(data["user"])
  ts = focusbot.safe_str(data["item"]["ts"])
  reaction = focusbot.safe_str(data["reaction"])

  if(reaction == "loudspeaker"):
    user_obj = web_client.users_info(user=user_id)
    #print(f"UserObj={user_obj}")
    user_name = focusbot.safe_str(user_obj["user"]["name"])

    #print(f"update_emoji info channel_id={channel_id}")
    chan_obj = web_client.channels_info(channel=channel_id)
    #print(f"ChanObj={chan_obj}")
    #{'ok': True, 'channel': {'id': 'CPRN1AQN7', 'name': 'city__sweden__stockholm', 'is_channel': True, 'created': 1572709189, 'is_archived': False, 
    # 'is_general': False, 'unlinked': 0, 'creator': 'UNYEJ90P4', 'name_normalized': 'city__sweden__stockholm', 'is_shared': False, 
    # 'is_org_shared': False, 'is_member': True, 'is_private': False, 'is_mpim': False, 'last_read': '1572710812.000900', 
    # 'latest': {'client_msg_id': '494c94a7-f267-4010-ba98-18f80b0c3ff6', 'type': 'message', 'text': 'skulle', 'user': 'UNYEJ90P4', 
    # 'ts': '1572944129.002500', 'team': 'TPDE5536J', 'reactions': [{'name': 'loudspeaker', 'users': ['UNYEJ90P4'], 'count': 1}]}, 
    # 'unread_count': 33, 'unread_count_display': 32, 'members': ['UNYEJ90P4', 'UQ5CN126A'], 'topic': {'value': '', 'creator': '', 'last_set': 0}, 
    # 'purpose': {'value': 'Stockholm', 'creator': 'UNYEJ90P4', 'last_set': 1572709189}, 'previous_names': []}}
    channel_name = focusbot.safe_str(chan_obj["channel"]["name"])
    channel_name_short = channel_name.split('__')[-1]
    message_time = focusbot.safe_str(chan_obj["channel"]["latest"]["ts"])
    now = datetime.datetime.now()
    shout_time = now.strftime("%H:%M, %b %d")
    message_text = focusbot.safe_str(chan_obj["channel"]["latest"]["text"])
    if 'username' in focusbot.safe_str(chan_obj["channel"]["latest"]) and focusbot.safe_str(chan_obj["channel"]["latest"]["username"]) == 'focusbot':
      focusbot.log.warning(f"Focusbot: Refusing to shout out one of focusbot's own messages")
      return
    decorated_message_text = f"{user_name} to {channel_name_short}, {shout_time}\n{message_text}"

    #history = web_client.conversations_history(channel=channel_id, count=1, latest=ts)
    #history = web_client.conversations_history(channel=channel_id)
    #print(f"update_emoji history={history}")

    if(message_time == ts):
      # Run restconf action to send notif
      reply = focusbot.restconf_client.action(
        path="/registrar:registrar/registrar:notify",
        inputData={
          'registrar:input': {
            'target': channel_name.replace('__','/'),
            'message': decorated_message_text,
          }
        })
      #print(f"Notified, reply={reply.text}")
      jsonreply = json.loads(reply.content)
      #print(f"Notified, jsonreply={jsonreply}")
      if jsonreply["registrar:output"]["success"]:
        try:
          notifications_count = focusbot.safe_str(jsonreply["registrar:output"]["count"])
        except:
          notifications_count = None
        
        focus = focus_message(channel_id)
        message = focus.get_message_payload(user_name, channel_name, decorated_message_text, notifications_count)
        response = web_client.chat_postMessage(**message)
        # Store the message sent in onboarding_tutorials_sent
        if channel_id not in focusbot.shouts:
            focusbot.shouts[channel_id] = {}
        focusbot.shouts[channel_id][user_id] = message
      else:
        focusbot.log.error(f"Focusbot: Notification queueing failed:\n{jsonreply}")
        message = focus.get_message_payload(user_name, channel_name, None, notifications_count)
        response = web_client.chat_postMessage(**message)

    else:
      focusbot.log.warning(f"Focusbot: Reaction was not for latest message {message_time} != {ts}")

class focusbot:
  restconf_client = None
  shouts = {}
  log = None

  def focusbot.safe_str(unsafe_str):
    return unsafe_str.replace("'","")

  def run_server(self):
    focusbot.log = logging.getLogger()
    focusbot.log.setLevel(logging.DEBUG)
    focusbot.log.addHandler(logging.StreamHandler())

    focusbot.restconf_client = restconf_client(
      host="play.for.eco",
      port=47111,
      user=os.environ["REGISTRAR_USER"],
      password=os.environ["REGISTRAR_PASSWORD"])

    ssl_context = ssl_lib.create_default_context(cafile=certifi.where())
    slack_token = os.environ["SLACK_BOT_TOKEN"]
    rtm_client = slack.RTMClient(token=slack_token, ssl=ssl_context)
    rtm_client.start()

if __name__ == "__main__":
  focusbot().run_server()
