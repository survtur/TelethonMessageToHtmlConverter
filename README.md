# TelethonMessageToHtmlConverter
Telegram/Telethon message with entities to HTML converter.
It needs `message` and `entities` fields from `telethon.tl.custom.message.Message` objects. Use it like this:

    for msg in tg_client.iter_messages(invite_link):
      converter = MessageToHtmlConverter(msg.message, msg.entities)
      html = converter.html
      
 Not all `MessageEntity*` items are processing. You may add new one to `_ENTITIES_TO_TAG` dict.
