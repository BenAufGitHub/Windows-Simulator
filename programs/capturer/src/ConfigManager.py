from genericpath import isfile
import pickle
from os import path
import os


def filename():
    return "./resources/setting.cfg"

def savepath():
    return "./resources/recordings/"


# ====== setup =====>

def get_standard_settings():
    return {
        "Version: 1.0.0."
        "recording": None,
        "simulation": None,
        "recordingList": set(),
    }


def init_config_file():
    obj = get_standard_settings()
    with open(filename(), 'wb') as f: 
        pickle.dump(obj, f)


def init_if_new():
    if path.isfile(filename()): return
    init_config_file()


def load():
    data = None
    with open(filename(), 'rb') as f: 
        data = pickle.load(f)
    return data

def write(obj):
    with open(filename(), 'wb') as f: 
        pickle.dump(obj, f)

# <==== setupt =====

def save_file_exists(name):
    directory = "./resources/recordings/"
    filename = f"{name}.json"
    return filename in os.listdir(rf'{directory}')



def set_recording(name, obj=load()):
    init_if_new()
    obj["recording"]=f"{name}.json"
    write(obj)
    if save_file_exists(name):
        return "Careful"
    return "Done"


def create_new_recording(name):
    obj = load()
    set_recording(name, obj=obj)
    append_recording(obj, name)
    if save_file_exists(name):
        return "Careful"
    return "Done"


def append_recording(obj, name):
    if not hasattr(obj, "recordingList"):
        obj["recordingList"] = set()
    if name in obj["recordingList"]: return
    obj["recordingList"].add(name)
