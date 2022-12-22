const fs = require('fs')
    , ini = require('ini')


config_path = './resources/appConfigs.ini'


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