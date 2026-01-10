# region imports
from AlgorithmImports import *
# endregion

# Your New Python File
class Logger:
    def __init__(self, log = None, debug = None):
        self.log = log
        self.debug = debug

    def print_message(self, message):
        if self.log: self.log(message)
        if self.debug: self.debug(message)

    def info(self, message:str):
        info_msg = f'INFO: {message}'
        self.print_message(info_msg)
    
    def error(self, message:str):
        info_msg = f'ERROR: {message}'
        self.print_message(info_msg)
        
    def format_datetime(self, datetime):
        return datetime.strftime("%Y-%m-%d, %H:%M:%S")

    def format_date(self, date):
        return date.strftime("%Y-%m-%d")
    
