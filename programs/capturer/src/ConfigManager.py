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
        "Version": "1.0.0",
        "recording": None,
        "simulation": None,
        "recordingList": [],
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


def get_recording():
    init_if_new()
    obj= load()
    if not obj["recording"]:
        return None
    f = obj["recording"]
    return f[0: f.find(".json")]

def set_recording(name):
    init_if_new()
    obj=load()
    append_recording(obj, name)
    obj["recording"]=f"{name}.json"
    write(obj)
    if save_file_exists(name):
        return "Careful"
    return "Done"


def append_recording(obj, name):
    if not "recordingList" in obj:
        obj["recordingList"] = []
    if name in obj["recordingList"]: return
    obj["recordingList"].append(name)
    write(obj)


def get_record_list():
    init_if_new()
    obj = load()

    return add_imported_records(obj["recordingList"])


def get_simulation_list():
    directory = "./resources/recordings/"
    files = os.listdir(rf'{directory}')
    result = []
    for f in files:
        if f.find('.json') == -1: continue
        result.append(f[:f.find('.json')])
    return result
    


def add_imported_records(saved: list) -> list:
    result = list()
    result.extend(saved)
    directory = "./resources/recordings/"
    for filename in os.listdir(rf'{directory}'):
        if filename.find('.json') == -1:
            continue
        if not filename.replace('.json', '') in result:
            result.append(filename.replace('.json', ''))
    return result


def get_simulation():
    init_if_new()
    obj = load()
    if not obj["simulation"]:
        return None
    f = obj["simulation"]
    return f[0: f.find(".json")]
