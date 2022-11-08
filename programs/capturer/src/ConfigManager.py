import pickle
import os, shutil


def filename():
    return "./resources/setting.cfg"

def savepath():
    return "./resources/recordings/"

def capturepath():
    return "./resources/start_capture/"

def scpath():
    return "./resources/screenshots/"


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
    if os.path.isfile(filename()): return
    init_config_file()


def load():
    init_if_new()
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
    obj= load()
    if not obj["recording"]:
        return None
    f = obj["recording"]
    return f[0: f.find(".json")]

def set_recording(name):
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
    obj = load()
    return add_imported_records(obj["recordingList"])


def delete_recording(filename):
    obj = load()
    recording = f"{filename}.json"
    if recording != obj["recording"]:
        raise Exception("Only the selected recording can be deleted.")
    removeRecordingTraces(obj, filename, recording)
    removeRecordingFiles(filename, recording)
    write(obj)
    return "DONE"


def removeRecordingTraces(obj, filename, recording):
    try:
        obj["recording"] = None
        obj["recordingList"].remove(filename)
        if obj["simulation"] == recording:
            obj["simulation"] = None
    except ValueError:
        pass


def removeRecordingFiles(folder_name, file):
    ignoreNotFound( lambda: os.remove(savepath() + file))
    ignoreNotFound( lambda: os.remove(capturepath() + file))
    shutil.rmtree(scpath() + folder_name, ignore_errors=True)



def ignoreNotFound(io_function):
    try:
        return io_function()
    except FileNotFoundError:
        pass



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
    obj = load()
    if not obj["simulation"]:
        return None
    f = obj["simulation"]
    return f[0: f.find(".json")]

def set_simulation(name):
    obj = load()
    file = f"{name}.json"
    raise_if_not_found(file)
    obj["simulation"] = file
    write(obj)
    return "DONE"


def raise_if_not_found(file):
    directory = "./resources/recordings/"
    if not file in os.listdir(rf'{directory}'):
        raise IOError('File not found')