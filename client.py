from dotenv import dotenv_values

from model.User import User
from ui.TUI import TUI
#-----------------------------------------MONGODB IMPORTS----------------------------------------------------------
from pymongo import MongoClient
from bson import ObjectId
#-------------------------------------PROMPT TOOLKIT IMPORTS-------------------------------------------------------
from prompt_toolkit.shortcuts import ProgressBar
from prompt_toolkit.styles import Style
from prompt_toolkit.shortcuts.progress_bar import formatters
from time import sleep

#-----------------------------------ENV VARIABLES AND CONSTANTS----------------------------------------------------
config = dotenv_values(".env")

MONGODB_CONNECT = config["MONGODB_CONNECT"]
#------------------------------------------------------------------------------------------------------------------
mongo_client = MongoClient(MONGODB_CONNECT)
mdb_db = mongo_client['chat_rooms']
mdb_users = mdb_db['user']

def main():
    id = ObjectId()
    client = User(id)
    T_G = input("Do you want to load the GUI or TUI? (G/T)\n").lower()
    if T_G == "g":
        print("The GUI is still under development.")
        style = Style.from_dict({
            'label': 'bg:#ffff00 #000000',
            'percentage': 'bg:#ffff00 #000000',
            'current': '#448844',
            'bar': '',
        })

        custom_formatters = [
            formatters.Label(),
            formatters.Text(': [', style='class:percentage'),
            formatters.Percentage(),
            formatters.Text(']', style='class:percentage'),
            formatters.Text(' '),
            formatters.Bar(sym_a='#', sym_b='#', sym_c='.'),
            formatters.Text('  '),
        ]

        with ProgressBar(style=style, formatters=custom_formatters) as pb:
            for i in pb(range(250), label='Opening using TUI'):
                sleep(.01)
        sleep(1)
    tui = TUI(client)
    tui.run()

if __name__ == "__main__":
    main()


