import sys

# noinspection PyUnresolvedReferences
import toDusbot
from toDusbot import bot, bot_users, groups, loop
# noinspection PyUnresolvedReferences
from toDusbot.modules import event_handlers, silent_mode
from toDusbot.strings import welcome_message
from toDusbot.stuff.bot_user import bot_user
# noinspection PyUnresolvedReferences
import toDusbot.stuff.helper_functions

if __name__ == "__main__":
    print("Starting Bot.")

    async def startup():
        for group_id in groups:
            users = await bot.get_participants(group_id)
            for user in users:
                print(user.id)
                if user.id not in bot_users:
                    bot_users[user.id] = bot_user()

    async def welcome():
        await bot.send_message(groups[0], welcome_message)

    loop.create_task(startup())
    loop.create_task(welcome())
    loop.run_forever()
