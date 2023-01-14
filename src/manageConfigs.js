const fs = require('fs')
    , ini = require('ini')


config_path = process.cwd() + '\\resources\\appConfigs.ini'


exports.createConfigs = (lang) => {
    data = {
        customizable: {
            language: lang,
            takeScreenshots: true,
            controlWindows: true
        }
    }
    fs.writeFileSync(config_path, ini.stringify(data))
}


exports.loadConfigs = () => {
    return ini.parse(fs.readFileSync(config_path, 'utf-8'))
}


exports.changeSettings = (lang, screnshots, ctrlWins) => {
    data = {
        customizable: {
            language: lang,
            takeScreenshots: screnshots,
            controlWindows: ctrlWins
        }
    }
    fs.writeFileSync(config_path, ini.stringify(data))
    return data;
}